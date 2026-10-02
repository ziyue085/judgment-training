# 案例档案与提交模板（prediction-record-template）

> 档案是这套系统的资产。没有档案，训练不可累积、不可复盘、不可校准。

---

## 一、档案格式与位置

每轮案例两个文件，默认写在用户工作区：

```text
judgment-training/
├─ <case-id>.yaml          # 结构化主档案（脚本可读，用于检查与评分）
├─ <case-id>.md            # 人类可读记录（研究轨迹 + 对话摘要）
└─ principles.md           # 跨案例判断原则库
```

命名：`<对象拼音>-<截点年份>`，例如 `shenmu-2010`、`daqing-2013`、`kele-2008`。

**若运行环境不支持持久化**：在会话内维护同一结构，每轮结束时输出可复制的 Markdown。
不要假设任何沙箱路径永久存在。

---

## 二、YAML 主档案结构

```yaml
case_id: shenmu-2010
object: 神木
object_type: city            # city | company
historical_cutoff: 2010-12-31
forecast_to: 2015-12-31
difficulty: 2                # 1 | 2 | 3
stage: RESEARCH               # 状态机中的当前状态
version: V1                   # V1 / V2 / ...

base_rate_provided: false

sources:
  - date: 2010-11-20
    kind: fact               # fact | opinion | inference | assumption
    note: 截点前公开材料
    usable: true
  - date: 2013-05-01
    kind: post_cutoff
    note: 截点后材料，已隔离
    usable: false

indicators:
  - name: GDP
    kind: flow               # flow | stock | ratio | price | quantity | count
    base_value: null
    base_period: "2010"
    base_unit: 亿元
    base_caliber: 当年价/全市
    base_source_date: null
    history: []              # [{year, value}]
    drivers: []
    constraints: []
    stock_flow_relevant: false
    stock_flow_resolved: false
    quantity_price_relevant: true
    quantity_price_split: false
    qualitative_direction: up   # up | flat | down | uncertain
    forecast_form: range        # range | point
    forecast_low: null
    forecast_high: null
    center: null
    probability: null
    proposition: null
    reasoning: null
    failure_conditions: null
    counterargument: null
    missing_info: null

prob_relations:
  - a: "GDP > 1000"
    b: "GDP > 900"
    relation: subset          # a ⊆ b

exclusive_sets:
  - name: 增长方向
    items:
      - { label: 下降, p: 0.25 }
      - { label: 持平, p: 0.35 }
      - { label: 增长, p: 0.40 }

checks:
  findings: []                # judge_checks.py 输出

outcome: null
postmortem: null
principle: null
```

---

## 三、最终预测提交格式（锁定前必填）

每项预测至少包含以下字段。缺任一项 → 不允许锁定。

```text
预测命题：      （对象 + 指标 + 期限 + 判定条件，形式化）
基期：          （数值 + 期间 + 口径 + 单位）
预测期限：      2010-12-31 → 2015-12-31（n = 5 年）
预测区间：      900 — 1100 亿元
中心估计（可选）：1000 亿元
概率：          P(命题) = 60%
推导过程：      （基期 → 增速 → 结果，可复算）
主要依据：      （哪些当时可获得的信息）
关键驱动变量：  （列 2—4 个）
关键约束变量：  （列 1—3 个）
情景：          （2—4 个有机制的情景）
最大风险：      （最可能让预测失败的因素）
最强反方解释：  （反方最强的论证，不是套话）
失效条件：      （什么观测结果会让你承认错了）
当前最缺的信息：
基准率情况：    provided / missing（若 missing，概率须相应下调）
```

---

## 四、版本链与更新留痕

同一对象跨截点续练时使用。

```yaml
versions:
  - version: V1
    cutoff: 2010-12-31
    locked_at: null
    forecasts: []
    updates: []
  - version: V2
    cutoff: 2012-12-31
    locked_at: null
    forecasts: []
    updates: []
```

单条更新记录：

```yaml
updates:
  - at: 2012-06-15
    original: { low: 900, high: 1100, p: 0.60 }
    revised:  { low: 850, high: 1000, p: 0.55 }
    info_class: B            # A = 截点前遗漏；B = 截点后新增
    new_info: （简述）
    reason: （为什么这样更新，幅度依据是什么）
```

**B 类信息不得并入 V1。** 使用 B 类信息必须新开版本。

---

## 五、复盘模板

揭晓后填写。分项评价，**不用单一总分掩盖问题**。

```yaml
postmortem:
  outcome:
    actual: null
    actual_source: null
    interval_hit: null
    brier: null
  scores:                      # 每项 A/B/C/D + 必须写原因
    - item: 信息搜集完整性
      grade: null
      reason: null
    - item: 基期准确性
      grade: null
      reason: null
    - item: 数据口径
      grade: null
      reason: null
    - item: 因果链
      grade: null
      reason: null
    - item: 驱动变量识别
      grade: null
      reason: null
    - item: 基准率使用
      grade: null
      reason: null
    - item: 数值推导
      grade: null
      reason: null
    - item: 情景设计
      grade: null
      reason: null
    - item: 概率校准
      grade: null
      reason: null
    - item: 反方思考
      grade: null
      reason: null
  error_attribution: []        # 见下表
  verdict: null                # 见 judge_checks.py postmortem
  transferable_principle: null # 必须由用户自己写
```

### 错误来源分类

| 代码 | 含义 |
|---|---|
| `FACTUAL` | 事实错误（用错了当时的信息） |
| `CALIBER` | 数据口径错误（口径/单位/价别混淆） |
| `REASONING` | 推理错误（因果链断裂、逻辑不一致） |
| `BASE_RATE_IGNORED` | 忽略基准率 |
| `MODEL` | 模型结构错误（用了不适用的分解） |
| `PARAMETER` | 参数错误（增速、利润率等取值离谱） |
| `PROBABILITY` | 概率失准（方向对但概率标定错） |
| `BLACK_SWAN` | 真正难以预见的事件 |
| `LUCK` | 纯粹运气（好或坏） |

### 裁决规则（对应 `judge_checks.py postmortem`）

| 过程质量 | 结果 | 裁决 |
|---|---|---|
| 无严重缺陷 | 命中 | `PROCESS_GOOD_OUTCOME_HIT` |
| 无严重缺陷 | 未命中（含落入低概率情景） | `PROCESS_GOOD_OUTCOME_MISS` —— **不得因结果错判过程失败** |
| 有严重缺陷 | 命中 | `LUCKY_ACCURATE` —— **结果对不等于预测好** |
| 有严重缺陷 | 未命中 | `PROCESS_DEFECTIVE_OUTCOME_MISS` |

其中"严重缺陷"指存在 `BLOCK` 级发现却仍被锁定，或事后归因中含 `REASONING` / `BASE_RATE_IGNORED` / `CALIBER` 三类之一。

---

## 六、判断原则库

`judgment-training/principles.md`

```markdown
# 判断原则库

## P-001 · 资源型对象的量价拆分
来源：shenmu-2010（2026-10-03）
原则：预测资源型城市或企业的收入，必须先拆产量与价格两条线；只看储量会系统性高估产量增速。
适用边界：价格由外部市场决定、产能建设周期长的对象。不适用于价格受管制或库存极低的场景。
```
