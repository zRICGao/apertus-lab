# v3 架构交付验收（2026-10-15）

## 范围和结论

按用户“先按照计划书完成架构”的授权完成本地并行启发式研究平台。本轮不调用外部模型，不发布、不推送、不将模拟候选标为真实发现。根基线为 `4925c63b848b11ed179a4d1ce5119773b10c8605`，原有工作区改动保留。新版开发代码、旧冻结比赛包与真实研究结果分别记录。

平台已从本机和 Linux Docker 跑通。它是单宿主、单操作员的研究平台：API 与 worker 独立进程，跨角色/任务共享最多10请求。不是分布式集群，也没有用模拟结果证明 Apertus 的攻击或防御效果。

## 验证结果

| 检查 | 实际结果 |
|---|---|
| Python 全套 | 98 tests / 185.503s / OK；含26项平台行为检查和原实验回归 |
| 前端 | Vitest 4 tests passed；TypeScript + Vite 生产构建通过 |
| 依赖审计 | npm audit：0 vulnerabilities；Vitest 已由4.1.7升至4.1.12 |
| 并行上限 | 模拟 provider + barrier 使真实 worker 同时10次发送；断言峰值10；另有25个竞争预留仅准入10的原子检查 |
| 预算/恢复 | 失败不退额度、阶段不可挪用、pause/unknown不重发、非法参数、证据禁止覆盖/删除等行为检查通过 |
| Planner/Mutator | Planner种子反馈先于扩展；stop只停止变体不取消确认；Mutator收到实际匹配回答 |
| 判定/人工门控 | 格式不算偏见；13客观回归样例；开放题每次引用标注；mock禁止正式确认；官方字段/配对walkthrough通过 |
| 传输故障 | 模拟HTTPS异常/绝对时限保留部分原始字节；unicode转义密钥回显丢弃；输入密钥在持久化前拒绝 |
| 本机8770 | `campaign-d81328fb4adc4f5d989746e7bb0896c2` completed，10次模拟调用，SSE事件续读、20文件哈希与4次独立replay通过 |
| Docker8780 | `campaign-c35381eaf4534efe869587377ea0c57a` 同样10次模拟调用、20文件哈希与4次独立replay通过 |
| 包根make run | 从新导出的研究ZIP解包目录根执行，Docker构建和replay完成4次；无UI/Planner/Wiki依赖 |
| 断网replay | 同一导出源码构建独立容器，`--network none` 完成4次mock请求 |
| 完整原版Wiki | 3000/8000健康；历史页面、新候选页和来源可读；笔记浏览器编辑、API读取及重开验证；同名保护409；另3项SQLite回归通过 |

调用数均包括研究辅助角色；mock不是HTTP模型调用。测试中的“Set LLM_NAME…”及“BASIC command failed…”是原有负向用例的预期输出，不是本次验收失败。Starlette TestClient 对 httpx 的弃用提示仍存在，测试通过，今后升级测试客户端时处理。

## 完整默认模拟流程

`campaign-f2d3442f6ad349829360e481a4ea5194`：3方向、3语言、27种子，完成66对用例与3个候选；432次模拟调用：规划90、探索132、确认30、防御180；缺口0、正式finding0。

防御开发集只交给Defender；冻结策略后四组各测20攻击+20正常。baseline/rules模拟攻击违规均20/20，system/combined均0/20，正常均20/20，错误/不确定0。它们是预编程fixture的管线断言，不是服务测量或有效性证据。reported_tokens为null，不能把模拟空usage写成真实费用或token数。

模拟来源快照同步到共享Wiki，页名 `research-campaign-f2d3442f6ad349829360e481a4ea5194-f8118044e2e8.md`，标记candidate/mock、范围和来源哈希。原版Web显示该页及源JSON。新增验收笔记仅记录MOCK和浏览器持久化验证，没有修改历史实验结论。

## 修复与可追踪性

- 原审查R1：两份JSON仅移除尾部字面量非法字符，旧/新哈希见 `spec-syntax-repairs-2026-10-15.json`。
- R2/R3：配对漂移按pair_reports进入review证据，并保留control；拒答不能掩盖明确工具执行声称/操作性细节。新增回归通过。
- R4：医疗德语中性称谓采用新版本 `medical-triage-proxy-v3` / `medical-triage-proxy-direction-v2`；旧规格保留。不重跑真实医疗实验。
- R5：历史医疗摘要存在算术和设计问题，已标疑；外部账本不可用，不编造新的聚合结论。
- 完整Wiki基线 `aac3e6493306b7fff3b09cb181ca93918e93d0e6` 原版SQLite两处查询错误引用托管字段。子仓库最小修复使用workspace表派生ID，保留用户与工作区范围，添加2个独立回归并运行原写锁回归；补丁独立保存为 `wiki-local-sqlite-2026-10-15.diff`。子仓库修改尚未提交。
- Windows沙箱限制回环/asyncio及TEMP；最终HTTP验收在正常本机权限或Linux容器中执行。Wiki环境缺pytest，直接用asyncio执行同一3项原生测试函数，未假称pytest已安装或已运行全套Wiki测试。

## 文件与复验

机器摘要和文件哈希：`workbench-v3-verification-2026-10-15.json`。界面预览：`workbench-v3-preview-2026-10-15.png`。

原版Wiki笔记重开后显示Saved的预览：`wiki-v3-edit-preview-2026-10-15.png`。最终收紧Docker构建上下文后再次构建成功，排除运行知识、Wiki/BreachWeave子仓库及Next缓存。269个非忽略文件检查未发现配置中的密钥，根.env保持忽略；运行来源、导入材料及本次笔记也已加入忽略规则。验收容器8780已关闭并保留卷/日志，8770工作台与3000/8000 Wiki继续运行。

本机详细日志和研究包保留于被忽略的 `experiments/results/`：`workbench-final-tests.log`、`workbench-ui-tests.log`、`workbench-ui-build.log`、`workbench-npm-audit.log`、`workbench-native-acceptance.log`、`workbench-docker-acceptance.log`、`workbench-export-make-run.log`、`workbench-replay-network-none.log`、`workbench-wiki-tests.log`，以及 `workbench-acceptance/<campaign>/`。运行证据与密钥不加入Git。

复验入口：`python scripts/test-workbench.py`、`npm --prefix workbench/research-ui test`、`npm --prefix workbench/research-ui run build`，已启动服务后 `python scripts/verify-workbench.py`。默认全流程用 `python scripts/workbench.py demo`。独立研究包根执行 `make run`；mock包继续mock，live包要求真实凭据并只做冻结复测。

## 尚未完成的研究/比赛验收

真实10并行及限流表现、研究角色生成/批评质量、领域和语言人员校准、标注一致性、跨任务家族泛化和历史外部账本复核仍需完成。完整BreachWeave原版UI未在本次接通；v3使用自己的可追踪调度器和既有提取资产。旧BASIC候选不自动迁移为正式finding。

研究包已实现[官方 Track 1A](https://github.com/HackApertus/project-template/blob/main/track_1a/README.md)要求的可执行布局及相关导出门槛；官方PDF限制为正文6页、不含参考文献。新模拟包没有正式finding/PDF，仍非比赛提交。官方schema语法兼容、完整T&C、评审访问与最终发布仍待独立闭合。
