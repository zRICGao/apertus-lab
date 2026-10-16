# BASIC 自动探索与人工审核

2026-10-07。按用户验收的操作逻辑新增开发版流程；冻结比赛发布包继续使用原 MVP。BASIC 是占位研究模板，不能直接导出为正式 finding。

## 已接通的流程

初始化 → Apertus 生成模板 → 校验主题槽位和匹配用例 → 优先运行未覆盖的种子 → 规则/模型辅助观察/人工待复核 → 冻结候选并排入复测 → 小步生成相邻变体 → 停止 → 人工审核。

生成、观察、目标执行和复测都使用固定 CSCS Apertus v1.5 70B 的新会话；生成讨论不会注入目标请求。BASIC 允许同一模型与赞助凭据承担这些角色，分别标记调用用途；其自评只决定探索优先级，不证明问题成立。外部研究模型适配仍是后续工作。

## 先运行离线示例

在项目根执行：

```powershell
python scripts/explore.py init --config experiments/examples/basic-config.json --store experiments/runs/basic-demo
python scripts/explore.py run --store experiments/runs/basic-demo
python scripts/explore.py status --store experiments/runs/basic-demo
python scripts/explore.py export --store experiments/runs/basic-demo --output experiments/runs/basic-demo-package
```

默认 `mode=mock`，模板和响应由确定性模拟器产生，不是 Apertus 输出。默认场景包含可疑输出以验证扩展和复测；`run --scenario normal|timeout|invalid|duplicate` 可在新的示例任务中检查对应行为。导出目录必须不存在。

## Apertus 生成真实模板

复制 basic-config.json，使用新的 id，将 mode 改为 live，按资源约束调整额度。默认配置最多 70 次调用，其中 40 次预留给复测；每次最多 2048 输出 tokens，总时限 3600 秒。生成、格式修正、辅助观察和测试共享非复测额度。模板来自模型，主题与指标均为占位，可能被结构校验拒绝。

按 CSCS_API_SETUP.md 在当前终端配置 LLM_NAME、LLM_BASE_URL、LLM_API_KEY。密钥不写入配置文件。

```powershell
python scripts/explore.py init --config <live配置路径> --store <新的任务目录>
python scripts/explore.py run --store <任务目录> --live --max-steps 1
python scripts/explore.py inspect --store <任务目录>
```

第一步最多发出一次模型请求，用于生成模板；`--max-steps 1` 是本次进程步数限制，不会重置持久总额度。生成无效时修正任务会保留在队列。继续 `run --live` 才继续派发。

当前代理会话未发现上述环境变量；本次只验证离线流程，真实模板与服务吞吐未验收。

## 模板与变体

每个主题槽位包含 label、hypothesis、language、control、probe、criterion。criterion.kind 支持 exact、model、human。exact 只比较字面文本；model 返回 suspicious/not_observed/needs_review；human 直接进入待复核候选。生成期望值的有效性仍由人判断。

模板保存版本哈希、生成调用和原始响应。变体保存父用例、根用例、生成理由、变更变量及来源调用。首版只允许改变 probe 的措辞；control、语言、判定规则和目标配置继承不变。语义等价性明确标记 unverified；文本去重不等于语义去重。

导出的 template.json 可人工修改后用于新任务：

```powershell
python scripts/explore.py init --config <新配置> --template <编辑后的template.json> --source-campaign <原任务id> --store <新目录>
```

这样修改 benchmark、主题或指标会生成新版本，不重写既有证据。BASIC-1 仍固定温度为 0、单轮文本、无显式 system prompt；8B、语言变体、多模态需要后续契约扩展。

## 持久队列与停止

SQLite 保存追加的状态历史、请求预留与原始响应，并带哈希。每次请求先在事务内扣除额度；同一目录只有一个执行进程。调用状态包括 pending/reserved/sending/completed/failed/unknown/not_sent/skipped/invalid。

- 达到总额度或绝对截止时间：停止全部调用。
- 非复测额度用尽：跳过后续探索，继续已经排队且有额度的复测。
- 达到用例数、深度、候选上限：记录分支停止原因。
- 重复观察标签或重复/无效变体达到阈值：停止继续生成变体。它是调度启发式，不是语义新颖性评估。
- 超时、限流、截断、模型不符：保存失败并停止，不产生自动 finding。
- 存储失败：抛出错误并停止；未完成预留需显式恢复。

```powershell
python scripts/explore.py pause --store <任务目录>
python scripts/explore.py resume --store <任务目录>
python scripts/explore.py run --store <任务目录> --live
python scripts/explore.py cancel --store <任务目录>
python scripts/explore.py recover --store <任务目录>
```

pause/cancel 不保证撤回已在途请求。recover 只能在执行进程退出后运行，将未完成调用标为 unknown，不补发、不返还额度。resume 只恢复待执行任务；未知结果保留。暂停不延长任务的绝对截止时间。更换目录不能用来绕过已有任务额度，目录之间无账户级共享配额。

自动任务可以结束于 completed，并留下 awaiting_review 候选；这不意味着研究结论完成。有跳过或未知调用则为 completed_with_gaps。CLI run 返回 2 表示停止、暂停、取消或存在缺口，返回 1 表示命令/校验失败。

## 人工闭合

根据 inspect 或导出包填写 experiments/examples/basic-review.json。reviewer 与 rationale 必填，evidence_refs 至少引用该候选的一条实际结果 call id，可补充外部来源。程序校验引用和状态，不替代人检查事实依据。

```powershell
python scripts/explore.py review --store <任务目录> --review <人工审核JSON>
```

decision 支持 supported、insufficient、rejected、retest、merge。supported 要求复测完整，字面规则明确未复现时拒绝支持。结果名称为 human_supported_placeholder，仍不可官方导出。retest 创建新调用并保留旧轮次；不能重复加入已有待执行复测，受剩余额度和原截止时间约束。merge 需额外字段 merge_into，记录人工归并，原始证据仍完整保留。默认分组只是同一变体树的临时分组。

report.md 展示状态、调用数、变体关系及审核队列；campaign.json/evidence.json 保留完整来源和响应。后续正式 finding 仍须使用经过独立审查的非占位实验及既有正式 Registry 流程。

## 与现有组件的关系

新增模块 basic_contracts/basic_store/basic/basic_cli；复用 CSCSClient、传输结果验证、源码 manifest 与进程锁。BASIC 账本独立于原 MVP 账本，避免旧数据被新调度修改。当前工作台和 Wiki 同步仍读取原 MVP 记录；BASIC 通过 CLI 和导出包操作，尚未接入其 UI。完整 Wiki 集成保留为后续任务。
