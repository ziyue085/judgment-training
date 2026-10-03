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
  - name: 神木县 2009 年国民经济和社会发展统计公报
    kind: fact                   # fact | opinion | inference | assumption
    data_period_start: 2009-01-01
    data_period_end: 2009-12-31  # 数据「讲的是哪一段时间」
    published_at: 2010-03-15     # 数据「什么时候能被看到」——防火墙比较的是这个
    revision_status: final       # initial | revised | final | unknown
    usable: true
    available_at_cutoff: true
    note: 截点前公开
  - name: 神木县 2011 年国民经济和社会发展统计公报
    kind: post_cutoff
    data_period_end: 2011-12-31
    published_at: 2012-03-15
    usable: false                # 已隔离：报 FIREWALL_ISOLATED(INFO)，不报 BLOCK
    note: 截点后材料

indicators:
  - name: GDP
    kind: flow                   # flow | stock | quantity | price | ratio | count
    base_value: null
    base_period: "2010"
    base_unit: 亿元
    base_caliber: 当年价/全市
    base_published_at: null      # 基期值的公开时间（与 base_period 是两件事）
    history: []                  # [{period, value, published_at?}]
    history_basis: trend         # trend | alternative | mechanism | capacity | order | share | contract | admin
    alternative_mechanism: null  # history_basis 非 trend 时必填；写了路径却不写机制 → 仍 BLOCK
    drivers: []
    constraints: []
    # 三态字段：true / false / "unknown"。**缺席 = 未检查 ≠ 已通过**，不得默认 false
    stock_flow_relevant: unknown
    stock_flow_resolved: null    # relevant=true 时必须显式 true
    quantity_price_relevant: unknown
    quantity_price_split: null   # relevant=true 时必须显式 true
    qualitative_direction: up    # up | flat | down | uncertain
    forecast_form: range         # range | point
    forecast_low: null
    forecast_high: null
    center: null
    probability: null
    proposition: null
    reasoning: null
    failure_conditions: null
    counterargument: null
    missing_info: null
    extreme_justified: null      # 隐含 CAGR > 25% 时的罕见机制说明

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

# 结果记录：多指标按指标名映射；单指标可退化为顶层 outcome: {...}
outcomes:
  地区生产总值:
    actual_value: null
    actual_unit: 亿元
    actual_caliber: 当年价/全市     # 必须与 base_caliber 一致，否则 REVEAL_CALIBER_MISMATCH (BLOCK)
    actual_period: "2013"
    source: 2013 年国民经济和社会发展统计公报  # 城市优先公报/年鉴/官方库；企业优先年报/交易所
    published_at: 2014-03-15
    revision_status: revised        # initial | revised | final | unknown
    as_reported_then: null          # 当时公布值（revised/final 时必填）
    latest_revised: null            # 最新修订值
    actual: null                    # 复盘用数值（可与 actual_value 相同）
    interval_hit: null
    note: null

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
  # 结果来源：档案顶层的 outcomes{指标名: {...}}；单指标案例可用顶层 outcome: {...}
  # 若没有任何结果记录 → 一律按「结果未知」裁决，不得当成「未命中」
  indicator_results:          # 由 judge_checks.py 逐指标生成
    - indicator: 地区生产总值
      proposition: P(2013 年 GDP > 420 亿元)
      probability: 0.60
      forecast_low: 480
      forecast_high: 520
      actual: 500
      interval_hit: true       # true | false | null(=未知)
      brier: 0.16
      block_codes: []
      warn_codes: []
      error_attribution: []
      process_clean: true
      verdict: PROCESS_GOOD_OUTCOME_HIT
  case_summary:                # 案例级汇总
    n_indicators: 3
    n_hit: 1
    n_miss: 1
    n_unknown: 1
    overall: CASE_MIXED        # 见下表
    outcome_status: PARTIAL    # REVEALED | PARTIAL | UNKNOWN
  scores:                      # 每项 A/B/C/D + 必须写原因（逐指标或整轮）
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
  verdict: null                # 单指标 = 该指标裁决；多指标见 case_summary.overall
  transferable_principle: null # 必须由用户自己写
```

> **作用域隔离**：某个指标的过程缺陷不得污染其他指标的过程评价。
> 唯一例外是 case 级致命缺陷（`CUTOFF_NOT_SET` / 信息污染 / 前视泄漏）——那会让整轮作废。

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
| 无严重缺陷 | **未知（未揭晓 / 未提供结果）** | `PROCESS_GOOD_OUTCOME_UNKNOWN` —— **未知 ≠ 未命中** |
| 有严重缺陷 | 命中 | `LUCKY_ACCURATE` —— **结果对不等于预测好** |
| 有严重缺陷 | 未命中 | `PROCESS_DEFECTIVE_OUTCOME_MISS` |
| 有严重缺陷 | **未知** | `PROCESS_DEFECTIVE_OUTCOME_UNKNOWN` —— 缺陷足以定论"当时不该锁定"，无需知道结果 |

其中"严重缺陷"指存在 `BLOCK` 级发现却仍被锁定，或事后归因中含 `REASONING` / `BASE_RATE_IGNORED` / `CALIBER` 三类之一。

### 案例级汇总（`case_summary.overall`）

| 取值 | 含义 |
|---|---|
| `CASE_INVALIDATED` | 存在使整轮作废的 case 级缺陷（信息污染 / 前视泄漏 / 未设截点） |
| `CASE_NO_INDICATORS` | 案例不含指标，无法复盘 |
| `CASE_MIXED` | 各指标过程质量不一致——**必须逐指标评价，不得用一个总分掩盖差异** |
| `CASE_CONSISTENT_CLEAN` | 各指标均无明显缺陷 |
| `CASE_CONSISTENT_DEFECTIVE` | 各指标均存在缺陷 |

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
