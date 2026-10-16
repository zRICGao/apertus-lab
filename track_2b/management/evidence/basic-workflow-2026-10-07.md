# BASIC 自动探索验收记录

日期：2026-10-07，Europe/Zurich。范围：用户验收的 BASIC 管理流程；真实模型生成尚未验收。

## 结果

- 全套 Python 单元/集成测试：56 项通过，日志 basic-tests-2026-10-07.txt。
- 最终导出快照一致性、报告哈希和冻结复测规则补记后：24 项 BASIC 专项测试通过，日志 basic-focused-tests-2026-10-07.txt。
- 新增测试覆盖：正常无候选退出、可疑输出扩展、主题覆盖和父子关系、模板非法次数上限、超时不晋升、重复去重、断点继续不重发、暂停时保存响应、未知结果、进程中断恢复、复测额度保护、绝对截止时间、取消终态、mock/live隔离、重复初始化拒绝、字段变更约束、人工引用和占位门控、追加复测保留旧轮次、追加账本、编辑模板新版本、模型辅助观察、人工判定路径、待执行复测防重复和跨候选引用拒绝。
- 首批测试发现并修复未关闭SQLite连接。自查进一步修复人工处理被后续复测覆盖、恢复缺口误报完整完成及导出一致性等问题。
- `git diff --check` 无差异空白错误；存在用户原有 .gitignore CRLF 提示，未作无关格式修改。

## 命令行完整示例

使用 experiments/examples/basic-config.json，调用 scripts/explore.py 的 init、run、export。

| 项目 | 实际结果 |
|---|---|
| Campaign | basic-offline-demo-v1 |
| Mode | mock，固定模拟器，无网络 |
| 结束状态 | completed / queue_exhausted |
| 覆盖 | 5 个临时主题槽位；未评估主题0 |
| 用例 | 5个种子 + 5个措辞变体，每个含control/probe |
| 模拟调用 | 66：模板1、目标20、变体生成5、独立复测40 |
| 候选 | 10条，全部awaiting_review；不是模型漏洞 |
| 未知调用 | 0 |
| 正式findings | 0 |

持久目录：experiments/runs/basic-acceptance-2026-10-07。

导出目录：experiments/runs/basic-acceptance-2026-10-07-package。report.md 可查看关系及审核队列；template.json 可用于人工修改后的新任务；campaign.json/evidence.json 保存完整状态历史、调用和证据。

四个导出文件均重新计算SHA-256并与manifest一致。包合计14,242,194字节。manifest.json SHA-256：

`b41d8f534a5f99f47b62fd768ac3cac41538ed4bb1ef4aef4fc53179e2b4dd15`

## 实现边界与下一步

- 当前进程的 LLM_API_KEY、LLM_NAME、LLM_BASE_URL 均未设置；没有发出真实请求，也没有将模拟模板宣称为Apertus生成。
- 同模型生成/观察/受测已按用户授权实现独立会话和用途记账，真实调用入口必须显式 `--live`。
- 自动变体当前只允许probe措辞变化；语义等价性未认证。模型自评和生成期望值不是可靠问题依据。
- 人工supported仍是human_supported_placeholder，不能官方导出。正式指标、benchmark、发现评审尚需人工完善。
- BASIC账本独立，旧MVP账本、用户已有上游差异和冻结发布包未修改。完整工作台/Wiki UI尚未接入BASIC。
- 存储采用追加快照，适合当前小规模有界探索；不宣称支持100个Solver或大规模并发。不同目录无共享账户级额度。
- 下一步在可用CSCS会话中限一次生成请求验证模板质量，再按冻结额度推进live；UI/Wiki集成为独立后续项。
