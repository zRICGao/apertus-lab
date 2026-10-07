# 成对并行开发版验证

日期：2026-10-07。仅离线 fixture；没有访问 CSCS 或研究模型。

- 新规格可显式写 `dispatch: {"mode":"paired_parallel","max_in_flight":2}`，旧规格保持串行；奇数/未知模式在执行前拒绝。
- 同一 pair 的 control/probe 通过线程 Barrier 验证同时进入发送阶段。探索6条、独立确认12条全部落盘，`confirmation_summary` 为 `not_supported`。
- 一个在途 probe 返回模拟429：本批两条请求及结果均记录，后续4条未发送，run为 `rate_limited`，无未知 attempt。
- 在途取消：本批两条完成记录，后续不派发，run为 `cancelled`。
- `python -m unittest discover -s experiments/tests -v`：32/32通过（含4个并行专项测试）。
- 冻结的 `submission/release/track_1a` 未修改，现有真实 demo 的账本/结论不用于本次测试。

真实并行效率、服务端限流和请求完成时间受 CSCS 当前配额/负载影响，尚未验收。研究 Agent 生成多 prompt 与自动候选筛选仍未实现。
