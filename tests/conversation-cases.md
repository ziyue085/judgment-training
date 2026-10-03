# 对话级测试（自然语言 → 结构化状态）

JSON 夹具能证明**规则层正确**，但不能证明**规则层接通了真实对话**。

v0.2.2 之前存在一个工程断点：规则写好了，但"用户说人话 → 系统得到结构化状态"这一步
没有测试覆盖。结果是——夹具全绿，真实训练仍可能因为抽取错误而失守。

本目录的 4 个用例补上这一段。每个 `*.json` 的每个 step 包含：

| 字段 | 含义 |
|---|---|
| `utterance` | 用户**原话**（模拟真实对话输入） |
| `extract` | 从这句话**应当**抽取出的字段与值（映射断言） |
| `extract_absent` | 抽取后**必须仍然缺席**的字段（未检查 ≠ 已通过） |
| `case` | 按 `extract` 映射得到的结构化案例档案 |
| `expect` | 交给规则层后应当产生的发现 |

运行：

```bash
python tests/run_regression.py --conversation --verbose
```

`extract` / `extract_absent` 由 `run_regression.py` 直接核对，因此这些用例
**同时验证映射与规则**，而不只是重跑规则。

---

## Test 1 · 存量流量识别（`conv-01-stock-flow.json`）

**用户原话**：「神木煤特别多，我记得储量有几百亿吨，我猜 2013 年产量能到 4 亿吨，把握七成吧。」

一句话里混了「储量」（存量）与「产量」（流量）。正确映射：
`kind: quantity`、`stock_flow_relevant: true`，但**不得**擅自给出 `stock_flow_resolved`。

- step1：`stock_flow_resolved` 缺席 → `GATE_STOCK_FLOW_UNRESOLVED`（BLOCK），不可锁定。
- step2：用户澄清"我说的是产量不是储量" → `stock_flow_resolved: true` → 放行。

**它防的错**：把用户没提的 `stock_flow_resolved` 默认成 `false`（默认放行）。

## Test 2 · 定性定量矛盾（`conv-02-qual-quant.json`）

**用户原话**：「我觉得神木财政会缓一缓，但还是往上走，2013 年大概 85 亿吧。」

`qualitative_direction: up` 但预测值 85 < 基期 100。映射本身没错，矛盾由量化检查捕捉。

- step1：`GATE_QUAL_QUANT_CONFLICT`（BLOCK）。
- step2：用户改成 130 亿 → 矛盾解除。

**它防的错**：用户语气自信（"还是往上走"）就放松检查。

## Test 3 · 统一概率（`conv-03-uniform-85.json`）

**用户原话**：「这三个我都给 85% 吧，感觉差不多。」

三个不确定性来源完全不同的指标被赋予同一概率。

- step1：`PROB_UNIFORM`（WARN，案例级）。可继续，但须逐个说明理由。
- step2：用户区分成 60% / 75% / 90% → 解除。

**它防的错**：把"懒得分"当成"概率校准"。

## Test 4 · 「凭感觉」阻止锁定（`conv-04-sense-lock.json`）

**用户原话**：「我不想写那些推导了，就凭感觉吧：财政收入能到 150 亿……直接锁定。」

数值与概率齐备，但**命题、推导过程、失效条件、最强反方、最缺信息**全缺。

- step1：`LOCK_FIELD_MISSING`×4 + `PROB_NO_PROPOSITION`（BLOCK），不可锁定。
  前台只呈现 2 条（去重后）：`PROB_NO_PROPOSITION` 与 `LOCK_FIELD_MISSING`。
- step2：用户补齐 → 放行。

**它防的错**：把"有数字"当成"可锁定"。判断力训练的产出是**可复核的推理**，不是数字。

---

## 维护约定

- 新增对话用例时，`utterance` 必须是**真实口语**，不得写成字段名堆砌。
- `extract` 只列**这句话直接蕴含**的字段；推断出来的字段应能追溯到一个规则。
- 若某用例的 `extract_absent` 为空，说明该用例没有覆盖"未检查 ≠ 已通过"，应补。
