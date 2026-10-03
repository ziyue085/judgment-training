# 回归测试用例（test-cases）

> 每个用例都对应 `tests/cases/` 下的一个可执行夹具。全部由 `tests/run_regression.py` 断言。

```bash
python tests/run_regression.py            # 全部 JSON 夹具（27 tests / 55 steps）
python tests/run_regression.py --verbose  # 打印每个 step 的实际发现
python tests/run_regression.py --conversation   # 追加 4 个对话级映射用例（63 steps）
python tests/mutation_check.py            # 变异测试 A—I：确认测试不是空转
python scripts/judge_checks.py case tests/cases/test-11-shenmu-2010-regression.json
```

> v0.2.3 起，凡带 `probability` 的指标夹具都显式写出 `scored_event`，
> 其取值**按各夹具自己的 `proposition` 解析**，不是照抄预测区间 ——
> 详见用例 20 与 `references/state-extraction.md` 4.6 节。
> 断言能力也扩了：`expect.indicator_results` 可逐指标核对
> `interval_hit` / `scored_event_hit` / `brier` / `actual_value`。
>
> v0.2.4 起，凡参与复盘评分的夹具都使用**完整揭晓记录**
> （`actual_value` + `actual_unit` + `actual_caliber` + `actual_period` + `source`）。
> 裸 `actual` 会触发 `LEGACY_UNVERIFIED`，见用例 26。

---

## 用例总表

| # | 用例 | 夹具 | 期望行为 |
|---|---|---|---|
| 1 | 缺基期 | `test-01-missing-base.json` | 拦截，要求补基期 |
| 2 | 定性定量矛盾 | `test-02-qual-quant-conflict.json` | 反推隐含 CAGR 并指出矛盾 |
| 3 | 统一 85% | `test-03-uniform-85.json` | 要求分别解释概率 |
| 4 | 存量流量混淆 | `test-04-stock-flow.json` | 指出储量是存量、产量是流量 |
| 5 | 点预测过度精确 | `test-05-point-precision.json` | 要求给区间并重新校准 |
| 6 | 概率包含关系错误 | `test-06-prob-subset.json` | 指出概率逻辑错误 |
| 7 | 事后信息污染 | `test-07-post-cutoff-contamination.json` | 隔离，不允许进入预测 |
| 8 | 结果对但过程烂 | `test-08-lucky-accurate.json` | 判定为 `LUCKY_ACCURATE` |
| 9 | 结果错但过程合理 | `test-09-good-process-miss.json` | 判定为 `PROCESS_GOOD_OUTCOME_MISS` |
| 10 | AI 抢答 | `test-10-ai-answer-giving.json` | 拦截抢答、剧透、问题过多、夸奖 |
| 11 | 神木回归 | `test-11-shenmu-2010-regression.json` | 第一轮 8 类问题全部被拦 |
| 12 | 反向对照 | `test-12-clean-negative-control.json` | 干净案例**不得**被误拦 |
| 13 | 完整日期期限 | `test-13-full-date-horizon.json` | 按天折算期限，禁止年份相减 |
| 14 | 结果未知 | `test-14-outcome-unknown.json` | `*_OUTCOME_UNKNOWN`，未知 ≠ 未命中 |
| 15 | 多指标复盘 | `test-15-multi-indicator-postmortem.json` | 逐指标 hit / miss / unknown + 案例级汇总 |
| 16 | 发布时间晚于截点 | `test-16-publication-after-cutoff.json` | 前视泄漏 / 污染 / 已隔离 三种情形分开 |
| 17 | 历史不足与替代路径 | `test-17-limited-history-alt-mechanism.json` | 有机制降级 WARN，无机制仍 BLOCK |
| 18 | 三态字段映射 | `test-18-tri-state-mapping.json` | `true`/`false`/`"unknown"`/缺席 四种处置 |
| 19 | 揭晓 → 复盘贯通 | `test-19-reveal-postmortem-integration.json` | 揭晓写的 `actual_value` 复盘真能读到（v0.2.3） |
| 20 | Brier 事件绑定 | `test-20-brier-event-binding.json` | 概率评的是 `scored_event`，不是区间（v0.2.3） |
| 21 | 发布时间不明分半 | `test-21-publication-unknown-block.json` | 在用材料 BLOCK，已隔离材料不 BLOCK（v0.2.3） |
| 22 | 揭晓目标期校验 | `test-22-reveal-target-period.json` | 期末 ≠ `forecast_to` → BLOCK（v0.2.3） |
| 23 | 全链路贯通 | `test-23-full-pipeline-integration.json` | 草稿→可锁→揭晓→复盘四项同源（v0.2.3） |
| 24 | 无效揭晓不得评分 | `test-24-invalid-reveal-no-scoring.json` | 期间错位 → `outcome_valid=false`、命中与 Brier 全 `null`（v0.2.4） |
| 25 | 口径不符不得评分 | `test-25-caliber-mismatch-no-scoring.json` | 「数字正好落区间」也无效 → `REVEAL_CALIBER_MISMATCH`（v0.2.4） |
| 26 | 裸 legacy actual | `test-26-legacy-actual-unverified.json` | `{"actual": 500}` → `LEGACY_UNVERIFIED`、`brier=null`（v0.2.4） |
| 27 | 修订双轨评价 | `test-27-revision-dual-evaluation.json` | `as_reported_then` 与 `latest_revised` 两轨各算各的（v0.2.4） |

> **用例 08 / 09 / 15 的迁移（v0.2.4）**：这三个夹具原先使用裸 `actual`，
> 在新规则下会被判为 `LEGACY_UNVERIFIED` 而改变裁决。判定为**夹具本身不完整**
> （不是期望逻辑有误），故按 §11 升级为正式揭晓记录（补 `actual_unit` /
> `actual_caliber` / `actual_period` / `source` 等），**期望值一行未改**，
> 原有测试意图完整保留。legacy 路径改由用例 26 专门覆盖。

### 对话级用例（`tests/conversation/`，需 `--conversation`）

| # | 用例 | 夹具 | 期望行为 |
|---|---|---|---|
| C1 | 存量流量识别 | `conv-01-stock-flow.json` | 不从"没提到"推断出 `false` |
| C2 | 定性定量矛盾 | `conv-02-qual-quant.json` | 语气自信不放宽检查 |
| C3 | 统一概率 | `conv-03-uniform-85.json` | 三个指标同一概率 → `PROB_UNIFORM` |
| C4 | 凭感觉锁定 | `conv-04-sense-lock.json` | 缺命题与推导字段 → 不可锁定 |

说明见 `tests/conversation-cases.md`。

---

## 用例 1 · 缺基期

**用户输入**
> 我预测五年后 GDP 800 亿。

未提供当前 GDP 值、口径、单位。

**正确行为**：拦截。`GATE_BASE_MISSING` → `lockable=NO`。

**错误行为**：接受 800 亿并开始讨论增速。

---

## 用例 2 · 定性定量矛盾

**用户输入**
> 我认为未来五年会继续高速增长。（基期 600 亿，预测 500 亿）

**正确行为**：反推隐含 CAGR ≈ −3.58%/年，指出与"高速增长"矛盾。`GATE_QUAL_QUANT_CONFLICT`。

**关键**：不只说"矛盾"，要把隐含增速算给用户看。

---

## 用例 3 · 统一 85%

**用户输入**：GDP / 人口 / 产量 / 财政收入 四个预测全部 85%。

**正确行为**：`PROB_UNIFORM`，追问"为什么恰好相同？不确定性来源是否一样？"

**错误行为**：接受并在复盘中才发现。

---

## 用例 4 · 存量流量混淆

**用户输入**
> 煤炭储量还有 500 亿吨，所以未来五年产量肯定大增。

**正确行为**：`GATE_STOCK_FLOW_UNRESOLVED` —— 储量是存量，产量是流量，需要解释产能、运输、需求、价格等机制。

---

## 用例 5 · 点预测过度精确

**用户输入**
> 5 年后 GDP 恰好 817.3 亿，90%。

**正确行为**：`PROB_PRECISION` —— 精度超出数据本身能支撑的程度，要求给区间并重新校准。

**对照**：夹具第二个 step 给出区间 [750,900] + 55%，**不应**再触发该 WARN。

---

## 用例 6 · 概率包含关系错误

**用户输入**
```text
GDP > 1000：70%
GDP > 900：60%
```

**正确行为**：`PROB_LOGIC_SUBSET` —— 前者是后者的子集，概率不可能更高。

**对照**：夹具第二个 step 修正为 900→70% / 1000→60%，**不应**再触发。

---

## 用例 7 · 事后信息污染

历史截点 2010-12-31，用户引用 2013 年材料。

**正确行为**：`FIREWALL_CONTAMINATION` —— 只说明"这条不能用"，**不解释它意味着什么**。

**对照**：同一材料标记为隔离时，只输出 `FIREWALL_ISOLATED`（INFO），不报错。

---

## 用例 8 · 结果对但过程烂

用户纯凭直觉报一个数，碰巧接近。

**正确行为**：`LUCKY_ACCURATE`，归因为 `FACTUAL` / `PROBABILITY` / `BASE_RATE_IGNORED`，并写明"命中应归因于运气"。

**核心原则**：结果正确 + 推理糟糕 ≠ 好预测。

> v0.2.4 迁移：结果记录由裸 `actual` 升级为完整揭晓记录（否则会被判 `LEGACY_UNVERIFIED`）。
> 期望值未改，见用例总表脚注。

---

## 用例 9 · 结果错但过程合理

用户给出 55% 区间 [800,1000]，实际落在剩余 45% 内。

**正确行为**：`PROCESS_GOOD_OUTCOME_MISS`。

**核心原则**：不得因结果错就判过程失败。概率诚实的落空是好预测的正常代价。

> v0.2.4 迁移：同用例 8，结果记录升级为完整揭晓记录。

---

## 用例 10 · AI 抢答

**用户输入**
> 我不知道该怎么分析。

**错误行为**：直接给出一份完整的城市分析报告。
**正确行为**：给最小方法提示 + 第一问（夹具 step 2 即此形态，应通过）。

同时覆盖：
- 截点前泄露结局（`COACH_ANSWER_GIVING` / `COACH_SPOILER_RISK`）
- 一轮抛出 5 个问题（`COACH_TOO_MANY_QUESTIONS`）
- 夸奖用语（`COACH_PRAISE`）
- 揭晓状态下的正常陈述不得被误判

---

## 用例 11 · 神木 2010 回归案例

见 `examples/shenmu-2010-regression-case.md`。夹具逐条复现第一轮的失败形态，要求全部被拦。

v0.2.2 时该夹具触发 39 BLOCK + 8 WARN；v0.2.3 起为 **45 BLOCK + 6 WARN**：
2 条"基期公开时间不明"由 WARN 升级为 `BASE_PUBLICATION_UNKNOWN`(BLOCK)，
新增 4 条 `PROB_SCORED_EVENT_MISSING`(BLOCK)。
**变多不是变严格，是原来漏掉了两类缺陷**：这轮失败里，基期值的公开时间从没被记录过，
四个预测的概率也都没有绑定到任何命题。

---

## 用例 12 · 反向对照（防误报）

一个完全合格的 Level 1 案例：基期、口径、单位、历史序列、驱动、约束、量价拆分、命题、四个提交字段、基准率齐备。

**期望**：0 BLOCK、0 WARN、`lockable=YES`，且不得出现任何已知闸门码（夹具列出的 23 项 `must_not_codes`）。

**意义**：没有这个用例，闸门可以靠"全部拦截"通过所有测试。

---

## 用例 13 · 完整日期期限

截点 `2010-12-31`，终点 `2013-01-01`。按年份差会算成 3 年，实际只有 732 天 ≈ **2.00 年**。

夹具构造了一个只在"正确期限"下才触发 `EXTREME_GROWTH_UNJUSTIFIED` 的数值（基期 100、中心 170）：

- 正确（≈2.00 年）：CAGR ≈ 30.3% > 25% → 触发 WARN ✔
- 错误（3 年）：CAGR ≈ 19.3% < 25% → 不触发 ✘

**对照 step**：把终点改到 `2013-12-31`（≈3.00 年）后同样数值不再触发，证明差异来自期限算法本身。

---

## 用例 14 · 结果未知

过程干净、但没有提供任何结果记录。

**正确行为**：`PROCESS_GOOD_OUTCOME_UNKNOWN`，`outcome_status=UNKNOWN`，`n_unknown=1`。
**错误行为**：因为没有命中记录就判成 `PROCESS_GOOD_OUTCOME_MISS`。

**核心原则**：未知 ≠ 未命中。

---

## 用例 15 · 多指标复盘

三个指标，结果分别为命中、未知、未命中。

**正确行为**：
- `indicator_verdicts = [HIT, UNKNOWN, MISS]`
- `n_hit=1 n_miss=1 n_unknown=1`，`outcome_status=PARTIAL`
- `case_summary.overall = CASE_CONSISTENT_CLEAN`

**错误行为**：只评价 `indicators[0]`，或用一个总分掩盖指标间差异。

---

## 用例 16 · 发布时间晚于截点

三种情形必须分开：

| 情形 | 所属期 | 发布 | 期望 |
|---|---|---|---|
| 前视泄漏 | ≤ 截点 | > 截点 | `FIREWALL_LOOKAHEAD_LEAKAGE`（BLOCK） |
| 污染 | > 截点 | > 截点 | `FIREWALL_CONTAMINATION`（BLOCK） |
| 已隔离 | > 截点 | > 截点 | `FIREWALL_ISOLATED`（INFO），`lockable=YES` |

**核心原则**：所属期在截点之前 ≠ 截点当天已经公开。最典型的是"2010 年全年 GDP"——
该值通常 2011 年才发布。

---

## 用例 17 · 历史序列不足与替代推导路径

| step | 配置 | 期望 |
|---|---|---|
| 1 | `history_basis=capacity` + 写明机制 + 概率 0.72 | `LIMITED_HISTORY` + `LIMITED_HISTORY_PROB_TOO_HIGH`（均 WARN），**不** BLOCK |
| 2 | `history_basis=capacity` 但无机制 | `GATE_NO_HISTORY_SERIES`（BLOCK） |
| 3 | `history_basis=trend`，仅 1 个时点 | `GATE_NO_HISTORY_SERIES`（BLOCK） |

**核心原则**：规则可以通融，但通融必须换来"说清机制"与"降低概率"。

---

## 用例 18 · 三态字段映射

把 `state-extraction.md` 的核心原则变成可执行断言：

| step | `stock_flow_relevant` | 期望 |
|---|---|---|
| 1 | `"unknown"` | `GATE_FIELD_UNKNOWN`（BLOCK） |
| 2 | **缺席** | `GATE_FIELD_UNCHECKED`（BLOCK） |
| 3 | `false` | 通过，`lockable=YES` |

**核心原则**：未检查 ≠ 已通过。字段缺席不得被默认成 `false`。

---

## 用例 19 · 揭晓 → 复盘字段贯通

**要修的 bug**：揭晓写的是 `actual_value`，`postmortem()` 却只读 `actual`。
于是"揭晓成功"和"复盘当没揭晓"同时成立，裁决塌成 `OUTCOME_UNKNOWN`。

| step | 模式 | 期望 |
|---|---|---|
| 1 | `reveal` | 字段/口径/来源/期间全过 → `REVEAL_OK` |
| 2 | `postmortem` | `actual_value=800`、`interval_hit=true`、`verdict=PROCESS_GOOD_OUTCOME_HIT`、`outcome_status=REVEALED` |

**关键断言**：`indicator_results[0].actual_value == 800`。
**反证**：变异 E（复盘退回只读 `actual`）会让本用例转红。
**意义**：这条链一旦断，后面所有复盘结论都建立在"没有结果"之上。

---

## 用例 20 · Brier 必须绑定评分命题

三种形态，核心是 Case A。

| step | 区间 | 评分命题 | 概率 | 实际 | 期望 |
|---|---|---|---|---|---|
| A | [480,520] | `threshold > 420` | 0.80 | 450 | `interval_hit=false`、`scored_event_hit=true`、**`brier=0.04`** |
| B | [480,520] | `interval [480,520]` | 0.60 | 500 | `interval_hit=true`、`scored_event_hit=true`、`brier=0.16` |
| C | [480,520] | **缺失** | 0.70 | — | `PROB_SCORED_EVENT_MISSING`（BLOCK） |

**Case A 是全部要点**：区间没命中但命题命中了，Brier 的正确值是 `(0.8−1)²=0.04`，
若是 `0.64` 说明又退回用 `interval_hit` 评分了。
**反证**：变异 F 会让本用例转红。
**顺带**：Case A 的 `verdict` 也是 `PROCESS_GOOD_OUTCOME_HIT` ——
裁决评的同样是命题，不是你顺口给的区间。

---

## 用例 21 · 发布时间不明：分半处理

| step | 情形 | 期望 |
|---|---|---|
| A | 在用材料（`usable != false`）无 `published_at` | `SOURCE_DATE_UNKNOWN`（**BLOCK**） |
| B | 已隔离材料（`usable: false`）无 `published_at` | `SOURCE_DATE_UNKNOWN`（INFO），`lockable=YES` |
| C | 有 `base_value` 但无 `base_published_at` | `BASE_PUBLICATION_UNKNOWN`（**BLOCK**） |
| D | C 补齐 `base_published_at` 后 | 两个码都不出现，`lockable=YES` |

**为什么必须分半**：如果只做"缺时间就 BLOCK"，用户会为了推进流程伪造一个发布时间 ——
那比缺时间更危险。已隔离的材料本来就不参与预测，提示即可。
反过来，**正在使用**的材料缺时间只给 WARN 就等于永不设防。

---

## 用例 22 · 揭晓目标期校验

预测目标期固定为 `2013-12-31`。

| step | 结果期间 | 期望 |
|---|---|---|
| A | `actual_period_end = 2013-12-31` | `REVEAL_OK` |
| B | `actual_period_end = 2012-12-31` | `REVEAL_TARGET_PERIOD_MISMATCH`（**BLOCK**） |
| C | 旧档案写法 `actual_period = "2013"`（无 `_end`） | `REVEAL_OK`（年粒度兼容） |

**核心原则**：值对错了年份，命中判定整份作废 —— 620 是 2012 年的数，
它和"2013 年预测"的匹配程度没有意义。

---

## 用例 23 · 全链路贯通

把 `CASE→ADMISSION→FORECAST→LOCKABLE→REVEAL→POSTMORTEM` 串起来跑一遍。

| step | 模式 | 期望 |
|---|---|---|
| 1 | `case` | 只有数字没有推导 → `LOCK_FIELD_MISSING`，`lockable=false` |
| 2 | `case` | 补齐四字段 → `ADMISSION_OK`，`lockable=true` |
| 3 | `reveal` | 口径 / 来源 / 期间全过 → `REVEAL_OK` |
| 4 | `postmortem` | `interval_hit=false`、`scored_event_hit=true`、`brier=0.04`、`verdict=PROCESS_GOOD_OUTCOME_HIT`、`outcome_status=REVEALED` |

刻意选了"区间没命中、命题命中"的形态：**四项结论由同一份 `actual_value` 派生**，
任何一环断掉都会整体失败。变异 E 与 F 都会让本用例转红。

---

## 用例 24 · 无效揭晓不得评分（v0.2.4）

**要修的 bug**：`check_reveal()` 在 `REVEAL` 阶段会拦下期间错位的结果，
但 `postmortem()` **自己不验证** —— 绕过状态机直接复盘时，一份期间错位的结果照样被算分。

夹具构造：`forecast_to = 2013-12-31`，评分命题 `GDP > 420`，`actual_value = 450`、
但 `actual_period_end = 2012-12-31`。**单看 450 > 420 本该命中**，但期间错位。

| step | 模式 | 期望 |
|---|---|---|
| 1 | `reveal` | 报 `REVEAL_TARGET_PERIOD_MISMATCH`（BLOCK） |
| 2 | `postmortem` | `outcome_valid=false`、`outcome_status=INVALID`、命中与 Brier 全 `None` |

**关键断言**：`scored_event_hit is None`、`brier is None`、
`actual_value == 450`（保留展示）、`process_clean == True`、
`verdict == PROCESS_GOOD_OUTCOME_INVALID`。
**错误行为**：给出 `PROCESS_GOOD_OUTCOME_HIT` —— 那就等于用一个错年份的数字
给用户记一次命中。
**反证**：变异 G（忽略失效码）会让本用例转红。

---

## 用例 25 · 口径不符不得评分（v0.2.4）

预测的是**常住人口**口径，揭晓拿到的是**户籍人口**口径，数字恰好落在预测区间内。

| step | 模式 | 期望 |
|---|---|---|
| 1 | `reveal` | 报 `REVEAL_CALIBER_MISMATCH`（BLOCK） |
| 2 | `postmortem` | `outcome_valid=false`、`outcome_status=INVALID`、`brier=None` |

**核心原则**：**数字落进区间 ≠ 可以评分。** 口径不一致时，这个"命中"毫无意义 ——
用户押的是常住人口，拿户籍人口的数去结算，评的不是同一件事。
这一条最容易被"结果看起来对得上"掩盖，所以必须有独立用例钉住。

---

## 用例 26 · 裸 legacy actual 不得正式评分（v0.2.4）

旧档案形态：`{"outcomes": {"GDP": {"actual": 500}}}` —— 只有数值，没有单位 / 口径 / 期间 / 来源。

| step | 模式 | 期望 |
|---|---|---|
| 1 | `postmortem` | `actual_value=500`（读出）、`outcome_status=LEGACY_UNVERIFIED`、`outcome_valid=false`、`brier=None` |

**核心原则**：兼容层的含义是「旧数据还能打开」，**不是**「旧数据可以免责」。
裸 `actual` 可以被读出来查看与迁移，但**不得绕过完整性要求参加正式统计**。
**反证**：变异 H（让裸 `actual` 继续评分）会让本用例转红。

---

## 用例 27 · 修订双轨评价（v0.2.4）

`reveal-protocol.md` 早就要求"当时公布值与最新修订值两个都算、都要报"，
但复盘实际只取一个数。本用例把这条规则变成可执行断言。

夹具：评分命题 `threshold <= 800`，概率 0.70。
`as_reported_then = 790`（≤800 → 命中）；`latest_revised = 812`（>800 → 未命中）。

| 字段 | 期望 |
|---|---|
| `revision_tracks.as_reported_then` | `scored_event_hit=true`、`brier=0.09` |
| `revision_tracks.latest_revised` | `scored_event_hit=false`、`brier=0.49` |
| `revision_comparison` | `DIFFERENT` |
| `outcome_flags` | 含 `OUTCOME_REVISION_SENSITIVE` |
| `primary_actual_basis` | `latest_revised` |

**核心原则**：两轨结论不同时，**前台必须明说**「按当时公布的 790：命中；
按修订后的 812：未命中」，不得只给一个最终 verdict。
`OUTCOME_REVISION_SENSITIVE` **不归入** REASONING / MODEL / PROBABILITY ——
统计修订不是用户的推理错误。
**反证**：变异 I（只评 `latest_revised`）会让本用例转红。
