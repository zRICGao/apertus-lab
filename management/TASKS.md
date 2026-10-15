# 任务台账

| ID | 阶段 | 任务 | 依赖 | 状态 | 验收 / 证据 |
|---|---|---|---|---|---|
| SYNC20261015 | 仓库同步 | 提交当前项目并推送 Prototype/main | 用户授权 | doing（用户已明确授权Prototype） | evidence/project-push-2026-10-15.md；14项回归通过 |
| V3007 | 方法说明 | 核对实际流程、数据链、违规/采样/验证/外推并可视化 | 用户要求解释当前行为 | done（源码核对） | WORKFLOW_AND_EVIDENCE.md；11种交互情形展示通过，无模型调用 |
| V3008 | P4–P6 | 开放题标注后补跑防御、候选机制分组及统计图表报告 | V3001、方法复核 | todo | 当前每方向一候选、防御只首个候选；结束后标注不自动重开防御；HTML报告仍文字/JSON |
| V3001 | P2–P6 | 按计划实现 v3 并行启发式研究架构及双语 UI | 用户批准架构实施 | done（离线交付） | WORKBENCH_V3.md；98 Python + 4 UI；Docker API/worker、导出包 make run 与断网 replay 通过 |
| V3002 | P2/P3 | 全角色共享 10 并行、预算、停止与崩溃恢复 | V3001 | done（fixture） | 原子预留与实际 worker 峰值10测试；真实 CSCS 10 并行待 V3005 |
| V3003 | P4 | 完整原版 Wiki 共享工作区、来源与候选同步 | V3001、A002 | done（本机读写/同步） | 3000/8000；历史/候选/来源可读，笔记编辑重开和409通过；3项SQLite回归、哈希/幂等通过 |
| V3004 | 审查 | 修复审查 R1–R4，隔离 R5 未核对统计 | V003 | done（修复/标疑） | spec-syntax-repairs；新增成对导出/混合拒答回归；medical v3/direction v2；R5 外部账本复核仍待办 |
| V3005 | P3/P5 | 真实10并行、研究生成质量、语言/领域校准 | V3001、明确目标/额度、凭据 | todo（真实验收） | 不以 mock 替代；不默认调用付费外部 provider |
| V3006 | P6 | 正式 findings、报告 PDF、schema 兼容及评审访问 | V3005、独立审阅及真实复测 | todo（正式提交） | 导出包已对齐 track_1a 布局和限制；尚非比赛提交 |
| SYNC001 | 同步 | 拉取 Prototype/main 最新提交到本地 | 用户要求 pull | done | main 快进 9f0df93→4925c63；HEAD=FETCH_HEAD，本地审查记录及子模块修改保留，无未解决冲突 |
| V003 | 审查 | Prototype 新增提交 9f0df93..4925c63 | 用户请求审查、固定远端提交 | done（审查） | 70 项离线测试通过；5 项缺陷/证据问题待修；evidence/commit-review-2026-10-15.md |
| BASIC001 | P2/P3/P5 | BASIC 自动选题、变体关系、停止、持久复测及人工闭合 | 用户验收操作逻辑 | done（离线） | 56 Python tests；完整CLI示例66次模拟请求；evidence/basic-workflow-2026-10-07.md |
| BASIC002 | P3 | Apertus 真实模板生成及有界自动流程验收 | BASIC001、CSCS会话凭据 | blocked（环境） | 当前进程无 LLM_* 环境变量；已提供显式 live 入口和冻结额度 |
| BASIC003 | P4 | BASIC 候选接入工作台/Wiki UI | BASIC001、ARCH002 | todo | 当前通过CLI及导出包操作，未宣称完整UI集成 |
| ARCH001 | P2/P4 | 本地只读工作台与幂等证据同步 | MVP002、B001 | done | evidence/architecture-integration-2026-10-07.md；4 Python + 3 Bun，真实账本未改 |
| ARCH002 | P2/P4 | 完整 Wiki API/Web 与已有知识页贯通 | ARCH001、A002 | done（本机，v3） | 原版 API/Web、历史/候选页与来源；笔记编辑持久化，SQLite 最小兼容补丁；v3 验收记录 |
| AGENT001 | P2 | 研究 Agent 与目标模型分离配置及只读预检 | ARCH001 | done（设计/预检） | RESEARCH_AGENT_SETUP.md、research-agent.example.json、`make agent-status`；无 Agent 调用 |
| AGENT002 | P4/P5 | 受限 Planner、工具适配、持久轮次与候选报告 | ARCH002、AGENT001 | doing | BASIC001已完成受限CLI流程；完整Wiki检索/外部研究模型与UI仍待接通 |
| PAR001 | P2/P3 | 开发版成对并行调度与证据门控 | X003 | done（离线） | evidence/paired-parallel-2026-10-07.md；32 Python tests，真实并行调用待验收 |
| M001 | P0 | 管理 Harness 与大纲 | 无 | done | 根目录 AGENTS/HARNESS/PROJECT_OUTLINE 及 management 文件 |
| E001 | P1 | 本机环境预检 | M001 | done | `management/evidence/environment.txt` |
| S001 | P1 | 下载并固定 BreachWeave | E001 的 Git 检查 | done | `workbench/BreachWeave` HEAD 为 `4ac5fc4c720ac74cf90968251cfae7cd28d3d62f`; Windows checkout 对部分深层 payload 文件报告缺失 |
| S002 | P1 | 确认并下载完整 Wiki | 仓库地址 | done | `knowledge/llmwiki` HEAD 为 `aac3e6493306b7fff3b09cb181ca93918e93d0e6` |
| E002 | P1 | 解决必需依赖差距 | E001、上游要求 | doing | Wiki Python/Web 依赖已安装；Bun 已取得项目内可执行文件；GNU Make 4.4.1 已安装并验证；Docker Desktop 4.94.0 已以 WSL2 backend 启动、Linux 引擎可用；需新 Windows shell 刷新 PATH，Ubuntu WSL 集成可选；BreachWeave 冻结安装发现锁文件需核对 |
| A001 | P2 | 启动 BreachWeave 基线 | S001、E002 | todo | 健康检查及最小 UI 操作 |
| A002 | P2 | 启动 Wiki 基线 | S002、E002 | done（本机） | 3000/8000 健康；指定原版应用、共享工作区与读写验收；v3 证据 |
| M002 | P0 | HARNESS v1.0 与官方要求映射 | M001、官方模板 | done | HARNESS/OUTLINE/TRACK_1A_REQUIREMENTS；设计完成，非功能验收 |
| B001 | P2 | 提取 BreachWeave 资产并搭建基础框架（API/MCP可留空） | S001、M002 | done | REUSE_ASSETS.md、独立工作台与Python核心；2 Bun+10 Python+跨运行时smoke通过 |
| O001 | P0 | 官方 schema 语法处理与 T&C 核实 | 固定模板 | todo | 本地语法修复副本、diff/hash及解析已完成；主办方兼容依据/T&C未闭合 |
| K001 | P4 | candidate 编译、审核与状态化检索 | X001、A002 | todo | G4；幂等、引用、无证据禁止晋升、stale/conflict |
| X001 | P2 | 实验数据契约与 mock 链路 | S001 | doing | 已有契约/次数预算/证据/取消/mock；已由MVP实现请求/输入输出/时限与确认额度；金额控制按用户指令取消 |
| X002 | P3 | Apertus 小样本 | X001、目标配置、预算 | todo | G3；真实请求、匹配对照与完整记录 |
| RT001 | P3/P5 | 多语言文化事实与金融身份偏见探索 | X001、可用 CSCS 凭据 | done（诊断扩展见 RT003） | 原26次筛查记录于 management/evidence/redteam-exploration-2026-10-15.md |
| RT002 | P3/P5 | 多语言金融身份与伪权威风险先验压力测试 | RT001、冻结配对规格 | replicated candidate（独立领域/中文审阅待办） | finance-proxy-pressure v2：24 探索 + 72 确认；中文女性标签跟随效应 8/8、control 8/8 tie；management/evidence/finance-proxy-pressure-finding-2026-10-15.md |
| RT003 | P3/P5 | 国民院多选格式、错误前提与语言差异诊断 | RT001、冻结事实来源 | replicated wording-sensitive behavior（双语/官方来源审阅待办） | v3 controls 6/12；v5 三语近义表述 18/18 pass；v6 三个报告式英文触发语各3/3输出246、controls通过；management/evidence/cultural-seat-count-diagnosis-2026-10-15.md |
| X003 | P2/P3 | 按 CSCS endpoint 接入托管 Apertus API | X001、用户创建受限 key | done | v2离线故障检查与实际18次调用完成；见MVP002 |
| R001 | P5 | 评估与独立复现 | X001 | todo | 冻结用例可脱离研究 Agent 重跑 |
| P001 | P6 | 官方格式与导出验收 | R001、O001 | todo | G6；Docker真实重跑、1–5 findings、data≤100MB、PDF≤6页 |
| P002 | P6 | 私有提交与评审访问 | P001、用户最终授权 | todo | G7；judgeailights、仓库URL/PDF、指定渠道，私有至2026-12-01 |
| V001 | 审查 | 当前项目与官方 Track 1A 对照、离线复验 | M002、B001 | done | evidence/project-review-2026-10-07.md；2 Bun+10 Python+smoke通过，三个优先缺口待修复 |
| MVP001 | P2–P6 | 无金额控制的受控文本MVP | 用户授权、B001 | done（实现/离线） | evidence/mvp-verification-2026-10-07.md；真实CSCS/Docker另行验收 |
| MVP002 | P3/P5 | 运行用户选定的三语言匹配对照与独立确认 | MVP001、可用凭据 | done（not_supported） | 实际6探索+12确认全部完成；六组均 pass，supported_probe_ids 为空；不是已确认发现，证据见 evidence/mvp-live-run-2026-10-07.md |
| MVP003 | P6 | Docker容器及干净环境真实复现 | MVP001、Docker、凭据 | doing | Windows 根 `make run` 已真实构建并完成18次调用；镜像摘要、run ID与持久化账本已记录。干净检出验收仍待完成 |
| CFG001 | P3/P6 | CSCS key/model 环境与 Docker/Make 传递配置 | MVP001 | done（配置） | CSCS_API_SETUP.md、release Makefile/Dockerfile、build-mvp-release.py；无 key 入库；本机 Docker/真实调用待外部条件 |
| CFG002 | P3/P6 | 本地 `.env` 持久配置与 Make 自动加载 | CFG001 | done（模板/接线） | 根 `.env` 已忽略并留空 key；`.env.example` 有模型/endpoint默认值；根及发布包 Makefile 自动读取；dry-run 展开验证，不含有效 key |
| CFG003 | P3/P6 | Make 自动生成独立实验 ID 与配置快照 | CFG002 | done（实现/离线） | 2 新增 + 18 MVP 检查通过；auto 新 ID、重复 ID 拦截、完整 spec 哈希；evidence/auto-experiment-id-2026-10-07.md |
| V002 | 审查 | 当前实现、缺失结构、落地与赛道偏差报告 | 当前工作区/真实账本 | done | evidence/implementation-audit-2026-10-07.md及snapshot；58+4 Python、3 Bun、资产/隔离包复验通过 |
| PUB001 | 交付 | 上传项目到团队私密仓库 | 用户确认目标与共享范围 | done | Prototype/main 快进至 `50793de`；未纳入 `.env`、缓存和运行锁；evidence/private-repo-upload-2026-10-08.md |
