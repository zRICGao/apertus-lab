# 基础框架验收 — 2026-10-06

目标：提取 BreachWeave 可复用资产，在项目中搭建可执行基础框架；API/MCP等外部接口允许留空。

执行命令：项目根 `./scripts/test-foundation.ps1`，退出码0。

| 要求 | 证据 | 结果 |
|---|---|---|
| 真正提取可复用代码 | scripts/extract_breachweave.py --check 比对固定Git对象、4文件及manifest | 通过 |
| 上游许可与来源 | vendor/breachweave/LICENSE、manifest.json、NOTICE.md | 原件保留 |
| 运行态框架 | Bun测试：持久化、Idea去重、scope隔离、状态板 | 2 tests通过，7 assertions |
| 实验核心 | Python tests/test_foundation.py | 10 tests通过 |
| 调用次数控制 | 20并发预留只有2个成功；重开账本仍耗尽 | 通过 |
| 证据与错误语义 | 重复写/删除拒绝；服务错误不算模型fail；取消阻止新预留 | 通过 |
| 候选知识 | 幂等、保留人工修改、空证据拒绝、mock禁止导出 | 通过 |
| 跨组件实际连接 | scripts/smoke_foundation.py 调用Bun生成快照，再运行Python CLI | 通过 |
| 新重跑 | 修改mock响应后重跑结果变化，id不同，冻结spec哈希相同 | 通过 |
| API/MCP可空 | 显式未配置异常；live硬禁用 | 通过 |

基础框架交付范围完成。以上不证明G2/G4/G5/G6整体通过：仅次数预算，没有完整token/时长/费用与确认预算；暂无真实模型、自动研究Agent、完整知识审核检索、官方导出、Web工作台或Docker交付。暂不要求这些后续能力才能使用离线基础框架。

测试全部使用临时目录；未更改已有Wiki页面、研究记录或用户Git暂存状态。根.gitignore新增缓存/生成物规则不影响已经暂存的文件，后续版本整理需单独审查。
