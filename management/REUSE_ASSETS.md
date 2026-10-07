# BreachWeave 资产提取清单

固定版本：4ac5fc4c720ac74cf90968251cfae7cd28d3d62f。提取到独立 workbench/apertus-workbench，不改上游工作区。

| 资产 | 处理 | 理由 |
|---|---|---|
| challenge/memory.ts | 原样提取、RuntimeState 封装 | 复用任务内 Memory/Idea、去重、持久化；不是证据数据库 |
| challenge-observer/types.ts | 原样提取、导出接口 | 复用事件审阅结构；Observer 模型连接留空 |
| challenge-observer/board-format.ts | 原样提取、用于 board | 复用状态展示与字符转义 |
| LICENSE | 原样提取 | 保留上游 Apache-2.0 条款，manifest 记录哈希 |
| ConfigManager / Runtime / RPC | 暂不复制，定义本项目 ports | 绑定 SDK、全局配置、Docker 和通用执行能力；不是最小框架必要依赖 |
| UI/Provider/MCP adapter | 保留上游供后续选取 | 用户允许 API/MCP 留空；接入前独立验证依赖及权限 |
| CTF prompts/flag/tools/payloads | 不提取 | 与模型实验职责不一致 |

提取脚本只从固定 Git 对象读取，不依赖上游工作区缺失文件。再次提取遇到修改文件即报错；--check 逐字核对资产与manifest。

上游存储有可变记录、5秒目录锁超时和60秒过期锁回收。首版仅用于单宿主短事务运行态，不能为跨主机并发或不可变证据提供保证。新实验核心独立实现证据与预算，不依赖该锁机制。
