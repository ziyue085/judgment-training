#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""判断力训练 — 确定性检查器 (judgment-training deterministic gate engine)

职责边界（严格）：
  本脚本只做**规则判定**。不做研究、不生成预测、不选参数、不提供答案。
  它把 SKILL.md 里的「铁律」翻译成可执行、可回归测试的代码。

三种模式：
  case      检查一个案例档案（准入闸门 / 隐含 CAGR / 概率逻辑 / 信息防火墙）
  reply     检查教练拟回复是否越界（抢答 / 剧透 / 问题过多 / 夸奖）
  postmortem 复盘裁决（过程质量 × 结果命中的四象限）

退出码：0 = 无 BLOCK；1 = 存在 BLOCK；2 = 输入错误。

无第三方依赖，Python 3.9+ 可用。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------- 常量 / 阈值

BLOCK, WARN, INFO = "BLOCK", "WARN", "INFO"
SEVERITY_ORDER = {BLOCK: 0, WARN: 1, INFO: 2}

MIN_HISTORY_POINTS = 3        # 历史序列最少时点
EXTREME_CAGR = 0.25           # 隐含 CAGR 绝对值超过此值 → 需罕见机制说明
TENSION_CAGR = 0.05           # 定性为"持平"但隐含 CAGR 超过此值 → 张力
UNIFORM_TOL = 0.02            # 统一概率判定容差
UNIFORM_MIN_COUNT = 3         # 至少几个指标同值才触发
POINT_PROB_HIGH = 0.80        # 点预测 / 过窄区间的概率上限
NARROW_REL_WIDTH = 0.05       # 区间相对宽度阈值
BASE_RATE_PROB_CAP = 0.70     # 缺基准率时允许的最高置信度
SUM_TOL = 0.05                # 互斥穷尽集合求和的容差
MAX_QUESTIONS_PER_TURN = 3    # 每轮最多提问数

# 教练越界词表
ANSWER_GIVING_PAT = re.compile(
    r"(预测|预计|会达到|将达到|后来|最终|结果是|实际上|真实结果|史实)"
    r"[^。；\n]{0,24}?\d"
)
SPOILER_VERB_PAT = re.compile(r"(后来|最终|结果是|真实|实际发生的|实际上)")


# ---------------------------------------------------------------- 数据结构

@dataclass
class Finding:
    code: str
    severity: str
    scope: str
    message: str
    detail: str = ""

    def __str__(self) -> str:
        d = f" | {self.detail}" if self.detail else ""
        return f"[{self.severity:5s}] {self.code:36s} @ {self.scope}: {self.message}{d}"


def sort_findings(findings):
    return sorted(findings, key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.scope, f.code))


def has_block(findings) -> bool:
    return any(f.severity == BLOCK for f in findings)


def codes(findings, severity=None):
    return [f.code for f in findings if severity is None or f.severity == severity]


# ---------------------------------------------------------------- 工具函数

def parse_year(value) -> int | None:
    """从 '2010'、'2010-12-31'、2010 中取出年份。"""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    m = re.match(r"^\s*(\d{4})", str(value))
    return int(m.group(1)) if m else None


def parse_date(value) -> date | None:
    if not value:
        return None
    try:
        y, m, d = (str(value).split("-") + ["1", "1"])[:3]
        return date(int(y), int(m), int(d))
    except Exception:
        return None


def forecast_years(case, indicator=None) -> float | None:
    """预测年数：优先显式 forecast_years，其次由截点与期限的年份差推导。"""
    if indicator and indicator.get("forecast_years"):
        return float(indicator["forecast_years"])
    if case.get("forecast_years"):
        return float(case["forecast_years"])
    y0 = parse_year(case.get("historical_cutoff"))
    y1 = parse_year(case.get("forecast_to"))
    if y0 and y1 and y1 > y0:
        return float(y1 - y0)
    d0, d1 = parse_date(case.get("historical_cutoff")), parse_date(case.get("forecast_to"))
    if d0 and d1 and d1 > d0:
        return (d1 - d0).days / 365.25
    return None


def implied_cagr(base, future, years):
    """隐含年均复合增速。基期或终值非正时返回 None（不得套用 CAGR）。"""
    if base in (None, 0) or future is None or not years:
        return None
    try:
        if float(base) <= 0 or float(future) <= 0:
            return None
        return (float(future) / float(base)) ** (1.0 / float(years)) - 1.0
    except Exception:
        return None


def point_estimate(ind) -> float | None:
    """取用于比较的单一数值：中心估计优先，否则区间中点，再否则点预测值。"""
    for key in ("center", "forecast_point"):
        if ind.get(key) is not None:
            return float(ind[key])
    lo, hi = ind.get("forecast_low"), ind.get("forecast_high")
    if lo is not None and hi is not None:
        return (float(lo) + float(hi)) / 2.0
    return None


def mid_of(ind):
    lo, hi = ind.get("forecast_low"), ind.get("forecast_high")
    if lo is not None and hi is not None:
        return (float(lo) + float(hi)) / 2.0
    return None


# ---------------------------------------------------------------- 检查：案例

def check_firewall(case) -> list[Finding]:
    """信息防火墙：截点之后公开的材料不得进入本轮预测。"""
    out: list[Finding] = []
    cutoff = parse_date(case.get("historical_cutoff"))
    if cutoff is None:
        out.append(Finding("CUTOFF_NOT_SET", BLOCK, "<case>",
                           "未设定历史截点，无法建立信息防火墙。"))
        return out

    for i, src in enumerate(case.get("sources") or []):
        scope = f"source[{i}]"
        d = parse_date(src.get("date"))
        if d is None:
            out.append(Finding("SOURCE_DATE_UNKNOWN", WARN, scope,
                               "材料发布日期不明；未确认截点前出处前不得用于预测。"))
            continue
        if d > cutoff:
            if src.get("usable") is False:
                out.append(Finding("FIREWALL_ISOLATED", INFO, scope,
                                   f"{src.get('date')} 晚于截点 {case.get('historical_cutoff')}，已正确隔离。"))
            else:
                out.append(Finding("FIREWALL_CONTAMINATION", BLOCK, scope,
                                   f"{src.get('date')} 发表于截点 {case.get('historical_cutoff')} 之后，不得进入本轮预测。",
                                   "只说明不可用，不解释其含义。"))

    for i, ind in enumerate(case.get("indicators") or []):
        d = parse_date(ind.get("base_source_date"))
        if d and d > cutoff:
            out.append(Finding("FIREWALL_CONTAMINATION", BLOCK, f"indicator[{i}].base_source_date",
                               f"基期数据来源日期 {ind.get('base_source_date')} 晚于截点。"))
    return out


def check_admission(case) -> list[Finding]:
    """预测准入门槛（十查中的八项硬门槛 + 提交字段完整性）。"""
    out: list[Finding] = []
    for i, ind in enumerate(case.get("indicators") or []):
        name = ind.get("name") or f"indicator[{i}]"
        scope = f"指标「{name}」"

        if ind.get("base_value") is None:
            out.append(Finding("GATE_BASE_MISSING", BLOCK, scope,
                               "缺少基期值。禁止进入正式数值预测。"))
        if not ind.get("base_unit"):
            out.append(Finding("GATE_UNIT_MISSING", BLOCK, scope, "缺少单位。"))
        if not ind.get("base_caliber"):
            out.append(Finding("GATE_CALIBER_MISSING", BLOCK, scope,
                               "缺少基期口径（价别/地域/人口分母等）。"))
        hist = ind.get("history") or []
        if len(hist) < MIN_HISTORY_POINTS:
            out.append(Finding("GATE_NO_HISTORY_SERIES", BLOCK, scope,
                               f"历史变化序列不足：{len(hist)} 个时点 < 要求 {MIN_HISTORY_POINTS} 个。"))
        if not ind.get("drivers"):
            out.append(Finding("GATE_DRIVER_MISSING", BLOCK, scope, "未识别主要驱动变量。"))
        if not ind.get("constraints"):
            out.append(Finding("GATE_CONSTRAINT_MISSING", BLOCK, scope, "未识别主要约束变量。"))
        if ind.get("stock_flow_relevant") and not ind.get("stock_flow_resolved"):
            out.append(Finding("GATE_STOCK_FLOW_UNRESOLVED", BLOCK, scope,
                               "涉及存量与流量，但未区分。储量是存量，产量是流量。"))
        if ind.get("quantity_price_relevant") and not ind.get("quantity_price_split"):
            out.append(Finding("GATE_QUANTITY_PRICE_UNRESOLVED", BLOCK, scope,
                               "金额类指标未拆分数量与价格。"))

        # 提交字段完整性（有预测值即视为已进入 CHECKS）
        if point_estimate(ind) is not None or ind.get("probability") is not None:
            for key, code, label in (
                ("reasoning", "LOCK_FIELD_MISSING", "推导过程"),
                ("failure_conditions", "LOCK_FIELD_MISSING", "失效条件"),
                ("counterargument", "LOCK_FIELD_MISSING", "最强反方解释"),
                ("missing_info", "LOCK_FIELD_MISSING", "当前最缺的信息"),
            ):
                if not ind.get(key):
                    out.append(Finding(code, BLOCK, scope, f"提交字段缺失：{label}。"))
            if not ind.get("proposition"):
                out.append(Finding("PROB_NO_PROPOSITION", BLOCK, scope,
                                   "未写成命题形式，概率无判定条件。"))
    return out


def check_quant(case) -> list[Finding]:
    """定量检查：隐含 CAGR、定性定量一致性、极端增速。"""
    out: list[Finding] = []
    years = forecast_years(case)
    for i, ind in enumerate(case.get("indicators") or []):
        name = ind.get("name") or f"indicator[{i}]"
        scope = f"指标「{name}」"
        base = ind.get("base_value")
        fut = point_estimate(ind)
        if base is None or fut is None:
            continue

        cagr = implied_cagr(base, fut, years)
        if cagr is None:
            out.append(Finding("IMPLIED_CAGR_NOT_APPLICABLE", INFO, scope,
                               "基期或终值非正，改用绝对变化量讨论，不得套用 CAGR。"))
            continue

        direction = ind.get("qualitative_direction")
        out.append(Finding("IMPLIED_CAGR_COMPUTED", INFO, scope,
                           f"隐含 CAGR = {cagr * 100:.2f}%/年（{years:g} 年）。"))

        if direction == "up" and fut < base:
            out.append(Finding("GATE_QUAL_QUANT_CONFLICT", BLOCK, scope,
                               f"定性判断为「增长」，但预测值 {fut:g} 低于基期 {base:g}。",
                               f"隐含 CAGR {cagr * 100:.2f}%/年，与定性判断矛盾。"))
        elif direction == "down" and fut > base:
            out.append(Finding("GATE_QUAL_QUANT_CONFLICT", BLOCK, scope,
                               f"定性判断为「下降」，但预测值 {fut:g} 高于基期 {base:g}。"))
        elif direction == "flat" and abs(cagr) > TENSION_CAGR:
            out.append(Finding("GATE_QUAL_QUANT_TENSION", WARN, scope,
                               f"定性判断为「基本持平」，但隐含 CAGR 达 {cagr * 100:.2f}%/年。",
                               "需解释幅度是否与'持平'相容。"))

        if abs(cagr) > EXTREME_CAGR and not ind.get("extreme_justified"):
            out.append(Finding("EXTREME_GROWTH_UNJUSTIFIED", WARN, scope,
                               f"隐含 CAGR 绝对值 {abs(cagr) * 100:.2f}% 超过 {EXTREME_CAGR * 100:.0f}%。",
                               "需给出罕见机制说明与基准率，否则建议下调或放宽区间。"))
    return out


def check_probabilities(case) -> list[Finding]:
    """概率结构：命题、量纲、统一概率、过窄区间、包含关系、互斥穷尽。"""
    out: list[Finding] = []
    inds = case.get("indicators") or []
    probs: list[tuple[str, float]] = []

    for i, ind in enumerate(inds):
        name = ind.get("name") or f"indicator[{i}]"
        scope = f"指标「{name}」"
        p = ind.get("probability")
        if p is None:
            if point_estimate(ind) is not None:
                out.append(Finding("PROB_MISSING", BLOCK, scope, "有预测值但没有概率。"))
            continue
        try:
            p = float(p)
        except Exception:
            out.append(Finding("PROB_OUT_OF_RANGE", BLOCK, scope, f"概率不是数值：{p!r}"))
            continue
        if not (0.0 <= p <= 1.0):
            out.append(Finding("PROB_OUT_OF_RANGE", BLOCK, scope, f"概率 {p} 不在 [0,1] 内。"))
            continue
        probs.append((name, p))

        lo, hi = ind.get("forecast_low"), ind.get("forecast_high")
        if lo is not None and hi is not None and float(lo) > float(hi):
            out.append(Finding("PROB_RANGE_INVERTED", BLOCK, scope,
                               f"区间上下限颠倒：low={lo} > high={hi}。"))

        # 点预测 / 过窄区间 + 高概率
        is_point = ind.get("forecast_form") == "point" or (lo is not None and lo == hi) \
            or (lo is None and hi is None and ind.get("center") is not None)
        if p >= POINT_PROB_HIGH and is_point:
            out.append(Finding("PROB_PRECISION", WARN, scope,
                               f"点预测概率 {p:.0%} ≥ {POINT_PROB_HIGH:.0%}。",
                               "要求给出合理区间并重新校准概率。"))
        elif p >= POINT_PROB_HIGH and lo is not None and hi is not None:
            base = ind.get("base_value")
            if base:
                rel = abs(float(hi) - float(lo)) / abs(float(base))
                if rel < NARROW_REL_WIDTH:
                    out.append(Finding("PROB_PRECISION", WARN, scope,
                                       f"区间相对宽度 {rel:.1%} < {NARROW_REL_WIDTH:.0%}，概率却达 {p:.0%}。",
                                       "精度超出数据本身能支撑的程度。"))

        if p >= 0.95 or p <= 0.05:
            out.append(Finding("PROB_EXTREME", WARN, scope,
                               f"极端概率 {p:.0%}：必须能说出什么观测会让你承认判断错误。"))

    # 统一概率
    if len(probs) >= UNIFORM_MIN_COUNT:
        vals = [p for _, p in probs]
        if max(vals) - min(vals) <= UNIFORM_TOL:
            out.append(Finding("PROB_UNIFORM", WARN, "<case>",
                               f"{len(probs)} 个指标概率几乎相同（{min(vals):.0%}—{max(vals):.0%}）。",
                               "不确定性来源不同，须逐个说明理由或重新校准。"))

    # 基准率
    if not case.get("base_rate_provided"):
        out.append(Finding("BASE_RATE_MISSING", WARN, "<case>",
                           "未提供任何基准率 / 可比参照。",
                           "允许继续，但须标记并相应降低置信度。"))
        high = [f"{n}={p:.0%}" for n, p in probs if p >= BASE_RATE_PROB_CAP]
        if high:
            out.append(Finding("BASE_RATE_MISSING_PROB_TOO_HIGH", WARN, "<case>",
                               f"缺基准率却给出 ≥{BASE_RATE_PROB_CAP:.0%} 的置信度：{', '.join(high)}。"))

    # 命题包含关系
    prop_p = {}
    for pr in case.get("propositions") or []:
        if pr.get("label") and pr.get("p") is not None:
            prop_p[pr["label"]] = float(pr["p"])
    for rel in case.get("prob_relations") or []:
        a, b = rel.get("a"), rel.get("b")
        pa, pb = prop_p.get(a), prop_p.get(b)
        if pa is None or pb is None:
            out.append(Finding("PROB_RELATION_UNRESOLVED", INFO, "<case>",
                               f"关系 {a} / {b} 缺少概率，未能校验。"))
            continue
        if rel.get("relation") == "subset" and pa > pb:
            out.append(Finding("PROB_LOGIC_SUBSET", BLOCK, "<case>",
                               f"P({a})={pa:.0%} > P({b})={pb:.0%}，但前者是后者的子集。",
                               "包含关系被破坏，先修概率结构再继续。"))

    # 互斥穷尽
    for es in case.get("exclusive_sets") or []:
        items = es.get("items") or []
        s = sum(float(it.get("p", 0)) for it in items)
        if abs(s - 1.0) > SUM_TOL:
            out.append(Finding("PROB_SUM", WARN, f"集合「{es.get('name')}」",
                               f"互斥穷尽集合概率合计 {s:.0%}，偏离 100% 超过 {SUM_TOL:.0%}。"))

    return out


def check_case(case) -> list[Finding]:
    """完整案例检查。返回排序后的 Finding 列表。"""
    out: list[Finding] = []
    out += check_firewall(case)
    out += check_admission(case)
    out += check_quant(case)
    out += check_probabilities(case)

    # 难度与结构的匹配
    lvl = case.get("difficulty")
    n_ind = len(case.get("indicators") or [])
    yrs = forecast_years(case)
    if lvl == 1:
        if n_ind > 2:
            out.append(Finding("LEVEL1_TOO_MANY_INDICATORS", WARN, "<case>",
                               f"Level 1 最多 2 个核心指标，当前 {n_ind} 个。"))
        if yrs and yrs > 3:
            out.append(Finding("LEVEL1_HORIZON_TOO_LONG", WARN, "<case>",
                               f"Level 1 期限建议 ≤3 年，当前 {yrs:g} 年。"))

    if not has_block(out):
        out.append(Finding("ADMISSION_OK", INFO, "<case>",
                           "无 BLOCK 级缺口，可进入下一状态。"))
    return sort_findings(out)


# ---------------------------------------------------------------- 检查：教练回复

def check_reply(state: str, text: str, cutoff=None, case=None) -> list[Finding]:
    """检查教练拟回复是否越界。研究/预测阶段适用。"""
    out: list[Finding] = []
    text = text or ""
    stage_locked = state in ("LOCK", "REVEAL", "POSTMORTEM", "PRINCIPLE", "ARCHIVED")
    cutoff_year = parse_year(cutoff) or (parse_year((case or {}).get("historical_cutoff")) if case else None)

    if not stage_locked:
        m = ANSWER_GIVING_PAT.search(text)
        if m:
            out.append(Finding("COACH_ANSWER_GIVING", BLOCK, f"state={state}",
                               f"尚未锁定预测就给出数值型结论：「{m.group(0)}」。",
                               "教练不得抢答或提供答案型资料。"))
        if cutoff_year:
            years = [int(y) for y in re.findall(r"(?:19|20)\d{2}", text)]
            future_years = [y for y in years if y > cutoff_year]
            if future_years and SPOILER_VERB_PAT.search(text):
                out.append(Finding("COACH_SPOILER_RISK", BLOCK, f"state={state}",
                                   f"回复涉及截点({cutoff_year})之后的年份 {sorted(set(future_years))} 并含剧透性表述。",
                                   "截点后信息不得透露。"))

    qmarks = len(re.findall(r"[?？]", text))
    numbered = len(re.findall(r"^\s*\d+[\.、)]", text, flags=re.M))
    q_count = max(qmarks, numbered)
    if q_count > MAX_QUESTIONS_PER_TURN:
        out.append(Finding("COACH_TOO_MANY_QUESTIONS", WARN, f"state={state}",
                           f"疑似提出 {q_count} 个问题，超过每轮上限 {MAX_QUESTIONS_PER_TURN}。",
                           "能问一个就不要问三个。"))

    if re.search(r"(太厉害了|非常棒|很棒|厉害|好想法|这个想法很好)", text):
        out.append(Finding("COACH_PRAISE", WARN, f"state={state}",
                           "出现夸奖用语；教练不因用户自信或表达而认同。"))

    if re.search(r"(我建议你|建议买入|综合来看我认为|给你一份完整分析)", text):
        out.append(Finding("COACH_ANALYST_TONE", WARN, f"state={state}",
                           "出现分析师口吻；教练只指缺口，不提供分析建议。"))

    if not out:
        out.append(Finding("REPLY_OK", INFO, f"state={state}", "未检测到越界。"))
    return sort_findings(out)


# ---------------------------------------------------------------- 复盘裁决

FLAG_TO_ATTRIBUTION = {
    "GATE_BASE_MISSING": "FACTUAL",
    "GATE_CALIBER_MISSING": "CALIBER",
    "GATE_UNIT_MISSING": "CALIBER",
    "GATE_NO_HISTORY_SERIES": "FACTUAL",
    "GATE_DRIVER_MISSING": "REASONING",
    "GATE_CONSTRAINT_MISSING": "REASONING",
    "GATE_STOCK_FLOW_UNRESOLVED": "MODEL",
    "GATE_QUANTITY_PRICE_UNRESOLVED": "MODEL",
    "GATE_QUAL_QUANT_CONFLICT": "REASONING",
    "BASE_RATE_MISSING": "BASE_RATE_IGNORED",
    "BASE_RATE_MISSING_PROB_TOO_HIGH": "BASE_RATE_IGNORED",
    "PROB_UNIFORM": "PROBABILITY",
    "PROB_PRECISION": "PROBABILITY",
    "PROB_EXTREME": "PROBABILITY",
    "PROB_LOGIC_SUBSET": "PROBABILITY",
    "PROB_SUM": "PROBABILITY",
    "PROB_NO_PROPOSITION": "PROBABILITY",
    "PROB_MISSING": "PROBABILITY",
    "EXTREME_GROWTH_UNJUSTIFIED": "PARAMETER",
    "FIREWALL_CONTAMINATION": "FACTUAL",
    "LOCK_FIELD_MISSING": "REASONING",
}

SEVERE_ATTRIBUTIONS = {"REASONING", "BASE_RATE_IGNORED", "CALIBER", "MODEL", "PARAMETER"}


def postmortem(case) -> dict:
    """复盘裁决：过程质量 × 结果命中 的四象限 + 错误归因。"""
    findings = case.get("checks", {}).get("findings") or []
    block_codes = [f["code"] for f in findings if f.get("severity") == BLOCK]
    warn_codes = [f["code"] for f in findings if f.get("severity") == WARN]
    explicit = (case.get("postmortem") or {}).get("process_flags")
    flags = list(explicit) if explicit is not None else block_codes

    # 错误归因覆盖 BLOCK 与 WARN 两级：缺基准率等 WARN 级缺陷也必须进入归因。
    attention = {}
    for c in list(flags) + list(warn_codes):
        a = FLAG_TO_ATTRIBUTION.get(c)
        if a:
            attention[a] = attention.get(a, 0) + 1

    outcome = case.get("outcome") or {}
    ind = (case.get("indicators") or [{}])[0]
    lo, hi = ind.get("forecast_low"), ind.get("forecast_high")
    actual = outcome.get("actual")
    hit = outcome.get("interval_hit")
    if hit is None and actual is not None and lo is not None and hi is not None:
        hit = float(lo) <= float(actual) <= float(hi)

    p = ind.get("probability")
    brier = None
    if hit is not None and p is not None:
        brier = (float(p) - (1.0 if hit else 0.0)) ** 2

    process_clean = not flags and not any(a in SEVERE_ATTRIBUTIONS for a in attention)
    if process_clean and hit:
        verdict = "PROCESS_GOOD_OUTCOME_HIT"
    elif process_clean and hit is False:
        verdict = "PROCESS_GOOD_OUTCOME_MISS"
    elif not process_clean and hit:
        verdict = "LUCKY_ACCURATE"
    else:
        verdict = "PROCESS_DEFECTIVE_OUTCOME_MISS"

    return {
        "verdict": verdict,
        "process_clean": process_clean,
        "process_flags": flags,
        "warn_codes": warn_codes,
        "error_attribution": sorted(attention.keys()),
        "interval_hit": hit,
        "brier": brier,
        "notes": {
            "LUCKY_ACCURATE": "结果正确不等于预测优秀：过程存在缺陷，命中应归因于运气。",
            "PROCESS_GOOD_OUTCOME_MISS": "结果落在低概率情景，但过程合理且概率诚实：不得判定过程失败。",
            "PROCESS_DEFECTIVE_OUTCOME_MISS": "过程有缺陷且未命中，按 error_attribution 分项复盘。",
            "PROCESS_GOOD_OUTCOME_HIT": "过程与结果均达标。",
        }[verdict],
    }


# ---------------------------------------------------------------- CLI

def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _iter_cases(payload, mode):
    """兼容两种输入：
       (a) 裸案例档案（含 indicators / historical_cutoff）
       (b) 测试夹具（外层含 steps[]）——取其中匹配 mode 的步骤
    返回 [(label, case_dict), ...]。
    """
    if isinstance(payload, dict) and isinstance(payload.get("steps"), list):
        out = []
        for i, step in enumerate(payload["steps"], 1):
            if step.get("mode", "case") == mode and isinstance(step.get("case"), dict):
                out.append((f"{payload.get('id', 'fixture')} · step{i}", step["case"]))
        if not out:
            raise ValueError(f"夹具中不存在 mode={mode} 的步骤")
        return out
    if mode == "case" or isinstance(payload, dict):
        return [("<case>", payload)]
    raise ValueError("无法识别的输入结构")


def _emit(payload, as_json):
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return payload


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="judge_checks", description="判断力训练确定性检查器")
    sub = ap.add_subparsers(dest="mode", required=True)

    p_case = sub.add_parser("case", help="检查案例档案")
    p_case.add_argument("path")
    p_case.add_argument("--json", action="store_true")

    p_reply = sub.add_parser("reply", help="检查教练回复是否越界")
    p_reply.add_argument("--state", required=True)
    p_reply.add_argument("--text", required=True)
    p_reply.add_argument("--cutoff")
    p_reply.add_argument("--json", action="store_true")

    p_pm = sub.add_parser("postmortem", help="复盘裁决")
    p_pm.add_argument("path")
    p_pm.add_argument("--json", action="store_true")

    args = ap.parse_args(argv)

    if args.mode == "case":
        payload = _load(args.path)
        targets = _iter_cases(payload, "case")
        worst = []
        payloads = []
        for label, case in targets:
            findings = check_case(case)
            worst += findings
            payloads.append({"step": label, "findings": [f.__dict__ for f in findings]})
            if not args.json:
                if len(targets) > 1:
                    print(f"### {label}")
                for f in findings:
                    print(f)
                print(f"-- block={len(codes(findings, BLOCK))} warn={len(codes(findings, WARN))} "
                      f"lockable={'YES' if not has_block(findings) else 'NO'}")
                print()
        if args.json:
            print(json.dumps(payloads, ensure_ascii=False, indent=2))
        return 1 if has_block(worst) else 0

    if args.mode == "reply":
        findings = check_reply(args.state, args.text, args.cutoff)
        if args.json:
            print(json.dumps([f.__dict__ for f in findings], ensure_ascii=False, indent=2))
        else:
            for f in findings:
                print(f)
        return 1 if has_block(findings) else 0

    if args.mode == "postmortem":
        payload = _load(args.path)
        targets = _iter_cases(payload, "postmortem")
        rc = 0
        results = []
        for label, case in targets:
            case = json.loads(json.dumps(case))
            if not case.get("checks", {}).get("findings"):
                case.setdefault("checks", {})["findings"] = [
                    f.__dict__ for f in check_case(case)
                ]
            result = postmortem(case)
            results.append({"step": label, **result})
            if not args.json:
                if len(targets) > 1:
                    print(f"### {label}")
                print(f"verdict               : {result['verdict']}")
                print(f"process_clean         : {result['process_clean']}")
                print(f"process_flags         : {', '.join(result['process_flags']) or '(none)'}")
                print(f"error_attribution     : {', '.join(result['error_attribution']) or '(none)'}")
                print(f"interval_hit          : {result['interval_hit']}")
                print(f"brier                 : {result['brier']}")
                print(f"notes                 : {result['notes']}")
                print()
            if not result["process_clean"]:
                rc = 1
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        return rc

    return 2


if __name__ == "__main__":
    sys.exit(main())
