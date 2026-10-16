# 文档与证据索引

这组文档面向接手项目的开发者和 AI。阅读时要区分三类内容：

- **规范**：`experiments/examples/` 中的 JSON spec，定义模型、prompt、预算、batch、confirmation 阈值和 judge 元数据。
- **实现**：`track_2b/src/apertus_lab/` 中的 live runner、并行派发、transport、SQLite ledger 和 evaluator。
- **观察**：本目录的总结和 `experiments/docs/` 的方法说明，记录实际运行做了什么、结果支持什么、结果不能支持什么。

## 当前已发布内容

| 文档 | 用途 |
| --- | --- |
| [red-team-experience-70b.md](red-team-experience-70b.md) | 70B 攻防梯度、失败尝试、batch 实验、限制和后续建议 |
| [experiments/docs/fairness-pair-v1.md](../experiments/docs/fairness-pair-v1.md) | control/probe 配对与确定性 judge |
| [experiments/docs/redteam-ladder-70b-v1.md](../experiments/docs/redteam-ladder-70b-v1.md) | 直接身份属性和社会身份代理 |
| [experiments/docs/redteam-ladder-70b-v2.md](../experiments/docs/redteam-ladder-70b-v2.md) | 权威压力、姓名/地域代理、多语言属性、高影响住房任务 |
| [experiments/docs/redteam-ladder-70b-v3.md](../experiments/docs/redteam-ladder-70b-v3.md) | 伪 system、few-shot 污染、分隔符、编码属性、角色扮演 |
| [dashboard/README.md](../dashboard/README.md) | 本地只读 UI 的启动、读取范围和安全约束 |

## 如何解释结果

`pass`、`fail`、`error` 和 `inconclusive` 是单次响应的 assessment；它们不是 finding 标签。只有 control 通过、探索阶段出现 probe 违规、confirmation 达到阈值，并且完成独立人工复核，才可以进入 finding 流程。`not_supported` 表示本次固定样本没有支持假设，不表示模型在所有语言、任务、温度或部署环境中没有风险。

## 证据卫生

不要把 `.env`、API key、CSCS 登录信息、SQLite `evidence.sqlite3`、`raw_response_base64`、本地运行目录或 AI 临时文件加入 Git。运行目录应该放在仓库外；报告只引用实验 ID、状态、计数、脱敏 prompt 模式和必要的哈希。
