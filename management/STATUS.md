# 当前状态

## 当前实现审查快照（2026-10-07）

- 本轮直接只读核验：真实MVP账本已有4个run、36次请求，两组探索/确认均completed且全部pass，结论均not_supported；正式review记录0，发布包finding/PDF均0。此前18次描述仅为早期一组的历史记录。
- 重新验证：58项核心Python、4项工作台Python、3项Bun测试、4个资产校验及隔离发布包smoke均通过。BASIC持久示例仍为mock（66模拟调用、10候选），不算真实发现。
- 主要缺口：BASIC候选到正式实验的显式冻结桥接、领域评价/影响/新颖性依据、完整Wiki审核集成、干净检出及全包验收。开发版能力不等于冻结发布包能力。
- 另发现独立Track 2B基线仓库（694f98e），默认仅run-mock，报告仍占位；未据此切换主赛道或公开任何材料。根仓库尚无可验证HEAD提交。
- 完整报告：evidence/implementation-audit-2026-10-07.md；机器快照：evidence/implementation-audit-2026-10-07-snapshot.json。本轮没有真实模型调用或业务代码变更。


## 自动配置实验 ID（2026-10-07，最新）

- `submission/release/track_1a/data/spec.json:62` 的模板 ID 仍为 `multilingual-distraction-demo-v1`。根 `make run` 默认 `EXPERIMENT_ID=auto`，容器启动后以模板 ID、UTC 时间及随机后缀生成新实验 ID。
- 新 ID 只改变 `spec.id`，案例、目标、生成参数和每轮额度不变；探索和确认共用新实验 ID，分别生成 run ID。每次 `make run` 表示新的独立实验，当前模板每轮最多 18 次真实请求；不能把新 ID 用作中断恢复。
- 可用 `make run EXPERIMENT_ID=my-experiment-01` 显式指定；已有同 ID 阶段仍拒绝重发。原账本和旧运行记录保留。
- 开始每个阶段前保存 `launch-<run_id>.json`，包含模板 ID/hash、实际 ID/spec/hash；摘要同时包含实验和模板 ID。发布包生成器同步支持新行为。
- 新增 2 项离线行为检查与 18 项 MVP 检查通过；未发真实请求。当前 release 本地修订哈希见 `submission/release/local-update-manifest.json`，初始 build-manifest 保留。

## 本地 API key 配置（2026-10-07，最新）

- 根目录 `.env` 已创建并被 `.gitignore` 忽略；预填默认 Apertus 模型和 CSCS endpoint，`LLM_API_KEY` 留空，未在本次会话或磁盘中写入真实 key。
- 根 `make run` 与直接调用发布包 Makefile 都会加载根 `.env`；模板见 `.env.example`。用户首次将 key 写入本地 `.env` 后，后续运行无需重新设置 shell 环境变量。
- 本地 dry-run 验证见 `management/evidence/local-env-config-2026-10-07.md`。真实 Docker/API 调用未执行。
- 下一步：用户在 `.env` 的 `LLM_API_KEY=` 后填入 key 并保存，即可从仓库根执行 `make run`。

## BASIC 自动探索闭合（2026-10-07，最新）

- 用户验收操作逻辑后授权实施：允许 Apertus 在独立新会话中生成 BASIC 占位模板、辅助观察和接受测试。该授权更新了此前“人工用例/无自主 Planner”的开发版限制。
- 新增 `scripts/explore.py`：自动主题种子覆盖、规则/模型辅助/人工三种观察路径、有限措辞变体、父子关系与去重、全角色额度和复测预留、持久复测、暂停/取消/恢复、人工追加复测/归并/处理、候选包与报告。
- 人工编辑导出模板后可创建有来源关系的新版本；模板内容不能修改宿主额度或目标配置。所有 BASIC 结果保留 placeholder，不能直接进入正式 Finding Registry。
- 全套 56 项 Python 测试通过（新增 24 项 BASIC）；修正导出快照一致性及报告哈希后再次运行 BASIC 专项测试。证据见 `evidence/basic-workflow-2026-10-07.md`。
- 命令行离线示例完整结束：5 个主题槽位、5 个种子及5个措辞变体、66 次模拟调用（含40次独立复测）、10 条待人工审核候选，正式 finding 为0。产物位于 `experiments/runs/basic-acceptance-2026-10-07-package/`。
- 本次执行环境未发现 LLM_API_KEY/LLM_NAME/LLM_BASE_URL，未发真实请求；Apertus 实际生成的模板尚未验收。BASIC CLI 尚未接入完整工作台/Wiki UI；旧 MVP 账本及冻结发布包未改。
- 下一步：凭据可用时进行有界 live 模板生成验收；完整 Wiki/API/Web 和 BASIC UI 接线继续作为独立后续任务，不以其完成情况冒充本次 CLI 的能力。

## BASIC 之前的优先级与架构（2026-10-07，历史阶段）

- 用户要求先调试与完善架构，暂停新实验设计；下一工作单元是完整 Wiki API/Web 的最小流程集成。
- Windows Make → Linux Docker → CSCS 的真实链路已验证：6 次探索 + 12 次确认全部符合预期，假设未获支持，无 finding。早期缺 Docker/key 的记录已被后续证据取代。
- 新增本地只读工作台：运行列表、逐条输入/实际回答/判定、Wiki 引用状态和范围；地址 `http://127.0.0.1:8765`，入口 `make lab`。
- 新增显式幂等同步 `make sync`：现有两次运行生成 2 条 Memory、2 张运行草稿和 1 张汇总；重复同步数量不变，原账本 SHA256 不变。
- 本轮 4 个 Python 集成测试、3 个 Bun 测试通过；浏览器已显示运行与逐条证据。未新增真实模型请求。详见 `evidence/architecture-integration-2026-10-07.md`。
- 完整 Wiki 仍保留指定应用；新增启动转发入口但 API/Web 尚未验收。完整 BreachWeave UI、研究 Agent、状态化审核检索和干净环境复现仍待完成。
- 研究 Agent 新增双模型非秘密配置模板与只读 `make agent-status` 预检；Planner、自动发现与候选报告仍未实现。配置/未来使用路径见 `RESEARCH_AGENT_SETUP.md`。
- 开发版现支持新规格显式 `paired_parallel`，2–8 条（偶数）在途、按匹配对分批；默认串行。32个Python测试通过，包括真实并发、限流停派、取消及独立重跑的离线测试；真实并行 CSCS 调用未做，冻结发布包未改。详见 `evidence/paired-parallel-2026-10-07.md`。
- Gate 更正：G3 的真实请求/对照/assessment 技术闭环已完成，假设未获支持不等于 G3 失败；G5 仍无 confirmed finding。G1/G4/G6/G7 与 G0 的剩余要求未闭合。
- 实际架构及后续顺序见 `ARCHITECTURE.md`。以下为历史阶段记录，环境/下一步以本节为准。

## 历史阶段记录

更新时间：2026-10-07（Europe/Zurich）。本节取代早期“live 全部禁用/金额控制待完成”的状态；历史证据保留原日期。

- 当前阶段：受控文本 MVP 已实现，默认不调用模型；v2 `run-live` 显式启用，旧 v1 mock runner 继续拒绝 live。没有真实 confirmed finding，不是已完成比赛提交。
- 用户确定：使用赞助资源，删除金额预算和精确定价相关控制；采用英语/德语/法语“无关背景下保持明确输出指令”的匹配对照示例。
- 固定范围：CSCS Apertus v1.5 70B、文本、人工用例、串行、无自动重试、无自主 Planner。示例探索 6 次、确认 12 次；每次最多 32 输出 tokens。
- 已实现：严格 v2 spec、持久化探索/确认额度、进程级串行锁、调用前预留、输入字符/输出 token/时限、取消、崩溃封存与重复启动拒绝。
- 已实现：原始请求及成功/错误响应字节、哈希、解析结果、usage（允许明确缺失）、时间、模型/结束原因和源码 manifest。限流、超时、截断、拒绝、模型不符不算模型 fail。
- 已实现：独立 replay、新 run/attempt、冻结 spec 与代码检查、全部用例分母统计、人工 review registry、官方字段导出、100 MB 导出检查。未知 revision 仅允许明确的 hosted_service 归因。
- 已实现：live candidate Wiki 编译、引用 freshness 检查；BreachWeave 提取状态模块接收运行摘要；独立复现不依赖两应用。
- 已实现：发布包构建器、两级 make run、Dockerfile、独立源码与 spec、报告草稿、来源/许可/构建哈希。包默认只含示例，无真实 finding、无最终 PDF。
- 已验证：28 个 Python 测试、2 个 Bun 测试、4 个提取资产校验、旧跨运行时 smoke、隔离发布包 smoke（18 个离线 HTTP fixture 响应）通过。完整证据见 evidence/mvp-verification-2026-10-07.md。
- 修复：添加与现有 gitlink 对应的 .gitmodules；保留用户暂存项及 BreachWeave 原有删除标记。尚未执行联网的全新递归 Git 检出。
- 官方 schema：本地仅转义 description 中的非法换行；原件不变，diff/hash 已保存。主办方兼容依据与额外 T&C 仍待闭合，G0 未通过。
- 环境限制：本轮执行环境未配置 LLM_API_KEY；Docker 未在 PATH 或常见安装路径找到，因此本轮未发真实模型请求，未启动 Docker。GNU Make 4.4.1 已通过 conda-forge 安装到用户 Miniconda base，并可从 PATH 调用。
- 配置更新（2026-10-07）：CSCS setup 文档现说明受限 key 的会话配置及 Make/Docker 运行；release Makefile 默认模型与 endpoint、校验 key 缺失并透传三个变量；Dockerfile 设置非秘密默认值；构建器同步生成这些配置。没有实际 key 写入文件。当前环境缺少 Docker 和 key，运行验收仍待用户环境完成。
- 环境更新（2026-10-07）：GNU Make 4.4.1 已安装于 `C:\Users\gaoch\miniconda3\Library\bin\make.exe`，该目录已在用户 PATH；`make --version` 验证通过。详情见 `management/evidence/gnu-make-install-2026-10-07.txt`。
- 运行预检（2026-10-07）：用户表示 API key 与 Docker 已配置，但本次执行 shell 的进程/用户/系统环境均未发现 `LLM_API_KEY`，也未找到 Docker 命令或常见安装路径；没有发出模型请求。待在可访问二者的终端会话重试，细节见 `management/evidence/mvp-run-preflight-2026-10-07.md`。
- Make 入口修复（2026-10-07）：用户从仓库根执行 `make run` 时发现缺少根级 Makefile。新增根级转发目标，指向 `submission/release/track_1a` 的实际 Docker runner；通过 dry-run 验证命令展开，未启动容器。记录见 `management/evidence/root-make-entry-2026-10-07.md`。
- 凭据拦截（2026-10-07）：用户再次从根执行 `make run` 后，track_1a Makefile 报告当前 shell 未设置 `LLM_API_KEY`，因此在 Docker build 前停止；尚无真实请求。需在同一 PowerShell 进程设置临时环境变量后重试，证据见 `management/evidence/mvp-key-env-block-2026-10-07.md`。
- Docker 启动拦截（2026-10-07）：随后 Make 已通过 key 检查，但 Windows 原生 Make 无法创建 `docker build` 进程（找不到可执行文件），容器未构建、API 未调用。项目需要在 Docker 可访问的 Linux/WSL shell 中启动；本代理 WSL 探测被系统 E_ACCESSDENIED 拒绝，细节见 `management/evidence/mvp-docker-cli-block-2026-10-07.md`。
- Docker Desktop 更新（2026-10-07）：按用户请求从 Docker 官方下载并以当前用户模式安装 4.94.0，指定 WSL 2 backend 后启动。WSL 2.6.1 可用；Docker CLI 报告 Server 29.8.2、OSType=linux，确认 Linux 引擎运行。安装器更新了用户 PATH，但本次既有进程环境未刷新；Ubuntu WSL 集成尚未启用，因此继续从 Windows 新 PowerShell 启动即可，或在 Docker Desktop 的 Resources > WSL Integration 开启 Ubuntu。未发模型请求。证据见 `management/evidence/docker-desktop-install-2026-10-07.md`。
- 真实示例运行（2026-10-07）：用户从 Windows 仓库根成功执行 `make run`，Docker 镜像构建并完成 6 次探索、12 次确认。18 次均无 error/inconclusive，六组 control/probe 全部精确输出 BLUE；摘要 `not_supported`、supported_probe_ids 为空。该 pipeline demo 没有支持假设，不是 finding。run IDs、image digest 与持久化证据哈希见 `management/evidence/mvp-live-run-2026-10-07.md`；运行记录保存在 release `track_1a/output/`。
- 上游基线：BreachWeave 4ac5fc4c720ac74cf90968251cfae7cd28d3d62f；完整 LLM Wiki aac3e6493306b7fff3b09cb181ca93918e93d0e6；官方模板 7f2382275461baf3fa6c8855d157d86abffe9f0e。
- 完整 Wiki：依赖及 workspace 初始化已存在；本轮验证文件级候选集成，完整 API/Web 操作与高级冲突/审核检索尚未验收。完整 BreachWeave UI 也未验收。
- 当时建议（已被架构优先指令取代）：设计新实验。当前不执行此方向；demo id 已耗尽阶段额度。
- Gate：MVP G2 离线控制验证通过（按 v1.1 资源策略）；当前 demo 的 Docker/live 闭环已通过，但 G3 未发现支持假设的行为、G5 无可确认 finding；G4 文件级子流程通过但完整能力未通过，G6 仅当前机器 Docker 入口通过，干净检出/正式导出与 G7 未通过。
