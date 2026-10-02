#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""判断力训练 — 回归测试运行器

驱动 tests/cases/*.json 中的夹具，对 scripts/judge_checks.py 的规则层做断言。

每个夹具形如：
{
  "id": "test-01-missing-base",
  "title": "缺基期即拦截",
  "steps": [
    {
      "mode": "case" | "reply" | "postmortem",
      "case": {...},                 // mode=case / postmortem
      "state": "RESEARCH",           // mode=reply
      "text": "...",                 // mode=reply
      "cutoff": "2010-12-31",        // mode=reply，可选
      "expect": {
        "must_block_codes": [],      // 必须出现的 BLOCK
        "must_warn_codes": [],       // 必须出现的 WARN
        "must_info_codes": [],       // 必须出现的 INFO
        "must_not_codes": [],        // 任何级别都不得出现
        "lockable": true|false,      // mode=case
        "verdict": "...",            // mode=postmortem
        "must_attribution": []       // mode=postmortem
      }
    }
  ]
}

用法：python tests/run_regression.py [--verbose]
退出码：0 = 全部通过；1 = 存在失败。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "scripts"))

from judge_checks import (  # noqa: E402
    BLOCK, WARN, INFO, check_case, check_reply, postmortem, has_block, codes,
)

CASES_DIR = HERE / "cases"


def run_step(step):
    mode = step.get("mode", "case")
    if mode == "case":
        findings = check_case(step["case"])
        extra = {"lockable": not has_block(findings)}
    elif mode == "reply":
        findings = check_reply(step["state"], step["text"], step.get("cutoff"))
        extra = {}
    elif mode == "postmortem":
        case = json.loads(json.dumps(step["case"]))  # 深拷贝，避免污染夹具
        if not case.get("checks", {}).get("findings"):
            case.setdefault("checks", {})["findings"] = [
                f.__dict__ for f in check_case(case)
            ]
        result = postmortem(case)
        findings = check_case(case)
        extra = {"verdict": result["verdict"],
                 "error_attribution": result["error_attribution"],
                 "interval_hit": result["interval_hit"]}
    else:
        raise ValueError(f"未知 mode: {mode}")
    return findings, extra


def assert_step(step, findings, extra):
    exp = step.get("expect", {})
    errs = []
    present = set(codes(findings))

    for key, sev in (("must_block_codes", BLOCK), ("must_warn_codes", WARN),
                     ("must_info_codes", INFO)):
        for c in exp.get(key, []):
            if c not in codes(findings, sev):
                errs.append(f"缺少 {sev} 发现：{c}（{key}）")

    for c in exp.get("must_not_codes", []):
        if c in present:
            errs.append(f"出现了不应有的发现：{c}")

    if "lockable" in exp and extra.get("lockable") != exp["lockable"]:
        errs.append(f"lockable 期望 {exp['lockable']}，实际 {extra.get('lockable')}")

    if "verdict" in exp and extra.get("verdict") != exp["verdict"]:
        errs.append(f"verdict 期望 {exp['verdict']}，实际 {extra.get('verdict')}")

    for a in exp.get("must_attribution", []):
        if a not in (extra.get("error_attribution") or []):
            errs.append(f"错误归因缺少：{a}")

    return errs


def main(argv=None):
    verbose = "--verbose" in (argv or sys.argv)
    files = sorted(CASES_DIR.glob("*.json"))
    if not files:
        print(f"未找到测试夹具：{CASES_DIR}")
        return 1

    total_steps = passed_steps = 0
    failed_tests = []

    for path in files:
        with open(path, encoding="utf-8") as fh:
            fixture = json.load(fh)
        tid = fixture.get("id", path.stem)
        title = fixture.get("title", "")
        test_errs = []

        for si, step in enumerate(fixture.get("steps", []), 1):
            total_steps += 1
            try:
                findings, extra = run_step(step)
            except Exception as exc:  # noqa: BLE001
                test_errs.append(f"  step{si} 执行异常：{type(exc).__name__}: {exc}")
                continue
            errs = assert_step(step, findings, extra)
            if errs:
                test_errs += [f"  step{si} {e}" for e in errs]
            else:
                passed_steps += 1

            if verbose:
                print(f"    step{si} [{step.get('mode','case')}] "
                      f"BLOCK={codes(findings, BLOCK)} WARN={codes(findings, WARN)} "
                      f"INFO={codes(findings, INFO)}")

        if test_errs:
            failed_tests.append((tid, title, test_errs))
            print(f"FAIL  {tid}  {title}")
            for e in test_errs:
                print(e)
        else:
            print(f"PASS  {tid}  {title}")

    print("-" * 72)
    print(f"tests: {len(files)}  steps: {passed_steps}/{total_steps} passed  "
          f"failed_tests: {len(failed_tests)}")
    print("REGRESSION_STATUS=" + ("PASS" if not failed_tests else "FAIL"))
    return 0 if not failed_tests else 1


if __name__ == "__main__":
    sys.exit(main())
