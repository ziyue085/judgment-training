# E2E B · 真实历史案例全流程（real-historical-full-run）

> ⚠ **`DO_NOT_USE_FOR_REAL_TRAINING`** —— 本用例只作工程测试。
> 未来**不得**把它作为用户正式训练题重复使用；也不得进入正式选题池。

- 对象：山东省淄博市 · 截点 `2012-12-31` · 目标期 `2015-12-31`（3.0 年）· Level 1 · 2 指标
- 指标：地区生产总值（亿元）、人均地区生产总值（元/人）

## 一、Forecast 阶段的允许清单（先写死，再预测）

| id | 事实 | 所属期 | 发布时间 | 来源 | 用于预测 |
|---|---|---|---|---|---|
| A1 | 淄博市 2011 年地区生产总值 = 3280.23 亿元 | 2011 | 2012-02-16 | 《2011年淄博市国民经济和社会发展统计公报》（淄博市统计局，2012-02-16） | 是 |
| A2 | 淄博市 2011 年人均地区生产总值 = 72380 元 | 2011 | 2012-02-16 | 《2011年淄博市国民经济和社会发展统计公报》（淄博市统计局，2012-02-16） | 是 |
| A3 | 淄博市地区生产总值 2007—2011 年度序列 | 2007—2011 | 各年度公报（2008-02 … 2012-02） | 各年度《淄博市国民经济和社会发展统计公报》 | 是 |
| X1 | 淄博市 2015 年地区生产总值 = 4130.2 亿元 | 2015 | 2016-03-01 | 《2015年淄博市国民经济和社会发展统计公报》（淄博市统计局，2016-03-01） | 否（outcome 阶段） |
| X2 | 淄博市 2015 年人均地区生产总值 = 89235 元 | 2015 | 2016-03-01 | 《2015年淄博市国民经济和社会发展统计公报》（淄博市统计局，2016-03-01） | 否（outcome 阶段） |

> A3 的口径说明：历年的序列值原本由**各年度公报**发布（均在截点前）；
> 本次交叉核对使用到的《山东统计年鉴 2013》汇编发布于 2013 年，**晚于截点**，
> 因此不计入允许清单。

## 二、LOCK：预测锁定与完整性

- LOCK 阶段 `case` 模式：BLOCK=0 WARN=1 lockable=YES
- 锁定档案 `tests/e2e/locked-forecast.json`
- `LOCKED_FORECAST_SHA256` = `b01f29bdce1863f77066f4455881c59d09310a6157f219ad9f2cd6149f44d665`
- 揭晓后重新计算哈希 = `b01f29bdce1863f77066f4455881c59d09310a6157f219ad9f2cd6149f44d665`
- **`FORECAST_LOCK_INTEGRITY` = `PASS`**（锁定后预测未被改写）

| 级别 | code | 作用域 | 信息 |
|---|---|---|---|
| WARN | `LIMITED_HISTORY` | 指标「人均地区生产总值」 | 历史序列只有 0 个时点，未走趋势外推，采用替代推导路径（alternative）。 |
| INFO | `ADMISSION_OK` | <case> | 无 BLOCK 级缺口，可进入下一状态。 |
| INFO | `IMPLIED_CAGR_COMPUTED` | 指标「人均地区生产总值」 | 隐含 CAGR = 4.25%/年（2.99795 年）。 |
| INFO | `IMPLIED_CAGR_COMPUTED` | 指标「地区生产总值」 | 隐含 CAGR = 5.94%/年（2.99795 年）。 |

## 三、REVEAL 核验

- 揭晓核验：BLOCK=0 WARN=0
  - `INFO` `REVEAL_OK` @ <case>：揭晓记录字段与口径核验通过。

揭晓记录（每项都带所属期 / 发布时间 / 来源）：

| 指标 | 实际值 | 口径 | 期末 | 来源 | 发布时间 | 修订状态 |
|---|---|---|---|---|---|---|
| 地区生产总值 | 4130.2 | 全市、当年价 | 2015-12-31 | 《2015年淄博市国民经济和社会发展统计公报》（2016-03-01） | 2016-03-01 | initial |
| 人均地区生产总值 | 89235 | 全市、当年价、常住人口分母 | 2015-12-31 | 《2015年淄博市国民经济和社会发展统计公报》（2016-03-01） | 2016-03-01 | initial |

## 四、POSTMORTEM 裁决

- `outcome_status` = `REVEALED` · `case_summary.overall` = `CASE_CONSISTENT_CLEAN`

| 指标 | 概率 | 预测区间 | 评分命题 | 实际值 | 区间命中 | 命题命中 | Brier | 裁决 |
|---|---|---|---|---|---|---|---|---|
| 地区生产总值 | 0.6 | [3700, 4100] | {"type": "threshold", "op": ">", "value": 3900} | 4130.2 | False | True | 0.16 | PROCESS_GOOD_OUTCOME_HIT |
| 人均地区生产总值 | 0.6 | [78000, 86000] | {"type": "interval", "low": 78000, "high": 86000} | 89235 | False | False | 0.36 | PROCESS_GOOD_OUTCOME_MISS |

> 注意地区生产总值：**区间未命中、评分命题命中**——这正是 v0.2.3 §8 要分开表达的
> 两件事。Brier 只针对用户真正押的命题（> 3900 亿元）。

## 五、Fault Injection（对同一个已锁定案例）

| 情形 | outcome_status | valid | 失效码 | 区间命中 | 命题命中 | Brier | 裁决 |
|---|---|---|---|---|---|---|---|
| Fault A · 错误年份（期末 2014-12-31） | `INVALID` | False | ['REVEAL_TARGET_PERIOD_MISMATCH'] | None | None | None | `PROCESS_GOOD_OUTCOME_INVALID` |
| Fault B · 错误口径（不变价） | `INVALID` | False | ['REVEAL_CALIBER_MISMATCH'] | None | None | None | `PROCESS_GOOD_OUTCOME_INVALID` |
| Fault C · 只有裸 actual | `LEGACY_UNVERIFIED` | False | ['LEGACY_UNVERIFIED'] | None | None | None | `PROCESS_GOOD_OUTCOME_INVALID` |
| 修正后 · 正确 outcome | `VALID` | True | — | False | True | 0.16 | `PROCESS_GOOD_OUTCOME_HIT` |

- Fault A · 错误年份（期末 2014-12-31）：`actual_value` 仍保留为 `4130.2`（供阅读），但 `brier` 为 `None` —— **拒绝评分**。
- Fault B · 错误口径（不变价）：`actual_value` 仍保留为 `4130.2`（供阅读），但 `brier` 为 `None` —— **拒绝评分**。
- Fault C · 只有裸 actual：`actual_value` 仍保留为 `4130.2`（供阅读），但 `brier` 为 `None` —— **拒绝评分**。
- 修正后：`actual_value=4130.2`，`interval_hit=False`，`scored_event_hit=True`，`brier=0.16` —— 正常评分。

## 六、CLI 跨阶段一致性

| 检查项 | 结果 |
|---|---|
| object_consistent | PASS |
| indicator_names_match | PASS |
| scored_event_match | PASS |
| actual_value_match | PASS |
| caliber_and_period_used | PASS |
| indicator_scopes_exist | PASS |
| reveal_all_clear | PASS |
| reply_ok | PASS |

**`CLI_CROSS_STAGE_STATUS` = `PASS`**

## 七、已知限制（必须声明）

- **`SELF_RUN_MODEL_PRIOR_KNOWLEDGE_RISK = YES`**：本次执行者（同一个模型实例）
  在建立允许清单**之前**检索资料时，已经一并看到过 2015 年的结果数值。
  因此本轮的 `FORECAST_LOCK_INTEGRITY=PASS` 只能证明**流程被遵守**
  （允许清单先写死、预测文件哈希锁定后未变），
  **不能**证明执行者对后截点信息不知情。
- 结论：本用例是**程序性演练**，不是有效的盲测。
  真正有效的盲测必须在**无任何后截点检索史**的独立会话 / 独立 agent 中进行。
- 另：预测阶段的历史序列值取自各年度公报（均在截点前），
  但本次核对用到的省级年鉴汇编发布于截点之后，已明确排除在允许清单外。
