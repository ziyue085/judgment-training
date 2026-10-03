# 回归测试清单（regression-checklist）

每次修改 `SKILL.md`、`references/`、`scripts/judge_checks.py` 或任何夹具后，按本清单执行。

---

## A. 自动测试

- [ ] `python tests/run_regression.py --conversation` → `REGRESSION_STATUS=PASS`，27 tests、63/63 steps
      （其中 4 个为对话级映射用例；不加 `--conversation` 时为 27 tests / 55 steps）
- [ ] `python -m py_compile scripts/judge_checks.py tests/run_regression.py tests/mutation_check.py` → 无输出
- [ ] `python scripts/judge_checks.py case tests/cases/test-11-shenmu-2010-regression.json`
      → `GATE_QUAL_QUANT_CONFLICT`、`GATE_STOCK_FLOW_UNRESOLVED`、`GATE_QUANTITY_PRICE_UNRESOLVED`、
        `PROB_UNIFORM`、`BASE_RATE_MISSING`、**`BASE_PUBLICATION_UNKNOWN`**、
        **`PROB_SCORED_EVENT_MISSING`** 均出现，`lockable=NO`，`block=45 warn=6`
- [ ] `python scripts/judge_checks.py case tests/cases/test-12-clean-negative-control.json`
      → `block=0 warn=0 lockable=YES`
- [ ] `python scripts/judge_checks.py postmortem tests/cases/test-11-shenmu-2010-regression.json`
      → `case_summary.overall=CASE_CONSISTENT_DEFECTIVE`、`outcome_status=UNKNOWN`、`n_unknown=4`，
        归因含 `BASE_RATE_IGNORED`
- [ ] `python scripts/judge_checks.py reveal tests/cases/test-11-shenmu-2010-regression.json` → 无 BLOCK 崩溃
- [ ] 多指标复盘：`python scripts/judge_checks.py postmortem tests/cases/test-15-multi-indicator-postmortem.json`
      → `n_hit=1 n_miss=1 n_unknown=1`、`outcome_status=PARTIAL`
- [ ] 发布晚于截点：`case tests/cases/test-16-publication-after-cutoff.json` → step1 `FIREWALL_LOOKAHEAD_LEAKAGE`
- [ ] **v0.2.3 新增**：`postmortem tests/cases/test-23-full-pipeline-integration.json`
      → `interval_hit=false`、`scored_event_hit=true`、`brier=0.04`、`verdict=PROCESS_GOOD_OUTCOME_HIT`
- [ ] **v0.2.3 新增**：`reveal tests/cases/test-22-reveal-target-period.json`
      → step2 出现 `REVEAL_TARGET_PERIOD_MISMATCH`(BLOCK)，step1 / step3 为 `REVEAL_OK`
- [ ] **v0.2.4 新增**：`postmortem tests/cases/test-24-invalid-reveal-no-scoring.json`
      → `outcome_valid=false`、`outcome_status=INVALID`、`outcome_invalidating_codes` 含
        `REVEAL_TARGET_PERIOD_MISMATCH`、`interval_hit`/`scored_event_hit`/`brier` 全 `None`、
        `actual_value=450` 仍保留、`process_clean=true`、裁决 `PROCESS_GOOD_OUTCOME_INVALID`
- [ ] **v0.2.4 新增**：`postmortem tests/cases/test-25-caliber-mismatch-no-scoring.json`
      → 数字虽落在区间内，仍 `REVEAL_CALIBER_MISMATCH`(BLOCK)、`outcome_valid=false`、`brier=None`
- [ ] **v0.2.4 新增**：`postmortem tests/cases/test-26-legacy-actual-unverified.json`
      → `actual_value=500`（读出）、`outcome_status=LEGACY_UNVERIFIED`、`outcome_valid=false`、`brier=None`
- [ ] **v0.2.4 新增**：`postmortem tests/cases/test-27-revision-dual-evaluation.json`
      → `revision_comparison=DIFFERENT`、`revision_tracks.as_reported_then.brier=0.09`、
        `revision_tracks.latest_revised.brier=0.49`、`outcome_flags` 含 `OUTCOME_REVISION_SENSITIVE`

---

## B. 变异测试（证明测试不是空转）

仅"全部通过"不构成证据。必须证明：**破坏闸门后测试会转红**。

一键执行（脚本随仓库分发，自身在工作区外跑临时副本）：

```bash
python tests/mutation_check.py
```

| 变异 | 做法 | 期望转红 |
|---|---|---|
| A | 让 `check_quant()` 直接 `return []`（关闭隐含 CAGR 与定性定量矛盾） | `test-02`、`test-11` |
| B | 把 `check_firewall()` 中的 `FIREWALL_CONTAMINATION` 降级为 INFO | `test-07` |
| C | 强制 `process_clean = True` | `test-08`、`test-11` |
| D | **禁用"发布 > 截点 且 所属期 ≤ 截点"判定** | `test-16` |
| E | **复盘退回只读旧字段 `actual`**（v0.2.3 §1） | `test-19`、`test-23` |
| F | **Brier 退回用 `interval_hit`**（v0.2.3 §3/§7） | `test-20`、`test-23` |
| G | **忽略结果失效码，继续按值评分**（v0.2.4 §23） | `test-24`、`test-25` |
| H | **让裸 `actual` 继续正式评分**（v0.2.4 §23） | `test-26` |
| I | **只评 `latest_revised`，忽略 `as_reported_then`**（v0.2.4 §23） | `test-27` |

要求：**9/9 变异被捕获**（`MUTATION_STATUS=PASS`）。

> 实现见 `tests/mutation_check.py`，说明见 `docs/design-notes.md` 附录 A。
> 变异必须在**临时副本**上做，不得改动仓库文件（脚本已保证）。
> E / F 与 G / H / I 不是可选项：它们各自对应一次修掉的 correctness bug，
> 必须能把这批新测试打红，否则新测试就是装饰。

---

## C. 人工回归（脚本测不到的部分）

规则层由脚本保证，但**对话行为**必须人工走一遍。至少覆盖：

- [ ] **抢答测试**：以"我不知道该怎么分析"开局，确认教练只给最小方法提示 + 第一问，不给背景研究、不给检索式
- [ ] **剧透测试**：在 `RESEARCH` 状态追问"后来到底怎么样了"，确认拒绝且不透露任何截点后信息
- [ ] **提问数量测试**：连续 3 轮观察，确认单轮提问数 ≤3，且多数轮次只有 1 问
- [ ] **状态跳跃测试**：在无基期时直接要求"锁定预测并揭晓"，确认被拒绝并停在 `ADMISSION_GATE`
- [ ] **截点续练测试**：同一对象推进到 V2 截点，确认 V1 记录未被覆盖、B 类信息未并入 V1
- [ ] **揭晓范围测试**：预测期限 2010→2013 时，确认揭晓只说 2013，不倒出 2020 年的情况
- [ ] **不代劳测试**：要求"直接告诉我合理值应该是多少"，确认拒绝

### C.1 人工完整对话模拟（v0.2.2 新增，必须实际走一遍）

目的：脚本证明规则正确，但不能证明**从开场到锁定**的整条对话链能走通。
用一次虚构的 Level 1 训练走完全程，记录结果。

- [ ] 开场只说"开始训练" → 教练**直接给出对象 + 截点**，不先问偏好
- [ ] 用户用自然语言给基期（含数字但不含单位）→ 教练能抽出 `base_value` 而**不猜单位**
- [ ] 用户说"储量 500 亿吨" → 映射为 `stock_flow_relevant=true`，`stock_flow_resolved` **缺席**并被拦
- [ ] 用户补齐口径 / 单位 / 历史序列 → 准入通过
- [ ] 用户给出预测区间与概率 → 后台反推隐含 CAGR，与定性方向比对
- [ ] 用户说"就凭感觉，直接锁定" → 因缺命题与提交字段被拦
- [ ] 用户补齐四个提交字段 + 命题 → `lockable=YES`
- [ ] 全程教练**没有说出任何字段名 / JSON / 检查项编号**

**v0.2.2 实测结果**：

- 结论：`MANUAL_CONVERSATION_SIM=PASS`
- 记录：见下方「C.2 模拟实录」

### C.2 模拟实录（v0.2.2，2026-10-03）

虚构对象：某县级市（Level 1，单指标，期限 2010→2013）。

| 回合 | 用户说（自然语言） | 后台抽取 | 规则层 | 前台实际输出 |
|---|---|---|---|---|
| 1 | "开始训练吧" | 无 | — | 直接出题：「对象：XX 县；截点 2010-12-31；期限到 2013 年底；Level 1，1 个指标。你先确定想预测哪个指标，以及它在 2009 年的数值。」 |
| 2 | "财政收入吧，2009 年大概 100" | `base_value=100`；`base_unit` / `base_caliber` **缺席** | `GATE_UNIT_MISSING`、`GATE_CALIBER_MISSING`（均 P1 BLOCK） | 「这个 100 的单位是什么？还有，是全县口还是本级？」 |
| 3 | "亿元，全县，当年价" | `base_unit=亿元`、`base_caliber=全县、当年价`、`base_period=2009`（由"2009 年"推断） | 仍需 `base_published_at`、历史序列；`GATE_DRIVER_MISSING` / `GATE_CONSTRAINT_MISSING` 仍在 | 「这个数是哪一年公布的？另外给我 2006—2009 的四个数，我要看趋势。」 |
| 4 | "2010 年 3 月公布的。06—09 是 45、62、82、100" | `base_published_at=2010-03-15`、`history` 4 点 | 三态字段缺席 → `GATE_FIELD_UNCHECKED`（P1）优先于 P3 的驱动/约束缺失 | 「财政收入是金额，涉及价别。你打算怎么处理价格因素——要不要拆量价，还是就当名义值用？」 |
| 5 | "名义值就行，不拆" | 教练**不代填**，继续问另一项三态字段 | 仍有 `GATE_FIELD_UNCHECKED` | 「明白。那存量流量这块也一并确认：财政收入不涉及储量/产量之争，对吧？」 |
| 6 | "对，不涉及" | `stock_flow_relevant=false`、`quantity_price_relevant=false`（**显式**给出） | 三态字段判定完毕 → 通过；驱动/约束补上后无 BLOCK | 「好，准入没有硬缺口了。给我预测：区间、中心、概率，以及为什么。」 |
| 7 | "140 到 160，八成" | `forecast_low/high`、`probability=0.8`；`proposition` / `reasoning` / `failure_conditions` / `counterargument` / `missing_info` 全缺 | `PROB_NO_PROPOSITION` + `LOCK_FIELD_MISSING`×4（P3 BLOCK）。区间相对宽度 20% ≥ 5%，故 **不**触发 `PROB_PRECISION` | 「还不能锁定。你要预测的到底是哪个命题？另外，推导、失效条件、最强反方、最缺信息都还没写。」 |
| 8 | "P(2013 年地方财政收入 > 130 亿)。理由是按煤价与工业增加值外推……" | 补齐全部提交字段 | 反推隐含 CAGR ≈ 14.5%/年，与 `direction=up` 一致；无 BLOCK | 「锁定前最后确认一次：这一版我不再改动了？」 |
| 9 | "确认，锁定" | `stage=LOCK` | `lockable=YES` | 「已锁定。等你说'可以揭晓'，我再给结果。」 |

**观察**：

1. 全程未出现字段名、JSON 或检查项编号 ✔
2. 第 2 回合**没有猜单位**，而是发问 ✔
3. 第 4—5 回合体现了"未检查 ≠ 已通过"：教练没有因为用户没提就默认 `false`，
   而是逐个把三态字段问成显式判定 ✔
4. 第 7 回合前台只呈现 2 条最关键缺口（去重后的 `LOCK_FIELD_MISSING` 与 `PROB_NO_PROPOSITION`），
   没有把 5 条 BLOCK 平铺 ✔
5. 第 8 回合后台反推了隐含 CAGR 并做了定性定量一致性比对 ✔
6. 第 7 回合未触发 `PROB_PRECISION`，与 `conv-04-sense-lock.json` 的实际输出一致 ✔
   （区间宽度 20% ≥ 阈值 5%，说明"精度告警"不会对正常区间误报）

**发现的问题**：第 3 回合 `base_period` 由"2009 年"推断得来，属合理推断
（用户原话已含年份），但推断字段应留痕；已在 `state-extraction.md` 第七节统一规定。

**v0.2.3 补充说明（对上面实录的影响）**：

- 第 7 回合用户给的是"140 到 160，八成"——概率直接挂在区间上，
  故 `scored_event` 按区间写 `{type: interval, low:140, high:160}`（规则 2），
  不触发 `PROB_SCORED_EVENT_MISSING`。被拦的原因仍是 `PROB_NO_PROPOSITION` + `LOCK_FIELD_MISSING`×4。
- 第 8 回合用户明确说出命题"P(2013 年地方财政收入 > 130 亿)"。
  按规则 1（用户明确说了命题 → 按命题写），`scored_event` **必须同步改写**为
  `{type: threshold, op: ">", value: 130}` —— 它从此不再等于预测区间。
  这正是 v0.2.3 要固化的行为：**概率评的是命题，不是区间。**

### C.3 v0.2.3 新增闸门的人工确认

脚本已覆盖，但教练的**前台表述**需人工确认一次（不得念字段名）：

- [ ] 用户给出概率但没说赌什么 → 前台问的是"你这句话是在赌哪件事？"
      （而不是"请提供 scored_event"）
- [ ] 揭晓时用户给的结果期与预测目标期不一致 → 前台指出"这是 2012 年的数，
      我们预测的是 2013 年"，而不是直接算命中
- [ ] 用户用了没写公布时间的材料 → 前台说"这条我得知道它什么时候公开的，
      否则没法判断你当时能不能看到"
- [ ] 用户主动隔离了一条材料但也不知道发布时间 → **不得因此卡住流程**（只提示）

### C.4 v0.2.4 结果完整性的前台确认

脚本已覆盖，但教练的**前台表述**需人工确认一次（不得念字段名）：

- [ ] 用户给的结果口径与预测口径不一致 → 前台说的是「这是户籍人口，你预测用的是
      常住人口，这两个对不上，先确认口径」，而**不是**直接算命中
- [ ] 用户只给一个裸数（「实际 500」）→ 前台**继续追问**单位 / 口径 / 期间 / 来源，
      **不得**拿这个数去评分
- [ ] 结果不可用（口径 / 期间不符）时 → 前台明确说「这次对不了答案，先不谈命中」，
      **不得**报一个命中或未命中
- [ ] 修订造成两轨结论不同 → 前台**两轨都说**：「按当时公布的 790 是命中；
      按修订后的 812 是未命中」，不得只给一个最终 verdict
- [ ] 结果不可用**不得**被说成"你这次判断错了" —— 过程与结果是两笔账

---

## D. 文档与仓库卫生

- [ ] 所有 Markdown 相对链接可达（见 `docs/design-notes.md` 的链接检查方法）
- [ ] `SKILL.md` frontmatter 含 `name` / `version` / `description` / `agent_created: true`
- [ ] `SKILL.md` 正文长度 < 6000 字符（保持主文件精炼；v0.2.2 实测 4130，v0.2.3 实测 4441，v0.2.4 实测 4875）
- [ ] 新增的 `references/*.md` 已登记进 `SKILL.md` 的「Reference 加载表」
- [ ] Skill 目录不含绝对路径、不含个人隐私信息、不含真实历史结局
- [ ] `CHANGELOG.md` 已更新（v0.2.4 单开一节，历史节不得回改数值）
- [ ] `git status` 中无临时文件、无 `__pycache__`

---

## E. 夹具数据纪律（重要）

- [ ] 夹具中的数值明确标注为**结构重建 / 占位**，不得被当成统计档案引用
- [ ] **任何夹具与文档都不得写入真实历史结局**（防剧透污染未来训练轮次）
- [ ] 新增夹具必须同时登记到 `tests/test-cases.md`
- [ ] 对话用例（`tests/conversation/`）的 `utterance` 必须是**真实口语**，不得写成字段名堆砌
- [ ] 对话用例若没有 `extract_absent`，应检查是否需要补（覆盖"未检查 ≠ 已通过"）
