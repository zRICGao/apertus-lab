# Apertus Lab

## 并行研究工作台 v3（2026-10-15）

当前开发入口是 [v3 工作台使用与研究标准](management/WORKBENCH_V3.md)。包含双语 React UI、FastAPI、独立持久 worker、跨任务最多 10 个在途请求、27 张三语研究卡、启发式变体、冻结确认、四组防御比较、人工审核和独立 Docker replay 导出。默认模拟；启动服务不调用模型。

### Probe 交互式测试

Probe 是独立于 campaign 的多语言红队工作流。它允许在设置页保存多个 OpenAI-compatible 模型，选择一个目标模型和一个辅助模型，然后从偏见、公平、错误前提、谄媚、伤害性语言、隐私和指令边界等领域设计测试。翻译阶段会为选定语言建立独立任务；测试、建议和分析调用均在 UI 中显示第三方模型、地址、语言和请求数量，并在用户确认后发送。翻译失败只影响对应语言，worker 重启不会重发未知调用。

```powershell
make workbench
# 或
docker compose -f compose.workbench.yml up --build
```

打开 `http://127.0.0.1:8770`，进入 Probe 或 Settings。首次启动会从被忽略的根目录 `.env` 发现默认 Apertus 70B；模型配置和 SQLite 账本保存在 `WORKBENCH_DATA`。密钥只在后端本地使用，不出现在 API 响应、浏览器存储、事件、记录导出或 Git 中。保存结果后可在 Records 中按领域和语言筛选，并导出 JSON 或 Markdown；“忽视”只保留不可变审计元数据，不进入普通记录。

Probe 的接口和状态约定见 [Probe v1 工作流](management/PROBE_V1.md)。自动分析是证据整理，不会自动创建 finding、推断训练原因、总体发生率或法律结论；开放式结果仍需人工复核。

```powershell
docker compose -f compose.workbench.yml up --build -d
# 本机已安装依赖时：python scripts/workbench.py serve
```

打开 http://127.0.0.1:8770，按“新建研究 → 预检 → 创建 → 启动”操作。完整指定 LLM Wiki 用 `python scripts/wiki-local.py` 启动，地址 http://localhost:3000，与研究台共享知识工作区。部署、角色配置、预算、检测与人工审核见上述手册；验收结果见 [架构验收记录](management/evidence/workbench-v3-acceptance-2026-10-15.md)。

本次完成平台离线与 Docker 流程；真实 10 并行、研究模型质量和领域校准仍需独立验证。下文保留原只读 dashboard、BASIC CLI 与旧冻结发布包的历史用法，它们不是 v3 的能力边界。根 `make run` 仍指向旧冻结比赛包；新任务应从 v3 导出的包根执行 `make run`。

## 面向后续开发者与 AI 的入口

先读 [项目产品记录](PRODUCT.md) 了解 dashboard 的边界，再读 [70B 攻防经验](docs/red-team-experience-70b.md) 了解已经尝试过的 prompt、失败原因、实际结果和 judge 局限。需要查看真实运行过程时，启动 [只读证据 dashboard](dashboard/README.md)；它读取仓库外的 SQLite 运行目录，不发送模型请求，也不修改账本。

推荐阅读顺序：

1. [项目状态与约束](management/STATUS.md)
2. [实验操作手册](experiments/README.md)
3. [Fairness judge 说明](experiments/docs/fairness-pair-v1.md)
4. [70B red-team ladder v1](experiments/docs/redteam-ladder-70b-v1.md)、[v2](experiments/docs/redteam-ladder-70b-v2.md)、[v3](experiments/docs/redteam-ladder-70b-v3.md)
5. [攻防经验与后续建议](docs/red-team-experience-70b.md)

真实 API 运行输出和本地凭据不属于 Git 内容。后续 AI 应把 `experiments/examples/` 中的规格、`experiments/src/apertus_lab/` 中的 runner/judge、外部 SQLite 证据和人工报告分开阅读；`not_supported` 是当前样本未支持假设，不是普遍安全证明。

## BASIC 自动探索（开发版）

已接通占位模板生成、自动选题、有限措辞变体、持久复测、停止策略及人工审核。默认离线模拟，完整操作见 [BASIC 使用说明](management/BASIC_EXPLORATION.md)；[本次验收记录](management/evidence/basic-workflow-2026-10-07.md)包含测试结果与实际边界。

```powershell
python scripts/explore.py init --config experiments/examples/basic-config.json --store experiments/runs/basic-demo
python scripts/explore.py run --store experiments/runs/basic-demo
```

真实调用须另建 live 配置并显式传入 `--live`。BASIC 候选均带占位标记，不直接成为正式 finding。下文的人工用例和无自主Planner限制描述原 MVP，独立Docker发布包仍保持原实现。

## 本地工作台

当前先完善架构，使用已有证据调试。见 [实际架构](management/ARCHITECTURE.md)。在项目根执行：

```powershell
make sync       # 将既有证据同步为 Wiki 草稿和 Memory 摘要，无模型调用
make lab        # 打开 http://127.0.0.1:8765
```

`make lab-status` 检查账本与引用；`make wiki` 调用完整 Wiki 启动器（API/Web 流程待验收）。工作台只读访问原始证据。`make run` 是独立 Docker 实验入口，每次自动生成新实验 ID 并调用目标模型；当前模板每轮最多 6 次探索及 12 次确认。可用 `make run EXPERIMENT_ID=my-experiment-01` 指定 ID，已有阶段仍拒绝重发。启动时显示 ID，实际配置及模板哈希保存在 output 的 `launch-<run_id>.json` 中。中断恢复应检查原 run ID，不能把新 ID 当作恢复。

研究 Agent 的双模型配置、预检入口及未来自动循环见 [研究 Agent 配置](management/RESEARCH_AGENT_SETUP.md)。`make agent-status` 只读检查非秘密模板和环境变量，不启动模型或实验。

围绕 CSCS Apertus v1.5 70B 的文本研究 MVP：人工用例、串行调用、持久化资源限制、原始证据、独立重跑、候选 Wiki、人工确认与 finding 导出。

金额预算和精确定价控制已按用户要求删除。调用次数、输入字符、输出 token、时限和取消仍受控制；不会自动重试或启动自主 Planner。

- [操作手册](experiments/README.md)：验证、live、取消/恢复、Wiki、人工确认和导出。
- [实验示例](experiments/examples/live-spec.json)：英/德/法三组匹配对照，探索 6 次、确认 12 次。
- [CSCS 接入](management/CSCS_API_SETUP.md)：仅配置官方托管 API，无需本地模型服务。
- [项目契约](HARNESS.md)与[当前状态](management/STATUS.md)：区分实现、离线验证、真实模型与最终交付。

Python 运行时只有标准库；BreachWeave 提取资产用于任务摘要，完整 LLM Wiki 用于研究知识，两者不参与独立复现入口。原有 mock 路径继续可用。

在项目根设置 PYTHONPATH=experiments/src 后，可运行 `python -m apertus_lab.cli validate-live --spec experiments/examples/live-spec.json` 做无网络检查；`python -m unittest discover -s experiments/tests -v` 执行离线测试。

本项目当前没有已确认的真实模型 finding。已完成 Docker/CSCS 连接、batch benchmark、初始 fairness screen 以及 70B red-team ladder v1/v2/v3；公开到 Git 的是可复现代码、规格、方法文档和脱敏总结，不包含真实 API 输出账本或凭据。
