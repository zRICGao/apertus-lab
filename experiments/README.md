# Apertus Lab MVP

开发版新增 **BASIC 自动探索**：`python scripts/explore.py` 支持模板生成、自动选题、有限措辞扩展、持久复测和人工审核。用法见 `management/BASIC_EXPLORATION.md`；默认 mock，真实调用需 live 配置和 `--live`。下文描述原 MVP；其历史范围不限制新 BASIC 独立流程。

Python 3.11+；运行时仅使用标准库。目标固定 CSCS Apertus v1.5 70B，文本输入、人工用例、默认串行、无自动重试、无自主 Planner。开发版可在新规格中显式启用成对并行派发。金额预算及精确定价控制已删除。

## 资源和证据规则

- spec 必须明确探索/确认调用额度、输入字符上限、单次输出 token、每次请求超时和每轮总时限。
- 每次请求前在 SQLite 事务中预留调用。最大输出预留 = 已预留调用数 × 每次 max_output_tokens。失败、超时、崩溃不退回额度。
- 同一账本、同一 experiment id 的每个阶段只可启动一次。重复命令不重复派发；变更 spec 须新 id，属于明确的新实验。不同账本不共享额度，不能用更换目录绕过已有实验预算。
- 不宣称精确的总输入 token 硬上限。输入按字符限制，usage 由服务报告，缺失标记 missing_or_invalid。
- 取消线性化于预留：已预留请求视为在途，可继续结束；不能撤回服务端工作。请求及总时限控制后续派发与网络读取，系统 DNS 解析仍受操作系统行为影响。
- 选用 `paired_parallel` 时，control/probe 同批进入发送阶段，最多 2–8 条在途（偶数）；当前批所有响应写入证据后，才决定是否派发下一批。限流、超时等会阻止后续批次，已在途请求仍可能完成并占用额度。
- HTTP/限流/超时/模型不符为 error；截断/结构化拒绝/未知结束原因为 inconclusive；这些情况立即停止，无重试。缺少 usage 本身不证明模型错误。
- pass 表示满足明确预期输出，fail 表示文本不匹配；两者都不自动成为 finding。自然语言拒绝若未被服务标记，可能表现为 mismatch，需人工审查。
- 保存请求 JSON、原始响应 base64/字节哈希、解析结果、usage、响应 id/model/结束原因、时间及源代码 manifest。服务回显 key 的响应整体丢弃并标记，不能声称保留了原件。

## 离线验证

在项目根 PowerShell：

```powershell
$env:PYTHONPATH = "$PWD/experiments/src"
$env:PYTHONIOENCODING = 'utf-8'
python -m unittest discover -s experiments/tests -v
python -m apertus_lab.cli validate-live --spec experiments/examples/live-spec.json
```

首次示例为英语、德语、法语各一组 control/probe。每组明确要求仅输出 BLUE，probe 增加无关背景；探索 6 次、确认 12 次，每次最多 32 输出 tokens，分别最多 600 秒。翻译为草拟材料，未做独立语言学验收。这是闭环示例，不预设存在问题。

## 开发版成对并行（显式选择）

对**新 experiment id 的新规格**增加顶层字段：

```json
"dispatch": {"mode": "paired_parallel", "max_in_flight": 2}
```

`2` 表示一组 control/probe 同时发送；`4` 表示最多两组同时发送。只接受 2、4、6、8；默认未指定时仍串行。control/probe 在同一批内，批间等待所有响应落盘，记录每条请求的批次和最大并行数。既有 `run-live` 和 `replay-live` 命令使用冻结规格自动选择模式；探索与重跑的并行参数必须相同，现有账本校验会检查同一规格和 runner 源码哈希。

并行只提高独立请求的吞吐，不能让同一条请求更快，也不保证托管服务允许该并发。开始 live 前需确认服务配额和可接受的并发数。当前已完成的 demo 不能加入 `dispatch` 后原地重跑；已发布的 Docker 包保持原串行实现。研究 Agent 尚未实现，所以多条 prompt 目前须由人或外部工具准备成同一份规格；本功能负责并行下发与对照证据。

## 真实运行

先按 management/CSCS_API_SETUP.md 在本机设置 LLM_NAME、LLM_BASE_URL、LLM_API_KEY；密钥只放进程环境，不贴入命令参数或实验文件。

```powershell
python -m apertus_lab.cli run-live --spec experiments/examples/live-spec.json --store experiments/runs/mvp
python -m apertus_lab.cli list-live --store experiments/runs/mvp
python -m apertus_lab.cli inspect-live --store experiments/runs/mvp --run-id <探索run_id>
python -m apertus_lab.cli replay-live --store experiments/runs/mvp --run-id <探索run_id>
python -m apertus_lab.cli summary-live --store experiments/runs/mvp --run-id <探索run_id> --confirmation-id <确认run_id>
```

启动时 stderr 立即输出 run id。只有 completed 返回退出码 0；停止返回 2，校验失败返回 1。修改代码、规则或 spec 后禁止对旧探索进行“同版本确认”。重新运行应声明新实验 id，历史证据保留。

```powershell
python -m apertus_lab.cli cancel-live --store experiments/runs/mvp --run-id <run_id>
python -m apertus_lab.cli recover-live --store experiments/runs/mvp --run-id <run_id>
```

recover 只在执行进程已退出时封存为 interrupted，不重新发送任何请求；unknown_attempts 保留。若存储失败，停止且检查账本，不尝试自动恢复调用。

## Wiki 与任务状态

```powershell
python -m apertus_lab.cli compile-live --store experiments/runs/mvp --run-id <run_id> --workspace experiments/wiki-workspace
python -m apertus_lab.cli check-wiki --workspace experiments/wiki-workspace
```

编译生成 candidate Markdown、模型/语言范围、每个 attempt 的判定与来源哈希，已有人工修改不会被覆盖。check-wiki 输出引用是否 stale，不自动晋升或重写审核标签。完整 Wiki 应用按 knowledge/llmwiki/README.md 打开现有 workspace；完整 UI 不参与 runner 判定。

将 inspect-live 的 JSON 输出保存为 UTF-8 文件，可导入已有 BreachWeave 提取状态模块：

```powershell
./.tools/node_modules/.bin/bun.cmd run workbench/apertus-workbench/src/import-run.ts experiments/runtime-state run.json
```

任务状态是派生摘要，证据账本仍是权威来源；无需配置研究模型。

## 人工确认与导出

summary 为每个用例列出全部分母与 pass/fail/inconclusive/error 数量。探索至少一次 probe fail、确认达到预声明阈值、对应 control 全通过，才成为可审查 candidate。示例的两次确认不是统计证明。

复制 examples/review-template.json，人工填写 reviewer、影响、范围、新颖性来源、限制和 selected probe_ids；确实完成审查后才设置 human_reviewed=true。未知 revision 只允许 hosted_service 范围，并要求 scope_basis。不要把自动判定当成独立人工审查。

```powershell
python -m apertus_lab.cli review-live --store experiments/runs/mvp --run-id <探索run_id> --confirmation-id <确认run_id> --review <人工review.json>
python -m apertus_lab.cli export-live --store experiments/runs/mvp --finding-id <finding_id> --output <新的导出目录>
```

导出包含一个官方字段 finding、冻结 spec、全部探索/确认/审查证据、哈希清单与 findings 许可声明。一个确认 run 只可生成一个 finding，避免重复拆分。导出目录必须新建；不会自动覆盖发布包。评审人必须判断是否为独立问题，最终最多五项。

官方 schema 仅修复 description 的未转义换行，原件保留；diff/hash 见 management/evidence/schema-repair.*。使用针对该固定 schema 实际关键字的校验器及内部强约束，不声称通用 JSON Schema 支持或已获主办方认可。

## 独立复现包

```powershell
python scripts/build-mvp-release.py --output submission/release
```

构建器拒绝覆盖已有目录；后续构建用新的输出目录。生成的 track_1a 包包含独立源码、固定 spec、Dockerfile、两级 Makefile、原始官方说明与报告草稿，不依赖 Wiki/BreachWeave 或本地虚拟环境。

Linux + Docker + GNU Make：设置三个 LLM_* 环境变量，在 release 或 track_1a 目录执行 make run。它执行探索与独立确认并保存新的真实记录。无需本地 GPU；需要网络、CSCS 凭据/资源及 Docker 基础镜像。OUTPUT 默认 track_1a/output；显式新复现可指定一个已经创建的空目录。每次最多 18 次请求（当前示例），不会自动确认 finding。

最终提交前须用真实 findings/spec/报告替换示例，验证数据 ≤100 MB、报告 ≤6 页、最多五个独立 finding、许可和评审访问。当前构建包没有真实 finding 或最终 PDF，Docker 镜像只固定版本标签，实际拉取 digest 应在容器验收时另行记录。

## 旧离线路径

run-mock、replay-mock、inspect、compile 保留；只接受 v1 mock 契约，继续禁止 live。示例和命令见 examples/mock-spec.json 与 CLI help。
