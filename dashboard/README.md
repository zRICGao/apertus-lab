# Apertus evidence dashboard

这是一个只读的本地实验监控界面。它扫描 `--log-root` 下的 `evidence.sqlite3`，展示运行状态、批次进度、输入 prompt、模型输出、解析 JSON、judge、transport 和 usage。它不会发送模型请求、修改 SQLite 或复制运行产物到仓库。

## 启动

在 `Prototype` 目录运行：

```powershell
python dashboard/server.py --log-root D:\Github-Helium-Peng --port 8790
```

打开 <http://127.0.0.1:8790>。`--log-root` 可以指向包含多个实验目录的父目录，也可以直接指向一个 `evidence.sqlite3` 文件。

## 读取范围与安全

- SQLite 使用 `mode=ro` 和 `PRAGMA query_only=ON`。
- 浏览器只收到相对数据库路径，不收到环境变量或 API key。
- 原始响应的 base64 与哈希不会直接展示；服务端只解码原始 JSON 供人工核对。
- 数据库损坏、锁定、缺表和空目录会显示为可见错误，不会被当作测试失败。
- 运行输出、缓存和 `.env` 不应复制到 `dashboard/` 或 Git。

## 适合读者的证据顺序

先看 phase/status 和 batch，再看时间线；打开具体 attempt 后，按 Input prompt → Model output → Parsed response → Judge → Transport → Raw response 的顺序核对。`not_supported` 仍需要结合实验规格和人工复核阅读。
