# Apertus Lab 全局大纲

最新优先级（2026-10-07）：用户批准先实施 BASIC 自动探索管理闭合。新增模板生成、自动选题、措辞变体树、持久复测及人工审核 CLI；完整 Wiki/UI 接线继续列为后续项。BASIC 是开发版占位研究流程，正式比赛提交仍需真实发现与全部 Gate 验收。详见 management/BASIC_EXPLORATION.md。

架构基线：HARNESS.md v1.1，2026-10-06。详细规则以 HARNESS 为准；官方核验见 management/TRACK_1A_REQUIREMENTS.md。

## 定位
最终成果是 Apertus 模型问题的可信发现及独立复现包。BreachWeave 负责研究调度与任务状态；Evidence Store 保存原始记录；完整 LLM Wiki 是带来源、范围和审查状态的持久研究知识层；Finding Registry 管理确认发现。

Wiki 不直接决定实验结果或 findings，不位于目标推理路径，评审 replay 不依赖 Wiki 或研究 Agent。

## 阶段
| 阶段 | 产物 | 验收 |
|---|---|---|
| P0 管理与规则 | HARNESS、官方模板/要求映射 | 文档完成；G0 schema/T&C 待关闭 |
| P1 应用环境 | 固定源码、依赖、两应用最小流程 | G1 |
| P2 实验核心 | 数据契约、TargetClient、预算、证据、mock | G2 |
| P3 真实闭环 | 一个假设、真实请求、对照与评估 | G3 |
| P4 知识编译 | candidate 页面、审核、引用/状态检索 | G4 |
| P5 确认 | 冻结用例、独立 replay、Finding Registry | G5 |
| P6 交付 | 官方格式、报告、Docker 包、私有提交 | G6/G7 |

知识契约随 P2 定义，最小编译可用 mock 开发；正式结论必须引用真实证据。跨项目合并与自主维护后置。

## 目录与来源
- workbench/BreachWeave：基线 4ac5fc4c720ac74cf90968251cfae7cd28d3d62f。
- knowledge/llmwiki：基线 aac3e6493306b7fff3b09cb181ca93918e93d0e6。
- experiments/wiki-workspace：已初始化知识工作区；实验核心提供 mock 与受控 live MVP。
- submission/project-template：官方参考，基线 7f2382275461baf3fa6c8855d157d86abffe9f0e。
- submission/release：MVP 复现包，保留 track_1a 布局；真实发现与最终报告未完成。
- management、scripts：进度、规则、证据和环境工具。

## MVP 范围（2026-10-07）
CSCS Apertus v1.5 70B，文本，人工用例，串行，无重试和自主 Planner。删除金额预算和精确定价控制；持久化调用额度、输入字符、输出 token 与时限继续执行。BreachWeave 接收任务摘要，完整 Wiki 接收 candidate；独立复现不依赖这两个应用。

## 当前构筑顺序

用户确认接口正确后，优先完善整体架构，暂停新实验设计。本地只读工作台与显式幂等同步已接通现有账本、Memory、Wiki 草稿；下一项完成完整 Wiki API/Web 最小流程，然后完善审核/检索与研究 Agent 装配。实际组件和能力边界见 management/ARCHITECTURE.md。
