# 神木 2010 回归案例（shenmu-2010-regression-case）

> **本文件的性质**：这是第一轮失败过程的**结构重建**，用作回归测试的参照。它不是统计数据档案，其中的数值为结构占位，**真实历史结局被刻意排除在外**（防止污染后续训练轮次）。

对应夹具：`tests/cases/test-11-shenmu-2010-regression.json`

---

## 一、案例设定

| 项目 | 值 |
|---|---|
| 对象 | 神木（资源型城市） |
| 类型 | city |
| 历史截点 | 2010-12-31 |
| 预测期限 | 2015-12-31（5 年） |
| 第一轮实际难度 | 近乎 Level 1 的做法，却配了 Level 3 的野心 |

---

## 二、第一轮的失败清单（用户自述）

| # | 问题 | 错误层级 |
|---|---|---|
| 1 | 没有先核实 2010 年 GDP 基期 | 事实 / 基期意识 |
| 2 | 没有先核实财政收入基期 | 事实 / 基期意识 |
| 3 | 人口预测缺乏人口历史趋势支撑 | 事实 / 数据 |
| 4 | 数字很多是凭感觉 | 推理 / 参数 |
| 5 | 定性"经济继续发展"与部分预测数字矛盾 | 推理 |
| 6 | 四个不同预测统一给 85% | 概率 |
| 7 | 没有做隐含 CAGR 检查 | 数学 |
| 8 | 没有建立基准率 | 基准率 |
| 9 | 没有区分资源储量与未来产量增长 | 模型 / 存量流量 |
| 10 | 没有充分考虑"量 × 价" | 模型 / 分解 |

---

## 三、拦截映射（新系统如何拦住它）

| 原问题 | 触发码 | 级别 | 前台话术（教练实际会说的话） |
|---|---|---|---|
| 1、2 缺基期 | `GATE_BASE_MISSING` | BLOCK | 先补这个指标的基期值。现在还不能开始预测。 |
| 3 人口无历史趋势 | `GATE_NO_HISTORY_SERIES` | BLOCK | 你的预测需要至少三个历史时点，现在一个都没有。 |
| 4 凭感觉 | `LOCK_FIELD_MISSING`、`PROB_NO_PROPOSITION` | BLOCK | 这个数字的推导过程写一下；另外你的概率要写成命题。 |
| 5 定性定量矛盾 | `GATE_QUAL_QUANT_CONFLICT` | BLOCK | 你写的是"继续发展"，但数字隐含年均 −4.4%。这两句不能同时成立。 |
| 6 统一 85% | `PROB_UNIFORM` | WARN | 四个指标的不确定性来源不同，为什么恰好都是 85%？ |
| 7 无隐含 CAGR | `IMPLIED_CAGR_COMPUTED`（INFO）+ `EXTREME_GROWTH_UNJUSTIFIED`（WARN） | 必执行 | 系统在任何预测提交后强制反推 CAGR，不再依赖用户自觉。 |
| 8 无基准率 | `BASE_RATE_MISSING`、`BASE_RATE_MISSING_PROB_TOO_HIGH` | WARN | 没有参照组却给 85%，先把置信度降下来或补一个基准率。 |
| 9 储量当产量 | `GATE_STOCK_FLOW_UNRESOLVED` | BLOCK | 储量是存量，产量是流量。中间那几步靠什么支撑？ |
| 10 未拆量价 | `GATE_QUANTITY_PRICE_UNRESOLVED` | BLOCK | 这个数字背后产量和价格分别假设了什么？ |
| 附加：难度越界 | `LEVEL1_TOO_MANY_INDICATORS`、`LEVEL1_HORIZON_TOO_LONG` | WARN | 第一轮就 4 个指标 5 年期，先把 2 个指标 3 年跑通。 |

**测试结果**：该夹具触发 36 个 BLOCK 发现、6 个 WARN 发现，`lockable=NO`。

---

## 四、复盘裁决

```text
verdict           : PROCESS_DEFECTIVE_OUTCOME_MISS
process_clean     : False
error_attribution : FACTUAL, CALIBER, REASONING, MODEL, PROBABILITY, BASE_RATE_IGNORED
interval_hit      : False
```

注意：这一轮**不是因为结果错才被判失败**。判定依据是过程缺陷——即使结果碰巧命中，裁决也会是 `LUCKY_ACCURATE`。

---

## 五、这一轮沉淀的可迁移原则（示例形态）

> 注：以下为示例格式。真实训练中原则必须由用户自己写出，教练只帮压缩表达。

**P-001 · 资源型对象的量价拆分**
预测资源型城市或企业的收入，必须先拆产量与价格两条线；只看储量会系统性高估产量增速。

**P-002 · 先基期后增速**
任何"五年后达到 X"的说法，在基期未核实前都没有检验价值。

**P-003 · 概率不是信心刻度**
四个不同变量共用一个概率，通常说明概率是从情绪而非不确定性来源推出来的。

---

## 六、回归测试的判定标准

新版本遇到**同一形态的输入**时，必须满足：

1. 在用户提交最终预测**之前**触发全部 36 个 BLOCK 中的核心闸门
2. `lockable=NO`，不得进入揭晓
3. 前台只输出其中**最关键的一条**（基期缺失优先），不得把 36 条摊给用户
4. 复盘时归因必须覆盖 `FACTUAL` / `REASONING` / `MODEL` / `PROBABILITY` / `BASE_RATE_IGNORED`

不满足任一条，视为回归失败。

---

## 七、使用方式

```bash
python tests/run_regression.py
python scripts/judge_checks.py case tests/cases/test-11-shenmu-2010-regression.json
python scripts/judge_checks.py postmortem tests/cases/test-11-shenmu-2010-regression.json
```

**不要**把本案例的真实历史结局补进来。这一轮的价值在于"错误在进入最终预测前被拦住"，而不是"重新替用户预测神木"。
