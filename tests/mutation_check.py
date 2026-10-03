#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""判断力训练 — 变异测试（mutation check）

目的：证明回归套件**不是空转**。故意破坏某一处闸门，
确认*预期的那几个*测试转红；若变异后仍然全绿，说明那些测试没在真正检验它。

全部操作在 %TEMP% 的临时副本上进行，绝不改动仓库文件。

用法：
  python tests/mutation_check.py [项目根目录]

退出码：0 = 全部变异都被捕获；1 = 存在未被捕获的变异。
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE.parent
PY = sys.executable
TMP = Path(tempfile.gettempdir())

# name -> (原文, 变异后, 期望转红的测试)
MUTATIONS = {
    "A-disable-quant-check": (
        'def check_quant(case) -> list[Finding]:\n'
        '    """定量检查：隐含 CAGR、定性定量一致性、极端增速。"""\n'
        '    out: list[Finding] = []\n',
        'def check_quant(case) -> list[Finding]:\n'
        '    """MUTATED"""\n'
        '    return []\n',
        ["test-02", "test-11"],
    ),
    "B-disable-firewall": (
        'out.append(Finding("FIREWALL_CONTAMINATION", BLOCK, scope,',
        'out.append(Finding("FIREWALL_CONTAMINATION_OFF", INFO, scope,',
        ["test-07"],
    ),
    "C-force-process-clean": (
        'clean = (not blocks) and (not case_fatal)',
        'clean = True  # MUTATED',
        ["test-08", "test-11"],
    ),
    "D-disable-lookahead-firewall": (
        'elif period_end and period_end <= cutoff:',
        'elif False:  # MUTATED',
        ["test-16"],
    ),
    # v0.2.3 §24 E：复盘退回只读旧字段 actual → 揭晓写进去的 actual_value 读不到
    "E-postmortem-legacy-field-only": (
        '        actual = oc.get("actual_value")\n'
        '        if actual is None:\n'
        '            actual = oc.get("actual")\n',
        '        actual = oc.get("actual")\n',
        ["test-19", "test-23"],
    ),
    # v0.2.3 §24 F：Brier 退回用区间命中 → 评的就不是概率真正押的那个命题
    "F-brier-from-interval-hit": (
        'brier = (prob - (1.0 if se_hit else 0.0)) ** 2 \\\n'
        '            if (prob is not None and se_hit is not None) else None',
        'brier = (prob - (1.0 if hit else 0.0)) ** 2 \\\n'
        '            if (prob is not None and hit is not None) else None',
        ["test-20"],
    ),
}


def run(name, old, new, expect_fail):
    work = TMP / ("jt_mut_" + name)
    shutil.rmtree(work, ignore_errors=True)
    shutil.copytree(SRC, work, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(".git", "__pycache__"))
    tgt = work / "scripts" / "judge_checks.py"
    src = tgt.read_text(encoding="utf-8")
    if old not in src:
        print(f"[{name}] SKIP 目标代码未匹配 —— 变异无效，请更新脚本")
        return False
    tgt.write_text(src.replace(old, new, count=1), encoding="utf-8")

    proc = subprocess.run(
        [PY, str(work / "tests" / "run_regression.py"), "--conversation"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(work),
    )
    out = proc.stdout or ""
    failed = [ln.split()[1] for ln in out.splitlines() if ln.startswith("FAIL ")]
    ok = all(any(e in f for f in failed) for e in expect_fail)
    print(f"[{name}] 期望转红={expect_fail} 实际={failed} --> "
          f"{'CAUGHT' if ok else 'NOT CAUGHT'}")
    return ok


def main() -> int:
    results = [run(n, *v) for n, v in MUTATIONS.items()]
    caught = sum(results)
    print(f"MUTATION_STATUS={'PASS' if caught == len(results) else 'FAIL'} "
          f"({caught}/{len(results)})")
    return 0 if caught == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
