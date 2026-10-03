# 设计说明（design-notes）

记录本项目的工程取舍、边界与已知限制。供未来的自己（或任何维护者）判断"为什么是这样"。

---

## 一、命名决策

| 项 | 决定 | 理由 |
|---|---|---|
| Skill 目录名 | `judgment-training` | ASCII，规避跨平台编码问题；避免中文路径在 Windows 沙箱与 Git 中的干扰 |
| 显示名 | 判断力训练 | 用户指定 |
| version | `0.2.0` | 相对 GPT 原始规格中的"历史预测与判断训练教练"属重大结构升级；0.x 表示方法论仍在迭代 |
| 仓库名 | `judgment-training` | 与技能目录一致。任务书中曾建议 `history-prediction-coach`，因用户明确改名为"判断力训练"而采用现名 |

> **实操提示**：GitHub 网页创建仓库时，中文仓库名会被 sanitize 成短横线（实测"判断力训练"变成了字面 `---`）。**新建仓库请直接用 ASCII 名**，中文名只用于 README、描述与 `SKILL.md` 的显示名。

---

## 二、为什么把规则写成脚本，而不是写进提示词

**问题**：纯提示词形态的"铁律"无法被测试。模型可能在某次会话中忘记检查基期，而没有任何机制会发现。

**做法**：把可判定的规则（准入十查、隐含 CAGR、概率一致性、信息防火墙、教练越界、复盘四象限）实现为 `scripts/judge_checks.py`，并用 `tests/` 冻结行为。

**收益**：
- 规则可回归、可变异测试（见附录）
- 提示词可以保持精简（`SKILL.md` 仅 3471 字符 / 约 7.2 KB）
- 失败是**显式**的（BLOCK/WARN 分级），而不是"模型这次没想起来"

**代价**：
- 夹具需要手工维护
- 脚本只能覆盖**可判定**部分；对话语气、提问质量仍需人工回归（见 `tests/regression-checklist.md` C 节）

---

## 三、目录结构取舍

```text
SKILL.md                              精炼主文件：角色 / 铁律 / 状态机 / 加载表
references/                           按需加载的方法论，避免主文件膨胀
  methodology.md                      训练目标、难度分级、提问设计、动态更新
  coaching-rules.md                   职责边界、防火墙话术、越界场景守则
  probability-calibration.md          命题化、逻辑一致性、校准评分
  quantitative-forecasting.md         准入十查、分解族、隐含 CAGR、基准率
  prediction-record-template.md       档案 schema、提交字段、复盘模板
examples/                             给人看的（含失败案例）
tests/                                给机器跑的（夹具 + 运行器 + 清单）
scripts/judge_checks.py               确定性规则层
docs/design-notes.md                  本文件
```

与任务书建议结构的差异：未设 `assets/`。本技能不产出模板文件，`assets/` 会是空目录。

---

## 四、关键设计决策

### 4.1 状态机而非流程清单

11 个状态各有明确出口条件。好处：教练无法"跳跃"到揭晓；用户也知道自己卡在哪一步。

### 4.2 BLOCK / WARN 双级

- `BLOCK`：禁止推进状态、禁止锁定预测
- `WARN`：必须显式处理（补参照、降置信度），但不阻断

设计理由：基准率缺失在 Level 1 是常见的，一刀切禁止会让新手寸步难行。规则是"标记 + 降置信度"，符合任务书第六节要求。

### 4.3 前台 1—3 问，后台全清单

`judge_checks.py` 一次可能返回 40+ 条发现（神木夹具为 36 BLOCK + 6 WARN）。**绝不**原样输出。教练只引用最靠前的一条。完整清单写入档案，供复盘使用。

这条纪律由 `check_reply()` 的 `COACH_TOO_MANY_QUESTIONS` 部分兜底。

### 4.4 复盘四象限

| 过程 | 结果 | 裁决 |
|---|---|---|
| 干净 | 命中 | `PROCESS_GOOD_OUTCOME_HIT` |
| 干净 | 未命中 | `PROCESS_GOOD_OUTCOME_MISS` |
| 有缺陷 | 命中 | `LUCKY_ACCURATE` |
| 有缺陷 | 未命中 | `PROCESS_DEFECTIVE_OUTCOME_MISS` |

"过程干净"的判定依据是**是否存在 BLOCK 级缺陷**，而非结果。
错误归因则覆盖 BLOCK 与 WARN 两级（否则"忽略基准率"这类 WARN 会漏掉归因）。

### 4.5 反向对照用例（test-12）

没有这个用例，闸门可以靠"一律拦截"通过全部测试。所以必须有一个完全合格的案例，要求 0 BLOCK、0 WARN，且不得出现 17 个已知闸门码中的任何一个。

---

### 4.6 分发方式：一句话提示词，而不是安装脚本

安装一个 Agent Skill 的本质动作是**把一个目录放进技能目录**。这件事由 AI 自己做比让用户跑脚本更通用：

| 方案 | 为什么否掉 / 采纳 |
|---|---|
| ~~shell 安装脚本~~ | 用户得先有 shell、还得知道自己的技能目录在哪；无法覆盖纯对话型 AI。实测还引入三个 Windows 特有陷阱（PS 5.1 无 BOM 时按 GBK 解码 `.ps1`、原生程序 stderr 在 `ErrorActionPreference='Stop'` 下被当成终止性错误、`exit` 会杀掉 `irm \| iex` 的调用方会话） |
| **一句话提示词** | 一句自然语言即可交给任意能读写文件 / 执行命令的 AI；对方自己解析仓库、放进自己的技能目录、回报触发条件。无法执行命令的 AI 则退化为「读取 URL 作为长期指令」 |

因此 README 的安装章节以「把这句话复制给任意 AI」为第一方案，人工 `git clone` 只作为兜底。

---

## 五、已知限制（KNOWN LIMITATIONS）

1. **脚本只覆盖可判定规则**。提问质量、语气、是否真的"像教练而不像问卷机器人"，脚本测不了，依赖人工回归。
2. **阈值是启发式的**。`EXTREME_CAGR = 25%`、`UNIFORM_TOL = 0.02`、`NARROW_REL_WIDTH = 5%` 等为经验取值，不是统计结论。修改它们会改变闸门敏感度，需同步更新测试期望。
3. **信息防火墙依赖用户如实申报材料日期**。若用户隐瞒引用来源，脚本无法发现。这是流程的信任边界。
4. **`PROB_PRECISION` 对"窄区间 + 高概率"有误报可能**。某些确定性极高的命题（如受行政命令直接约束的指标）确实可以窄区间高概率，脚本会 WARN。此时由教练判断并显式说明，属可接受噪声。
5. **博弈型对象（公司）的行为预测更差**。城市预测的变量相对连续，企业预测受管理层决策影响，随机性更高。Level 1—2 建议以城市为主。
6. **未内置案例库**。选题由教练现场给出，不做对象推荐清单——那会不可避免地暗示趋势。
7. **持久化依赖运行环境**。档案默认写用户工作区；若环境不持久，只能在会话内维护并输出可复制 Markdown。

---

## 六、验证方法

### 6.1 回归测试

```bash
python tests/run_regression.py
```

期望：`12/12 tests`、`20/20 steps`、`REGRESSION_STATUS=PASS`。

### 6.2 Markdown 链接检查

```bash
python - <<'EOF'
import re, pathlib
root = pathlib.Path(".")
bad = []
for md in root.rglob("*.md"):
    for m in re.finditer(r"\[[^\]]+\]\(([^)#]+?)", md.read_text(encoding="utf-8")):
        t = m.group(1).strip()
        if t.startswith(("http://", "https://", "mailto:")):
            continue
        if not (md.parent / t).exists():
            bad.append(f"{md}: {t}")
print("BROKEN_LINKS=", len(bad))
[print(" ", b) for b in bad]
EOF
```

### 6.3 主文件体量检查

```bash
python -c "import pathlib; s=pathlib.Path('SKILL.md').read_text(encoding='utf-8'); print('SKILL.md chars =', len(s))"
```

要求 < 6000 字符。

### 6.4 防剧透检查

```bash
python -c "
import pathlib,re
hits=[]
for p in pathlib.Path('.').rglob('*'):
    if p.suffix in {'.md','.json','.py'}:
        t=p.read_text(encoding='utf-8',errors='ignore')
        if re.search(r'(2015|2016|2017)年.{0,12}(亿元|万人|亿吨)', t) and '神木' in t:
            hits.append(str(p))
print('SHENMU_OUTCOME_RISK=', hits)"
```

---

## 附录 A · 变异测试脚本

用于证明回归套件不是空转。**必须在临时副本上执行，不得修改仓库文件。**

```python
#!/usr/bin/env python3
"""变异测试：破坏闸门，确认回归套件会转红。"""
import shutil, subprocess, sys, pathlib

SRC = pathlib.Path(r"<本项目根目录>")
PY = sys.executable
TMP = pathlib.Path(__import__("tempfile").gettempdir())

MUTATIONS = {
    "A-disable-quant-check": (
        'def check_quant(case) -> list[Finding]:\n    """定量检查：隐含 CAGR、定性定量一致性、极端增速。"""\n    out: list[Finding] = []\n',
        'def check_quant(case) -> list[Finding]:\n    """MUTATED"""\n    return []\n',
        ["test-02", "test-11"],
    ),
    "B-disable-firewall": (
        'out.append(Finding("FIREWALL_CONTAMINATION", BLOCK, scope,',
        'out.append(Finding("FIREWALL_CONTAMINATION_OFF", INFO, scope,',
        ["test-07"],
    ),
    "C-force-process-clean": (
        'process_clean = not flags and not any(',
        'process_clean = (True) or not flags and not any(',
        ["test-08", "test-11"],
    ),
}

def run(name, old, new, expect_fail):
    work = TMP / ("jt_mut_" + name)
    shutil.rmtree(work, ignore_errors=True)
    shutil.copytree(SRC, work)
    tgt = work / "scripts" / "judge_checks.py"
    src = tgt.read_text(encoding="utf-8")
    if old not in src:
        print(f"[{name}] SKIP 目标代码未匹配"); return False
    tgt.write_text(src.replace(old, new), encoding="utf-8")
    proc = subprocess.run([PY, str(work / "tests" / "run_regression.py")],
                          capture_output=True, text=True, encoding="utf-8", cwd=str(work))
    failed = [ln.split()[1] for ln in (proc.stdout or "").splitlines() if ln.startswith("FAIL ")]
    ok = all(any(e in f for f in failed) for e in expect_fail)
    print(f"[{name}] 期望转红={expect_fail} 实际={failed} --> {'CAUGHT' if ok else 'NOT CAUGHT'}")
    return ok

if __name__ == "__main__":
    rs = [run(n, *v) for n, v in MUTATIONS.items()]
    print(f"MUTATION_STATUS={'PASS' if all(rs) else 'FAIL'} ({sum(rs)}/{len(rs)})")
    sys.exit(0 if all(rs) else 1)
```

---

## 附录 B · 环境要求

- Python ≥ 3.9（仅用标准库：`argparse` / `json` / `re` / `dataclasses` / `pathlib` / `datetime`）
- 无第三方依赖，无需虚拟环境
- 跨平台：Windows / macOS / Linux 均可运行
