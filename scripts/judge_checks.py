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

MIN_HISTORY_POINTS = 3        # 历史序列最少时点（趋势外推路径）
EXTREME_CAGR = 0.25           # 隐含 CAGR 绝对值超过此值 → 需罕见机制说明
TENSION_CAGR = 0.05           # 定性为"持平"但隐含 CAGR 超过此值 → 张力
UNIFORM_TOL = 0.02            # 统一概率判定容差
UNIFORM_MIN_COUNT = 3         # 至少几个指标同值才触发
POINT_PROB_HIGH = 0.80        # 点预测 / 过窄区间的概率上限
NARROW_REL_WIDTH = 0.05       # 区间相对宽度阈值
BASE_RATE_PROB_CAP = 0.70     # 缺基准率时允许的最高置信度
LIMITED_HISTORY_PROB_CAP = 0.70  # 历史不足但走替代机制时允许的最高置信度
SUM_TOL = 0.05                # 互斥穷尽集合求和的容差
MAX_QUESTIONS_PER_TURN = 3    # 每轮最多提问数
FRONT_STAGE_LIMIT = 3         # 前台一次最多呈现几条

# 三态字段：true / false / "unknown"。缺失 = 未检查，不得默认通过。
UNKNOWN = "unknown"
TRI_STATE_REQUIRED = ("stock_flow_relevant", "quantity_price_relevant")

# 评分命题（v0.2.3）：概率必须绑定到"它到底在赌哪件事"。
# 预测区间（forecast_low/high）与评分命题是**两回事**，允许不同，但都必须写下。
SCORED_EVENT_TYPES = ("interval", "threshold", "direction")
THRESHOLD_OPS = (">", ">=", "<", "<=")
DIRECTION_OPS = ("up", "down", "flat")
# 适用该字段的 kind（kind 缺失时视为 flow，从严）
FLOW_LIKE_KINDS = {"flow", "stock", "quantity"}
AMOUNT_LIKE_KINDS = {"flow", "stock"}
# 历史序列不足时的替代推导路径：声明后由 BLOCK 降级为 LIMITED_HISTORY(WARN)
ALT_HISTORY_BASES = {"alternative", "mechanism", "capacity", "order", "share", "contract", "admin"}

# 前台呈现优先级（v0.2.2）：让"一次只处理最关键 1—3 个"有确定实现
PRIORITY_ORDER = ["P0", "P1", "P2", "P3", "P4", "P5", "P6", "P7"]
PRIORITY = {
    # P0 信息污染 / 时间边界 —— 污染即整轮作废
    "CUTOFF_NOT_SET": "P0", "FIREWALL_CONTAMINATION": "P0",
    "FIREWALL_LOOKAHEAD_LEAKAGE": "P0", "SOURCE_DATE_UNKNOWN": "P0",
    "BASE_PUBLICATION_UNKNOWN": "P0",
    # P1 基期 / 口径 / 单位 / 字段未判定 / 期间错配
    "GATE_BASE_MISSING": "P1", "GATE_CALIBER_MISSING": "P1",
    "GATE_UNIT_MISSING": "P1", "GATE_FIELD_UNKNOWN": "P1",
    "GATE_FIELD_UNCHECKED": "P1", "REVEAL_TARGET_PERIOD_MISMATCH": "P1",
    # P2 定性定量明显矛盾
    "GATE_QUAL_QUANT_CONFLICT": "P2", "GATE_QUAL_QUANT_TENSION": "P2",
    # P3 推导链缺失
    "GATE_NO_HISTORY_SERIES": "P3", "LIMITED_HISTORY": "P3",
    "GATE_DRIVER_MISSING": "P3", "GATE_CONSTRAINT_MISSING": "P3",
    "LOCK_FIELD_MISSING": "P3", "PROB_NO_PROPOSITION": "P3", "PROB_MISSING": "P3",
    "PROB_SCORED_EVENT_MISSING": "P3", "PROB_SCORED_EVENT_INVALID": "P3",
    "REVEAL_FIELD_MISSING": "P3", "REVEAL_CALIBER_MISMATCH": "P3",
    "REVEAL_RECORD_MINIMAL": "P3",
    # P4 模型结构
    "GATE_STOCK_FLOW_UNRESOLVED": "P4", "GATE_QUANTITY_PRICE_UNRESOLVED": "P4",
    # P5 概率
    "PROB_UNIFORM": "P5", "PROB_PRECISION": "P5", "PROB_SUM": "P5",
    "PROB_LOGIC_SUBSET": "P5", "PROB_EXTREME": "P5", "PROB_OUT_OF_RANGE": "P5",
    "PROB_RANGE_INVERTED": "P5", "PROB_RELATION_UNRESOLVED": "P5",
    "PROB_SCORED_EVENT_MULTIPLE": "P5",
    "OUTCOME_SCOPE_AMBIGUOUS": "P5",
    # P6 基准率
    "BASE_RATE_MISSING": "P6", "BASE_RATE_MISSING_PROB_TOO_HIGH": "P6",
    "LIMITED_HISTORY_PROB_TOO_HIGH": "P6",
    # P7 优化项 / 信息类
    "LEVEL1_TOO_MANY_INDICATORS": "P7", "LEVEL1_HORIZON_TOO_LONG": "P7",
    "EXTREME_GROWTH_UNJUSTIFIED": "P7", "IMPLIED_CAGR_COMPUTED": "P7",
    "IMPLIED_CAGR_NOT_APPLICABLE": "P7", "ADMISSION_OK": "P7",
    "FIREWALL_ISOLATED": "P7", "REVEAL_SOURCE_TIER_LOW": "P7",
    "SOURCE_DATE_LEGACY_FIELD": "P7",
    "REVEAL_REVISION_UNRECORDED": "P7", "REVEAL_PERIOD_MISMATCH": "P7",
    "REVEAL_OK": "P7", "REPLY_OK": "P7", "COACH_PRAISE": "P7",
    "COACH_TOO_MANY_QUESTIONS": "P7", "COACH_ANALYST_TONE": "P7",
    "COACH_ANSWER_GIVING": "P0", "COACH_SPOILER_RISK": "P0",
    # 复盘裁决相关
    "CASE_INVALIDATED": "P0",
}

# 复盘：这些 case 级缺陷使整轮作废（不是"某个指标的问题"）
CASE_FATAL_CODES = {
    "CUTOFF_NOT_SET", "FIREWALL_CONTAMINATION", "FIREWALL_LOOKAHEAD_LEAKAGE",
}
# 复盘：结果记录的来源层级（权威度由高到低）
REVEAL_SOURCE_TIERS = {
    "city": ("统计公报", "统计年鉴", "统计数据库", "政府", "统计局"),
    "company": ("年报", "交易所", "10-K", "20-F", "法定披露", "audited"),
}

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


def priority_of(code: str) -> str:
    """发现的前台优先级（P0 最紧急）。未登记的一律 P7。"""
    return PRIORITY.get(code, "P7")


def sort_findings(findings):
    """按前台优先级排序：先 P0..P7，同级别内 BLOCK → WARN → INFO。

    v0.2.2：此前按 severity 排序，导致神木案例会把 36 条 BLOCK 平铺出来。
    规则优先级必须显式化，前台才能稳定地只处理最关键 1—3 条。
    """
    return sorted(findings, key=lambda f: (
        PRIORITY_ORDER.index(priority_of(f.code)),
        SEVERITY_ORDER.get(f.severity, 9),
        f.scope,
        f.code,
    ))


INFO_NOISE = {"ADMISSION_OK", "IMPLIED_CAGR_COMPUTED", "REPLY_OK", "FIREWALL_ISOLATED", "REVEAL_OK"}


def front_stage(findings, limit: int = FRONT_STAGE_LIMIT):
    """前台实际应该说的那几条：按优先级取前 N 个不同 code，跳过纯信息项。

    完整清单仍写入档案供复盘，不在前台摊给用户。
    """
    out, seen = [], set()
    for f in sort_findings(findings):
        if f.code in INFO_NOISE or f.code in seen:
            continue
        seen.add(f.code)
        out.append(f)
        if len(out) >= limit:
            break
    return out


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


FULL_DATE_RE = re.compile(r"^\s*(\d{4})-(\d{1,2})-(\d{1,2})\s*$")


def parse_full_date(value) -> date | None:
    """仅当输入是完整 `YYYY-MM-DD` 时返回 date；只有年份或年月则返回 None。

    必须能区分 `2010` 与 `2010-12-31`：前者不能用于按天精确计算期限。
    """
    if value is None:
        return None
    m = FULL_DATE_RE.match(str(value))
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def parse_date(value) -> date | None:
    """宽松解析（用于时间防火墙比较）：仅有年份时按 01-01 处理。"""
    if not value:
        return None
    d = parse_full_date(value)
    if d:
        return d
    try:
        parts = (str(value).split("-") + ["1", "1"])[:3]
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except Exception:
        return None


def forecast_years(case, indicator=None) -> float | None:
    """预测期限年数。

    v0.2.2 修复：此前优先使用年份差，`2010-12-31 → 2013-01-01` 会被算成 3 年，
    实际只有 732 天 ≈ 2.00 年 —— 会让隐含 CAGR 被系统性低估。
    现在：两端都是**完整日期**时，用 (d1 - d0).days / 365.25；
    只有在日期不完整（仅年份）时才退回年份差。
    """
    if indicator and indicator.get("forecast_years"):
        return float(indicator["forecast_years"])
    if case.get("forecast_years"):
        return float(case["forecast_years"])

    d0 = parse_full_date(case.get("historical_cutoff"))
    d1 = parse_full_date(case.get("forecast_to"))
    if d0 and d1:
        if d1 <= d0:
            return None
        return (d1 - d0).days / 365.25

    y0, y1 = parse_year(case.get("historical_cutoff")), parse_year(case.get("forecast_to"))
    if y0 and y1 and y1 > y0:
        return float(y1 - y0)

    # 退化：一端完整日期、一端只有年份
    dd0, dd1 = parse_date(case.get("historical_cutoff")), parse_date(case.get("forecast_to"))
    if dd0 and dd1 and dd1 > dd0:
        return (dd1 - dd0).days / 365.25
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


# ------------------------------------------------- 评分命题（v0.2.3）
#
# 规则（写死，不留给解释）：
#   1. 概率必须绑定到**唯一一个** primary scored event —— 「你到底在赌哪件事」。
#   2. 预测区间 `forecast_low/high` 与评分命题是两个不同的承诺，允许不同：
#        「我觉得会落在 480—520」   ← 区间
#        「我赌它 > 420，八成把握」  ← 评分命题 + 概率
#      这两句可以同时为真，也可以一真一假 —— 所以必须分开输出、分开裁决。
#   3. 每个指标只允许一个 primary scored event；多命题要拆成多指标
#      （架构不做 scored_predictions[]，见 docs/design-notes.md）。
#   4. 判定结果是三态：True / False / None。None = 无法判定，
#      **不等于未命中**，因此 Brier 在 None 时不出数。

def scored_event_of(ind) -> tuple:
    """取指标的 primary scored event。返回 (event_or_None, issue_code_or_None)。"""
    raw = ind.get("scored_event")
    if raw is None:
        return None, None
    if isinstance(raw, list):
        items = [x for x in raw if isinstance(x, dict)]
        if len(items) == 1 and len(raw) == 1:
            return items[0], None
        if not raw:
            return None, None
        return None, "PROB_SCORED_EVENT_MULTIPLE"
    if isinstance(raw, dict):
        return raw, None
    return None, "PROB_SCORED_EVENT_INVALID"


def validate_scored_event(ev) -> str | None:
    """校验评分命题的结构。合法返回 None，否则返回人话错误说明。"""
    if not isinstance(ev, dict):
        return "不是一个对象"
    t = str(ev.get("type") or "").strip().lower()
    if t not in SCORED_EVENT_TYPES:
        return (f"type 必须是 {'/'.join(SCORED_EVENT_TYPES)} 之一，当前为 {ev.get('type')!r}")
    if t == "interval":
        lo, hi = ev.get("low"), ev.get("high")
        if lo is None or hi is None:
            return "interval 必须同时给出 low 与 high"
        try:
            if float(lo) > float(hi):
                return f"interval 上下限颠倒：low={lo} > high={hi}"
        except (TypeError, ValueError):
            return "interval 的 low/high 必须是数值"
        return None
    if t == "threshold":
        if ev.get("value") is None:
            return "threshold 必须给出 value"
        try:
            float(ev.get("value"))
        except (TypeError, ValueError):
            return "threshold 的 value 必须是数值"
        if str(ev.get("op") or "").strip() not in THRESHOLD_OPS:
            return (f"threshold 的 op 必须是 {'/'.join(THRESHOLD_OPS)} 之一，"
                    f"当前为 {ev.get('op')!r}")
        return None
    # direction
    if str(ev.get("direction") or "").strip().lower() not in DIRECTION_OPS:
        return (f"direction 的 direction 必须是 {'/'.join(DIRECTION_OPS)} 之一，"
                f"当前为 {ev.get('direction')!r}")
    return None


def evaluate_scored_event(actual, scored_event, base_value=None):
    """判定结果是否命中**被评分的那一个命题**。返回 True / False / None。

    None = 无法判定（缺结果值、命题不完整、direction 缺基期）——
    必须与 False 严格区分：**未知 ≠ 未命中**。
    """
    if actual is None or not isinstance(scored_event, dict):
        return None
    if validate_scored_event(scored_event) is not None:
        return None
    try:
        a = float(actual)
    except (TypeError, ValueError):
        return None

    t = str(scored_event.get("type")).strip().lower()
    if t == "interval":
        return float(scored_event["low"]) <= a <= float(scored_event["high"])
    if t == "threshold":
        th = float(scored_event["value"])
        op = str(scored_event["op"]).strip()
        if op == ">":
            return a > th
        if op == ">=":
            return a >= th
        if op == "<":
            return a < th
        return a <= th
    # direction：相对基期值
    try:
        b = float(base_value)
    except (TypeError, ValueError):
        return None
    d = str(scored_event.get("direction")).strip().lower()
    if d == "up":
        return a > b
    if d == "down":
        return a < b
    return a == b


def period_matches_forecast_target(actual_period, forecast_to):
    """结果所属期末是否等于预测目标期。返回 True / False / None。

    v0.2.3：揭晓最容易出的错不是"值不对"，而是**值对错了时期**——
    拿 2012 年的数字去结算 2013 年的预测，命中判定整份作废。
    两端都是完整日期时要求同日；否则退化为同年比较（旧档案只写"2013"也兼容）。
    """
    if actual_period in (None, "") or forecast_to in (None, ""):
        return None
    ad, fd = parse_full_date(actual_period), parse_full_date(forecast_to)
    if ad and fd:
        return ad == fd
    ay, fy = parse_year(actual_period), parse_year(forecast_to)
    if ay is None or fy is None:
        return None
    return ay == fy


# ---------------------------------------------------------------- 检查：案例

def _publish_date(rec) -> tuple:
    """取一条记录中可用的"发布时间"及其字段名。新字段优先。"""
    for key in ("published_at", "source_date", "date"):
        if rec.get(key):
            return parse_date(rec.get(key)), key
    return None, None


def check_firewall(case) -> list[Finding]:
    """信息防火墙（v0.2.2 升级）。

    必须把两件事分开：
      - `data_period_end`  数据**描述**的统计期间结束 → 它"讲的是哪一段时间"
      - `published_at`     数据**真正公开**的时间     → 它"什么时候能被看到"

    最典型的历史盲测泄漏：数据所属期在截点之前，但截点当天根本还没公布。
    例如截点 2010-12-31，使用"2010 全年 GDP"——该值通常 2011 年才发布。
    仅比较 `data_year <= cutoff_year` 是**不够的**。
    """
    out: list[Finding] = []
    cutoff = parse_date(case.get("historical_cutoff"))
    if cutoff is None:
        out.append(Finding("CUTOFF_NOT_SET", BLOCK, "<case>",
                           "未设定历史截点，无法建立信息防火墙。"))
        return out

    # ---- 材料级 ----
    for i, src in enumerate(case.get("sources") or []):
        scope = f"source[{i}]"
        isolated = src.get("usable") is False
        pub, key = _publish_date(src)
        period_end = parse_date(src.get("data_period_end"))
        lab = src.get("published_at") or src.get("source_date") or src.get("date")

        if pub is None:
            if isolated:
                # v0.2.3 §11：已隔离材料不参与预测，发布时间不明只提示，**不得阻断**
                # （否则用户会因为"不敢删的旧材料"而卡死，被迫伪造时间）。
                out.append(Finding("SOURCE_DATE_UNKNOWN", INFO, scope,
                                   "已隔离材料未记录发布时间；不参与预测，暂不阻断。",
                                   "若要重新启用作依据，必须先补 published_at。"))
            elif src.get("available_at_cutoff") is False:
                out.append(Finding("FIREWALL_LOOKAHEAD_LEAKAGE", BLOCK, scope,
                                   "记录标注为截点前不可获得，却没有发布时间，无法核验。",
                                   "先补 published_at 再谈能不能用。"))
            else:
                # v0.2.3 §10：**正在使用**的材料没有发布时间 → 硬闸门。
                # 在此之前只是 WARN，导致"截点前可获得"从未被真正证明过。
                out.append(Finding("SOURCE_DATE_UNKNOWN", BLOCK, scope,
                                   "正在使用的材料没有发布时间，无法证明截点当天可获得。",
                                   "补 published_at（或 source_date）；否则只能把它隔离。"))
            continue

        if pub > cutoff:
            if isolated:
                out.append(Finding("FIREWALL_ISOLATED", INFO, scope,
                                   f"{lab} 晚于截点 {case.get('historical_cutoff')}，已正确隔离。"))
            elif period_end and period_end <= cutoff:
                out.append(Finding("FIREWALL_LOOKAHEAD_LEAKAGE", BLOCK, scope,
                                   f"数据期截止 {src.get('data_period_end')} 在截点前，"
                                   f"但发布时间 {lab} 在截点 {case.get('historical_cutoff')} 之后。",
                                   "所属期在截点之前 ≠ 截点当天已经公开。"))
            else:
                out.append(Finding("FIREWALL_CONTAMINATION", BLOCK, scope,
                                   f"{lab} 发表于截点 {case.get('historical_cutoff')} 之后，不得进入本轮预测。",
                                   "只说明不可用，不解释其含义。"))
        elif key != "published_at":
            out.append(Finding("SOURCE_DATE_LEGACY_FIELD", INFO, scope,
                               f"以旧字段 `{key}` 当作发布日期；建议改用 published_at + data_period_end。"))

    # ---- 指标级：基期值的公开时间 ----
    for i, ind in enumerate(case.get("indicators") or []):
        name = ind.get("name") or f"indicator[{i}]"
        scope = f"指标「{name}」"
        raw = ind.get("base_published_at") or ind.get("base_source_date")
        base_pub = parse_date(raw)
        if base_pub is not None and base_pub > cutoff:
            out.append(Finding("FIREWALL_CONTAMINATION", BLOCK, scope,
                               f"基期数据公开时间 {raw} 晚于截点 {case.get('historical_cutoff')}。",
                               "截点当天拿不到这个基期值。"))
        elif base_pub is None and ind.get("base_value") is not None:
            # v0.2.3 §12：有基期值却没有它的公开时间 —— 与"在用材料无发布时间"同级。
            # 此前只是 WARN，于是"这个基期值截点当天真能拿到吗"从未被证明。
            out.append(Finding("BASE_PUBLICATION_UNKNOWN", BLOCK, scope,
                               "有基期值，但未记录该值的公开时间，无法证明截点当天可获得。",
                               "补 base_published_at（或 base_source_date）。"))
    return out


def indicator_kind(ind) -> str:
    """指标类型；缺失时从严视为 flow（金额/流量类）。"""
    return str(ind.get("kind") or "flow").strip().lower()


def _is_unknown(value) -> bool:
    return isinstance(value, str) and value.strip().lower() == UNKNOWN


def _tri_state(ind, field: str, applicable: bool, scope: str, out: list) -> bool:
    """三态字段判定（true / false / "unknown"）。返回该字段是否为显式 true。

    v0.2.2 核心原则：**未检查 ≠ 已通过**。
      - 字段缺失      → `GATE_FIELD_UNCHECKED` (BLOCK)：不得默认 false
      - 字段 = unknown → `GATE_FIELD_UNKNOWN`   (BLOCK)：明确尚未判定
    因此不允许因为"用户没提存量流量"就自动填 false。
    """
    if not applicable:
        return False
    if field not in ind or ind.get(field) is None:
        out.append(Finding("GATE_FIELD_UNCHECKED", BLOCK, scope,
                           f"字段 `{field}` 未判定。未检查 ≠ 已通过。",
                           "教练必须显式判定 true 或 false；不能因为用户没提就默认 false。"))
        return False
    if _is_unknown(ind.get(field)):
        out.append(Finding("GATE_FIELD_UNKNOWN", BLOCK, scope,
                           f"字段 `{field}` 目前是 unknown —— 尚未判定，不得进入预测。",
                           "先查清楚，再谈预测。"))
        return False
    return bool(ind.get(field))


def _flag_unknown_or_unresolved(ind, field: str, scope: str, out: list, code: str, message: str):
    """relevant=true 时，resolved/split 必须显式为 true；unknown 单独报错。"""
    val = ind.get(field)
    if _is_unknown(val):
        out.append(Finding("GATE_FIELD_UNKNOWN", BLOCK, scope,
                           f"字段 `{field}` 目前是 unknown —— 尚未判定。"))
    elif val is not True:
        out.append(Finding(code, BLOCK, scope, message))


def check_admission(case) -> list[Finding]:
    """预测准入门槛（八项硬门槛 + 三态字段 + 提交字段完整性）。"""
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

        # ---- 历史序列：趋势路径需要 ≥3 点；替代机制路径可豁免但降级为 WARN ----
        hist = ind.get("history") or []
        basis = str(ind.get("history_basis") or "trend").strip().lower()
        alt_mech = str(ind.get("alternative_mechanism") or "").strip()
        if len(hist) < MIN_HISTORY_POINTS:
            if basis in ALT_HISTORY_BASES:
                if alt_mech:
                    out.append(Finding("LIMITED_HISTORY", WARN, scope,
                                       f"历史序列只有 {len(hist)} 个时点，未走趋势外推，"
                                       f"采用替代推导路径（{basis}）。",
                                       f"替代机制：{alt_mech}。须说明为何历史外推不适用，"
                                       f"并降低概率或扩大区间。"))
                    try:
                        p = float(ind.get("probability"))
                    except (TypeError, ValueError):
                        p = None
                    if p is not None and p >= LIMITED_HISTORY_PROB_CAP:
                        out.append(Finding("LIMITED_HISTORY_PROB_TOO_HIGH", WARN, scope,
                                           f"历史不足却给出 {p:.0%} 置信度"
                                           f"（≥{LIMITED_HISTORY_PROB_CAP:.0%}）。",
                                           "应降低概率或扩大区间。"))
                else:
                    out.append(Finding("GATE_NO_HISTORY_SERIES", BLOCK, scope,
                                       f"声称走替代推导路径（{basis}），却没有写清是什么机制。",
                                       "必须写明 alternative_mechanism，否则视同缺口。"))
            else:
                out.append(Finding("GATE_NO_HISTORY_SERIES", BLOCK, scope,
                                   f"历史变化序列不足：{len(hist)} 个时点 < 要求 "
                                   f"{MIN_HISTORY_POINTS} 个，且未声明替代推导机制。"))

        if not ind.get("drivers"):
            out.append(Finding("GATE_DRIVER_MISSING", BLOCK, scope, "未识别主要驱动变量。"))
        if not ind.get("constraints"):
            out.append(Finding("GATE_CONSTRAINT_MISSING", BLOCK, scope, "未识别主要约束变量。"))

        # ---- 三态字段（未判定不得视为通过） ----
        kind = indicator_kind(ind)
        if _tri_state(ind, "stock_flow_relevant", kind in FLOW_LIKE_KINDS, scope, out):
            _flag_unknown_or_unresolved(
                ind, "stock_flow_resolved", scope, out, "GATE_STOCK_FLOW_UNRESOLVED",
                "涉及存量与流量，但未区分。储量是存量，产量是流量。")
        if _tri_state(ind, "quantity_price_relevant", kind in AMOUNT_LIKE_KINDS, scope, out):
            _flag_unknown_or_unresolved(
                ind, "quantity_price_split", scope, out, "GATE_QUANTITY_PRICE_UNRESOLVED",
                "金额类指标未拆分数量与价格。")

        # ---- 提交字段完整性（有预测值即视为已进入 CHECKS） ----
        if point_estimate(ind) is not None or ind.get("probability") is not None:
            for key, label in (
                ("reasoning", "推导过程"),
                ("failure_conditions", "失效条件"),
                ("counterargument", "最强反方解释"),
                ("missing_info", "当前最缺的信息"),
            ):
                if not ind.get(key):
                    out.append(Finding("LOCK_FIELD_MISSING", BLOCK, scope,
                                       f"提交字段缺失：{label}。"))
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

        # ---- v0.2.3 §5：概率必须绑定到"同一个命题" ----
        # 没有这一步，Brier 只能拿预测区间硬凑，评的就不是用户真正押的那件事。
        ev, ev_issue = scored_event_of(ind)
        if ev_issue:
            out.append(Finding(ev_issue, BLOCK, scope,
                               "存在多个评分命题；每个指标只允许一个 primary scored_event。",
                               "把概率绑定到唯一的主命题，其余命题另立指标。"))
        elif ev is None:
            out.append(Finding("PROB_SCORED_EVENT_MISSING", BLOCK, scope,
                               "有概率，但没有说明这个概率绑定的是哪个命题（scored_event）。",
                               "补 scored_event：type=interval / threshold / direction。"))
        else:
            bad = validate_scored_event(ev)
            if bad:
                out.append(Finding("PROB_SCORED_EVENT_INVALID", BLOCK, scope,
                                   f"scored_event 不合法：{bad}。"))

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


REVEAL_REQUIRED = (("actual_value", "结果值"), ("actual_unit", "单位"),
                   ("actual_caliber", "口径"), ("actual_period", "期间"), ("source", "来源"))
REVEAL_RECORD_KEYS = ("actual_value", "actual_unit", "actual_caliber", "actual_period",
                      "source", "revision_status", "as_reported_then", "latest_revised")


def _find_indicator(case, name):
    for i, ind in enumerate(case.get("indicators") or []):
        if (ind.get("name") or f"indicator[{i}]") == name:
            return ind
    return None


def check_reveal(case) -> list[Finding]:
    """揭晓阶段核验（v0.2.2 新增）。

    揭晓不只是记录 `actual = 800`，必须同时记录单位、口径、期间、来源、公开时间与修订状态，
    并检查口径与预测所用的 base / proposition 是否一致。
    城市优先统计公报/年鉴/官方数据库；企业优先年报/交易所披露/法定文件。
    """
    out: list[Finding] = []
    names = _indicator_names(case)

    records = []
    explicit = case.get("outcomes")
    if isinstance(explicit, dict):
        for n in names:
            if isinstance(explicit.get(n), dict):
                records.append((f"结果「{n}」", explicit[n], _find_indicator(case, n)))
    elif case.get("outcome") is not None and names and len(names) <= 1:
        records.append((f"结果「{names[0]}」", case["outcome"], _find_indicator(case, names[0])))

    if not records:
        return out

    stage = str(case.get("stage") or "").upper()
    obj_type = str(case.get("object_type") or "city").lower()
    tier = REVEAL_SOURCE_TIERS.get(obj_type, REVEAL_SOURCE_TIERS["city"])

    for scope, rec, ind in records:
        formal = any(k in rec for k in REVEAL_RECORD_KEYS)
        if not formal:
            out.append(Finding("REVEAL_RECORD_MINIMAL", WARN, scope,
                               "结果记录只有一个裸数值，没有口径 / 来源 / 期间。",
                               "复盘算命中可以用，但正式揭晓必须补全口径与来源。"))
            if stage != "REVEAL":
                continue

        for key, label in REVEAL_REQUIRED:
            if rec.get(key) in (None, ""):
                out.append(Finding("REVEAL_FIELD_MISSING", BLOCK, scope,
                                   f"揭晓记录缺少{label}（{key}）。"))
        if rec.get("published_at") in (None, ""):
            out.append(Finding("REVEAL_FIELD_MISSING", WARN, scope, "揭晓记录缺少公开时间。"))
        if rec.get("revision_status") in (None, ""):
            out.append(Finding("REVEAL_FIELD_MISSING", WARN, scope,
                               "揭晓记录缺少修订状态（initial / revised / final / unknown）。"))

        src = str(rec.get("source") or "")
        if src and not any(t.lower() in src.lower() for t in tier):
            out.append(Finding("REVEAL_SOURCE_TIER_LOW", WARN, scope,
                               f"来源「{src}」不属于该对象类型的优先来源层级。",
                               f"{'城市' if obj_type == 'city' else '企业'}优先："
                               + " / ".join(tier) + "。其他来源只能作补充。"))

        if ind is not None:
            bc = str(ind.get("base_caliber") or "").strip()
            ac = str(rec.get("actual_caliber") or "").strip()
            if bc and ac and bc != ac:
                out.append(Finding("REVEAL_CALIBER_MISMATCH", BLOCK, scope,
                                   f"结果口径「{ac}」与基期口径「{bc}」不一致。",
                                   "口径不一致时命中判定无效：常住/户籍、当年价/不变价、全市/市辖区。"))
            bp = str(ind.get("base_period") or "").strip()
            ap = str(rec.get("actual_period") or "").strip()
            if bp and ap and bp == ap:
                out.append(Finding("REVEAL_PERIOD_MISMATCH", WARN, scope,
                                   f"结果期间「{ap}」与基期期间相同，疑似取错时点。"))

        if str(rec.get("revision_status") or "").lower() in ("revised", "final") \
                and not rec.get("as_reported_then"):
            out.append(Finding("REVEAL_REVISION_UNRECORDED", WARN, scope,
                               "结果标注为已修订 / 终值，但未保留当时公布值（as_reported_then）。",
                               "须同时保留「当时公布值」与「后来修订值」，不得只留对预测有利的那个。"))

        # v0.2.3 §14—§17：揭晓最隐蔽的错不是"值不对"，而是"值对错了年份"。
        # 旧实现只做 base_period == actual_period 的 WARN，完全不校验预测目标期。
        period_end = rec.get("actual_period_end") or rec.get("actual_period")
        match = period_matches_forecast_target(period_end, case.get("forecast_to"))
        if match is False:
            out.append(Finding("REVEAL_TARGET_PERIOD_MISMATCH", BLOCK, scope,
                               f"结果所属期末 {period_end} 与预测目标期 "
                               f"{case.get('forecast_to')} 不一致。",
                               "命中的前提是同一个时期：先对齐期间，再谈命中。"))

    if not out:
        out.append(Finding("REVEAL_OK", INFO, "<case>", "揭晓记录字段与口径核验通过。"))
    return out


def check_case(case) -> list[Finding]:
    """完整案例检查。返回按前台优先级排序后的 Finding 列表。"""
    out: list[Finding] = []
    out += check_firewall(case)
    out += check_admission(case)
    out += check_quant(case)
    out += check_probabilities(case)
    out += check_reveal(case)

    # 难度与结构的匹配
    lvl = case.get("difficulty")
    n_ind = len(case.get("indicators") or [])
    yrs = forecast_years(case)
    if lvl == 1:
        if n_ind > 2:
            out.append(Finding("LEVEL1_TOO_MANY_INDICATORS", WARN, "<case>",
                               f"Level 1 最多 2 个核心指标，当前 {n_ind} 个。"))
        # 容差 0.05 年：按 365.25 天换算时，含闰日的整年区间会略超 3.0000
        if yrs and yrs > 3 + 0.05:
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
    "LIMITED_HISTORY": "FACTUAL",
    "GATE_DRIVER_MISSING": "REASONING",
    "GATE_CONSTRAINT_MISSING": "REASONING",
    "GATE_FIELD_UNCHECKED": "REASONING",
    "GATE_FIELD_UNKNOWN": "REASONING",
    "GATE_STOCK_FLOW_UNRESOLVED": "MODEL",
    "GATE_QUANTITY_PRICE_UNRESOLVED": "MODEL",
    "GATE_QUAL_QUANT_CONFLICT": "REASONING",
    "GATE_QUAL_QUANT_TENSION": "REASONING",
    "BASE_RATE_MISSING": "BASE_RATE_IGNORED",
    "BASE_RATE_MISSING_PROB_TOO_HIGH": "BASE_RATE_IGNORED",
    "LIMITED_HISTORY_PROB_TOO_HIGH": "PROBABILITY",
    "PROB_UNIFORM": "PROBABILITY",
    "PROB_PRECISION": "PROBABILITY",
    "PROB_EXTREME": "PROBABILITY",
    "PROB_LOGIC_SUBSET": "PROBABILITY",
    "PROB_SUM": "PROBABILITY",
    "PROB_NO_PROPOSITION": "PROBABILITY",
    "PROB_SCORED_EVENT_MISSING": "PROBABILITY",
    "PROB_SCORED_EVENT_INVALID": "PROBABILITY",
    "PROB_SCORED_EVENT_MULTIPLE": "PROBABILITY",
    "PROB_MISSING": "PROBABILITY",
    "PROB_OUT_OF_RANGE": "PROBABILITY",
    "PROB_RANGE_INVERTED": "PROBABILITY",
    "EXTREME_GROWTH_UNJUSTIFIED": "PARAMETER",
    "FIREWALL_CONTAMINATION": "FACTUAL",
    "FIREWALL_LOOKAHEAD_LEAKAGE": "FACTUAL",
    "SOURCE_DATE_UNKNOWN": "FACTUAL",
    "BASE_PUBLICATION_UNKNOWN": "FACTUAL",
    "LOCK_FIELD_MISSING": "REASONING",
    "REVEAL_FIELD_MISSING": "CALIBER",
    "REVEAL_CALIBER_MISMATCH": "CALIBER",
    "REVEAL_TARGET_PERIOD_MISMATCH": "CALIBER",
    "REVEAL_PERIOD_MISMATCH": "CALIBER",
    "REVEAL_REVISION_UNRECORDED": "CALIBER",
}

VERDICT_NOTES = {
    "PROCESS_GOOD_OUTCOME_HIT": "过程与结果均达标。",
    "PROCESS_GOOD_OUTCOME_MISS": "结果落在低概率情景，但过程合理且概率诚实：不得判定过程失败。",
    "PROCESS_GOOD_OUTCOME_UNKNOWN": "过程合理，但结果尚未提供 / 尚未揭晓：不得视为失败，也不得视为成功。",
    "LUCKY_ACCURATE": "结果正确不等于预测优秀：过程存在缺陷，命中应归因于运气。",
    "PROCESS_DEFECTIVE_OUTCOME_MISS": "过程有缺陷且未命中，按 error_attribution 分项复盘。",
    "PROCESS_DEFECTIVE_OUTCOME_UNKNOWN": "过程缺陷已足以判定当时不应 LOCK —— 无需知道结果即可定论。",
    "CASE_INVALIDATED": "存在使整轮作废的 case 级缺陷（信息污染 / 未设截点），个别指标的过程评价失去意义。",
    "CASE_NO_INDICATORS": "案例未包含指标，无法复盘。",
    "CASE_MIXED": "各指标过程质量不一致：必须逐指标评价，不得用一个总分掩盖差异。",
    "CASE_CONSISTENT_CLEAN": "各指标过程质量一致（均无明显缺陷）。",
    "CASE_CONSISTENT_DEFECTIVE": "各指标过程质量一致（均存在缺陷）。",
}


def _scope_of(finding) -> str:
    return str(finding.get("scope") or "")


def _codes_of(findings, severity=None):
    return [f["code"] for f in findings if severity is None or f.get("severity") == severity]


def _attribution(codes_):
    att = {}
    for c in codes_:
        a = FLAG_TO_ATTRIBUTION.get(c)
        if a:
            att[a] = att.get(a, 0) + 1
    return att


def _quadrant(clean: bool, hit):
    """过程质量 × 结果 的六象限。hit=None 是"未知"，不是"未命中"。"""
    if clean:
        if hit is True:
            return "PROCESS_GOOD_OUTCOME_HIT"
        if hit is False:
            return "PROCESS_GOOD_OUTCOME_MISS"
        return "PROCESS_GOOD_OUTCOME_UNKNOWN"
    if hit is True:
        return "LUCKY_ACCURATE"
    if hit is False:
        return "PROCESS_DEFECTIVE_OUTCOME_MISS"
    return "PROCESS_DEFECTIVE_OUTCOME_UNKNOWN"


def _indicator_names(case):
    return [(ind.get("name") or f"indicator[{i}]") for i, ind in enumerate(case.get("indicators") or [])]


def _outcomes_for(case):
    """把结果记录映射到具体指标。

    v0.2.2 修复：此前任何 case 级 outcome 都作用在 indicators[0] 上，
    多指标案例实际只评价了第一个指标。

    规则：
      - `outcomes: {指标名: {...}}` 优先，逐指标映射
      - 单指标案例允许用 `outcome: {...}` 直接对应
      - 多指标却只给一个 `outcome` → 归属不明，一律按"结果未知"处理并给出 WARN
    """
    names = _indicator_names(case)
    out_map, warn = {}, None
    explicit = case.get("outcomes")
    if isinstance(explicit, dict):
        for n in names:
            if isinstance(explicit.get(n), dict):
                out_map[n] = explicit[n]
        return out_map, warn

    if case.get("outcome") is not None:
        if len(names) <= 1:
            if names:
                out_map[names[0]] = case["outcome"]
        else:
            pinned = (case.get("postmortem") or {}).get("outcome_scope")
            if isinstance(pinned, str) and pinned in names:
                out_map[pinned] = case["outcome"]
            else:
                warn = Finding("OUTCOME_SCOPE_AMBIGUOUS", WARN, "<case>",
                               f"案例有 {len(names)} 个指标，但只提供了一个 outcome，归属不明。",
                               "请改用 outcomes: {指标名: {...}}；否则全部按结果未知处理。")
    return out_map, warn


def postmortem(case) -> dict:
    """复盘裁决（v0.2.2）：逐指标裁决 + 作用域归因 + 案例级汇总。

    关键原则：
      - **作用域隔离**：某个指标的问题不得污染其他指标的过程评价。
        唯一例外是 case 级致命缺陷（信息污染 / 未设截点）——那会让整轮作废。
      - **未知 ≠ 未命中**：没有结果输入时给 `*_OUTCOME_UNKNOWN`，
        不得因为"没有命中记录"就判成 MISS。
    """
    findings = case.get("checks", {}).get("findings") or []
    indicators = case.get("indicators") or []
    ind_scopes = {f"指标「{n}」" for n in _indicator_names(case)}

    case_findings = [f for f in findings if _scope_of(f) not in ind_scopes]
    case_block = _codes_of(case_findings, BLOCK)
    case_warn = _codes_of(case_findings, WARN)
    case_fatal = sorted(set(case_block) & CASE_FATAL_CODES)
    case_att = _attribution(case_block + case_warn)

    out_map, scope_warn = _outcomes_for(case)
    if scope_warn is not None:
        case_warn = case_warn + [scope_warn.code]
        for k, v in _attribution([scope_warn.code]).items():
            case_att[k] = case_att.get(k, 0) + v

    indicator_results = []
    for i, ind in enumerate(indicators):
        name = ind.get("name") or f"indicator[{i}]"
        scope = f"指标「{name}」"
        ind_findings = [f for f in findings if _scope_of(f) == scope]
        blocks = _codes_of(ind_findings, BLOCK)
        warns = _codes_of(ind_findings, WARN)

        clean = (not blocks) and (not case_fatal)

        oc = out_map.get(name) or {}
        lo, hi = ind.get("forecast_low"), ind.get("forecast_high")
        # v0.2.3 §1：揭晓写的是 `actual_value`，复盘却一直只读 `actual` ——
        # 于是"揭晓成功、复盘却当没揭晓"（OUTCOME_UNKNOWN）。`actual` 仅作旧档案兼容。
        actual = oc.get("actual_value")
        if actual is None:
            actual = oc.get("actual")

        # 区间命中：用户对"落在哪一段"的承诺
        hit = oc.get("interval_hit")
        if hit is None and actual is not None and lo is not None and hi is not None:
            try:
                hit = float(lo) <= float(actual) <= float(hi)
            except (TypeError, ValueError):
                hit = None

        # v0.2.3 §8：评分命题命中是**另一个概念**，与区间命中分开输出。
        # 允许合法地出现 interval_hit=false / scored_event_hit=true。
        ev, _ = scored_event_of(ind)
        se_hit = oc.get("scored_event_hit")
        if se_hit is None:
            se_hit = evaluate_scored_event(actual, ev, ind.get("base_value"))

        try:
            prob = float(ind.get("probability"))
        except (TypeError, ValueError):
            prob = None
        # v0.2.3 §3/§7：Brier 必须针对"同一个概率命题" = scored_event。
        # 旧实现直接拿 interval_hit 代入，等于用一个用户没赌过的区间给概率打分。
        brier = (prob - (1.0 if se_hit else 0.0)) ** 2 \
            if (prob is not None and se_hit is not None) else None

        indicator_results.append({
            "indicator": name,
            "proposition": ind.get("proposition"),
            "probability": prob,
            "forecast_low": lo,
            "forecast_high": hi,
            "forecast_range": [lo, hi] if (lo is not None or hi is not None) else None,
            "actual_value": actual,
            "actual": actual,          # v0.2.1 兼容别名（新档案请用 actual_value）
            "interval_hit": hit,
            "scored_event": ev,
            "scored_event_hit": se_hit,
            # v0.2.3：裁决与 Brier 用**同一个**结果——评分命题优先。
            # 没有评分命题时才退回区间命中（老档案 / 无概率的纯区间预测）。
            "outcome_hit": se_hit if se_hit is not None else hit,
            "brier": None if brier is None else round(brier, 6),
            "block_codes": blocks,
            "warn_codes": warns,
            "error_attribution": sorted(_attribution(blocks + warns).keys()),
            "process_clean": clean,
            "verdict": _quadrant(clean, se_hit if se_hit is not None else hit),
            "note": oc.get("note") if isinstance(oc, dict) else None,
        })

    verdicts = [r["verdict"] for r in indicator_results]
    counts = {}
    for v in verdicts:
        counts[v] = counts.get(v, 0) + 1
    clean_flags = {r["process_clean"] for r in indicator_results}

    if case_fatal:
        overall = "CASE_INVALIDATED"
    elif not indicator_results:
        overall = "CASE_NO_INDICATORS"
    elif len(clean_flags) > 1:
        overall = "CASE_MIXED"
    elif clean_flags == {True}:
        overall = "CASE_CONSISTENT_CLEAN"
    else:
        overall = "CASE_CONSISTENT_DEFECTIVE"

    # 整轮归因 = case 级 + 全部指标（去重）；单指标归因见 indicator_results
    whole_att = dict(case_att)
    for r in indicator_results:
        for a in r["error_attribution"]:
            whole_att[a] = whole_att.get(a, 0) + 1

    first = indicator_results[0] if indicator_results else None
    top_verdict = first["verdict"] if first else overall
    resolved = [r for r in indicator_results if r["outcome_hit"] is not None]

    return {
        # ---- 兼容字段（v0.2.1 及以前的调用方）：单指标时语义不变 ----
        "verdict": top_verdict,
        "process_flags": sorted(set(case_block + [c for r in indicator_results for c in r["block_codes"]])),
        "warn_codes": sorted(set(case_warn + [c for r in indicator_results for c in r["warn_codes"]])),
        "error_attribution": sorted(whole_att.keys()),
        "interval_hit": first["interval_hit"] if first else None,
        "scored_event_hit": first["scored_event_hit"] if first else None,
        "brier": first["brier"] if (first and len(indicator_results) == 1) else None,
        "process_clean": bool(first["process_clean"]) if first else False,
        # ---- 新结构 ----
        "indicator_results": indicator_results,
        "case_level": {
            "block_codes": case_block,
            "warn_codes": case_warn,
            "case_fatal_codes": case_fatal,
            "error_attribution": sorted(case_att.keys()),
        },
        "case_summary": {
            "n_indicators": len(indicator_results),
            "n_hit": sum(1 for r in indicator_results if r["outcome_hit"] is True),
            "n_miss": sum(1 for r in indicator_results if r["outcome_hit"] is False),
            "n_unknown": sum(1 for r in indicator_results if r["outcome_hit"] is None),
            # 区间视角的命中计数，与评分命题视角分开（两者可合法不同）
            "n_interval_hit": sum(1 for r in indicator_results if r["interval_hit"] is True),
            "n_interval_miss": sum(1 for r in indicator_results if r["interval_hit"] is False),
            "verdict_counts": counts,
            "overall": overall,
            "outcome_status": (
                "PARTIAL" if 0 < len(resolved) < len(indicator_results)
                else "REVEALED" if indicator_results and len(resolved) == len(indicator_results)
                else "UNKNOWN"
            ),
        },
        "notes": VERDICT_NOTES.get(overall, "") if overall.startswith("CASE_") and overall in ("CASE_INVALIDATED", "CASE_NO_INDICATORS", "CASE_MIXED") else VERDICT_NOTES.get(top_verdict, ""),
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

    p_rv = sub.add_parser("reveal", help="揭晓记录核验（来源层级 / 口径 / 修订）")
    p_rv.add_argument("path")
    p_rv.add_argument("--json", action="store_true")

    args = ap.parse_args(argv)

    if args.mode == "case":
        payload = _load(args.path)
        targets = _iter_cases(payload, "case")
        worst = []
        payloads = []
        for label, case in targets:
            findings = check_case(case)
            worst += findings
            tops = front_stage(findings)
            payloads.append({"step": label,
                             "findings": [f.__dict__ for f in findings],
                             "front_stage": [f.__dict__ for f in tops]})
            if not args.json:
                if len(targets) > 1:
                    print(f"### {label}")
                for f in findings:
                    print(f)
                print(f"-- block={len(codes(findings, BLOCK))} warn={len(codes(findings, WARN))} "
                      f"lockable={'YES' if not has_block(findings) else 'NO'}")
                if tops:
                    print("-- 前台应只说（1—3 条，按优先级）:")
                    for f in tops:
                        print(f"   {priority_of(f.code)} | {f.message}")
                print()
        if args.json:
            print(json.dumps(payloads, ensure_ascii=False, indent=2))
        return 1 if has_block(worst) else 0

    if args.mode == "reveal":
        payload = _load(args.path)
        if isinstance(payload, dict) and isinstance(payload.get("steps"), list):
            cases = [s["case"] for s in payload["steps"] if isinstance(s.get("case"), dict)]
        else:
            cases = [payload]
        allf, dump = [], []
        for case in cases:
            findings = check_reveal(case)
            allf += findings
            dump.append({"findings": [f.__dict__ for f in findings]})
            if not args.json:
                for f in findings:
                    print(f)
        if args.json:
            print(json.dumps(dump, ensure_ascii=False, indent=2))
        return 1 if has_block(allf) else 0

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
                cs, cl = result["case_summary"], result["case_level"]
                print(f"case_summary.overall : {cs['overall']}")
                print(f"outcome_status       : {cs['outcome_status']}  "
                      f"(hit={cs['n_hit']} miss={cs['n_miss']} unknown={cs['n_unknown']})")
                if cl["case_fatal_codes"]:
                    print(f"case_fatal           : {', '.join(cl['case_fatal_codes'])}")
                if cl["block_codes"]:
                    print(f"case_level BLOCK     : {', '.join(sorted(set(cl['block_codes'])))}")
                print("--- 逐指标 ---")
                for r in result["indicator_results"]:
                    print(f"  {r['indicator']}")
                    print(f"    proposition : {r['proposition']}")
                    print(f"    probability : {r['probability']}")
                    print(f"    forecast    : {r['forecast_range']}")
                    print(f"    scored_event: {json.dumps(r['scored_event'], ensure_ascii=False)}")
                    print(f"    actual      : {r['actual_value']}  "
                          f"interval_hit={r['interval_hit']}  "
                          f"scored_event_hit={r['scored_event_hit']}  brier={r['brier']}")
                    print(f"    verdict     : {r['verdict']}")
                    print(f"    attribution : {', '.join(r['error_attribution']) or '(none)'}")
                    if r["block_codes"]:
                        print(f"    BLOCK       : {', '.join(sorted(set(r['block_codes'])))}")
                print("--- 整轮 ---")
                print(f"whole_attribution    : {', '.join(result['error_attribution']) or '(none)'}")
                print(f"notes                : {result['notes']}")
                print()
            if any(not r["process_clean"] for r in result["indicator_results"]) \
                    or result["case_level"]["case_fatal_codes"]:
                rc = 1
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        return rc

    return 2


if __name__ == "__main__":
    sys.exit(main())
