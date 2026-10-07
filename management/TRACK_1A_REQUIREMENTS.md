# Track 1A 要求核验记录

核验日期：2026-10-06。官方来源：[模板固定版本](https://github.com/HackApertus/project-template/tree/7f2382275461baf3fa6c8855d157d86abffe9f0e/track_1a)。本地原件位于 submission/project-template，未修改。

## 已核实
| 来源文件 | 要求 |
|---|---|
| 根 README.md | 保持赛道布局；data 最大100 MB；Docker make run；LLM_NAME/LLM_BASE_URL/LLM_API_KEY |
| track_1a/README.md | Apertus v1.5 8B或70B；最多5个独立finding；私有至2026-12-01；findings许可CDLA-Permissive-2.0 |
| 同上 | 私有仓库添加judgeailights；提交仓库URL和≤6页TeamName_Report.pdf；通过指定网站而非Devpost提交 |
| 同上评分表 | 每issue严重性/范围/新颖性/复现四项均至少1分才获分；报告与代码按N/2加权 |
| technical_report.md | Problem、Red Teaming Method、Findings Dataset、Lessons、Reproducibility、License、References；报告许可CC-BY-4.0 |
| findings/findings.schema | 官方字段、additionalProperties限制及文本长度限制 |

截止时间来自[赛事主页](https://hackapertus.devpost.com/)：2026-10-16 12:00 CEST。

## 实际检查与未闭合项
1. 官方 findings.schema 原始文件 SHA-256：6F1EF151154578FDABBBC31D3EE2D9738A09E004CEFCF37ED97F6527C0717508。
2. Python标准json解析返回 Invalid control character，line 57 column 247：description含字面换行。尚未修复原件。后续如制作语法修复副本，必须保存diff/哈希，仅修语法并核实上游认可情况。
3. 根对象没有required字段；项目验收需补独立必填检查，不篡改官方契约。
4. 根README把赛道目录定义为项目根，同时评审描述强调根make run。项目同时提供仓库根转发和track_1a入口，保留原目录。
5. T&C链接 https://hackapertus.ch/terms-and-conditions 本次网页提取未得到正文；除模板明确条款外不推定额外条件。
6. 官方模板仅是占位Makefile，make run目前主动退出1；不是已可复现项目。

G0：要求主体已核实，schema与额外T&C仍未闭合。最终生成包前重新核对模板版本、具体模型服务与评审访问条件。
