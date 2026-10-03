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
- 提示词可以保持精简（`SKILL.md` 仅 4130 字符）
- 失败是**显式**的（BLOCK/WARN 分级），而不是"模型这次没想起来"

**代价**：
- 夹具需要手工维护
- 脚本只能覆盖**可判定**部分；对话语气、提问质量仍需人工回归（见 `tests/regression-checklist.md` C 节）

---

## 三、目录结构取舍

```text
SKILL.md                              精炼主文件：角色 / 铁律 / 状态机 / 加载表
references/                           按需加载的方法论，避免主文件膨胀
  methodology.md                      训练目标、难度分级、提问设计、动态更新、复盘六象限
  coaching-rules.md                   职责边界、防火墙话术、越界场景守则、前台纪律
  probability-calibration.md          命题化、逻辑一致性、校准评分
  quantitative-forecasting.md         准入十查、分解族、隐含 CAGR、基准率、P0—P7
  prediction-record-template.md       档案 schema、提交字段、多指标复盘模板
  state-extraction.md                 自然语言 → 结构化状态映射（v0.2.2）
  reveal-protocol.md                  揭晓协议：来源层级 / 口径核验 / 统计修订（v0.2.2）
examples/                             给人看的（含失败案例）
tests/                                给机器跑的（夹具 + 运行器 + 清单）
  conversation/                       对话级映射用例（v0.2.2）
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

### 4.3 前台 1—3 条，后台全清单

`judge_checks.py` 一次可能返回 40+ 条发现（神木夹具为 39 BLOCK + 8 WARN）。**绝不**原样输出。

v0.2.2 把这个纪律**做成了确定实现**，而不是靠模型自觉：

- `sort_findings()` 按 **P0—P7 优先级**排序（同级别 BLOCK 优先于 WARN）
- `front_stage()` 去重后取前 3 条不同 code，并跳过纯信息项（`ADMISSION_OK` / `IMPLIED_CAGR_COMPUTED` / …）
- CLI 在输出末尾直接打印「前台应只说（1—3 条，按优先级）」

完整清单仍写入档案，供复盘使用。另有 `check_reply()` 的 `COACH_TOO_MANY_QUESTIONS` 兜底。

> 为什么需要显式优先级：此前按 severity 排序，神木案例会平铺 39 条 BLOCK，
> 用户无法判断该先补哪一个。优先级让"一次推进一个瓶颈"变得可执行。

### 4.4 复盘六象限（v0.2.2 由四象限扩展）

| 过程 | 结果 | 裁决 |
|---|---|---|
| 干净 | 命中 | `PROCESS_GOOD_OUTCOME_HIT` |
| 干净 | 未命中 | `PROCESS_GOOD_OUTCOME_MISS` |
| 干净 | **未知** | `PROCESS_GOOD_OUTCOME_UNKNOWN` |
| 有缺陷 | 命中 | `LUCKY_ACCURATE` |
| 有缺陷 | 未命中 | `PROCESS_DEFECTIVE_OUTCOME_MISS` |
| 有缺陷 | **未知** | `PROCESS_DEFECTIVE_OUTCOME_UNKNOWN` |

"过程干净"的判定依据是**是否存在 BLOCK 级缺陷**，而非结果。
错误归因覆盖 BLOCK 与 WARN 两级（否则"忽略基准率"这类 WARN 会漏掉归因）。

**"未知"这一列是 v0.2.2 新增的。** 旧实现在 `hit` 为 `None` 时走 `if hit is False` 的另一侧，
把"还没揭晓 / 没提供结果"和"未命中"混为一谈，导致**未揭晓的案例被误判成 MISS**。
现在 `hit=None` 有独立分支，并区分 `PROCESS_GOOD_OUTCOME_UNKNOWN` 与
`PROCESS_DEFECTIVE_OUTCOME_UNKNOWN`（后者：缺陷已足以定论"当时不该锁定"，无需知道结果）。

### 4.5 反向对照用例（test-12）

没有这个用例，闸门可以靠"一律拦截"通过全部测试。所以必须有一个完全合格的案例，要求 0 BLOCK、0 WARN，且不得出现 23 项已知闸门码中的任何一个。

v0.2.2 中 test-12 还修了一处**时间逻辑自洽性**问题：此前它的基期取自"2009 全年"但未标注公布时间，
在升级后的双层防火墙下既可能被误拦、也可能放行一个现实中拿不到的数。现在基期改用
2009 全年正式公布值（`base_published_at: 2010-02-25`），材料也补齐 `data_period_*` 与 `published_at`。

---

### 4.6 分发方式：一句话提示词，而不是安装脚本

安装一个 Agent Skill 的本质动作是**把一个目录放进技能目录**。这件事由 AI 自己做比让用户跑脚本更通用：

| 方案 | 为什么否掉 / 采纳 |
|---|---|
| ~~shell 安装脚本~~ | 用户得先有 shell、还得知道自己的技能目录在哪；无法覆盖纯对话型 AI。实测还引入三个 Windows 特有陷阱（PS 5.1 无 BOM 时按 GBK 解码 `.ps1`、原生程序 stderr 在 `ErrorActionPreference='Stop'` 下被当成终止性错误、`exit` 会杀掉 `irm \| iex` 的调用方会话） |
| **一句话提示词** | 一句自然语言即可交给任意能读写文件 / 执行命令的 AI；对方自己解析仓库、放进自己的技能目录、回报触发条件。无法执行命令的 AI 则退化为「读取 URL 作为长期指令」 |

因此 README 的安装章节以「把这句话复制给任意 AI」为第一方案，人工 `git clone` 只作为兜底。

---

### 4.7 自然语言映射层（v0.2.2 新增）

**问题**：规则层是给结构化状态设计的，但训练是对话。用户说"大概 100"，不会说
`{"base_value": 100}`。此前没有规定"怎么把一句话变成字段"，于是同一句话可能被抽成不同状态，
规则层再正确也没用。

**做法**：新增 [`references/state-extraction.md`](../references/state-extraction.md)，给出逐字段映射表，
并确立一条核心原则：

> **未检查 ≠ 已通过。**

具体化为**三态字段**：`stock_flow_relevant` / `quantity_price_relevant` 等只有
`true` / `false` / `"unknown"` 三种合法取值。

| 状态 | 规则层反应 |
|---|---|
| 显式 `true` | 触发对应的 resolved / split 检查 |
| 显式 `false` | 判定为不涉及，通过 |
| 显式 `"unknown"` | `GATE_FIELD_UNKNOWN`（BLOCK） |
| **字段缺席** | `GATE_FIELD_UNCHECKED`（BLOCK） |

**为什么这一条最重要**：旧逻辑里，用户没提存量流量 → 字段不存在 → 检查被跳过 → 默认放行。
这等于把"没检查"当成"已确认无关"。**任何"用户没提就跳过"的设计都是默认放行。**

**边界**：这是**规范**，不是自动解析器。抽取仍由教练完成，脚本只能断言"抽取后的字段"是否符合规则。
所以 `tests/conversation/` 的用例同时断言 `extract`（抽取结果）与 `expect`（规则发现），
运行器为此加了 `extract` / `extract_absent` 两种断言——**这样才能测到映射层，而不只是重跑规则。**

### 4.8 多指标复盘与作用域隔离（v0.2.2 修复）

**问题**：`postmortem()` 此前把任何 case 级结果都作用在 `indicators[0]` 上。
多指标案例实际只评价了第一个指标，其余指标的命中/未命中被静默丢弃。

**做法**：

1. **逐指标裁决**：`indicator_results[]`，每个指标独立计算 `interval_hit` / `brier` / `verdict` / `error_attribution`
2. **结果映射**：优先 `outcomes: {指标名: {...}}`；单指标允许 `outcome: {...}`；
   多指标却只给一个 `outcome` → `OUTCOME_SCOPE_AMBIGUOUS`(WARN)，全部按结果未知处理
3. **作用域隔离**：`case_level` 与 `indicator-level` 分开归因。
   某指标的过程缺陷不得污染其他指标，**唯一例外是 case 级致命缺陷**
   （`CUTOFF_NOT_SET` / `FIREWALL_CONTAMINATION` / `FIREWALL_LOOKAHEAD_LEAKAGE`）→ `CASE_INVALIDATED`
4. **案例级汇总**：`case_summary{overall, n_hit, n_miss, n_unknown, outcome_status}`。
   `CASE_MIXED` 明确告诉使用者"各指标不一致，必须逐个看"，**而不是用一个总分掩盖差异**
5. **兼容旧调用方**：保留 `verdict` / `process_flags` / `interval_hit` / `brier` 等字段，单指标时语义不变

### 4.9 信息防火墙双层时间（v0.2.2 修复）

旧防火墙只比较"数据所属年份 ≤ 截点年份"。这漏掉最隐蔽的一类前视泄漏：

> 截点 `2010-12-31`，用户用了「**2010 年全年 GDP**」。
> 所属期在截点之内 ✔，但该值通常 **2011 年 1—2 月**才在统计公报发布 ✘。
> 截点当天，这个数**根本还不存在**。

**做法**：把两个时间分开——`data_period_end`（所属期）与 `published_at`（公开时间），
新增判定：

| 情形 | 结果 |
|---|---|
| 发布 > 截点 且 所属期 ≤ 截点 | `FIREWALL_LOOKAHEAD_LEAKAGE`（BLOCK） |
| 发布 > 截点 且 所属期 > 截点 | `FIREWALL_CONTAMINATION`（BLOCK） |
| 发布 > 截点 且 `usable: false` | `FIREWALL_ISOLATED`（INFO）—— 正确隔离，不报错 |
| 发布缺失 且 `available_at_cutoff: false` | `FIREWALL_LOOKAHEAD_LEAKAGE`（BLOCK） |
| 发布缺失 | `SOURCE_DATE_UNKNOWN`（WARN） |

由 `test-16` 三个 step 分别覆盖。变异测试 D 专门证明：**去掉这条判定，test-16 会转红。**

---

## 五、已知限制（KNOWN LIMITATIONS）

1. **脚本只覆盖可判定规则**。提问质量、语气、是否真的"像教练而不像问卷机器人"，脚本测不了，依赖人工回归。
2. **阈值是启发式的**。`EXTREME_CAGR = 25%`、`UNIFORM_TOL = 0.02`、`NARROW_REL_WIDTH = 5%` 等为经验取值，不是统计结论。修改它们会改变闸门敏感度，需同步更新测试期望。
3. **信息防火墙依赖用户如实申报材料日期**。若用户隐瞒引用来源，脚本无法发现。这是流程的信任边界。
   v0.2.2 起需要**两个**时间（所属期 + 发布时间），申报负担略增，但这是拦住"所属期在截点内、实际次年才公布"这类泄漏的必要代价。
4. **`PROB_PRECISION` 对"窄区间 + 高概率"有误报可能**。某些确定性极高的命题（如受行政命令直接约束的指标）确实可以窄区间高概率，脚本会 WARN。此时由教练判断并显式说明，属可接受噪声。
5. **博弈型对象（公司）的行为预测更差**。城市预测的变量相对连续，企业预测受管理层决策影响，随机性更高。Level 1—2 建议以城市为主。
6. **未内置案例库**。选题由教练现场给出，不做对象推荐清单——那会不可避免地暗示趋势。
7. **持久化依赖运行环境**。档案默认写用户工作区；若环境不持久，只能在会话内维护并输出可复制 Markdown。
8. **自然语言抽取仍是规范，不是解析器**（v0.2.2）。`state-extraction.md` 规定"怎么抽"，
   实际抽取由教练（模型）完成。因此 `tests/conversation/` 只能断言**抽取结果**是否符合预期，
   不能保证模型每次都能抽对。降低该风险的方式是把原则写死（三态字段、未检查 ≠ 已通过）
   并让它可被测试。
9. **来源层级判定靠关键词匹配**（v0.2.2）。`REVEAL_SOURCE_TIERS` 检查来源字符串是否含
   "统计公报""年报"等词，措辞差异可能漏判，故设为 WARN 而非 BLOCK。
10. **修订状态可能无法确定**（v0.2.2）。若用户不知道结果是否被修订过，只能记 `"unknown"`，
    命中判定按现行值处理，并在档案中标注"未来修订可能导致结论变化"。

---

## 六、验证方法

### 6.1 回归测试

```bash
python tests/run_regression.py --conversation
```

期望：`18 tests`、`41/41 steps`（含 4 个对话级映射用例）、`REGRESSION_STATUS=PASS`。

> 只跑 `python tests/run_regression.py`（不加 `--conversation`）时为 18 tests / 33 steps，
> 因为对话用例仅在显式请求时加载。

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
        'clean = (not blocks) and (not case_fatal)',
        'clean = True  # MUTATED',
        ["test-08", "test-11"],
    ),
    "D-disable-publication-firewall": (
        # 只关掉"所属期在截点内、但发布时间在截点后"这一分支，
        # 让前视泄漏退化为普通污染 —— 专门证明 test-16 在守着这条判定
        'elif period_end and period_end <= cutoff:',
        'elif False:  # MUTATED',
        ["test-16"],
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
