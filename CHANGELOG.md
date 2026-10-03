# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 的结构，版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

---

## [0.2.2] — 2026-10-03

定向可靠性修复（bugfix / reliability release）。**不重构架构、不新增 roadmap 大功能**。
目标是补齐从"结构化测试正确"到"真实长期训练可靠"之间的工程断点：两个最重要的缺口是
**自然语言 → JSON 状态**，以及 **预测结果 → 多指标可靠复盘**。

### Fixed

- **完整日期期限计算**：`forecast_years()` 此前优先用年份差，`2010-12-31 → 2013-01-01`
  被算成 3 年（实际 732 天 ≈ 2.00 年），使隐含 CAGR 被系统性低估。现在两端均为完整日期时
  按 `(d1−d0).days / 365.25` 计算，仅在日期不完整时退回年份差
- **历史序列门槛过度硬编码**：`MIN_HISTORY_POINTS=3` 从不可通融的死规则改为可降级——
  走替代推导路径（`history_basis` ∈ capacity/order/share/…）**且写清机制**时，由 BLOCK 降级为
  `LIMITED_HISTORY`(WARN)；概率 ≥70% 追加 `LIMITED_HISTORY_PROB_TOO_HIGH`(WARN)。
  声明路径却不写机制仍按 BLOCK
- **多指标复盘只评价第一个指标**：`postmortem()` 重写为逐指标裁决 + 案例级汇总，
  修复"任何 case 级 outcome 都作用在 `indicators[0]`"的缺陷
- **作用域污染**：引入 case-level 与 indicator-level 的归因隔离；某指标的过程缺陷不再污染
  其他指标的评价，唯一例外是 case 级致命缺陷（`CUTOFF_NOT_SET` / 污染 / 前视泄漏）
- **反向对照用例时间逻辑**：`test-12` 的基期改用 2009 全年正式公布值（`base_published_at: 2010-02-25`），
  修正此前"截点当天引用次年才公布的数据"这一现实中不可能的自洽错误
- **`LEVEL1_HORIZON_TOO_LONG` 容差**：365.25 天换算使含闰日的整年区间略超 3.0000，容差调整为 3.05

### Added

- **`references/state-extraction.md`** — 自然语言 → 结构化状态映射表（逐字段），
  确立核心原则 **「未检查 ≠ 已通过」**：字段缺席表示尚未检查，不得默认 `false`；
  允许并强制 `"unknown"` 作为显式第三态
- **`references/reveal-protocol.md`** — 揭晓协议：城市/企业来源层级、口径核验、
  统计修订处理（`as_reported_then` / `latest_revised` 必须同时保留）、`REVEAL_CALIBER_MISMATCH` 等规则
- **三态字段机制**：`stock_flow_relevant` / `quantity_price_relevant` 等字段支持
  `true` / `false` / `"unknown"`；缺席报 `GATE_FIELD_UNCHECKED`，`"unknown"` 报 `GATE_FIELD_UNKNOWN`
- **`OUTCOME_UNKNOWN` 结果三态**：`PROCESS_GOOD_OUTCOME_UNKNOWN` /
  `PROCESS_DEFECTIVE_OUTCOME_UNKNOWN` / `CASE_INVALIDATED` / `CASE_MIXED` 等案例级裁决。
  **未知 ≠ 未命中**：没有结果记录时不得判成 MISS
- **信息防火墙双层时间**：区分 `data_period_end`（数据所属期）与 `published_at`（公开时间），
  新增 `FIREWALL_LOOKAHEAD_LEAKAGE`（BLOCK）——最隐蔽的前视泄漏：所属期在截点前，
  但截点当天根本还没公布（如截点 2010-12-31 使用"2010 全年 GDP"）
- **前台呈现优先级 P0—P7**：`sort_findings()` + `front_stage()`，让"一次只处理最关键 1—3 条"
  有确定实现；神木案例不再把 36 条 BLOCK 平铺给用户
- **`reveal` CLI 子命令**与 `check_reveal()` 检查器
- **对话级测试**：`tests/conversation/`（4 个自然语言用例）+ `tests/conversation-cases.md`，
  运行器新增 `--conversation` 与 `extract` / `extract_absent` 映射断言
- **Test 13—18**：完整日期期限、结果未知、多指标复盘、发布时间晚于截点、历史不足与替代路径、三态字段映射
- **变异测试 D**：禁用"发布时间晚于截点"判定 → 期望 `test-16` 转红

### Changed

- **`INTAKE` 默认由教练直接出题**：给对象 + 截点，不先问偏好；仅当用户明确要求自选时才进入偏好确认
- 神木回归夹具的 postmortem 由"结果未命中"改为 **`PROCESS_DEFECTIVE_OUTCOME_UNKNOWN`**
  （无须知道结果即可定论"当时不应锁定"）
- `SKILL.md` 升至 `0.2.2`，登记两个新 reference；frontmatter 描述不变
- 测试规模：12 tests / 20 steps → **18 tests / 41 steps**（含 4 个对话级用例）

### Known Limitations

- 自然语言抽取仍依赖教练判断，脚本只能断言"抽取后的字段"是否符合规则；
  `state-extraction.md` 提供的是规范而非自动解析器
- 来源层级判定基于关键词匹配（`REVEAL_SOURCE_TIERS`），措辞差异可能漏判，故为 WARN 而非 BLOCK
- 修订状态若用户无法确定，只能记 `"unknown"`，命中判定按现行值处理并在档案中标注

---

## [0.2.1] — 2026-10-03

### Added

- README 新增 **「一句话安装」**：给出可直接复制给任意 AI Agent 的自然语言安装指令，含纯对话型 AI（不能执行命令）的「读取 URL 作为长期指令」变体，以及各 Agent 技能目录对照表
- README 补注 `raw.githubusercontent.com` 的连通性坑（实测直连返回 `000`），并给出仓库页面地址作为备选
- README 补充依赖说明（Python optional but recommended）与安装后自检命令

### Changed

- 仓库名由 `---` 改为 `judgment-training`；README 的 clone 地址由占位符换成真实地址
- 安装方式的定位从"给用户跑脚本"改为"给 AI 一句话"：安装的本质是把目录放进技能目录，交给 AI 自己完成比让用户执行脚本更通用

### Fixed

- 记录 GitHub 会用短横线 sanitize 中文仓库名的实操坑（实测"判断力训练"变成字面 `---`），写入 `docs/design-notes.md` 人工作业提示

### Removed

- 放弃两个 shell 安装脚本（`scripts/install.sh` / `install.ps1`）。**在提交前移除，未进入版本历史**。
  实测它们涉及三个 Windows 特有陷阱（PS 5.1 对无 BOM 的 UTF-8 `.ps1` 按 GBK 解码、原生程序 stderr 在 `ErrorActionPreference='Stop'` 下被当作终止性错误、`exit` 会杀掉 `irm | iex` 的调用方会话），维护成本高于收益

---

## [0.2.0] — 2026-10-03

对原"历史预测与判断训练教练"Skill 的**重大结构升级**。原版本仅为一段长提示词，规则不可测试、不可回归、不可累积；本版本将其重构为可长期维护的开源项目。

### Added

- **Forecast Admission Gate（预测准入闸门）** — 十查机制，其中八项为 BLOCK 级硬门槛。基期、口径、单位、历史序列、驱动变量、约束变量、存量流量、数量价格任一缺失即禁止进入正式数值预测
- **Base Rate Check（基准率检查）** — 缺基准率标记为 `BASE_RATE_MISSING`（WARN，不阻断），并在概率 ≥70% 时追加 `BASE_RATE_MISSING_PROB_TOO_HIGH`，强制下调置信度
- **Quantitative Forecast Workflow（定量预测流程）** — 分解族（量×价、收入×利润率、人口×人均、市场规模×市占率、产能×利用率×价格）、单位与口径陷阱清单
- **Implied CAGR Check（隐含 CAGR 反推）** — 任何预测提交后强制反推年均复合增速；`|CAGR| > 25%` 触发 `EXTREME_GROWTH_UNJUSTIFIED`；方向与定性判断相反则硬拦截（`GATE_QUAL_QUANT_CONFLICT`）
- **Probability Logic Validation（概率逻辑校验）** — 命题化强制（`PROB_NO_PROPOSITION`）、互斥穷尽求和（`PROB_SUM`）、包含关系单调性（`PROB_LOGIC_SUBSET`）、统一概率检测（`PROB_UNIFORM`）、点预测与窄区间精度（`PROB_PRECISION`）、极端概率追问（`PROB_EXTREME`）
- **Scenario Design（情景设计规范）** — 禁止机械三档；情景差异必须来自变量组合；每个情景须回答"哪几个变量变了"
- **Information Firewall（信息时间防火墙）** — 截点后材料隔离（`FIREWALL_CONTAMINATION`）；污染处理只说明不可用，不解释其含义
- **Dual-Version Prediction（V1/V2 版本链）** — 区分 A 类（截点前遗漏）与 B 类（截点后新增）信息；B 类不得并入原预测
- **Postmortem Four-Quadrant（复盘四象限）** — `PROCESS_GOOD_OUTCOME_HIT` / `PROCESS_GOOD_OUTCOME_MISS` / `LUCKY_ACCURATE` / `PROCESS_DEFECTIVE_OUTCOME_MISS`；错误归因九分类覆盖 BLOCK 与 WARN 两级
- **Deterministic Gate Engine** — `scripts/judge_checks.py`，将铁律实现为可执行规则，含教练回复越界守卫（抢答 / 剧透 / 问题过多 / 夸奖 / 分析师口吻）
- **Regression Tests** — 12 个可执行夹具、20 个步骤，另含反向对照用例防止"一律拦截"通过测试
- **Shenmu Case** — 神木 2010 失败案例作为回归基线；该夹具触发 36 BLOCK + 6 WARN
- **State Machine** — 11 状态流程（`INTAKE` → `ARCHIVED`），各状态有明确出口条件，禁止跳跃
- **Difficulty Levels** — Level 1/2/3 分级与升级判据
- **Archive Schema** — `references/prediction-record-template.md` 定义 YAML 档案、最终提交字段、更新留痕、复盘模板、判断原则库格式

### Changed

- `SKILL.md` 从"长提示词"改为精炼主文件（约 3.5k 字符）：只保留角色、九条铁律、状态机、检查器入口、reference 加载表、语气
- 复杂方法论全部外置到 `references/`，按需加载，避免主文件膨胀
- 前台上限从"无约束"收紧为**每轮 1—3 问**；重规则后台执行

### Fixed

- 修复"无基期也能开始预测"的漏洞
- 修复"定性判断与数值矛盾无人拦截"的漏洞
- 修复"统一概率无人质疑"的漏洞
- 修复"揭晓时倒出全部后续历史、破坏续练"的漏洞
- 修复 CLI 把测试夹具误当裸案例读取并静默给出错误结论的缺陷（`_iter_cases` 自动适配两种输入结构）

### Known Limitations

- 脚本只覆盖可判定规则；提问质量与语气依赖人工回归
- 阈值（CAGR 25%、区间相对宽度 5%、统一概率容差 2%）为经验取值
- 信息防火墙依赖用户如实申报材料日期
- 未内置案例库；未实现档案的自动读写

---

## [0.1.0] — 前身

原"历史预测与判断训练教练"提示词版本。无版本控制、无测试、无档案结构。

已知缺陷（本版本已修复）：

- AI 容易抢答、替用户做研究
- 无基期准入检查
- 无隐含 CAGR 检查
- 无基准率机制
- 无概率逻辑校验
- 无信息时间防火墙
- 无复盘归因体系
