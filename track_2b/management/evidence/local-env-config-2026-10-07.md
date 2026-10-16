# 本地 `.env` 持久配置验证（2026-10-07）

- 根 `.gitignore` 包含 `.env`，`git check-ignore .env` 返回 `.env`，确认真实凭据文件不会作为未跟踪文件提交。
- 根 `.env` 含现有默认模型 `swiss-ai/Apertus-v1.5-70B` 与 endpoint `https://api.inference.cscs.ch/v1`；`LLM_API_KEY` 保持空白，未写入真实凭据。
- 执行 `make -n run LLM_API_KEY=LOCAL_DRY_RUN_ONLY`，Make 成功通过根入口并展开到发布包的 Docker build/run 命令；该命令仅 dry-run，没有构建镜像或调用 API。
- 未验证实际 key、Docker 执行或模型请求。用户需在本机 `.env` 中自行填入 key；此后根目录 `make run` 自动读取。
