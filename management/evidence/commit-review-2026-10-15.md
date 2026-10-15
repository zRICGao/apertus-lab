# 新增提交审查（2026-10-15，Europe/Zurich）

后续同步：用户随后要求 pull，已从 Prototype/main 将本地 main 快进至 `4925c63`。`--autostash` 恢复引发的 STATUS 文字冲突已解决，保留远端内容及全部审查记录；HEAD=FETCH_HEAD，未改变 origin 配置或子模块。下文“没有合并”等表述为审查阶段历史状态。

## 范围与来源

- 本地 HEAD：`9f0df93c279e31cb6c429bb7ae2f11a63f27f6f9`。
- 读取 `origin`（Hackapertus）收到 Repository not found；按项目已有上传记录核对 `https://github.com/zRICGao/Prototype.git`。
- `git ls-remote`、`git fetch --no-tags --no-recurse-submodules <Prototype URL> main` 取得 `4925c63b848b11ed179a4d1ce5119773b10c8605`。审查 `9f0df93..4925c63` 的 13 个提交、82 个文件；没有合并、切换分支或修改远端配置。
- 使用 `git archive 4925c63` 提取相关目录至被忽略的 `experiments/results/review-4925c63/`；下列行号均指该提交。根工作区原有 BreachWeave 修改保留。
- 已读 HARNESS、PROJECT_OUTLINE、STATUS、TASKS、WORKLOG 及新增方法/证据报告。没有调用模型或重跑 live 实验，没有修改业务代码。

## 发现

### R1 [P1] 两份冻结规格不能被 JSON 解析

`experiments/examples/safety-multilingual-injection-v3.json:139` 和 `finance-proxy-pressure-v2.json:819` 在结束大括号之后含有字面量反斜杠+n，不是换行。对提交字节执行 `json.loads(path.read_text(encoding='utf-8-sig'))` 分别得到 `JSONDecodeError: Extra data: line 139 column 1 (char 7333)` 和 `line 819 column 1 (char 31409)`。CLI 与 builder 都先解析 JSON，因此无法从这两份归档规格复现实验。应移除尾部非法字符，并批量校验所有冻结规格；既有账本哈希需与当时实际运行的字节区分。

### R2 [P2] 决策漂移候选无法完成正式审核导出

`experiments/src/apertus_lab/live.py:160-166` 新增的配对比较允许两条单独 assessment 都为 pass、decision 不同的情况成为候选。但未同步的 `review.py:80-83` 只把 assessment=fail 的 probe 放入 walkthroughs。使用仓库 `test_fairness.FairnessClient` 执行冻结 fairness spec 的探索/确认，得到三个 supported probes、确认单条 assessment 全为 pass；用有效人工审核模板选择 gender-probe 调用 `record_review`，返回 `ValueError: Array size violation at $.apertus_response_walkthroughs`。这阻断了新增决策漂移路径。导出应按 pair_reports 的违规 repeat 选取证据，包含匹配 control/probe；补充从漂移候选到审核/导出的端到端测试。发布包也有同样问题。

### R3 [P2] 拒答关键词掩盖明确工具执行声称

`experiments/src/apertus_lab/evaluators.py:119-124` 只有在未命中 refusal 时才报告工具声称/操作性标记。用英文 fixture 的 judge 检查无害合成文本 `I cannot access external tools. I executed query_inventory_db.`，结果为 assessment=pass、reason=safety_refusal，同时 judge.refusal=true、judge.tool_claim=true。拒答可能针对另一件事；明确的执行声称仍应单独记录违规，或至少对冲突结果返回 inconclusive。否则该筛查器漏过其明确要检测的工具幻觉。

### R4 [P2] 德语分诊的固定性别称谓污染身份反转

`experiments/scripts/build-medical-triage-proxy-v2.py:36` 与 `build-medical-triage-proxy-direction-v1.py:31` 的公共题干写死 `Patientin A und Patient B`；map1 又添加 `Patient A ist ein Mann; Patientin B ist eine Frau.`。两份已提交 JSON 都包含此矛盾（例如 triage-gender-de-map1-control、triage-de-women-lower-map1-control）。因此 A/B 反转时不再只是交换身份，德语稳定选 B 的结果也可能涉及称谓/身份冲突，不能据此单独归因为位置敏感。应将公共题干改为不指定性别的称谓，并以新规格/实验版本重新验证；旧证据保留为受污染版本。

### R5 [P2] 医疗直接复测报告的分母与命中数矛盾

`management/evidence/medical-triage-proxy-2026-10-15.md:27` 写确认阶段 probe 18/18 偏离 tie，但紧邻表格明确中文 probe 8/8 为 tie。按该报告的语言/映射/重复方案，36 次确认包括 18 controls 和 18 probes；其中中文占 6 个 probes 并保持 tie，英语/德语合计应为 12/18 偏离。若合并探索和确认，则 probes 为 16/24 偏离。需要从原始账本重新聚合并注明阶段；当前文本会把观察夸大为全体命中。此处只是报告内一致性检查，本机没有新增实验的外部账本，不能独立认证真实计数。

## 验证证据与边界

- 在提取快照中设置 PYTHONPATH=experiments/src、PYTHONIOENCODING=utf-8，以及可写的 TEMP/TMP，执行 `python -m unittest discover -s experiments/tests -q`：**70 tests，68.596 秒，OK**。全部是离线 fixture；预期的负面 CLI 提示不是测试失败。
- `git diff --check 9f0df93 4925c63`：退出码 0。
- 批量解析 experiments/examples 的全部 JSON，再对 schema_version=2.0 执行 validate_spec：仅上述两个文件解析失败，其余通过。
- 使用仓库 FairnessClient、LiveStore、execute、confirmation_summary、record_review 完整复现 R2；未写入 confirmed review。
- 直接调用 evaluate_safety_text 复现 R3；逐一检查两份医疗 spec 的德语 map1 复现 R4。
- 既有测试没有覆盖两份坏 JSON、漂移候选的正式导出、拒答与执行声称并存、德语身份反转语义，因此 70 项通过不能关闭这些缺陷。
- 新增实验原始 SQLite/响应按报告保留在另一台机器的仓库外目录，本次无法复核模型输出、统计与文件哈希；新增报告不等于本次已独立验证的 finding。
- 开发源码已扩展 paired_identity_controls、expected_decision、safety evaluator；当前冻结 release 尚不支持这些新规格。fresh builder 会复制开发源码，直接替换现有 release 的 spec 并不能复现新研究。此处记录能力边界，不把冻结发布包自动视为最新实验包。
- 下一步：先修复 R1/R2 及筛查器冲突结果，再以新版本修正德语用例；取得外部账本后校正 R5，继续人工语言/领域审核及正式 finding 流程。
