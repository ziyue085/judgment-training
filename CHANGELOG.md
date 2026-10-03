# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 的结构，版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

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

- `SKILL.md` 从"长提示词"改为精炼主文件（约 5.6k 字符）：只保留角色、九条铁律、状态机、检查器入口、reference 加载表、语气
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
