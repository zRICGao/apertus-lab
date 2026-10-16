# Prototype 私密仓库上传记录（2026-10-08）

- 目标：`https://github.com/zRICGao/Prototype.git`
- 分支：`main`
- 推送方式：快进推送；保留目标原提交 `cff369945edd405589a8c913aec3a060a8249fae`，未强制改写历史。
- 上传提交：`50793de291fd4e03cfae7ee103ce4e928b0d28c2`（`Upload Apertus Lab project`）
- 提交包含 164 个路径变化，含项目源码、管理文档、发布包和已确认可共享的运行证据。
- 排除：根 `.env`、`experiments/wiki-workspace/.llmwiki/index.db` 缓存、发布目录的 `live.lock`。
- `.gitmodules` 补充了 `submission/project-template` 和 `submission/team-track-2b` 的来源地址，支持干净检出。
- `workbench/BreachWeave` 子模块工作区仍有本地未提交删除；上传记录保留其固定 gitlink 基线 `4ac5fc4c720ac74cf90968251cfae7cd28d3d62f`，未将这些删除写入该上游子仓库历史。
- 未运行测试；本次为仓库上传与 Git 状态核验。
