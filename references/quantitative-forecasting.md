# 定量预测与准入闸门（quantitative-forecasting）

> 本文件是 `ADMISSION_GATE` 与 `CHECKS` 两个状态的执行依据。

---

## 一、预测准入门槛（十查）

在**正式数值预测之前**，对每个指标逐项检查。一次只向用户指出最重要的 1—3 个缺口。

| # | 检查项 | 判定标准 | 失败码 |
|---|---|---|---|
| 1 | 基期值存在 | 有明确的基期数值 | `GATE_BASE_MISSING` |
| 2 | 基期口径明确 | 如"当年价/全市常住人口" | `GATE_CALIBER_MISSING` |
| 3 | 单位明确 | 亿元 / 万吨 / 万人 / % | `GATE_UNIT_MISSING` |
| 4 | 有历史变化序列，**或**合法替代推导路径 | 至少 3 个历史时点；不足时须同时声明 `history_basis` 与 `alternative_mechanism` | `GATE_NO_HISTORY_SERIES`（无替代路径或只声明不写机制）/ `LIMITED_HISTORY`（有替代路径，降级为 WARN） |
| 5 | 主要驱动变量已知 | 列出推动该指标变化的关键变量 | `GATE_DRIVER_MISSING` |
| 6 | 主要约束变量已知 | 列出限制其变化的变量（产能、政策、资源、需求） | `GATE_CONSTRAINT_MISSING` |
| 7 | 存量/流量**已判定** | 三态字段 `stock_flow_relevant`；若涉及，须 `stock_flow_resolved: true` | `GATE_FIELD_UNCHECKED`（未判定）/ `GATE_FIELD_UNKNOWN`（标为 unknown）/ `GATE_STOCK_FLOW_UNRESOLVED`（涉及但未区分） |
| 8 | 数量/价格**已判定** | 三态字段 `quantity_price_relevant`；若涉及，须 `quantity_price_split: true` | `GATE_FIELD_UNCHECKED` / `GATE_FIELD_UNKNOWN` / `GATE_QUANTITY_PRICE_UNRESOLVED` |
| 9 | 最低基准率或可比参照 | 有同类对象/历史时期的参照 | `BASE_RATE_MISSING`（WARN） |
| 10 | 定性判断与数值一致 | 方向与幅度不矛盾 | `GATE_QUAL_QUANT_CONFLICT`（BLOCK） |

第 1—8 项与第 10 项缺失 → **禁止进入正式预测**。
第 9 项缺失 → 允许继续，但必须标记 `BASE_RATE_MISSING` 并**相应降低置信度**。

> 关键：检查 ≠ 代填。我指出"缺基期"，不指出"基期大概是 600 亿"。

### 1.1 三态字段：未检查 ≠ 已通过

第 7、8 项是**三态字段**，取值只有 `true` / `false` / `"unknown"`：

| 取值 | 规则层反应 |
|---|---|
| `true` | 触发对应的 resolved / split 检查 |
| `false` | 判定为不涉及，通过 |
| `"unknown"` | `GATE_FIELD_UNKNOWN`（BLOCK）——用户明确表示尚未判定 |
| **字段缺席** | `GATE_FIELD_UNCHECKED`（BLOCK）——**连"不知道"都还没确认** |

**不得因为用户没提到存量流量，就把字段默认填 `false`。** 那是默认放行。
缺席时教练的动作是**提一个针对性问题**，把它变成 `true` 或 `false`。

### 1.2 历史序列不足的替代路径

`MIN_HISTORY_POINTS = 3` 不是不可通融的死规则。若用户走了替代推导路径，
`history_basis` 取 `alternative` / `mechanism` / `capacity` / `order` / `share` / `contract` / `admin`
之一，**且**写清了 `alternative_mechanism`：

- 原 `GATE_NO_HISTORY_SERIES`（BLOCK）→ 降级为 `LIMITED_HISTORY`（WARN）。
- 若此时概率 ≥ 70% → 追加 `LIMITED_HISTORY_PROB_TOO_HIGH`（WARN），要求降概率或扩区间。
- 声明了路径却不写机制 → **仍按 BLOCK 处理**（"你说你有办法，但没说是什么办法"）。

---

## 二、分解族

对 GDP、收入、利润、财政、产业规模等，主动检查适用的基本分解。**只提示适用哪种分解结构，不填数。**

| 指标类型 | 分解 |
|---|---|
| 名义金额 | 数量 × 价格 |
| 利润 | 收入 × 利润率 |
| 城市总量指标 | 人口 × 人均指标 |
| 企业规模 | 市场规模 × 市占率 |
| 产出 | 产能 × 利用率 × 价格 |
| 财政 | 税基 × 实际税率 + 非税收入 |
| 零售/消费 | 人口 × 人均消费 × 渗透率 |

用法示例（我给的话术，不给答案）：

> "这个数字背后隐含了产量和价格两个假设，把它们分开写出来。"

---

## 三、存量与流量的区分

这是资源型城市案例中最常见的错误。

| 概念 | 类型 | 说明 |
|---|---|---|
| 探明储量 | 存量 | 地下有多少，是**上限** |
| 年产量 | 流量 | 每年采出多少，受产能、需求、价格、政策约束 |
| 累计产量 | 累积流量 | 历史开采总量 |
| 资产规模 | 存量 | 时点值 |
| 营业收入 | 流量 | 期间值 |

**储量 ≠ 未来产量。** 从储量到产量需要经过至少四个约束：产能建设、开采成本、运输、需求与价格。

允许的生产能力上限估算（仅作为约束）：

```text
可达年产量 ≤ min(产能, 需求/价格能支撑的产量, 政策允许产量)
```

---

## 四、隐含 CAGR 反推（强制步骤）

用户提交任何预测值后，**必须**反推其隐含年均复合增速：

```text
CAGR = (Future / Base)^(1/n) − 1
```

其中 n 为年数。若基期或预测值为负，改用绝对变化量与区间讨论，不得直接套用。

**n 怎么算（v0.2.2 修正）**：截点与终点都是**完整日期**时，用真实天数折算：

```text
n = (forecast_to − historical_cutoff).days / 365.25
```

只有当日期不完整（仅年份）时才退回年份差。**不能直接用年份相减**：
`2010-12-31 → 2013-01-01` 实际只有 732 天 ≈ **2.00 年**，按年份差会算成 3 年，
使隐含 CAGR 被系统性低估约三分之一。

### 反推后的五项检查

1. 是否符合用户自己前面的定性判断？
2. 历史上该对象是否出现过这种增速？
3. 类似城市/企业是否常见？（基准率）
4. 什么现实机制能支撑它？
5. 是否依赖极端条件？

### 常用判定阈值（参照，非禁令）

| 隐含 CAGR | 处理 |
|---|---|
| \|CAGR\| ≤ 10% | 常规，仍需说明机制 |
| 10% < \|CAGR\| ≤ 25% | 要求明确写出驱动机制与基准率 |
| \|CAGR\| > 25% | 触发 `EXTREME_GROWTH_UNJUSTIFIED`，必须给出罕见机制说明，否则建议下调或放宽区间 |
| 方向与定性判断相反 | 触发 `GATE_QUAL_QUANT_CONFLICT`，**硬拦截** |

### 允许与不允许

| 我允许 | 我不允许 |
|---|---|
| 帮算 CAGR | 替用户选增长率 |
| 检查加减乘除与百分比 | 自己生成完整预测模型让用户照抄 |
| 检查单位换算（如吨↔万吨、亿元↔万元） | 替用户决定口径 |
| 反推"要达到这个数需要什么条件" | 直接给出"合理值应该是多少" |

---

## 五、基准率 / Outside View

### 5.1 为什么需要

个案叙事（inside view）天然导致极端预测。基准率提供现实约束。

### 5.2 用户至少要做到

对一个较大的预测，能回答：

> "类似的城市、行业或企业中，这种变化通常有多常见？"

### 5.3 参照组的构造思路（提示方向，不给结论）

- 同期同类城市（人口规模、产业结构相近）
- 同行业企业的历史增速分布
- 同一对象自身的历史增速分布
- 该地区长期平均增速

### 5.4 缺基准率时的处理

判定顺序：

1. 若缺 → 标记 `BASE_RATE_MISSING`（WARN，非 BLOCK）
2. 且用户给出的概率 ≥ 70% → 追加 `BASE_RATE_MISSING_PROB_TOO_HIGH`，要求降置信度或补参照
3. 不禁止继续，但档案与复盘中必须记录该缺陷

原则：**基准率不是答案，它只是防止用户沉迷个案故事。**

---

## 六、模型复杂度原则

优先训练**简单、透明、可解释**的方法。

```text
Future = Base × (1 + g)^n
```

变量结构不同时可用其他形式（如利润率法、市占率法），但：

> 预测越复杂，越要能解释每一个主要假设从哪里来。

若用户写出多变量模型，逐一追问每个参数的来源。**来源不明 = 未通过准入。**

---

## 七、单位与口径的常见陷阱

| 陷阱 | 说明 |
|---|---|
| 当年价 vs 不变价 | 名义增速含通胀，实际增速不含；混用会导致大幅偏差 |
| 常住人口 vs 户籍人口 | 城市人均指标的分母不同，结果差数十个百分点 |
| 全市 vs 市辖区 | 行政区划口径差异 |
| 万吨 vs 亿吨 | 差 10000 倍 |
| 亿元 vs 万元 | 差 10000 倍 |
| 累计值 vs 单期值 | 固定资产投资等常以累计口径公布 |
| 存量余额 vs 新增额 | 贷款、债务类指标 |

发现单位或口径不一致 → 立即中断，先统一口径。

---

## 八、发现的呈现优先级（P0—P7）

一次检查可能产出 30+ 条发现。若全部摊给用户，他会淹没在清单里，训练无法推进。
因此规则层为每条发现分配优先级，前台**一次只说最多 3 条**（去重后）。

| 级别 | 主题 | 典型代码 |
|---|---|---|
| **P0** | 信息污染 / 时间边界 / 抢答——**污染即整轮作废** | `CUTOFF_NOT_SET`、`FIREWALL_CONTAMINATION`、`FIREWALL_LOOKAHEAD_LEAKAGE`、`COACH_ANSWER_GIVING` |
| **P1** | 基期 / 口径 / 单位 / 字段未判定 | `GATE_BASE_MISSING`、`GATE_CALIBER_MISSING`、`GATE_UNIT_MISSING`、`GATE_FIELD_UNCHECKED`、`GATE_FIELD_UNKNOWN` |
| **P2** | 定性定量明显矛盾 | `GATE_QUAL_QUANT_CONFLICT`、`GATE_QUAL_QUANT_TENSION` |
| **P3** | 推导链缺失 / 提交字段不全 | `GATE_NO_HISTORY_SERIES`、`GATE_DRIVER_MISSING`、`GATE_CONSTRAINT_MISSING`、`LOCK_FIELD_MISSING`、`PROB_NO_PROPOSITION`、`REVEAL_FIELD_MISSING` |
| **P4** | 模型结构（存量流量 / 量价分解） | `GATE_STOCK_FLOW_UNRESOLVED`、`GATE_QUANTITY_PRICE_UNRESOLVED` |
| **P5** | 概率逻辑 | `PROB_UNIFORM`、`PROB_PRECISION`、`PROB_SUM`、`PROB_LOGIC_SUBSET` |
| **P6** | 基准率 | `BASE_RATE_MISSING`、`LIMITED_HISTORY_PROB_TOO_HIGH` |
| **P7** | 优化项与信息类 | `LEVEL1_*`、`EXTREME_GROWTH_UNJUSTIFIED`、`IMPLIED_CAGR_COMPUTED`、`SOURCE_DATE_LEGACY_FIELD` |

规则：

1. 先处理 P0 — 只要存在 P0 级 BLOCK，就不谈别的。
2. 同级别内 BLOCK 优先于 WARN。
3. 前台**跳过纯信息项**（`ADMISSION_OK` / `IMPLIED_CAGR_COMPUTED` / `REPLY_OK` 等）。
4. 完整清单仍写入档案，复盘时引用。

> 教练的动作是"一次推进一个瓶颈"，不是"一次汇报所有问题"。
