# E2E A · 合成全流程实跑记录（synthetic-full-run）

> **对象为虚构**（「临江市」不存在）。本用例只检验**状态机与前台 UX**，
> 不检验历史研究能力，也不涉及任何真实历史答案。
> 
> 记录方式：每一阶段的闸门输出由 `scripts/judge_checks.py` **实跑**产生，
> 不是手写结论。教练回复逐条经 `check_reply()` 校验。

## 一、逐阶段记录

### S1 · `INTAKE`

**用户**：我想练一次城市预测。对象是临江市（我自己虚构的一个资源型城市）。

**教练**：对象收到：临江市。先定历史截点——你打算站在哪一天往前看？给我一个具体日期。

- 教练回复自检：`OK` · ['REPLY_OK']
- 闸门：BLOCK=0 WARN=0 lockable=YES

### S2 · `CUTOFF_SET`

**用户**：就站在 2010-12-31，目标期看到 2013 年底。

**教练**：截点 2010-12-31、目标期 2013-12-31。接下来交材料：把你用到的每条材料连同它的发布时间写出来；发布时间不明的不能用。

- 教练回复自检：`OK` · ['REPLY_OK']
- 闸门：BLOCK=0 WARN=0 lockable=YES

### S3 · `INDICATOR_SELECT`

**用户**：我用的是《临江市 2009 年国民经济和社会发展统计公报》，2010 年 3 月 15 日发布。指标选两个：地区生产总值、地方财政收入。

**教练**：材料可以。两个指标各自先给基期值、单位、口径，以及这个基期值是哪一年公布的。

- 教练回复自检：`OK` · ['REPLY_OK']
- 闸门：BLOCK=0 WARN=0 lockable=YES

### S4 · `ADMISSION_GATE`

**用户**：地区生产总值我判断 2013 年会在 750 到 850 亿元之间。

**教练**：先补地区生产总值的基期值。基期没有核实之前，任何数字都没有检验价值。

- 教练回复自检：`OK` · ['REPLY_OK']
- 闸门：BLOCK=1 WARN=0 lockable=NO

| 级别 | code | 作用域 | 信息 |
|---|---|---|---|
| BLOCK | `GATE_BASE_MISSING` | 指标「地区生产总值」 | 缺少基期值。禁止进入正式数值预测。 |

- 前台只呈现：`['GATE_BASE_MISSING']`

### S5 · `ADMISSION_GATE`

**用户**：基期是 600 亿元，2009 年的。

**教练**：这个基期值是哪一年公布的？截点当天拿不到就不能用。

- 教练回复自检：`OK` · ['REPLY_OK']
- 闸门：BLOCK=1 WARN=0 lockable=NO

| 级别 | code | 作用域 | 信息 |
|---|---|---|---|
| BLOCK | `BASE_PUBLICATION_UNKNOWN` | 指标「地区生产总值」 | 有基期值，但未记录该值的公开时间，无法证明截点当天可获得。 |

- 前台只呈现：`['BASE_PUBLICATION_UNKNOWN']`

### S6 · `ADMISSION_GATE`

**用户**：我觉得这个城市未来还是继续增长的。数字我写 520 到 560。

**教练**：定性写的是「继续增长」，数字却是往下走。这两句不能同时成立，先改掉一个。

- 教练回复自检：`OK` · ['REPLY_OK']
- 闸门：BLOCK=1 WARN=0 lockable=NO

| 级别 | code | 作用域 | 信息 |
|---|---|---|---|
| BLOCK | `GATE_QUAL_QUANT_CONFLICT` | 指标「地区生产总值」 | 定性判断为「增长」，但预测值 540 低于基期 600。 |

- 前台只呈现：`['GATE_QUAL_QUANT_CONFLICT']`

### S7 · `CHECKS`

**用户**：我把地区生产总值的把握提到 85%。

**教练**：你给了 85% 的概率，但它押的是哪句话——区间、阈值还是方向？写清楚，这个概率后面才能评分。

- 教练回复自检：`OK` · ['REPLY_OK']
- 闸门：BLOCK=1 WARN=0 lockable=NO

| 级别 | code | 作用域 | 信息 |
|---|---|---|---|
| BLOCK | `PROB_SCORED_EVENT_MISSING` | 指标「地区生产总值」 | 有概率，但没有说明这个概率绑定的是哪个命题（scored_event）。 |

- 前台只呈现：`['PROB_SCORED_EVENT_MISSING']`

### S8 · `LOCK`

**用户**：改好了，这是我的最终预测，可以锁定。

**教练**：准入通过，可以锁定。锁定之后这两个数字不能再改。

- 教练回复自检：`OK` · ['REPLY_OK']
- 闸门：BLOCK=0 WARN=0 lockable=YES

### S9 · `REVEAL`

**用户**：临江市 2012 年公报里地区生产总值是 800 亿元，我用这个对答案。

**教练**：这份结果记录的所属期末是 2012-12-31，但本次目标期是 2013-12-31——数字再接近，评的也不是同一件事。先确认期间。

- 教练回复自检：`OK` · ['REPLY_OK']
- 揭晓核验：BLOCK=1 WARN=0

| 级别 | code | 作用域 | 信息 |
|---|---|---|---|
| BLOCK | `REVEAL_TARGET_PERIOD_MISMATCH` | 结果「地区生产总值」 | 结果所属期末 2012-12-31 与预测目标期 2013-12-31 不一致。 |

- 前台只呈现：`['REVEAL_TARGET_PERIOD_MISMATCH']`

### S10 · `POSTMORTEM`

**用户**：年份改对了，2013 年的数在公报里。地区生产总值当时公布 790 亿，后来修订为 812 亿。

**教练**：两轨我都算了：按当时公布值和按修订值，这一次结论相同。修订前后的数都留在档案里。

- 教练回复自检：`OK` · ['REPLY_OK']
- 揭晓核验：BLOCK=0 WARN=0

### S11 · `PRINCIPLE`

**用户**：这一轮我的问题主要是随便给了 85% 的把握。

**教练**：把这一轮学到的东西写成一句话原则，你自己写，我不替你写。

- 教练回复自检：`OK` · ['REPLY_OK']
- 闸门：BLOCK=0 WARN=0 lockable=YES

### S12 · `ARCHIVED`

**用户**：原则写好了。

**教练**：已归档。下次训练可以直接调用这条原则。

- 教练回复自检：`OK` · ['REPLY_OK']
- 闸门：BLOCK=0 WARN=0 lockable=YES

### S13 · `POSTMORTEM`

**用户**：这个数字当时公布是 790，后来修订成 812。

**教练**：按当时公布值：命中；按后来修订值：未命中。两轨都记，不说「总体命中」这种含糊话。

- 教练回复自检：`OK` · ['REPLY_OK']
- 揭晓核验：BLOCK=0 WARN=0

## 二、S9b · 错误年份的结果直接送进复盘（必须拒绝评分）

- `outcome_status` = `INVALID`
- `outcome_valid` = `False` · `outcome_invalidating_codes` = `['REVEAL_TARGET_PERIOD_MISMATCH']`
- `process_clean` = `True` ← 过程仍被单独评价，未被数据问题污染
- `interval_hit` = `None` · `scored_event_hit` = `None` · `brier` = `None`
- `actual_value` = `800`（保留供人类阅读，**不**参与评分）
- 裁决 = `PROCESS_GOOD_OUTCOME_INVALID`

> 值 800 单看是命中（区间 [750,850]），但期间错了。
> 复盘必须说「过程合格 / 这份答案不可用」，**不是**命中，也不是未命中。

## 三、S10 复盘裁决（实跑输出）

- `case_summary.overall` = `CASE_CONSISTENT_CLEAN`
- `outcome_status` = `REVEALED` (valid=2 invalid=0 legacy=0 unknown=0)

| 指标 | 概率 | 预测区间 | 评分命题 | 实际值 | 区间命中 | 命题命中 | Brier | 裁决 |
|---|---|---|---|---|---|---|---|---|
| 地区生产总值 | 0.6 | [750, 850] | {"type": "interval", "low": 750, "high": 850} | 812 | True | True | 0.16 | PROCESS_GOOD_OUTCOME_HIT |
| 地方财政收入 | 0.55 | [90, 120] | {"type": "interval", "low": 90, "high": 120} | 118 | True | True | 0.2025 | PROCESS_GOOD_OUTCOME_HIT |

### 修订双轨（地区生产总值）

- `revision_comparison` = `SAME`
- `primary_actual_basis` = `latest_revised`
- `outcome_flags` = `[]`
  - `as_reported_then`：value=790 interval_hit=True scored_event_hit=True brier=0.16
  - `latest_revised`：value=812 interval_hit=True scored_event_hit=True brier=0.16

> 前台必须同时说两轨：两轨一致时也要说清楚「这次修订没有改变结论」——
> 不能只挑一个说，也不能在不存在分歧时声称有分歧。

## 五、E2E 发现（必须在报告里如实列出）

**发现 1 · 零指标案例被报为可准入**：对 `indicators: []` 的档案运行 `case` 模式，
输出 INFO 码 = `['ADMISSION_OK']`，即「无 BLOCK 级缺口，可进入下一状态」。
这与「未检查 ≠ 已通过」的原则不一致：没有任何指标时不该宣告准入通过。
（本轮只记录，不扩规则 —— 它不会导致评分错误，属流程/UX 缺口。）

**发现 2 · 状态顺序不由代码强制**：S4—S7 连续四轮 BLOCK，但档案的 `stage` 标签
仍可被写成 `CHECKS`。`judge_checks.py` 只做规则判定，不校验状态迁移；
「BLOCK 期间不得推进状态」目前**只靠教练自律**。

**发现 3 · `check_reply()` 不校验陈述与档案事实是否一致**：
本次起草时曾写出与实算结果相反的台词（声称两轨分歧，而实算两轨相同），
`check_reply()` 返回 `REPLY_OK`。它只能拦抢答 / 剧透 / 问题过多 / 夸奖 / 分析师口吻，
不能发现「教练说错了」。这是真实的能力缺口。

## 四、S13 · 修订跨过预测阈值的双轨分歧（§38）

- 命题：`P(2013 年地区生产总值 <= 800 亿元) = 70%`，概率 `0.7`
- `scored_event` = `{"type": "threshold", "op": "<=", "value": 800}`，预测区间 `[700, 805]`
- `revision_comparison` = `DIFFERENT` · `primary_actual_basis` = `latest_revised` · `outcome_flags` = `['OUTCOME_REVISION_SENSITIVE']`

| 轨 | 值 | 区间命中 | 命题命中 | Brier |
|---|---|---|---|---|
| `as_reported_then` | 790 | True | True | 0.09 |
| `latest_revised` | 812 | False | False | 0.49 |

- 主轨（`latest_revised`）裁决 = `PROCESS_GOOD_OUTCOME_MISS`

> 前台应输出：「按当时公布的 790：命中；按修订后的 812：未命中。」
> 只给一个「最终 verdict」是**不合规**的。
