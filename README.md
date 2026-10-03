# 判断力训练 · Judgment Training

> 一个历史盲测预测训练系统。你站在某个历史截点，只用当时可获得的信息做预测，再由真实历史结果检验判断质量。

**核心主张：判断力可以用结果检验，但不能只用结果评价。**

---

## 这是什么

一个 Skill（技能包），把"预测训练"从随口猜数字变成有闸门、有档案、可回归的流程。

- **用户负责研究与判断** —— 选题之后，所有背景资料自己搜集
- **AI 负责流程** —— 设截点、控信息边界、查准入、查数学、查概率、提问、记录、揭晓、复盘

AI 不做研究、不给研究关键词、不给答案、不提前透露结局。

---

## 为什么做

常见的"预测训练"有三个致命缺陷：

1. **基期不清就开始猜** —— 不知道现在是多少，直接说五年后是多少
2. **概率是情绪刻度** —— 四个不同变量全部 85%
3. **只看结果对错** —— 猜中了就当自己判断力强，猜错了就否定整套方法

这个系统把上述三点都变成可拦截的规则。

---

## 核心哲学

| 原则 | 含义 |
|---|---|
| 基期先于增速 | 基期未核实，"五年后达到 X"没有检验价值 |
| 数字必须可推导 | 任何预测值都要能回答"这个数是怎么来的" |
| 概率必须对应命题 | `P(2015 年 GDP ∈ [900,1100]) = 60%`，不是"GDP：60%"；且要写清这个概率**绑定到哪一个命题**，复盘只评它 |
| 四步评同一件事 | 预测、概率、揭晓、复盘必须落在同一个事件、同一个时期、同一个口径上 |
| 区间优先于点 | 中心估计只是中枢，不是答案 |
| 基准率约束叙事 | 个案故事必须与同类对象的常态分布对照 |
| 过程与结果分开评价 | 结果正确 + 推理糟糕 ≠ 好预测<br>结果错误 + 推理合理 + 概率诚实 = 可能是好预测 |
| 结果不可用就不评分 | 对答案的数值本身不合法（口径不符 / 期间不符 / 字段缺失）时，**不产生命中与 Brier**；过程质量照常独立评价 |
| 信息时间防火墙 | 截点之后公开的信息不得进入预测 |

---

## 使用流程

```text
选题 → 设截点 → 自己研究 → 选指标 → 过准入闸门 → 提交预测
  → 规则检查（CAGR / 概率 / 基准率） → 锁定 → 揭晓 → 复盘 → 提炼原则
```

11 个状态各有出口条件，不满足就停在该状态。**只有用户显式说出"这是我的最终预测，可以揭晓"才揭晓。**

---

## 一句话安装

本仓库是标准的 **Agent Skill** 包（`SKILL.md` + YAML frontmatter + `references/` + `scripts/`）。
安装 = 把这个目录放进 AI 的技能目录。**不需要跑任何脚本。**

### 把这句话复制给任意 AI

```text
请把 https://github.com/ziyue085/judgment-training 安装成我的技能：
克隆到你的技能目录（例如 ~/.workbuddy/skills/ 或 ~/.claude/skills/），目录名用 judgment-training；
装好后确认 SKILL.md 存在，然后告诉我这个技能在什么情况下会被触发。
```

如果对方是纯对话型、不能执行命令的 AI，改用这句：

```text
请读取 https://raw.githubusercontent.com/ziyue085/judgment-training/main/SKILL.md
以及同仓库 references/ 目录下的 7 个文档，把它们作为我的长期指令保存下来。
以后我说「判断力训练」时，按 SKILL.md 里的角色和流程执行。
```

> ⚠️ `raw.githubusercontent.com` 在部分网络环境（如中国大陆直连）不可达，实测直连会返回 `000`。
> 若读不到，把上面两个链接换成仓库页面地址：
> - `https://github.com/ziyue085/judgment-training/blob/main/SKILL.md`
> - `https://github.com/ziyue085/judgment-training/tree/main/references`
>
> 或让 AI 直接执行下面的 `git clone`。

### 各 AI 的技能目录

| Agent | 目录 | 说明 |
|---|---|---|
| WorkBuddy | `~/.workbuddy/skills/` | 用户级；项目级为 `<项目>/.workbuddy/skills/` |
| Claude Code | `~/.claude/skills/` | 用户级 |
| 其他支持 `SKILL.md` 约定的 Agent | 见其文档 | 目录约定通常是 `<skills-dir>/<技能名>/SKILL.md` |

### 人工安装（两步）

```bash
git clone https://github.com/ziyue085/judgment-training.git ~/.workbuddy/skills/judgment-training
```

改 `~/.claude/skills/` 或你自己的技能目录均可。

### 依赖

- **无需安装任何依赖**。检查器只用 Python 标准库（≥3.9）
- **Python 可选但推荐**：`scripts/judge_checks.py` 提供确定性闸门。没有 Python 时技能仍可用，但规则层退化为"靠模型自觉"，可靠性下降
- 纯云端对话产品（如 ChatGPT 网页版）没有本地技能目录机制，无法安装；用上面的"读取 URL"句式把内容作为长期指令上传

### 装完自检

```bash
python ~/.workbuddy/skills/judgment-training/tests/run_regression.py
```

期望输出 `REGRESSION_STATUS=PASS`。

---

## 一个简短示例

```text
用户：开始判断力训练。

教练：对象：H 市（城市）。截点 2013-12-31，期限到 2016 年底，3 年。
      Level 1，最多 2 个核心指标。只能用截点当天及之前公开的信息。
      之后的事我一律不认，也不会透露。去研究吧。

用户：我找到 2013 年的统计公报，还有几篇 2014 年的分析。

教练：2014 年那几篇不能用，超出截点了。公报可以用。
      另外：公报里的是事实，评论文章里的是观点，提交时分开标注。

……

用户：我预测 2016 年 GDP 到 620 亿，把握 85%。

教练：620 是从 380 出来，三年，隐含年均增速约 17.7%。
      你前面说煤价大概率回落、产量增速放缓——那 17.7% 靠什么支撑？

用户：……政府投资吧。

教练：那把这个假设写进推导过程。85% 太高了，你没有基准率——
      同期同类资源型城市三年 CAGR 超过 15% 的有多少？
```

> 默认由教练**直接出题**（对象 + 截点），不先问"你想分析哪个城市"。
> 只有用户明确说"我想自己挑"时才进入偏好确认。

完整示例（含复盘）见 [`examples/example-session.md`](examples/example-session.md)。

---

## 难度分级

| 级别 | 对象 | 期限 | 指标 | 要求 |
|---|---|---|---|---|
| **Level 1** | 1 个 | 2—3 年 | ≤2 个 | 跑通完整预测链；简单基准率；简单区间与概率 |
| **Level 2** | 1 个 | 3—5 年 | 3—4 个 | 情景分析；正式概率结构；像样的参照组 |
| **Level 3** | 多个截点 | 多阶段 | 多变量 | 连续信息更新；宏观/行业/政策交互；反事实分析 |

升级判据：连续两轮复盘中"准入类"与"推理类"缺陷为零。

---

## 防剧透机制

三层：

1. **信息防火墙** —— 截点之后的材料标记为不可用。发现污染时只说明"这条不能用"，**不解释它意味着什么**
2. **揭晓授权** —— 必须用户显式授权；且揭晓范围**严格限定在预测期限内**（预测 2010→2013，就只说 2013，便于同一对象续练 2013→2016）
3. **仓库纪律** —— 本仓库的文档与测试夹具**不含任何真实历史结局**，包括神木回归案例。
   唯一例外是 `tests/e2e/real-historical-full-run.md`：它是端到端演练记录，
   明确标注 **`DO_NOT_USE_FOR_REAL_TRAINING`**，其对象**不得**作为正式训练题重复使用、
   也不得进入正式选题池（见 `tests/e2e/e2e-report.md` 开头声明）

---

## 神木 2010 回归案例

第一轮训练（神木 @ 2010-12-31 → 2015）留下了十类典型错误：未核实 GDP 与财政收入基期、人口预测无历史趋势、数字凭感觉、定性"继续发展"与数字矛盾、四个预测统一 85%、无隐含 CAGR 检查、无基准率、储量当产量、未拆量价。

它现在是一个**可执行的回归测试**：

```bash
python scripts/judge_checks.py case tests/cases/test-11-shenmu-2010-regression.json
```

该夹具触发 **45 个 BLOCK + 6 个 WARN**，`lockable=NO` —— 即新版本必须在错误进入最终预测之前将其拦住。

（v0.2.2 时为 39 BLOCK + 8 WARN；v0.2.3 把 2 条"基期公开时间不明"的 WARN 升级为 BLOCK，
并新增 4 条"概率未绑定命题"，因此变多。）

详见 [`examples/shenmu-2010-regression-case.md`](examples/shenmu-2010-regression-case.md)。

---

## 本版修复（v0.2.4）

一次**结果完整性补丁**。不重构、不扩功能。核心一句话：

> **结果数据本身不合法时，绝不能继续给预测打分。**

v0.2.3 让四步评的是同一件事；v0.2.4 让这套评分机制在"拿来对答案的那个数本身就不可靠"时**停手**。

**1）无效揭晓仍会被复盘评分。** v0.2.3 的 `check_reveal()` 会在 `REVEAL` 阶段拦下
口径不符、期间错位的结果，但 `postmortem()` 自己**不做验证**。只要有人绕过状态机
直接调用复盘（CLI、测试、其他 agent、迁移旧档案），一份期间错位的结果照样会被算出一个分数。
现在 `postmortem()` **主动重新验证**：`outcome_valid=false` 时命中与 Brier 一律 `null`，
`actual_value` 只保留展示，**预测过程的质量照常独立评价**——
不许把结果的问题算到用户推理的账上。

```text
outcome_status = INVALID     outcome_valid = false
scored_event_hit = null      interval_hit = null      brier = null
process_clean  = true        ← 过程仍被单独评价
verdict        = PROCESS_GOOD_OUTCOME_INVALID
```

**2）裸 `actual` 绕过了完整性要求。** 旧档案里只有 `{"actual": 500}` 时，这个值会被
当成正常结果参与正式评分。现在它只被读出来供查看与迁移，标记 `LEGACY_UNVERIFIED`，
**不得**再参加正式统计。兼容层的含义是"旧数据还能打开"，不是"旧数据可以免责"。

**3）修订双轨只写在文档里。** `reveal-protocol.md` 早就要求"当时公布值与最新修订值
两个都报"，但复盘实际只取一个数。现在 `as_reported_then` 与 `latest_revised`
**各算各的**，不一致时前台必须明说：

> 「按当时公布的 790：命中；按修订后的 812：未命中。」

而不是只给一个"最终结论"。这类分歧单独标记 `OUTCOME_REVISION_SENSITIVE`，
**不归因成预测过程错误**。

**4）"未知"与"已知但不可用"被分开。** 结果状态现在是四态：
`VALID` / `INVALID` / `LEGACY_UNVERIFIED` / `UNKNOWN`。多指标可为 `PARTIAL_INVALID`。
「没有结果」和「有结果但不能用来评分」是两件完全不同的事。

本版还额外自动跑了两条端到端演练（合成案例 + 真实历史案例）与一次故障注入，
理由很直接：**静态回归测不到的东西，只有在真跑一遍时才会冒出来。**
它们发现了 3 个真实缺口（零指标案例被报为可准入、状态顺序不由代码强制、
回复检查不校验陈述真实性），均如实记录，未擅自扩规则。

---

## 本版修复（v0.2.3）

一次**正确性补丁**。不重构、不扩功能、不新增大段方法论。
v0.2.2 让流程"跑得通"，v0.2.3 让四步真正评的是**同一个事件、同一个时期、同一个口径**。

四个正确性问题都是同一类毛病的不同侧面：**评的不是你押的那件事。**

**1）揭晓写进去，复盘读不到。** 揭晓记录的是 `actual_value`，`postmortem()` 却只读 `actual`。
结果是揭晓明明成功，复盘却当成"没有结果"，裁决塌成 `OUTCOME_UNKNOWN`。
现在主读 `actual_value`，`actual` 只作旧档案回退。

**2）Brier 评错了事件。** 旧实现直接拿 `interval_hit` 代入 `(p − o)²`。
看这个例子：

```text
预测区间 [480, 520]，命题「GDP > 420」，概率 80%，实际 450
```

区间没命中（450 ∉ [480,520]），但你押的命题命中了。旧算法给 Brier 打出
`(0.8 − 0)² = 0.64`（看起来过度自信到离谱），正确值是 `(0.8 − 1)² = 0.04`。
**差的这 0.6 不是你判断的问题，是算法评错了事件。**

现在引入结构化评分命题 `scored_event`：

```json
"scored_event": {"type": "threshold", "op": ">", "value": 420}
```

`type` 可为 `interval` / `threshold` / `direction`。概率必须有 `scored_event`，
缺失即 `PROB_SCORED_EVENT_MISSING`（BLOCK）。**预测区间与评分命题允许不同，
但必须分开写、分开评** —— `interval_hit` 与 `scored_event_hit` 分别输出，
可以合法地一假一真。

**3）"截点当天能否拿到"从来没被证明。** 正在使用的材料若缺 `published_at`，
旧版本只给一个 WARN；有基期值却没有它的公开时间，同样只是 WARN。
两条现在都升级为 **BLOCK**（`SOURCE_DATE_UNKNOWN` / `BASE_PUBLICATION_UNKNOWN`）。
被隔离（`usable: false`）的材料则相反：只提示，**不得阻断** ——
否则用户会为了推进流程而去伪造一个发布时间。

**4）揭晓不校验预测目标期。** 旧实现只比基期与结果期间，完全忽略 `forecast_to`。
拿 2012 年的数字结算 2013 年的预测，照样通过。现在结果期末与目标期不一致即
`REVEAL_TARGET_PERIOD_MISMATCH`（BLOCK），并引入 `actual_period_start` / `actual_period_end`
（旧档案只写"2013"的年粒度写法仍兼容）。

另外把裁决口径也对齐了：`verdict` 与命中计数改为跟随
`outcome_hit = scored_event_hit ?? interval_hit`，让"评的"与"算分的"是同一个事件。

---

## 项目结构

```text
judgment-training/
├─ SKILL.md                          主文件（精炼，4875 字符）
├─ README.md
├─ CHANGELOG.md
├─ LICENSE
├─ .gitignore
├─ references/                       按需加载的方法论
│  ├─ methodology.md                 训练目标 / 难度 / 提问设计 / 动态更新 / 复盘八象限
│  ├─ coaching-rules.md              职责边界 / 防火墙话术 / 越界场景 / 前台纪律
│  ├─ probability-calibration.md     命题化 / 逻辑一致性 / 校准评分
│  ├─ quantitative-forecasting.md    准入十查 / 分解族 / 隐含 CAGR / 基准率 / P0—P7
│  ├─ prediction-record-template.md  档案 schema / 提交字段 / 多指标复盘模板
│  ├─ state-extraction.md            自然语言 → 结构化状态映射（未检查 ≠ 已通过）
│  └─ reveal-protocol.md             揭晓协议：来源层级 / 口径核验 / 统计修订 / 目标期
├─ examples/
│  ├─ example-session.md             一轮完整对话（虚构对象）
│  └─ shenmu-2010-regression-case.md 失败案例与拦截映射
├─ tests/
│  ├─ test-cases.md                  27 个用例说明
│  ├─ conversation-cases.md          4 个对话级映射用例说明
│  ├─ regression-checklist.md        自动 + 变异 + 人工回归清单
│  ├─ run_regression.py              测试运行器（含 --conversation）
│  ├─ mutation_check.py              变异测试（A—I 九项，可一键复现）
│  ├─ cases/*.json                   27 个可执行夹具
│  ├─ conversation/*.json            4 个自然语言映射用例
│  └─ e2e/                           端到端演练记录（合成 + 真实历史 + 汇总报告）
├─ scripts/
│  └─ judge_checks.py                确定性规则层
└─ docs/
   └─ design-notes.md                设计取舍与已知限制
```

---

## 运行测试

```bash
python tests/run_regression.py                 # 27 tests / 55 steps
python tests/run_regression.py --verbose       # 打印每步实际发现
python tests/run_regression.py --conversation  # 追加 4 个对话级映射用例
python tests/mutation_check.py                 # 变异测试：故意破坏闸门，确认测试转红
```

期望输出：

```text
tests: 27  steps: 55/55 passed  failed_tests: 0
REGRESSION_STATUS=PASS
```

加 `--conversation` 时为 `27 tests / 63 steps`（含 4 个对话级映射用例）。

仅"全部通过"不构成证据。`tests/mutation_check.py` 会故意破坏九处闸门
（禁用量化检查 / 禁用防火墙 / 强制过程干净 / 禁用前视泄漏判定 /
复盘退回只读旧字段 / Brier 退回区间命中 / 忽略结果失效码 / 让裸 `actual` 继续评分 /
只评修订值忽略当时公布值），确认*预期的那几个*测试会转红。
当前 **9/9 被捕获** —— 若某个变异后仍然全绿，说明那批测试没在真正检验它。
原理见 [`docs/design-notes.md`](docs/design-notes.md) 附录 A。

---

## 本版修复（v0.2.2）

一次**定向可靠性修复**。不重构架构、不新增 roadmap 大功能，只补两个工程断点：

**1）自然语言 → JSON 状态。** 用户不会说 JSON。用户说"大概 100"，系统需要
`base_value: 100`，但**单位不能猜**。新增 [`references/state-extraction.md`](references/state-extraction.md)
给出逐字段映射表，并确立核心原则：

> **未检查 ≠ 已通过。** 字段缺席表示还没有检查过，不表示检查了、结论是否。
> 涉及存量流量/量价分解的判定字段是三态的：`true` / `false` / `"unknown"`。
> 缺席报 `GATE_FIELD_UNCHECKED`，`"unknown"` 报 `GATE_FIELD_UNKNOWN`——两者都是 BLOCK。

**2）预测结果 → 多指标可靠复盘。** 旧实现把任何结果都算在第一个指标上，
且把"没有结果"误判成"没命中"。现在：

- 逐指标裁决 + 案例级汇总（`indicator_results[]` / `case_summary`）
- **未知 ≠ 未命中**：新增 `PROCESS_GOOD_OUTCOME_UNKNOWN` 等三态结果
- 作用域隔离：某指标的问题不污染其他指标，除非是 case 级致命缺陷
- 新增 [`references/reveal-protocol.md`](references/reveal-protocol.md)：来源层级、
  口径核验、统计修订（`as_reported_then` 与 `latest_revised` 必须同时保留）

另外还修了三处：**完整日期期限算法**（`2010-12-31 → 2013-01-01` 是 2.00 年而非 3 年）、
**历史序列门槛的替代路径**（有机制可降级为 WARN）、
**信息防火墙双层时间**——区分数据所属期与发布时间，新增 `FIREWALL_LOOKAHEAD_LEAKAGE`
拦截"所属期在截点前、但截点当天还没公布"的隐蔽前视泄漏。

前台呈现也改为**优先级 P0—P7**：一次只说最多 3 条最关键发现，不再把数十条 BLOCK 摊给用户。

---

## 已知限制

- 脚本只覆盖**可判定**规则；提问质量与语气依赖人工回归
- 阈值（CAGR 25%、区间相对宽度 5% 等）为经验取值，非统计结论
- 信息防火墙依赖用户如实申报材料日期与**发布时间**（不只是所属期）
- 自然语言抽取依赖教练判断：脚本只能断言"抽取后的字段"是否符合规则，
  `state-extraction.md` 提供的是**规范**而非自动解析器
- 来源层级判定基于关键词匹配，措辞差异可能漏判（故为 WARN 而非 BLOCK）
- `scored_event` 每个指标只允许**一个** primary 命题；多个命题须拆成多个指标
  （本版不做 `scored_predictions[]`）
- 结果记录若只有裸数值 `actual` 而无 `actual_value`，目标期校验无从进行；
  v0.2.4 起这类记录被标记 `LEGACY_UNVERIFIED`，**只可查看、不可参与正式评分**
- **状态顺序不由代码强制**：`judge_checks.py` 只做规则判定，不校验 `stage` 迁移，
  「BLOCK 期间不得推进状态」靠教练自律
- **`check_reply()` 不校验陈述真实性**：能拦抢答 / 剧透 / 问题过多 / 夸奖，
  但发现不了"教练把实算结果说反了"
- **零指标案例被报为 `ADMISSION_OK`**（流程缺口，不造成评分错误）
- **自检自测不能替代盲测**：同一执行者在自己工作区里跑完锁定 → 揭晓时，
  `FORECAST_LOCK_INTEGRITY=PASS` 只证明流程被遵守，不能证明执行者无后截点知情
- 持久化依赖运行环境；档案默认写用户工作区

完整列表见 [`docs/design-notes.md`](docs/design-notes.md) 第五节。

---

## Roadmap

- [ ] `v0.3` 案例档案的自动读写（`new_case.py` / `update_case.py`）
- [ ] `v0.3` 跨案例校准曲线（累计 Brier 分数与过度自信诊断）
- [ ] `v0.4` 企业对象的专用分解模板（收入 × 利润率、市占率 × 市场规模）
- [ ] `v0.4` V1→V2 版本链的自动比对（识别更新过猛 / 更新不足）
- [ ] `v0.5` 判断原则库的检索与去重
- [ ] 可选：与本地日历/提醒集成，支持每日一题的训练节奏

---

## License

MIT
