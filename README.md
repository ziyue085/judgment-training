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
| 概率必须对应命题 | `P(2015 年 GDP ∈ [900,1100]) = 60%`，不是"GDP：60%" |
| 区间优先于点 | 中心估计只是中枢，不是答案 |
| 基准率约束叙事 | 个案故事必须与同类对象的常态分布对照 |
| 过程与结果分开评价 | 结果正确 + 推理糟糕 ≠ 好预测<br>结果错误 + 推理合理 + 概率诚实 = 可能是好预测 |
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
3. **仓库纪律** —— 本仓库的文档与测试夹具**不含任何真实历史结局**，包括神木回归案例

---

## 神木 2010 回归案例

第一轮训练（神木 @ 2010-12-31 → 2015）留下了十类典型错误：未核实 GDP 与财政收入基期、人口预测无历史趋势、数字凭感觉、定性"继续发展"与数字矛盾、四个预测统一 85%、无隐含 CAGR 检查、无基准率、储量当产量、未拆量价。

它现在是一个**可执行的回归测试**：

```bash
python scripts/judge_checks.py case tests/cases/test-11-shenmu-2010-regression.json
```

该夹具触发 **39 个 BLOCK + 8 个 WARN**，`lockable=NO` —— 即新版本必须在错误进入最终预测之前将其拦住。

详见 [`examples/shenmu-2010-regression-case.md`](examples/shenmu-2010-regression-case.md)。

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

前台呈现也改为**优先级 P0—P7**：一次只说最多 3 条最关键发现，不再把 39 条 BLOCK 摊给用户。

---

## 项目结构

```text
judgment-training/
├─ SKILL.md                          主文件（精炼，4130 字符）
├─ README.md
├─ CHANGELOG.md
├─ LICENSE
├─ .gitignore
├─ references/                       按需加载的方法论
│  ├─ methodology.md                 训练目标 / 难度 / 提问设计 / 动态更新 / 复盘六象限
│  ├─ coaching-rules.md              职责边界 / 防火墙话术 / 越界场景 / 前台纪律
│  ├─ probability-calibration.md     命题化 / 逻辑一致性 / 校准评分
│  ├─ quantitative-forecasting.md    准入十查 / 分解族 / 隐含 CAGR / 基准率 / P0—P7
│  ├─ prediction-record-template.md  档案 schema / 提交字段 / 多指标复盘模板
│  ├─ state-extraction.md            自然语言 → 结构化状态映射（未检查 ≠ 已通过）
│  └─ reveal-protocol.md             揭晓协议：来源层级 / 口径核验 / 统计修订
├─ examples/
│  ├─ example-session.md             一轮完整对话（虚构对象）
│  └─ shenmu-2010-regression-case.md 失败案例与拦截映射
├─ tests/
│  ├─ test-cases.md                  18 个用例说明
│  ├─ conversation-cases.md          4 个对话级映射用例说明
│  ├─ regression-checklist.md        自动 + 变异 + 人工回归清单
│  ├─ run_regression.py              测试运行器（含 --conversation）
│  ├─ cases/*.json                   18 个可执行夹具
│  └─ conversation/*.json            4 个自然语言映射用例
├─ scripts/
│  └─ judge_checks.py                确定性规则层
└─ docs/
   └─ design-notes.md                设计取舍与已知限制
```

---

## 运行测试

```bash
python tests/run_regression.py                 # 18 tests / 41 steps
python tests/run_regression.py --verbose       # 打印每步实际发现
python tests/run_regression.py --conversation  # 追加 4 个对话级映射用例
```

期望输出：

```text
tests: 18  steps: 41/41 passed  failed_tests: 0  (含对话映射 4 个)
REGRESSION_STATUS=PASS
```

仅"全部通过"不构成证据。`tests/regression-checklist.md` 的 B 节要求做**变异测试**：故意破坏四处闸门，确认测试会转红（4/4 被捕获）。方法见 [`docs/design-notes.md`](docs/design-notes.md) 附录 A。

---

## 已知限制

- 脚本只覆盖**可判定**规则；提问质量与语气依赖人工回归
- 阈值（CAGR 25%、区间相对宽度 5% 等）为经验取值，非统计结论
- 信息防火墙依赖用户如实申报材料日期与**发布时间**（不只是所属期）
- 自然语言抽取依赖教练判断：脚本只能断言"抽取后的字段"是否符合规则，
  `state-extraction.md` 提供的是**规范**而非自动解析器
- 来源层级判定基于关键词匹配，措辞差异可能漏判（故为 WARN 而非 BLOCK）
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
