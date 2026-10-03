#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""判断力训练 — 回归测试运行器

驱动 tests/cases/*.json 与 tests/conversation/*.json 中的夹具，
对 scripts/judge_checks.py 的规则层做断言。

夹具形如：
{
  "id": "...", "title": "...",
  "steps": [
    {
      "mode": "case" | "reply" | "reveal" | "postmortem",
      "case": {...}, "state": "...", "text": "...", "cutoff": "...",
      "expect": {
        "must_block_codes": [], "must_warn_codes": [], "must_info_codes": [],
        "must_not_codes": [], "lockable": true|false,
        "verdict": "...", "indicator_verdicts": [...],
        "case_summary_overall": "...", "outcome_status": "...",
        "n_hit": 0, "n_miss": 0, "n_unknown": 0,
        "must_attribution": [], "must_front_stage_codes": [], "max_front_stage": 3
      }
    }
  ]
}

用法：
  python tests/run_regression.py             # JSON 夹具
  python tests/run_regression.py --verbose
  python tests/run_regression.py --conversation   # 追加半自动对话映射检查
退出码：0 = 全部通过；1 = 存在失败。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "scripts"))

from judge_checks import (  # noqa: E402
    BLOCK, WARN, INFO,
    check_case, check_reply, check_reveal, postmortem,
    codes, front_stage, has_block,
)

CASES_DIR = HERE / "cases"
SCALAR_KEYS = ("verdict", "case_summary_overall", "outcome_status",
               "n_hit", "n_miss", "n_unknown", "lockable")


def run_step(step):
    mode = step.get("mode", "case")
    if mode == "case":
        findings = check_case(step["case"])
        extra = {
            "lockable": not has_block(findings),
            "front_stage_codes": [f.code for f in front_stage(findings)],
        }
    elif mode == "reply":
        findings = check_reply(step["state"], step["text"], step.get("cutoff"))
        extra = {}
    elif mode == "reveal":
        findings = check_reveal(step["case"])
        extra = {}
    elif mode == "postmortem":
        case = json.loads(json.dumps(step["case"]))  # 深拷贝，避免污染夹具
        if not case.get("checks", {}).get("findings"):
            case.setdefault("checks", {})["findings"] = [
                f.__dict__ for f in check_case(case)
            ]
        result = postmortem(case)
        findings = check_case(case)
        extra = {
            "verdict": result["verdict"],
            "error_attribution": result["error_attribution"],
            "interval_hit": result["interval_hit"],
            "scored_event_hit": result["scored_event_hit"],
            "indicator_verdicts": [r["verdict"] for r in result["indicator_results"]],
            "indicator_results": result["indicator_results"],
            "case_summary_overall": result["case_summary"]["overall"],
            "outcome_status": result["case_summary"]["outcome_status"],
            "n_hit": result["case_summary"]["n_hit"],
            "n_miss": result["case_summary"]["n_miss"],
            "n_unknown": result["case_summary"]["n_unknown"],
            "case_fatal_codes": result["case_level"]["case_fatal_codes"],
        }
    else:
        raise ValueError(f"未知 mode: {mode}")
    return findings, extra


MISSING = object()


def _resolve_path(case, path):
    """从案例档案中按 `case.x` / `indicator[0].x` / `sources[0].x` / `x` 取字段值。

    对话级用例用它断言「自然语言 → 结构化状态」的映射结果，
    而不只是断言规则层的发现。取不到时返回 MISSING。
    """
    p = path[5:] if path.startswith("case.") else path
    m = re.match(r"^(indicators?|sources?)\[(\d+)\]\.(.+)$", p)
    if m:
        coll_raw, idx, field = m.group(1), int(m.group(2)), m.group(3)
        coll = "indicators" if coll_raw.startswith("indicator") else "sources"
        items = case.get(coll) or []
        if idx >= len(items):
            return MISSING
        return items[idx].get(field, MISSING)
    return case.get(p, MISSING)


def assert_extraction(step, errs):
    """对话级用例：核对自然语言抽取出的字段值。

    - `extract`          {路径: 期望值}——必须精确相等（含 true/false/"unknown"）
    - `extract_absent`   [路径]——该字段必须**缺席**（未抽取 ≠ 抽成 false）
    """
    case = step.get("case")
    if not isinstance(case, dict):
        return
    for path, want in (step.get("extract") or {}).items():
        got = _resolve_path(case, path)
        if got is MISSING:
            errs.append(f"  抽取缺失：{path} 期望 {want!r}，实际字段不存在")
        elif got != want:
            errs.append(f"  抽取不符：{path} 期望 {want!r}，实际 {got!r}")
    for path in (step.get("extract_absent") or []):
        if _resolve_path(case, path) is not MISSING:
            errs.append(f"  抽取多余：{path} 本应缺席（未检查 ≠ 已通过），却已被赋值")


def assert_step(step, findings, extra):
    exp = step.get("expect", {})
    errs: list[str] = []
    present = set(codes(findings))

    for key, sev in (("must_block_codes", BLOCK), ("must_warn_codes", WARN),
                     ("must_info_codes", INFO)):
        for c in exp.get(key, []):
            if c not in codes(findings, sev):
                errs.append(f"缺少 {sev} 发现：{c}（{key}）")

    for c in exp.get("must_not_codes", []):
        if c in present:
            errs.append(f"出现了不应有的发现：{c}")

    for key in SCALAR_KEYS:
        if key in exp and extra.get(key) != exp[key]:
            errs.append(f"{key} 期望 {exp[key]}，实际 {extra.get(key)}")

    if "indicator_verdicts" in exp and extra.get("indicator_verdicts") != exp["indicator_verdicts"]:
        errs.append(f"indicator_verdicts 期望 {exp['indicator_verdicts']}，"
                    f"实际 {extra.get('indicator_verdicts')}")

    for a in exp.get("must_attribution", []):
        if a not in (extra.get("error_attribution") or []):
            errs.append(f"错误归因缺少：{a}")

    for c in exp.get("must_front_stage_codes", []):
        if c not in (extra.get("front_stage_codes") or []):
            errs.append(f"前台未包含应优先呈现的：{c}")

    if "max_front_stage" in exp:
        got = extra.get("front_stage_codes") or []
        if len(got) > exp["max_front_stage"]:
            errs.append(f"前台条目 {len(got)} 条，超过上限 {exp['max_front_stage']}：{got}")

    # v0.2.3：逐指标的精确断言（评分命题 / Brier 只能这样验，不能靠总体 verdict 猜）
    #   "indicator_results": [{"indicator": "GDP", "interval_hit": false,
    #                          "scored_event_hit": true, "brier": 0.04}]
    # 只比较写出来的键，其余键不约束。
    for want in exp.get("indicator_results") or []:
        nm = want.get("indicator")
        got_list = extra.get("indicator_results") or []
        got = next((r for r in got_list if r.get("indicator") == nm), None)
        if got is None:
            errs.append(f"indicator_results 中找不到指标：{nm}")
            continue
        for k, v in want.items():
            if k == "indicator":
                continue
            if got.get(k) != v:
                errs.append(f"indicator_results[{nm}].{k} 期望 {v!r}，实际 {got.get(k)!r}")

    return errs


def run_fixture(fixture, verbose=False):
    tid = fixture.get("id", "?")
    title = fixture.get("title", "")
    test_errs: list[str] = []
    total = passed = 0

    for si, step in enumerate(fixture.get("steps", []), 1):
        total += 1
        try:
            findings, extra = run_step(step)
        except Exception as exc:  # noqa: BLE001
            test_errs.append(f"  step{si} 执行异常：{type(exc).__name__}: {exc}")
            continue
        errs = assert_step(step, findings, extra)
        assert_extraction(step, errs)
        if errs:
            test_errs += [f"  step{si} {e}" for e in errs]
        else:
            passed += 1

        if verbose:
            print(f"    step{si} [{step.get('mode', 'case')}]")
            print(f"      BLOCK={codes(findings, BLOCK)}")
            print(f"      WARN ={codes(findings, WARN)}")
            print(f"      INFO ={codes(findings, INFO)}")
            if extra:
                print(f"      extra={ {k: v for k, v in extra.items() if k != 'front_stage_codes'} }")
            if extra.get("front_stage_codes"):
                print(f"      front={extra['front_stage_codes']}")

    return tid, title, test_errs, passed, total


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    verbose = "--verbose" in argv or "-v" in argv
    with_conversation = "--conversation" in argv

    files = sorted(CASES_DIR.glob("*.json"))
    if not files:
        print(f"未找到测试夹具：{CASES_DIR}")
        return 1

    total_steps = passed_steps = 0
    failed = []

    print("=" * 72)
    print("JSON 规则层回归（tests/cases/）")
    print("=" * 72)
    for path in files:
        with open(path, encoding="utf-8") as fh:
            fixture = json.load(fh)
        tid, title, errs, p, t = run_fixture(fixture, verbose)
        total_steps += t
        passed_steps += p
        if errs:
            failed.append(tid)
            print(f"FAIL  {tid}  {title}")
            for e in errs:
                print(e)
        else:
            print(f"PASS  {tid}  {title}")

    conv_note = ""
    if with_conversation:
        print("=" * 72)
        print("半自动对话映射检查（tests/conversation/）")
        print("=" * 72)
        conv_dir = HERE / "conversation"
        c_files = sorted(conv_dir.glob("*.json")) if conv_dir.exists() else []
        if not c_files:
            print("（未找到 tests/conversation/*.json）")
        for path in c_files:
            with open(path, encoding="utf-8") as fh:
                fixture = json.load(fh)
            tid, title, errs, p, t = run_fixture(fixture, verbose)
            total_steps += t
            passed_steps += p
            if errs:
                failed.append(tid)
                print(f"FAIL  {tid}  {title}")
                for e in errs:
                    print(e)
            else:
                print(f"PASS  {tid}  {title}")
        conv_note = f"  (含对话映射 {len(c_files)} 个)"

    print("-" * 72)
    print(f"tests: {len(files)}  steps: {passed_steps}/{total_steps} passed  "
          f"failed_tests: {len(failed)}{conv_note}")
    print("REGRESSION_STATUS=" + ("PASS" if not failed else "FAIL"))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
