# 项目与 Track 1A 对照审查

日期：2026-10-07（Europe/Zurich）。范围：当前本地工作区（含未提交文件）、三个固定上游、在线官方模板；未运行真实模型、未发布、未调整暂存区。结论：可用的离线研究基础框架，尚不是可提交的 Apertus 发现项目。

## 实际复验

- `python scripts/extract_breachweave.py --check`：4 个资产与固定版本一致。
- 项目内 Bun 执行 `test ./workbench/apertus-workbench/tests`：2 pass、7 assertions。
- 设置 PYTHONPATH=experiments/src 后 `python -m unittest discover -s experiments/tests -v`：10/10 通过。
- `python scripts/smoke_foundation.py`：运行态 → 证据 → candidate → 新 mock replay 通过；临时目录，无网络模型调用。
- `git diff --check`：退出 0，只有换行符提示。
- BreachWeave HEAD=4ac5fc4c720ac74cf90968251cfae7cd28d3d62f；Wiki HEAD=aac3e6493306b7fff3b09cb181ca93918e93d0e6；模板 HEAD=7f2382275461baf3fa6c8855d157d86abffe9f0e。
- BreachWeave 工作区存在删除标记；原因未判定。Wiki 工作区干净。根目录有大量既有暂存和未跟踪文件，均保留。
- 当前 shell 未找到 docker/make；这不证明机器任何位置均未安装。submission/release 不存在；官方 Makefile 仍是退出 1 的占位文件。

## 优先问题

1. **P1，启用 live 前：响应真实性与截断语义缺失。** ports.py:121–136 只提取文本、usage 和 id，不保存/验证响应 model、finish_reason、完整原始成功响应。使用假 opener 返回 model=different-model、finish_reason=length、content=partial，客户端正常返回 TargetReply。无真实网络调用。这使未来接通 engine 后可能把截断当作模型错误，并失去模型归属依据。建议记录原始成功响应及哈希，保留结束原因与服务元数据，明确截断/拒绝/模型不符的判定规则并补离线测试。当前 live 禁用使其尚未污染正式实验。
2. **P1，实验完整性：预算耗尽静默返回。** engine.py:36–37 捕获 BudgetExhausted 后直接 break，最终返回 run id。将现有两用例 spec 的 max_calls 改为 1，可得到只有 probe、cancelled=false 的运行，control 未执行。需要 completed/budget_exhausted/error 等终态及未执行列表；CLI、编译、确认必须识别不完整运行。不能仅凭 run id 或退出 0 判断实验完成。
3. **P1，干净检出：嵌套仓库登记不完整。** 根索引将 knowledge/llmwiki 与 workbench/BreachWeave 记录为 160000 gitlink，但没有 .gitmodules。按当前索引形成的根仓库无法通过常规 submodule init 恢复两个应用。建议明确使用正式 submodule 或锁定 SHA 的引导下载方式，随后验证全新目录恢复。现有 vendor 四文件可独立验证，不等同完整应用可恢复。
4. **交付阻塞，非回归 bug：** findings.py 始终抛 NotImplementedError；没有确认注册表、真实确认、报告 PDF 或发布目录。当前没有已验证的可提交 finding。CSCS 用户连接 smoke 只证明一次请求成功，不能算研究发现。
5. **G2/G5 尚未形成：** 当前只有单 run 调用次数预算；缺少 token/总时长/费用、探索与确认分账、跨 run 总预算及恢复链路。replay 产生新 run、新调用，但未记录 replay_of，未冻结 evaluator 实现哈希，也无确认阈值和独立 review。不能把 mock replay 当作科学确认。
6. **Wiki 与工作台完成度：** candidate 编译具备幂等和保留人工修改能力，但固定写 mock 元数据；无完整审核、范围检索、stale/conflict 闭环。当前独立工作台是 Memory/Idea 薄封装，不是已经运行的完整 BreachWeave UI/研究 Agent。完整 Wiki 源码已存在，服务流程本轮未验收。
7. **状态与版本卫生：** PROJECT_OUTLINE 仍写实验核心尚未实现，HARNESS 中也保留旧阶段描述，与当前基础框架不一致。缓存 index.db 已暂存，ignore 不会移除已有暂存项。应在专门版本整理中更新描述、明确缓存策略，不直接改动用户暂存区。

## 官方对照

本轮 GitHub 目录页读取失败，已改读官方 raw 文件。在线 main 内容不视为已固定的新提交。

- [赛道说明](https://raw.githubusercontent.com/HackApertus/project-template/main/track_1a/README.md)：以 Apertus v1.5 8B 或 70B 的真实问题为交付核心，至多五项；影响、范围、新颖性、复现四项均须至少一分。框架规模本身不能代替有效发现。当前方法设计符合方向，发现证据缺失。
- [根模板](https://raw.githubusercontent.com/HackApertus/project-template/main/README.md)：保持赛道结构，Docker/make run，LLM_* 环境变量，data ≤100 MB。当前只有参考模板与环境变量客户端，未形成评审包。
- [报告模板](https://raw.githubusercontent.com/HackApertus/project-template/main/track_1a/technical_report.md)：需问题、方法、发现、经验、复现、许可及参考；当前未填研究结果。赛道另要求六页以内 PDF、每个问题独立文件、私有仓库和指定评审访问。
- [schema](https://raw.githubusercontent.com/HackApertus/project-template/main/track_1a/findings/findings.schema)：在线文本仍显示 description 跨行；本地固定原件用标准 JSON 解析重现 Invalid control character，line 57 column 247。根级 required 缺失。保留原件，生成有 diff/hash 的语法修复副本及独立强校验；提交兼容依据仍需闭合。
- [T&C](https://hackapertus.ch/terms-and-conditions)：本轮提取仍无正文，额外条款未核实。本轮未重新验证赛事截止时间；此前日期记录不可视为本轮新验证。

## 建议顺序与验收

1. 完成 G2，修复响应语义、实验终态，补全预算、原始证据与离线负例测试；继续禁止默认 live。
2. 同步准备一个具体研究假设：先选一种模型、一个有影响的任务、匹配对照、规则、重复次数和独立确认预算。缺少用户预算/目标选择时只暂停真实调用。
3. 构建最小 Docker runner 与 LLM_* 入口；从干净检出复验，验证新请求和新结果。早做交付骨架以免临近提交才发现环境问题。
4. 有授权后完成首个真实小样本、冻结用例和规则，再独立 replay；记录全部失败、服务错误、分母及限制，做影响和新颖性调查。
5. 从确认注册表导出，校验 schema/数量/大小/许可，再完成六页报告。Wiki 最小维护可同步；大型 UI、自主规划和跨项目合并后置。

建议追求一至两项证据充分且有实际影响的发现，再决定扩展；不能保证发现数量或得分。G0/G1 未闭合，G2 部分通过，G3/G5/G6/G7 未通过，G4 仅离线 candidate 子流程通过。
