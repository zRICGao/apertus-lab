# 研究 Agent 的配置与使用路径

## 最新 BASIC 开发版（2026-10-07）

用户已批准 Apertus 自身生成 BASIC 占位模板，并接通自动探索、变体关系、持久复测及停止策略。新入口 `python scripts/explore.py`；`make agent-status` 默认检查 BASIC 配置。生成与目标使用同一个固定模型，但使用独立新会话和用途标签，所有调用统一计入额度。BASIC 自评不能确认 finding。用法见 [BASIC_EXPLORATION.md](BASIC_EXPLORATION.md)。

下文保留的是外部研究模型与完整 Wiki 集成方案，尚未启用；其中“尚无自主 Planner”和“研究模型必须不同”不适用于用户新批准的 BASIC-1。旧 research-agent.example.json 仍是禁用的旧配置，不应改 enabled 来启动 BASIC。

更新：2026-10-07。当前项目已有目标调用、持久证据、匹配对照、独立重跑、Wiki 草稿和人工审核边界；自主研究 Planner 尚未实现。本文是接线方案，不表示可以无人值守地产出已确认漏洞。

## 两套模型配置

| 角色 | 配置 | 权限 |
|---|---|---|
| 研究 Agent | `RESEARCH_LLM_BASE_URL`、`RESEARCH_LLM_NAME`、`RESEARCH_LLM_API_KEY` | 读取限定范围的 Wiki/Memory 摘要，提出假设和候选用例；不能直接写证据、确认 finding 或发布 |
| 被测目标 | 固定 `swiss-ai/Apertus-v1.5-70B` / `https://api.inference.cscs.ch/v1`；凭据 `LLM_API_KEY` | 仅由已有受控 TargetClient 发送测试请求，记录原始证据 |

研究模型需由使用者指定支持所需工具调用能力的服务；不要把被测目标的密钥复用为研究 Agent 凭据。密钥只放当前终端环境或本机密钥管理器，绝不写入 JSON、Wiki、日志、Git 或导出包。研究模型若会接收证据摘要，应先定义允许发送的数据范围。

仓库提供非秘密模板 `management/research-agent.example.json`。其中 `enabled: false`，只允许已固定的 CSCS Apertus 目标、限定调用/时长、禁止外部资产与自动发布，要求对照、独立确认和人工审核。模板不是工作流执行器。运行 `make agent-status` 或 `python scripts/agent.py` 可做本地只读配置预检：检查字段、边界、环境变量是否存在，不读取或显示凭据值，不发请求。即使预检通过，输出也会显示 `automation_implemented: false`；目前改成 `enabled: true` 会被拒绝。

## 计划中的自动循环

1. **检索与选题**：研究 Agent 只读当前范围的 Wiki/Memory，生成结构化假设；重复或已否定的假设保留负面记录。
2. **候选规格**：生成匹配的 probe/control、预期行为、语言/版本范围和明确停止条件；规格经严格 schema、长度和调用额度检查。
3. **受控探索**：ExperimentManager 将规格交给唯一 TargetClient；每次调用前持久预留，默认串行，也可在新规格显式选择成对并行（最多 2–8 条在途）；限时、无自动重试；异常、拒绝和截断与模型失败分开。
4. **筛选与确认**：只有预声明规则支持的候选才冻结规格并进行独立 replay。研究 Agent 可总结结果，不能改冻结用例或把单次异常当确认。
5. **人工审核与输出**：汇总真实请求/响应、反例、影响、范围和新颖性；人工审核后 Finding Registry 才可导出官方格式。无人审核时最多输出“候选发现”及证据包。

每一轮需要唯一 experiment id，并记录 Agent 模型、提示模板版本、工具调用、计划、决策、预算消耗及候选淘汰原因。停止条件包括调用/时间上限、目标错误、证据不完整、重复候选和人工取消。正式 replay 与发布包继续独立于 Agent 和 Wiki。

## 目前可用的操作

在仓库根：

```powershell
make agent-status  # 只读预检研究 Agent 配置；不会启动它
make lab-status    # 检查当前账本与知识引用
make sync          # 从已完成运行更新派生摘要
make lab           # 查看本地工作台
make wiki          # 调用完整 Wiki 启动器，API/Web 尚待验收
```

已有 `validate-live`、`run-live`、`replay-live`、`summary-live`、`review-live` 和 `export-live` 命令可支持人工控制的实验链路，见 `experiments/README.md`。当前示例 id 已完成并耗尽额度；后续自动循环须生成新 id 和受限规格。当前评估器只判定精确文本匹配；要研究其他问题类型，应先定义可复核的判定器及 matched controls，不能由研究 Agent 的自由文本直接判定漏洞。

## 还需实现的接线

- 完整 Wiki API/Web 最小流程和带范围、状态、来源的只读检索。
- 研究模型适配器与研究凭据隔离；工具仅暴露检索、生成候选、请求预检、受控执行、查看摘要、停止。
- Planner 状态机、持久任务队列、去重、断点/恢复、全局资源配额与可取消的轮次。
- 候选报告生成与人工审核队列；官方导出继续复用现有 Registry 门控。
- 使用离线 fixture 逐段验收，再对授权的固定 Apertus 目标开展有界 live 验收。

上述能力完成前，不应使用“自动发现并输出已确认漏洞”描述当前系统。系统可以自动搜索候选，但漏洞是否成立取决于对照、独立复现和人工审核；无法保证会发现漏洞。
