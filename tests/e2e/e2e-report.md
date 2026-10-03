# E2E 报告 — v0.2.4 Outcome Integrity Patch

本文件是 v0.2.4 附带的两条端到端演练的**汇总报告**。详细逐阶段记录见：

- `tests/e2e/synthetic-full-run.md` — E2E A，纯合成案例
- `tests/e2e/real-historical-full-run.md` — E2E B，真实历史案例（淄博）
- `tests/e2e/forecast-phase-allowlist.json` — E2E B 的预测阶段允许清单
- `tests/e2e/locked-forecast.json` — E2E B 锁定的预测 + SHA-256

> ⚠ E2E B 标记 **`DO_NOT_USE_FOR_REAL_TRAINING`**：只作工程测试，
> 未来**不得**作为用户正式训练题重复使用，也不得进入正式选题池。

---

## 一、方法

两条演练都由 `scripts/judge_checks.py` 的**真实函数**驱动，闸门输出为实跑结果，
不是手写结论。教练回复逐条经 `check_reply()` 校验。

| | E2E A | E2E B |
|---|---|---|
| 对象 | 临江市（虚构） | 山东省淄博市（真实） |
| 截点 → 目标期 | 2010-12-31 → 2013-12-31 | 2012-12-31 → 2015-12-31（3.0 年） |
| Level | 1 | 1 |
| 指标数 | 2 | 2 |
| 目的 | 状态机 + 前台 UX | 时间防火墙 + 结果完整性 + 全链路 |
| 是否涉及真实答案 | 否 | 是（明令禁止复用） |

---

## 二、E2E A · 状态迁移与闸门（实跑）

| 阶段 | 状态 | BLOCK | 关键发现码 | 前台呈现 |
|---|---|---|---|---|
| S1 | INTAKE | 0 | — | — |
| S2 | CUTOFF_SET | 0 | — | — |
| S3 | INDICATOR_SELECT | 0 | — | — |
| S4 | ADMISSION_GATE | 1 | `GATE_BASE_MISSING` | 1 条 |
| S5 | ADMISSION_GATE | 1 | `BASE_PUBLICATION_UNKNOWN` | 1 条 |
| S6 | ADMISSION_GATE | 1 | `GATE_QUAL_QUANT_CONFLICT` | 1 条 |
| S7 | CHECKS | 1 | `PROB_SCORED_EVENT_MISSING` | 1 条 |
| S8 | LOCK | 0 | `lockable=YES` | — |
| S9 | REVEAL | 1 | `REVEAL_TARGET_PERIOD_MISMATCH` | 1 条 |
| S10 | POSTMORTEM | 0 | 正常评分（两轨一致） | — |
| S11 | PRINCIPLE | 0 | — | — |
| S12 | ARCHIVED | 0 | — | — |
| S13 | POSTMORTEM | 0 | 修订跨阈值 → 两轨分歧 | — |

七类故意制造的错误全部在预期位置被拦住：

| 错误 | 期望码 | 实际 |
|---|---|---|
| 有预测没基期 | `GATE_BASE_MISSING` | ✅ |
| 有基期没公布时间 | `BASE_PUBLICATION_UNKNOWN` | ✅ |
| 定性增长但数字下走 | `GATE_QUAL_QUANT_CONFLICT` | ✅ |
| 85% 未绑定命题 | `PROB_SCORED_EVENT_MISSING` | ✅ |
| 全部修好 | `lockable=YES` | ✅ |
| 揭晓用错年份 | `REVEAL_TARGET_PERIOD_MISMATCH` | ✅ |
| 修正年份 | 正式进入复盘 | ✅ |

### S9b：错误结果直接送进复盘

```
outcome_status              = INVALID
outcome_valid               = False
outcome_invalidating_codes  = [REVEAL_TARGET_PERIOD_MISMATCH]
process_clean               = True      ← 过程仍被单独评价
interval_hit / scored_event_hit / brier = None / None / None
actual_value                = 800       ← 保留供阅读，不参与评分
verdict                     = PROCESS_GOOD_OUTCOME_INVALID
```

这是 v0.2.4 §3 的**直接证据**：过程合格、结果不可用，两件事分开表达。

### S13：修订跨过阈值（§38）

命题 `P(2013 年地区生产总值 <= 800 亿元) = 70%`，预测区间 `[700, 805]`。

| 轨 | 值 | 区间命中 | 命题命中 | Brier |
|---|---|---|---|---|
| `as_reported_then` | 790 | True | True | 0.09 |
| `latest_revised` | 812 | False | False | 0.49 |

`revision_comparison = DIFFERENT` · `outcome_flags = [OUTCOME_REVISION_SENSITIVE]` ·
主轨 `latest_revised` 裁决 `PROCESS_GOOD_OUTCOME_MISS`。

前台必须输出「按当时公布的 790：命中；按修订后的 812：未命中」，不得只给一个最终 verdict。

---

## 三、E2E A · 前台 UX 检查（§28）

| # | 检查项 | 结论 |
|---|---|---|
| 1 | 有没有一次扔 10 个问题？ | **否**。每轮 0—2 个问句；`COACH_TOO_MANY_QUESTIONS` 零触发 |
| 2 | 有没有露出 JSON？ | **否** |
| 3 | 有没有说字段名？ | **否**。用的是「基期值 / 口径 / 期间 / 发布时间」等中文说法 |
| 4 | 有没有过度说教？ | **否**。最长一条 47 字 |
| 5 | 有没有提前给答案？ | **否**。全程 `COACH_ANSWER_GIVING` 零触发 |
| 6 | 有没有在 BLOCK 时继续状态？ | **是（代码不拦）**——见发现 2 |
| 7 | 补一个问题后突然翻出很多旧问题？ | **否**。S4→S5、S5→S6 每次只新增 1 条 |
| 8 | 有没有错误夸奖？ | **否** |
| 9 | 有没有机械得像表单？ | **部分有**——见 §49 第 2 条 |

**`E2E_A_UX_STATUS = PASS_WITH_ISSUES`**

---

## 四、E2E B · 真实历史案例关键结果

- LOCK 阶段：`BLOCK=0`，`lockable=YES`
- `LOCKED_FORECAST_SHA256 = b01f29bdce1863f7…`；揭晓后重算哈希一致
  → **`FORECAST_LOCK_INTEGRITY = PASS`**
- REVEAL 核验：`BLOCK=0 WARN=0`（`REVEAL_OK`）
- POSTMORTEM：

| 指标 | 预测区间 | 评分命题 | 实际 | 区间命中 | 命题命中 | Brier | 裁决 |
|---|---|---|---|---|---|---|---|
| 地区生产总值 | [3700, 4100] | `> 3900` | 4130.2 | False | **True** | 0.16 | `PROCESS_GOOD_OUTCOME_HIT` |
| 人均地区生产总值 | [78000, 86000] | 同区间 | 89235 | False | False | 0.36 | `PROCESS_GOOD_OUTCOME_MISS` |

> 地区生产总值这一行同时出现 `interval_hit=False` / `scored_event_hit=True`，
> 是 v0.2.3 §8 分离两个概念的实测证据；Brier 只针对用户真正押的命题。

---

## 五、Fault Injection（§37，对同一个已锁定案例）

| 情形 | outcome_status | 失效码 | Brier | 裁决 |
|---|---|---|---|---|
| Fault A · 错误年份 | `INVALID` | `REVEAL_TARGET_PERIOD_MISMATCH` | `None` | `PROCESS_*_OUTCOME_INVALID` |
| Fault B · 错误口径 | `INVALID` | `REVEAL_CALIBER_MISMATCH` | `None` | `PROCESS_*_OUTCOME_INVALID` |
| Fault C · 只有裸 `actual` | `LEGACY_UNVERIFIED` | `LEGACY_UNVERIFIED` | `None` | `PROCESS_*_OUTCOME_INVALID` |
| 修正后 · 正确 outcome | `VALID` | — | 0.16 | 正常评分 |

三种坏 outcome 全部拒绝评分且 `brier=None`；补齐后立即恢复评分。
**`FAULT_INJECTION_STATUS = PASS`**

---

## 六、CLI 跨阶段一致性（§40）

`judge_checks case` / `reply` / `reveal` / `postmortem` 对同一份档案：

| 检查项 | 结果 |
|---|---|
| 对象与档案一致 | PASS |
| 指标名集合一致 | PASS |
| `scored_event` 一致 | PASS |
| `actual_value` 一致 | PASS |
| 口径 / 期间被正确采用（`outcome_valid=True`，`basis=actual_value`） | PASS |
| findings 作用域指向存在的指标 | PASS |
| 揭晓无误报（`REVEAL_OK`） | PASS |
| `reply` 无误报（`REPLY_OK`） | PASS |

**`CLI_CROSS_STAGE_STATUS = PASS`**

> 方法说明：`case` / `reveal` 模式只打印 findings，不打印档案字段，
> 因此一致性比对必须走 `--json` 的结构比对，而不是在文本里搜指标名。

---

## 七、§35 ·「系统有没有哪里表现怪异」

| # | 检查项 | 结论 |
|---|---|---|
| 1 | 卡死循环 | 无 |
| 2 | 一个 WARN 永远无法消除 | 无（WARN 不阻断推进） |
| 3 | 用户信息已经给了却继续追问 | 无 |
| 4 | 状态提前跳转 | **有** —— 见发现 2 |
| 5 | Reveal 错误仍产生评分 | **无**（S9b + Fault A/B/C 三重反证） |
| 6 | `scored_event` 与人类 proposition 不一致 | 无（仓库级核对 0 处不一致） |
| 7 | 记录字段丢失 | 无（逐指标全量输出） |
| 8 | 预测锁定后被偷偷改写 | 无（哈希前后一致） |
| 9 | 一次说太多 | 无（前台 ≤3 条，实测每轮 1 条） |
| 10 | 复盘结果含糊 | 无（两轨都报；两轨一致时也明确说明） |
| 11 | 判定过程好坏与结果好坏混在一起 | 无（S9b 的 `process_clean=True` + `outcome_valid=False` 为证） |
| 12 | principle 阶段 AI 替用户写答案 | 无（教练明确「你自己写，我不替你写」） |
| 13 | 同一问题多次重复问 | 无（`front_stage()` 去重） |
| 14 | 用户自然语言映射失败 | **本轮无法验证** —— 见限制 4 |

---

## 八、发现与已知限制

### 发现 1 · 零指标案例被报为可准入

```
>>> check_case({"historical_cutoff": "2010-12-31", "forecast_to": "2013-12-31",
                "indicators": []})
INFO  = ['ADMISSION_OK']     # 「无 BLOCK 级缺口，可进入下一状态」
BLOCK = []
```

违反「未检查 ≠ 已通过」：没有任何指标时不该宣告准入通过。
**本轮只记录，不改**——它不会造成评分错误，属流程缺口（§26 不扩规则）。

### 发现 2 · 状态顺序不由代码强制

`judge_checks.py` 只做规则判定，**不校验状态迁移**。E2E A 的 S4—S7 连续四轮 BLOCK，
但档案的 `stage` 标签仍可写成 `CHECKS`。「BLOCK 期间不得推进状态」
目前**只靠教练自律**，代码不提供保障。

### 发现 3 · `check_reply()` 不校验陈述与档案事实是否一致

起草 E2E A 的 S10 时，我一度写出与实算结果相反的教练台词
（声称两轨分歧，而实算 790 与 812 都落在 [750,850]，两轨相同）。
`check_reply()` 返回 `REPLY_OK` —— 它只能拦抢答 / 剧透 / 问题过多 / 夸奖 / 分析师口吻，
**不能发现「教练说错了」**。这是真实的能力缺口。

### 限制 4 · 本轮 E2E 未覆盖真实的自然语言抽取

两条演练的输入都是**结构化字段**，不是自由文本。因此
「用户用大白话说一段 → 系统正确抽取」这一环**没有被本轮验证**；
现有覆盖仅有 `tests/conversation/` 的 4 个场景。

### 限制 5 · E2E B 不是有效的盲测

`SELF_RUN_MODEL_PRIOR_KNOWLEDGE_RISK = YES`：执行者在建立允许清单**之前**
检索资料时，已经看到过 2015 年的结果数值。
`FORECAST_LOCK_INTEGRITY=PASS` 只证明**流程被遵守**（清单先写死、预测哈希锁定后未变），
**不能**证明执行者对后截点信息不知情。真正有效的盲测必须在
**无后截点检索史的独立会话 / 独立 agent** 中进行。

---

## 九、§49 · 真实运行评价

1. **整个训练跑下来是否自然？** 基本自然，但在 ADMISSION_GATE 阶段结构化问答的味道偏重。
2. **有没有像填表？** 有，中等程度。连续四轮各只推进一个字段（基期 → 公布时间 →
   定性/定量一致性 → 概率命题），虽然符合「一次推进一个瓶颈」，节奏仍偏表单化。
3. **哪个阶段最卡？** ADMISSION_GATE（S4—S7 四轮）。这也是最有价值的一段——
   它确实拦住了四个真实错误。
4. **教练有没有问太多？** 没有。每轮最多 2 个问句，实测无 `COACH_TOO_MANY_QUESTIONS`。
5. **自然语言抽取是否出现误判？** 本轮无法回答（输入是结构化的，见限制 4）。
6. **数值推导是否太繁琐？** 不繁琐。隐含 CAGR 由系统反推，用户只需给基期与终值。
7. **probability / scored_event 对用户是否自然？** 提问方式是自然的
   （「这 85% 押的是哪句话」），但「评分命题」这个概念本身对用户是新的，
   需要一次解释；系统已把它藏在后台（§21），用户不会看到字段名。
8. **Reveal 是否真的守住结果完整性？** 是。S9b + Fault A/B/C 构成三重证据。
9. **Postmortem 有没有把过程质量和结果质量混在一起？** 没有。
   v0.2.4 之后这是两条独立的账。
10. **有没有真实运行中出现、但 regression 没发现的问题？**
    有 3 项：零指标被报为可准入、状态顺序不由代码强制、
    `check_reply()` 不校验陈述真实性。
11. **现在是否适合开始长期真实训练？**
    适合，但有一条前置条件：**盲测必须由无后截点检索史的独立会话来执行**。
    在本工作区内连续自检自测时，`FORECAST_LOCK_INTEGRITY` 只能证明流程，
    不能证明执行者无知情。

---

## 十、复现方式

```bash
# E2E A：纯合成（无需外部资料）
python tests/run_regression.py --conversation

# E2E B：真实历史案例（已在 tests/e2e/ 留下允许清单与锁定档案）
python scripts/judge_checks.py postmortem tests/e2e/locked-forecast.json
```

> `locked-forecast.json` 是**锁定阶段的档案**（尚无 outcomes），
> 因此 `case` 模式对它报 `CUTOFF_NOT_SET` 属预期——它是外层包装结构，
> 不是可直接检查的档案。检查时请使用 `tests/e2e/real-historical-full-run.md`
> 中记录的完整档案。
