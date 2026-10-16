# Probe v1 工作流

Probe 是本地研究台中的一次性、多语言模型测试流程。它与 campaign 共用 SQLite 账本和最多 10 个在途请求，但不会改变 campaign 的固定 CSCS 目标约束。

## 启动

```powershell
make workbench
```

或者使用 Docker：

```powershell
docker compose -f compose.workbench.yml up --build
```

API 默认只监听 `127.0.0.1:8770`。首次启动会从根目录 `.env` 初始化默认 Apertus 70B profile。`.env`、`WORKBENCH_DATA`、SQLite、日志和原始响应均属于本地运行数据，不应提交到 Git。

## 一次 Probe

1. 在 Settings 中添加或编辑 OpenAI-compatible profile。名称、模型名、HTTPS base URL 和 key 必须有效；浏览器只能看到 `credentials_present`，key 永远不返回。
2. 在 Probe 首页选择风险领域，编写 prompt 或确认一次辅助模型的建议调用。建议结果只是草稿。
3. 选择一个目标模型和至少一种语言。默认是 `zh/en/de`，一次最多 12 种。
4. 点击开始翻译。翻译调用由 worker 执行，不需要额外确认；每种语言是独立任务。
5. 翻译完成后，批量确认测试调用。只对成功翻译的语言发出目标模型请求。失败、timeout、503、429、格式错误和未知状态保留在调用账本中，不自动重试。
6. 查看每种语言的原始 prompt、翻译、实际发送文本、回答、transport 状态和 request ID。保存结果后才可以调用分析模型；分析也需要再次确认。
7. 保存结果进入 Records；忽视结果会把 job 标记为 `discarded`，但不可变调用元数据仍可审计。已保存记录不能再被忽视。

## 状态和恢复

Job 状态包括 `queued`、`running`、`waiting_confirmation`、`completed`、`partial`、`failed`、`unknown` 和 `discarded`。worker 崩溃时已发送但未结束的调用变为 `unknown`，恢复过程不会重发。全量调用写入 `probe_calls`，结果和分析分别写入 `probe_records` 与 `probe_analyses`；事件通过现有 SSE `/api/v1/events` 提供。

## 分析边界

分析协议要求返回 `status`、`observed_behavior`、`evidence`、`alternative_explanations`、`severity_screen`、`limitations` 和 `needs_human_review`。它只能整理当前 prompt、语言和回答，不能推断总体发生率、训练数据原因、法律结论或正式 finding。

## API 入口

模型：`GET/POST/PATCH /api/v1/models`、`DELETE /api/v1/models/{id}`、`POST /api/v1/models/{id}/select-target`、`POST /api/v1/models/{id}/select-assistant`。

Probe：`GET /api/v1/probe/domains`、`POST /api/v1/probe/suggestions`、`POST /api/v1/probe/jobs`、`GET /api/v1/probe/jobs/{id}`、`POST /api/v1/probe/jobs/{id}/start-test`、`POST /api/v1/probe/jobs/{id}/save`、`POST /api/v1/probe/jobs/{id}/discard`、`POST /api/v1/probe/jobs/{id}/analysis`、`GET /api/v1/probe/records`、`GET /api/v1/probe/records/{id}` 和 `GET /api/v1/probe/records/{id}/export?format=json|markdown`。
