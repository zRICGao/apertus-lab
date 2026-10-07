# Apertus Lab

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

本项目尚无已验证的真实模型 finding。当前机器已完成 Docker/CSCS 的 18 次示例调用，假设未获支持；完整 Wiki UI、干净环境复现和最终报告 PDF 尚未完成。不会自动公开或提交。
