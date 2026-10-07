# CSCS Apertus API 接入

本说明依据用户提供的《CSCS inference endpoints》培训 PDF（2026-09-10）和 CSCS 官方 API 文档整理。PDF 是导师培训材料；其中模型与资源政策都可能更新，以用户项目当前 API 响应和 CSCS 页面为准。

## 服务性质

这是 CSCS 已部署并维护的托管推理 API。客户端直接访问 HTTPS endpoint，不需要在本项目或本地机器部署模型、GPU、vLLM、Slurm 或容器。项目仅需实现 API 客户端。API 与交互式 Chat app 的数据保留规则不同：培训材料称 API 不保存 prompt/response，但保留调用元数据；不要提交个人、机密或敏感数据。

## 取得受限 API key

1. 确认 CSCS 项目已有 inference resource。如果没有，由 PI 或 deputy PI 在项目资源处添加 `INFERENCE-API-U`；按培训材料，普通成员不能代替 PI 完成资源分配，资源可见后再申请 key。
2. 在 <https://ui.inference.cscs.ch> 为个人创建 key。设置 alias；可选 key token budget/reset period，并建议把可用模型限制到 `swiss-ai/Apertus-v1.5-70B`（若该 ID 不在选择列表，先查模型列表，不要猜名称）。key 通常只显示一次；遗失应撤销并创建新 key。
3. 本项目使用赞助资源；执行契约不包含金额预算或精确定价。服务实际配额仍适用，收到限流或额度不足即停止。

## 本机连通性

推荐在仓库根 PowerShell 中逐段粘贴以下命令；无需运行脚本文件，也无需更改 PowerShell Execution Policy：

```powershell
 $env:LLM_BASE_URL = 'https://api.inference.cscs.ch/v1'
 $secureKey = Read-Host 'CSCS Inference API key (input is hidden)' -AsSecureString
 $credential = [System.Net.NetworkCredential]::new('', $secureKey)
 $env:LLM_API_KEY = $credential.Password
 Remove-Variable credential, secureKey

 $headers = @{ Authorization = "Bearer $env:LLM_API_KEY" }
 $models = Invoke-RestMethod -Uri "$env:LLM_BASE_URL/models" `
     -Headers $headers -Method Get -TimeoutSec 30
 $apertusModels = @($models.data | Where-Object { $_.id -match 'Apertus' } | Select-Object -ExpandProperty id)
 $apertusModels

 if ($apertusModels -contains 'swiss-ai/Apertus-v1.5-70B') {
     $env:LLM_NAME = 'swiss-ai/Apertus-v1.5-70B'
     '70B v1.5 is available; no generation request was sent.'
 } else {
     Remove-Item Env:LLM_NAME -ErrorAction SilentlyContinue
     'Exact 70B v1.5 ID was not returned; LLM_NAME remains unset.'
 }
```

如果 `$apertusModels` 没有输出，不要立刻重建 key。先在同一个 PowerShell 窗口检查无密钥的响应结构：

```powershell
if ($null -eq $models) {
    'models variable is null'
} else {
    "response_type=$($models.GetType().FullName)"
    "top_level_fields=$($models.PSObject.Properties.Name -join ',')"
    if ($null -eq $models.data) {
        'data field is missing or null'
    } else {
        "data_count=$(@($models.data).Count)"
        $models.data | Select-Object -First 20 id, object, owned_by | Format-Table -AutoSize
    }
}
```

## 与 Docker / Make 一起运行

仓库根目录提供被 Git 忽略的 `.env`，已预填默认模型和 endpoint。首次只需在该文件的 `LLM_API_KEY=` 后粘贴 key 保存；之后每次在仓库根执行 `make run` 会自动读取该配置。`.env` 不会进入 Git。可用 `.env.example` 重建模板。不要把 `.env` 内容贴到聊天、日志或提交中。若直接在 `submission/release/track_1a` 运行 Make，也会读取仓库根 `.env`。

发布包需要 Linux/WSL、GNU Make 和 Docker。若实际运行 Docker 的 shell 是 WSL/Linux，请在该 shell 内输入 key；PowerShell 的进程环境不会自动传入 WSL：

```bash
export LLM_BASE_URL='https://api.inference.cscs.ch/v1'
export LLM_NAME='swiss-ai/Apertus-v1.5-70B'
read -rsp 'CSCS Inference API key: ' LLM_API_KEY; echo
export LLM_API_KEY
make -C submission/release run
```

Make 默认设置相同的模型名和 endpoint；容器镜像也声明这两个非秘密默认值。若不用本地 `.env`，`LLM_API_KEY` 也可由当前 shell 提供；缺少 key 时 Make 会停止。key 不写入镜像或命令行参数。首次运行需要 Docker 拉取 Python 基础镜像并构建容器。本机不需要 GPU。PowerShell 的 `/models` 连通性检查仍可单独按上文执行。

这些诊断只显示 `/models` 响应的模型元数据，不显示 Authorization header 或 key。若 `data_count=0`，检查 CSCS UI 上 key 是否限制了模型、inference resource 是否属于对应项目；若 top-level fields 与 `data` 字段不同，把字段名和模型 ID 发给项目维护者即可。

key 仅保存在当前 PowerShell 进程环境里；命令只调用 `GET /v1/models`，不会调用模型或消耗生成 token。`LLM_API_KEY` 是项目客户端读取的变量名，base URL 为 `https://api.inference.cscs.ch/v1`。关闭此 PowerShell 窗口会清除进程环境变量。仓库还提供 `scripts/connect-cscs.ps1` 作为等价脚本入口；如果本机执行策略禁止脚本，使用上方逐段粘贴方式，不要为此放宽系统策略。

API 模型列表是名称真值来源。培训材料列有 `swiss-ai/Apertus-v1.5-70B` 和 262144 context；服务可能改版，以当前 `GET /models` 和可用模型/定价页面为准。Thinking 变体禁用 tool use，不用于 Agent 工具循环。

## 真实调用启用闸门

连通性检查只确认 key 可以读模型列表，不代表实验 runner 已接好。当前 v2 `run-live` 已实现；v1 mock runner 仍拒绝 live。执行前检查：

- 按实验预先冻结的最大请求数和单次 `max_tokens`；每次发出请求前先在证据账本预留调用，失败也计数。
- spec 固定探索与确认调用额度、输入字符、输出 token、总时长及请求超时；后台可选配额作为补充，不能替代本地控制。
- 时限、取消、限速（服务当前可能按模型/提供方节流）、错误分类和有限/禁用自动重试。
- 原始请求/响应及可用 usage 与模型 ID、目标 revision/配置和哈希写入独立 Evidence Store；排除 key、Authorization header 和其他凭据。
- 单条小型 smoke call 明确限输出 token 并由用户启动；真实研究 run 只能在前述强闸门都通过后开展。

不要把 API key 写入 `.env` 并提交、实验 spec、SQLite、日志、截图或 Wiki 页面。若为了本机长期使用另存密钥，使用密码管理器；本项目忽略 `.env`，但忽略规则不是密钥存储方案。

## 支持排查

- `401`：重新导出此 CSCS project 的 key，确认进程变量存在；密钥不贴入工单或聊天。
- `403` / `Add Key` 无效：检查 inference resource 是否加到对应项目、key 限额和模型 restriction。
- 模型未找到：重新执行 `GET /v1/models`，使用完整匹配 ID。
- `429`：停止循环，检查 key 预算、模型限速和服务状态。
- `5xx`：先查 <https://inference.status.cscs.ch/>。

不要因为一次异常就将其记为模型发现。

具体运行命令及恢复规则见 ../experiments/README.md。金额、价格和精确输入 tokenizer 均不是启动门槛；未知 usage 或 revision 必须如实记录。
