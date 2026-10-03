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
| 附加（v0.2.2 新增）：字段未判定 | `GATE_FIELD_UNCHECKED` | BLOCK | GDP 与财政收入这两项，涉及存量流量/量价分解的判断还没做过——不能因为没说就当成"无关"。 |
| 附加（v0.2.3 修订）：基期公布时间不明 | `BASE_PUBLICATION_UNKNOWN` | BLOCK | 这个基期值是哪一年公布的？截点当天拿不到就不能用——有基期值却说不清公开时间，不能继续。 |
| 附加（v0.2.3 新增）：概率没绑定命题 | `PROB_SCORED_EVENT_MISSING` | BLOCK | 你给了 85% 的概率，但它押的是哪句话？区间、阈值还是方向？没写清楚，这个概率后面没法评分。 |

**测试结果**：该夹具触发 **45 个 BLOCK 发现、6 个 WARN 发现**，`lockable=NO`。

> 计数演进：v0.2.1 为 36 BLOCK / 6 WARN；v0.2.2 新增三态字段闸门（`GATE_FIELD_UNCHECKED`）后为 39 BLOCK / 8 WARN；
> v0.2.3 把「基期有值但公开时间不明」从 `SOURCE_DATE_UNKNOWN`（WARN）升级为 `BASE_PUBLICATION_UNKNOWN`（BLOCK），
> 并新增「概率必须绑定 scored_event」闸门（`PROB_SCORED_EVENT_MISSING`），故为 45 BLOCK / 6 WARN。
> 注意 WARN 由 8 降到 6：原 `SOURCE_DATE_UNKNOWN` 的 WARN 已升级为 BLOCK，不再重复计数。

---

## 四、复盘裁决

```text
case_summary.overall : CASE_CONSISTENT_DEFECTIVE
outcome_status       : UNKNOWN   (hit=0 miss=0 unknown=4)
verdict（逐指标）    : PROCESS_DEFECTIVE_OUTCOME_UNKNOWN ×4
error_attribution    : BASE_RATE_IGNORED, CALIBER, FACTUAL, MODEL, PROBABILITY, REASONING
interval_hit         : None
scored_event_hit     : None   (v0.2.3 起与 interval_hit 分开输出)
brier                : None   (无实际值 ⇒ 无评分，不按 0 或 1 硬填)
```

注意两点：

1. 这一轮**不是因为结果错才被判失败**。判定依据是过程缺陷——即使结果碰巧命中，裁决也会是 `LUCKY_ACCURATE`。
2. v0.2.2 起，当案例**没有提供结果记录**时，裁决是 `PROCESS_DEFECTIVE_OUTCOME_UNKNOWN`
   ——缺陷已足以定论"当时不应锁定"，**无须知道结果**。旧版会把它误判成 `..._MISS`（未知 ≠ 未命中）。
3. v0.2.3 起，`interval_hit`（预测区间是否覆盖实际值）与 `scored_event_hit`（概率真正押的那个命题是否成立）
   是两个独立结果，分开输出。本案例没有实际值，两者均为 `None`，Brier 同样为 `None`——**不计算，而不是记为 0**。

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

1. 在用户提交最终预测**之前**触发全部 45 个 BLOCK 中的核心闸门
2. `lockable=NO`，不得进入揭晓
3. 前台只输出其中**最关键的一条**（基期缺失优先），不得把 45 条摊给用户
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
