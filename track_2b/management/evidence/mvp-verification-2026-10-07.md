# MVP 实施验收 — 2026-10-07

## 授权与范围
用户要求删除金额预算/精确定价控制并构建 MVP；随后确认使用英/德/法无关背景干扰的匹配对照示例。代码不包含金额或价格门槛。实际模型调用未执行。

## 已实现与验证

| 验证 | 结果 |
|---|---|
| python -m unittest discover -s experiments/tests -v | 28/28 通过，最终一轮 12.951 秒，退出 0 |
| 项目内 Bun test workbench/apertus-workbench/tests | 2/2 通过，7 assertions |
| python scripts/extract_breachweave.py --check | 4 个固定上游资产逐字一致 |
| python scripts/smoke_foundation.py | 原有运行态→证据→candidate→新mock重跑通过 |
| python scripts/smoke_mvp.py | 隔离发布源码→6探索+12确认fixture→not_supported→重复执行拒绝→BreachWeave摘要→candidate Wiki，通过 |
| python -m apertus_lab.cli validate-live --spec experiments/examples/live-spec.json | 通过，无网络请求 |
| python scripts/build-mvp-release.py --output submission/release | 成功，原始模板保留；独立源码和 Docker/make 入口生成 |
| 发布manifest复核 | 32 个文件逐一 SHA-256 一致 |
| 发布data大小 | 2327 字节，低于 100,000,000 |
| git diff --check | 通过，只有既有 CRLF 提示 |

测试覆盖：缺失/额外配置（金额字段拒绝）、不够覆盖完整实验的额度、并发重复预留、重开账本额度不归零、重复阶段拒绝、崩溃未知请求不补发、取消前/在途、存储失败停止、总时限、429无重试、模型不符、截断、缺失usage、原始响应保存、密钥回显丢弃、冻结规则/代码、对照和确认、人工审核与导出、候选幂等及引用stale。所有模拟数据都在临时目录，未作为真实finding保留。

## 产物

- experiments/src/apertus_lab/live_contracts.py、live_store.py、live_transport.py、live.py：严格v2契约、持久化阶段额度、HTTP/原始证据、执行与确认统计。
- mvp_cli.py、review.py、reproduce.py：live操作、人工确认、官方字段导出、独立复现入口。
- knowledge.py：真实candidate及引用检查；workbench/apertus-workbench/src/import-run.ts：任务状态摘要。
- experiments/examples/live-spec.json：6探索+12确认，每次最多32输出tokens；请求30秒，每轮600秒。
- submission/release：MVP代码、固定spec、官方README、报告草稿、两级Makefile、Dockerfile及manifest。没有真实finding或最终PDF。
- .gitmodules：补全既有两个gitlink的来源；未改子仓库或暂存区。

## 限制与未验收

1. 执行环境 LLM_API_KEY 不存在（只检查是否存在，未读取输出秘密）；本轮无真实模型调用。G3/G5仍待实际运行及人工审查。
2. docker/make 未在PATH，常见Docker路径不存在；未运行容器。隔离源码smoke不等于Docker或完整干净Git检出验收。G6未通过。
3. git submodule status 因本机Git shell helper缺失 basename/sed/git-sh-setup失败；补环境PATH后仍失败。配置已补，联网递归检出未验证。现有BreachWeave删除状态保留。
4. 金额/精确定价控制已删除；输入按字符界限而非精确token。系统DNS解析仍受OS行为影响；取消不撤销服务端已受理工作。
5. 完整Wiki API/Web与高级审核/冲突检索未验收。MVP只验证候选文件和引用；独立runner无此依赖。
6. 官方schema仅做语法修复（diff/hash可追溯）；主办方认可与T&C未闭合。修复版校验器只实现固定schema实际使用的约束子集。
7. 托管模型revision/service_version未知；确认只允许有依据的hosted_service范围。示例翻译未独立审核，两次确认不构成统计证明。
8. 实施中一次本地文档编辑因Windows默认GBK读取UTF-8失败，随后显式UTF-8完成并复验；没有模型请求或证据损失。

下一步：在用户持有key的环境执行示例；真实输出完整记录，若没有支持假设的结果则保留not_supported。取得Docker后验证make run并记录镜像digest。实际finding还需影响、新颖性及人工审查，不自动晋升或发布。
