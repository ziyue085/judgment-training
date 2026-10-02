# 回归测试用例（test-cases）

> 每个用例都对应 `tests/cases/` 下的一个可执行夹具。全部由 `tests/run_regression.py` 断言。

```bash
python tests/run_regression.py            # 全部用例
python tests/run_regression.py --verbose  # 打印每个 step 的实际发现
python scripts/judge_checks.py case tests/cases/test-11-shenmu-2010-regression.json
```

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

---

## 用例 9 · 结果错但过程合理

用户给出 55% 区间 [800,1000]，实际落在剩余 45% 内。

**正确行为**：`PROCESS_GOOD_OUTCOME_MISS`。

**核心原则**：不得因结果错就判过程失败。概率诚实的落空是好预测的正常代价。

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

---

## 用例 12 · 反向对照（防误报）

一个完全合格的 Level 1 案例：基期、口径、单位、历史序列、驱动、约束、量价拆分、命题、四个提交字段、基准率齐备。

**期望**：0 BLOCK、0 WARN、`lockable=YES`，且不得出现 17 个已知闸门码中的任何一个。

**意义**：没有这个用例，闸门可以靠"全部拦截"通过所有测试。
