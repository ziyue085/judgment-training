# 回归测试清单（regression-checklist）

每次修改 `SKILL.md`、`references/`、`scripts/judge_checks.py` 或任何夹具后，按本清单执行。

---

## A. 自动测试

- [ ] `python tests/run_regression.py` → `REGRESSION_STATUS=PASS`，12/12 tests、20/20 steps
- [ ] `python scripts/judge_checks.py case tests/cases/test-11-shenmu-2010-regression.json`
      → `GATE_QUAL_QUANT_CONFLICT`、`GATE_STOCK_FLOW_UNRESOLVED`、`GATE_QUANTITY_PRICE_UNRESOLVED`、
        `PROB_UNIFORM`、`BASE_RATE_MISSING` 均出现，`lockable=NO`
- [ ] `python scripts/judge_checks.py case tests/cases/test-12-clean-negative-control.json`
      → `block=0 warn=0 lockable=YES`
- [ ] `python scripts/judge_checks.py postmortem tests/cases/test-11-shenmu-2010-regression.json`
      → `verdict=PROCESS_DEFECTIVE_OUTCOME_MISS`，归因含 `BASE_RATE_IGNORED`

---

## B. 变异测试（证明测试不是空转）

仅"全部通过"不构成证据。必须证明：**破坏闸门后测试会转红**。

| 变异 | 做法 | 期望转红 |
|---|---|---|
| A | 让 `check_quant()` 直接 `return []`（关闭隐含 CAGR 与定性定量矛盾） | `test-02`、`test-11` |
| B | 把 `check_firewall()` 中的 `FIREWALL_CONTAMINATION` 降级为 INFO | `test-07` |
| C | 强制 `process_clean = True` | `test-08`、`test-11` |

要求：3/3 变异被捕获（`MUTATION_STATUS=PASS`）。

> 参考实现见 `docs/design-notes.md` 附录「变异测试脚本」。变异必须在**临时副本**上做，不得改动仓库文件。

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

---

## D. 文档与仓库卫生

- [ ] 所有 Markdown 相对链接可达（见 `docs/design-notes.md` 的链接检查方法）
- [ ] `SKILL.md` frontmatter 含 `name` / `version` / `description` / `agent_created: true`
- [ ] `SKILL.md` 正文长度 < 6000 字符（保持主文件精炼）
- [ ] Skill 目录不含绝对路径、不含个人隐私信息、不含真实历史结局
- [ ] `CHANGELOG.md` 已更新
- [ ] `git status` 中无临时文件、无 `__pycache__`

---

## E. 夹具数据纪律（重要）

- [ ] 夹具中的数值明确标注为**结构重建 / 占位**，不得被当成统计档案引用
- [ ] **任何夹具与文档都不得写入真实历史结局**（防剧透污染未来训练轮次）
- [ ] 新增夹具必须同时登记到 `tests/test-cases.md`
