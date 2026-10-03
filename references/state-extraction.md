# 自然语言 → 结构化状态映射

本文件解决一个具体工程断点：**用户不会说 JSON。**

训练是对话。用户说"我查了 2009 年神木的财政支出，大概 30 亿"，不会说
`{"base_value": 30, "base_unit": "亿元"}`。但 `judge_checks.py` 需要结构化状态才能执行
准入闸门、隐含 CAGR、概率逻辑与防火墙检查。

因此每次用户发言后，教练必须在后台执行一次**状态抽取**：把自然语言还原成字段，
再交给规则层。本文件规定怎么抽、抽不到时怎么办。

---

## 一、第一原则：未检查 ≠ 已通过

这是 v0.2.2 最重要的规则，先于所有映射表。

> **字段缺失表示"还没有检查过"，不表示"检查了、结论是 false"。**

反例（旧逻辑的错误）：
用户没提存量流量问题 → 系统默认 `stock_flow_relevant = false` → 闸门通过。
这是**默认放行**，等于把"没检查"当成了"已确认无关"。

正确做法：三态字段。每个可判定字段有三种合法取值：

| 取值 | 含义 | 规则层反应 |
|---|---|---|
| `true` | 已判定为「是」 | 触发对应下一步检查 |
| `false` | 已判定为「否」 | 通过 |
| `"unknown"` | 明确知道"目前无法判定" | `GATE_FIELD_UNKNOWN`（BLOCK） |

而**字段完全缺席**（既不是 `true`/`false`，也不是 `"unknown"`）：

- 规则层报 `GATE_FIELD_UNCHECKED`（BLOCK）——连"不知道"都还没有被确认。
- 教练的动作：向用户提出一个针对性问题（每轮最多 1—3 个），把它变成 `true` 或 `false`。
- **教练不得替用户填 `false`。** 用户说"这个我不清楚"，应写 `"unknown"`，而不是 `false`。

适用三态机制的字段：
`stock_flow_relevant` / `stock_flow_resolved` / `quantity_price_relevant` / `quantity_price_split`。

> 其余字段（基期值、口径、单位、驱动、约束、概率）不是三态，而是"有 / 无"。
> 它们缺失时同样报 BLOCK，但语义上不需要"unknown"这一态——缺了就是没填。

---

## 二、抽取的四个步骤

每次用户发言后，后台按顺序做：

1. **定位阶段**：用户这句话属于状态机哪一步？（研究素材 / 候选指标 / 预测提交 / 锁定申请 / 揭晓请求）
2. **逐字段抽取**：对照下面第三、四节的表，把句子里的信息落到字段上。
3. **标记 unknown**：句子里**提到但说不清**的东西 → `"unknown"`。
   **完全没提**的 → 字段保持缺席（不写）。
4. **跑规则层**：`judge_checks.py case <档案>`，读 BLOCK/WARN，前台只说最关键 1—3 条。

抽取结果先写入会话内的案例档案（见 `prediction-record-template.md`），
不是写给用户看的。

---

## 三、案例级字段映射表

| 字段 | 类型 | 用户可能的说法 | 抽取规则 |
|---|---|---|---|
| `object_type` | `"city"` / `"company"` | 「分析一下神木」「看看这家公司」 | 城市 → `city`；企业 → `company`。缺省按 `city`，但**优先直接问清** |
| `historical_cutoff` | 日期字符串 | 「站在 2010 年底」「时间点定在 2010-12-31」 | 完整日期写 `YYYY-MM-DD`；只说年份则写 `YYYY`（会按 01-01 处理，并触发 `forecast_years` 的年份差路径） |
| `forecast_to` | 日期字符串 | 「预测到 2013 年底」「往后看三年」 | 同上。**强烈建议教练主动把截点与终点都落成完整日期**，否则期限计算不可靠 |
| `forecast_years` | 数字 | 「正好三年」 | 仅当用户明确指定年数且不想用两端日期推算时填；否则留给脚本按日期算 |
| `difficulty` | `1` / `2` / `3` | 「简单点」「常规难度」 | 默认 `1`；Level 1 限 2 个指标、期限 ≤3 年 |
| `base_rate_provided` | `true` / `false` | 「同类城市过去十年大致是 5%」 | 用户给出任何可比参照 → `true`；没给 → **不要写 `false`**，缺席即可（脚本默认报 `BASE_RATE_MISSING` WARN） |
| `sources[]` | 数组 | 「我看的是 2010 年统计公报」 | 每条至少填 `published_at`；若有统计期间，填 `data_period_start` / `data_period_end` |
| `outcomes{}` | 对象 | 「后来实际是 800」 | 多指标案例必须写成 `{指标名: {...}}`；单指标可用 `outcome` |

---

## 四、指标级字段映射表

一个指标 = 一个对象。下表逐字段给出「用户怎么说 → 怎么写」。

### 4.1 基期三件套（缺一即 BLOCK）

| 字段 | 用户可能的说法 | 抽取要点 |
|---|---|---|
| `base_value` | 「2009 年是 530」「基期大概 30 亿」 | 纯数值。**把口头单位剥出去**单独放 `base_unit` |
| `base_unit` | 「亿元」「万人」「美元」 | 若用户只说数字没说单位 → 字段缺席（BLOCK），**不要默认"元"** |
| `base_caliber` | 「按常住人口算」「当年价」「全市口径」 | 价别 / 地域 / 人口分母。用户说"就是这个数"但说不清口径 → `"unknown"` |
| `base_period` | 「2009 全年」「2009 年底」 | 基期数据所属期，用于揭晓时核对是否取错时点 |
| `base_published_at` | 「2010 年 2 月公布的」 | **基期值的公开时间**，防火墙用它。与 `base_period` 是两件事 |

> `base_value` 与 `base_published_at` 必须分开。
> 「2009 年 GDP」这个**值**通常 2010 年才**公布**。
> 截点 2010-12-31 时能否用它，取决于**公布时间**，不取决于所属期。

### 4.2 历史序列与推导路径

| 字段 | 用户可能的说法 | 抽取规则 |
|---|---|---|
| `history[]` | 「2005 到 2009 分别是…」 | 每个时点一个 `{year/period, value}`，尽量带 `published_at` |
| `history_basis` | 「没有连续数据，我按产能推的」 | 有连续序列 → `"trend"`（默认）；无序列走替代机制 → 见下 |
| `alternative_mechanism` | 「按在产煤矿设计产能 × 达产率」 | 当 `history_basis` 属于 `alternative/mechanism/capacity/order/share/contract/admin` 之一时，**必须**写出机制是什么 |

规则层的处理：

- `history` 少于 3 点 **且** 未声明替代机制 → `GATE_NO_HISTORY_SERIES`（BLOCK）。
- 声明了替代机制 → 降级为 `LIMITED_HISTORY`（WARN），但**概率 ≥70% 会追加**
  `LIMITED_HISTORY_PROB_TOO_HIGH`（WARN）。
- 声明了 `history_basis` 却没写 `alternative_mechanism` → 仍按 BLOCK 处理
  （"你说你有办法，但没说是什么办法"）。

### 4.3 三态字段（重点）

| 字段 | kind 适用 | 用户可能的说法 | 抽取规则 |
|---|---|---|---|
| `stock_flow_relevant` | `flow` / `stock` / `quantity` | 「这是地方财政收入」 | 判断该指标是否涉及存量流量区分。有 → `true`；明确无关 → `false`；说不清 → `"unknown"` |
| `stock_flow_resolved` | 同上，且 `relevant=true` | 「我用的是产量不是储量」 | `relevant=true` 时必填，且必须显式为 `true` |
| `quantity_price_relevant` | `flow` / `stock` | 「社会消费品零售总额」 | 金额类指标通常 `true` |
| `quantity_price_split` | 同上，且 `relevant=true` | 「我拆成了 300 万吨 × 均价 2000」 | 必须显式为 `true`（数量与价格分别给了才行） |

`kind` 字段：`flow`（流量/金额）/ `stock`（存量）/ `quantity`（实物量）/ `price`。
**`kind` 缺失时按 `flow` 从严处理**，因此存量流量检查会被激活。

> 常见误判提醒：
> - 用户说「煤炭产量」→ `kind: quantity`，存量流量 `relevant` 可为 `false`。
> - 用户说「煤炭储量」→ `kind: stock`，**是存量**，必须与产量区分。
> - 用户说「GDP」→ 金额、流量、涉及价别 → `stock_flow_relevant` 与
>   `quantity_price_relevant` 都可能为 `true`。

### 4.4 驱动 / 约束 / 定性方向

| 字段 | 用户可能的说法 | 抽取规则 |
|---|---|---|
| `drivers` | 「主要看煤炭价格和固定资产投资」 | 非空数组即通过；空 → `GATE_DRIVER_MISSING`（BLOCK） |
| `constraints` | 「上限是铁路运力」 | 同上 |
| `qualitative_direction` | 「我觉得会继续增长」 | `up` / `down` / `flat`。与预测数值必须一致，否则 `GATE_QUAL_QUANT_CONFLICT`（BLOCK） |

### 4.5 预测值 / 概率 / 提交字段

| 字段 | 用户可能的说法 | 抽取规则 |
|---|---|---|
| `forecast_low` / `forecast_high` | 「大概 700 到 900」 | 区间两端 |
| `center` / `forecast_point` | 「我押 800」 | 点估计。**区间优先**：3 年以上预测应给区间 |
| `forecast_form` | 「我就要一个数」 | `"point"` / `"interval"` |
| `probability` | 「大概八成把握」 | 0—1 的小数。口语"八成"→ `0.80`。**它绑定到 `scored_event`，不是绑定到预测区间** |
| `proposition` | 「P(2013 年财政支出超过 60 亿)」 | **必须命题化**。用户只给"85%"→ `PROB_NO_PROPOSITION`（BLOCK） |
| `scored_event` | 同上一行的句子 | **必须写**。概率到底在赌哪一件事，见 4.6。缺 → `PROB_SCORED_EVENT_MISSING`（BLOCK） |
| `reasoning` | 「我是这么推的…」 | 推导过程，非空 |
| `failure_conditions` | 「什么情况算我错了」 | 失效条件，非空 |
| `counterargument` | 「反方会说…」 | 最强反方解释，非空 |
| `missing_info` | 「我最缺的是…」 | 当前最缺信息，非空 |
| `extreme_justified` | 「因为新发现了大煤田」 | 隐含 CAGR 绝对值 >25% 时需要罕见机制说明 |

规则层会用 `point_estimate()` 取单一数值用于比较：优先 `center` / `forecast_point`，
否则区间中点。若 `probability` 缺失但有预测值 → `PROB_MISSING`（BLOCK）。

### 4.6 概率命题与评分命题（v0.2.3 重点）

一句话：**概率不是给"这个指标"的，是给"某一件具体的事"的。**
那件具体的事就是 `scored_event`，它决定复盘时 Brier 分数评的是什么。

抽取时把用户那句话拆成**三个独立字段**：

| 字段 | 回答的问题 | 例 |
|---|---|---|
| `forecast_low` / `forecast_high` | 你觉得它**会落在哪一段** | `[480, 520]` |
| `proposition` | 你嘴上说的**命题文字** | 「P(2013 年 GDP > 420 亿元)」 |
| `probability` | 你对**那件事**有多少把握 | `0.80` |
| `scored_event` | 上面那件事的**结构化形式** | `{"type": "threshold", "op": ">", "value": 420}` |

三者**可以不一致，而且经常不一致**，这是合法的：

```text
「我估计落在 480 到 520 之间，不过我更确定它会超过 420，这个有八成把握。」
  → forecast_low / forecast_high = 480 / 520
  → proposition  = "P(2013 年 GDP > 420 亿元)"
  → probability  = 0.80
  → scored_event = {"type": "threshold", "op": ">", "value": 420}
```

此时区间与命题是两个承诺，**分开输出、分开评价**：
`interval_hit` 看区间，`scored_event_hit` 看命题。允许出现
`interval_hit=false` 而 `scored_event_hit=true`。

`scored_event` 的三种类型：

| type | 结构 | 什么时候用 | 例 |
|---|---|---|---|
| `interval` | `{"type":"interval","low":a,"high":b}` | 用户赌的是"落在区间内" | 「会落在 480—520」 |
| `threshold` | `{"type":"threshold","op":">","value":x}` | 用户赌的是"超过/低于某个数" | 「会超过 420」 |
| `direction` | `{"type":"direction","direction":"up"}` | 用户赌的是"比基期高/低/持平" | 「会比 2009 年高」 |

`op` 取值：`>` / `>=` / `<` / `<=`。`direction` 取值：`up` / `down` / `flat`
（相对 `base_value` 判定）。

**抽取规则（按顺序）**：

1. 用户明确说了命题 → 按命题文字写 `scored_event`，**不要**直接抄预测区间。
2. 用户把概率直接挂在区间上（「这区间我有六成把握」）→
   `scored_event = {"type":"interval", ...}`，与区间同值。
3. 用户只给了一个点（「我押 800，六成把握」）→
   `scored_event = {"type":"interval","low":800,"high":800}`。
4. 用户说了"八成把握"但**没说赌什么** → `proposition` 与 `scored_event` **都保持缺席** →
   `PROB_NO_PROPOSITION` + `PROB_SCORED_EVENT_MISSING` 双 BLOCK，教练据此提问。
   **不要替用户编一个命题。**

> **每个指标只允许一个 `scored_event`。** 用户一次押了两件事
> （「既会超过 420，也会超过 500」）→ 拆成两个指标或让用户选一个，
> 传成列表会报 `PROB_SCORED_EVENT_MULTIPLE`（BLOCK）。

**评分时三态**：`evaluate_scored_event()` 返回 `True / False / None`。
`None` 表示"判定不了"（没结果、命题不完整、方向命题缺基期），
**与 `False`（明确没命中）严格区分**——`None` 时 Brier 不出数。

---

## 五、揭晓记录映射表

对应 `check_reveal()`。**裸数值不够**。

| 字段 | 用户可能的说法 | 抽取规则 |
|---|---|---|
| `actual_value` | 「实际是 812 亿」 | 数值 |
| `actual_unit` | 「亿元」 | 单位 |
| `actual_caliber` | 「按常住人口、当年价」 | 必须与 `base_caliber` 一致，否则 `REVEAL_CALIBER_MISMATCH`（BLOCK） |
| `actual_period` | 「2013 全年」 | 与 `base_period` 相同 → `REVEAL_PERIOD_MISMATCH`（WARN） |
| `actual_period_start` / `actual_period_end` | 「2013 年 1—12 月」「截止 2013-12-31」 | 结果所属期的起止。**期末必须等于 `forecast_to`**，否则 `REVEAL_TARGET_PERIOD_MISMATCH`（BLOCK） |
| `source` | 「统计公报」/「年报」 | 城市优先统计公报/年鉴/官方数据库；企业优先年报/交易所/法定披露 |
| `published_at` | 「2014 年 3 月公布」 | 缺 → WARN |
| `revision_status` | 「后来又修订过」 | `initial` / `revised` / `final`。缺 → WARN |
| `as_reported_then` | 「当时说的是 790」 | `revised`/`final` 时必须有，否则 `REVEAL_REVISION_UNRECORDED`（WARN） |
| `latest_revised` | 「修订后是 812」 | 可选 |

> 修订陷阱：**不得只留对预测有利的那个数**。
> 当时公布值与后来修订值要同时保留。详见 `reveal-protocol.md`。

> **时期陷阱（v0.2.3 新增）**：揭晓最隐蔽的错不是"值不对"，而是"值对错了年份"。
> 预测到 2013 年底，却拿 2012 年公报的 620 去结算 —— 数字再准也没有意义。
> 只写 `actual_period`（如「2013」）时按年比对；写了 `actual_period_end`
> 则要求与 `forecast_to` 完全同日。

---

## 六、信息防火墙映射（最容易做错的一段）

防火墙需要**两个时间**，不是一个：

| 时间 | 字段 | 回答的问题 |
|---|---|---|
| 数据所属期 | `data_period_end` | 这个数字**讲的是哪段时间** |
| 数据发布时间 | `published_at` | 这个数字**什么时候能被看到** |

规则层的判定顺序（`check_firewall`）：

```
发布时间 > 截点：
    数据所属期 ≤ 截点  →  FIREWALL_LOOKAHEAD_LEAKAGE (BLOCK)   ← 最隐蔽的前视泄漏
    否则              →  FIREWALL_CONTAMINATION    (BLOCK)
    且已标注 usable=false → FIREWALL_ISOLATED       (INFO)
发布时间 ≤ 截点：
    用了旧字段 date/source_date → SOURCE_DATE_LEGACY_FIELD (INFO)
发布时间缺失（v0.2.3 起分半处理）：
    已隔离 usable=false            → SOURCE_DATE_UNKNOWN (INFO)    ← 不参与预测，只提示
    标注 available_at_cutoff=false → FIREWALL_LOOKAHEAD_LEAKAGE (BLOCK)
    否则（正在使用）                → SOURCE_DATE_UNKNOWN (BLOCK)   ← v0.2.3 由 WARN 升级

指标级基期值（v0.2.3 新增硬闸门）：
    有 base_value 但无 base_published_at → BASE_PUBLICATION_UNKNOWN (BLOCK)
    base_published_at > 截点            → FIREWALL_CONTAMINATION    (BLOCK)
```

> **为什么"正在使用却没有发布时间"必须是 BLOCK**：只要它只是 WARN，用户就可以
> 一路推进到锁定，"这条材料截点当天到底能不能拿到"从头到尾没人证明过。
> 而已经隔离的材料（`usable: false`）本来就不参与预测，缺时间只提示不阻断 ——
> 否则用户会为了不被卡住而伪造一个发布时间，反而更危险。
> `base_value` 同理：**基期值是整条推导链的地基**，它拿不到，后面全塌。

**典型泄漏例子**：截点 `2010-12-31`，用户用了「2010 年全年 GDP」。
- `data_period_end = 2010-12-31` ≤ 截点 ✔ 看起来没问题
- 但 `published_at ≈ 2011-01`（统计公报通常次年 1—2 月发布）> 截点 ✘
- → `FIREWALL_LOOKAHEAD_LEAKAGE`。**截点当天根本拿不到这个数。**

这就是为什么只比较"数据年份 ≤ 截点年份"是不够的。

---

## 七、抽取歧义的处置规则

| 情形 | 处置 |
|---|---|
| 用户给了数字但没说单位 | `base_unit` 保持缺席 → 提一个针对性问题。**不要猜单位** |
| 用户说"我记得大概是…" | 照抽，但在 `note` 标记为回忆性、低置信 |
| 用户同时给了矛盾的两个值 | 两个都记，前台指出矛盾，请用户确认；不得自行择一 |
| 用户对某检查项说"不清楚" | 该三态字段写 `"unknown"` → 触发 BLOCK，教练据此提问 |
| 用户完全没提某检查项 | 字段**缺席** → 触发 `GATE_FIELD_UNCHECKED`（也是 BLOCK） |

**关键区别**：`"unknown"`（用户承认不知道）与"缺席"（教练还没问）在规则层都产生 BLOCK，
但**对教练的下一步动作不同**：
- `"unknown"` → 需要用户去补充信息（研究任务）。
- 缺席 → 教练需要**先发问**，把它变成明确判定。

---

## 八、自检清单（每次抽取后过一遍）

- [ ] 用户提到的每个数字，单位是否已分离到 `*_unit`？
- [ ] 涉及存量流量 / 量价分解的指标，三态字段是否**显式**给出了 `true`/`false`？
      还是被偷懒跳过了（→ 一律 BLOCK）？
- [ ] 基期值是否有对应的 `base_published_at`？还是只有所属期？（缺 → BLOCK）
- [ ] 材料是否有 `published_at`，且 ≤ 截点？**正在使用**的材料缺时间就是 BLOCK。
- [ ] 给了 `probability` 的指标，是否都写清了 `scored_event`，而不是照抄预测区间？
- [ ] 揭晓的 `actual_period_end` 是否等于 `forecast_to`？
- [ ] 若走了替代推导路径，`alternative_mechanism` 是否写清？
- [ ] 提交阶段四个字段（reasoning / failure_conditions / counterargument / missing_info）是否齐全？
- [ ] 是否把"用户没提"错误地当成了"用户确认否"？

任何一项答"否" → 不要推进状态，前台只说最关键的 1—3 条。
