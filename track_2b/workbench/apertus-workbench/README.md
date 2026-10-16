# Apertus Workbench 基础框架

独立于完整上游工作台，复用固定版本的 Memory/Idea 存储、Observer 类型和状态表格。资产清单见根目录 management/REUSE_ASSETS.md。

```powershell
# 在项目根执行
python scripts/extract_breachweave.py --check
./.tools/node_modules/.bin/bun.cmd test ./workbench/apertus-workbench/tests
./.tools/node_modules/.bin/bun.cmd run ./workbench/apertus-workbench/src/demo.ts ./experiments/runtime-state/demo
```

最后命令输出 schema_version=1.0 的快照，可由 Python runtime_adapter.normalize_snapshot 读取。适配器保留上游状态但只产生 candidate，不将 Idea verified 当作 finding。

Planner 模型和调度 API/MCP 尚未配置，ports 中保留明确接口并抛出未配置错误。完整上游应用仍单独保留。

新增 `local_lab.py` 和 `web/` 提供本地只读工作台。在仓库根运行 `python scripts/lab.py serve`，浏览器访问 `http://127.0.0.1:8765`；`python scripts/lab.py sync` 将已完成记录幂等同步到 Wiki 和 Memory。配置见 `management/lab-workspace.json`。工作台不发送模型请求，不修改证据账本；真实调用保留在独立实验核心。完整 Wiki 启动转发为 `python scripts/lab.py wiki`，尚待 API/Web 验收。
