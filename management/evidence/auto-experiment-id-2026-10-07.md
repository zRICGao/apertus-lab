# 实验 ID 自动配置（2026-10-07）

模板位置：`submission/release/track_1a/data/spec.json:62`，当前 ID `multilingual-distraction-demo-v1`。

实现：Make 默认导出 `EXPERIMENT_ID=auto`，Docker 只传递变量名；reproduce 解析新实验 ID 后以同一 spec 执行探索与独立确认。模板 ID 保留在启动快照和摘要内，不修改原始 spec 文件。手动 `EXPERIMENT_ID` 非法值被拒绝，同 ID/phase 重复请求保护保留。ID 最长 80 字符。

证据：

- `python -m unittest discover -s experiments/tests -p test_reproduce.py -v`：2 项通过。包括两个新 ID 在同一账本完成，手动 ID 重复启动没有新增模拟请求，模板和非 ID 字段不变，配置/模板哈希及 80 字符边界。
- `python -m unittest discover -s experiments/tests -p test_mvp.py -q`：18 项通过。
- `make -n run LLM_API_KEY=LOCAL_DRY_RUN_ONLY EXPERIMENT_ID=my-experiment-01`：展开 Docker 命令包含 `-e EXPERIMENT_ID`；没有执行 Docker/API。
- 当前 Python 无 pytest，使用 unittest 标准库运行。新增检查首次 hash 比较因默认文件解码失败；所有 JSON 读取指定 UTF-8 后通过。

运行行为：每次 `make run` 开始一轮新的有界真实实验，最多 6 探索 + 12 确认。`make run EXPERIMENT_ID=my-experiment-01` 固定 ID；已执行阶段不会重发。中断必须检查原 run ID，不把新实验当恢复。已有输出未改。

未进行真实 Docker/CSCS 验收；本地 release 修改的来源及文件哈希记录在 `submission/release/local-update-manifest.json`，初始构建清单保留。
