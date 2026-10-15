export type Data = Record<string, any>;
export async function api<T = Data>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(
    "/api/v1" + path,
    body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
  );
  const raw = await response.text();
  let result: Data;
  try {
    result = raw ? JSON.parse(raw) : {};
  } catch {
    throw new Error(
      `HTTP ${response.status}: ${response.ok ? "Invalid API response" : "Service unavailable"}`,
    );
  }
  if (!response.ok)
    throw new Error(
      typeof result.detail === "string"
        ? result.detail
        : JSON.stringify(result.detail),
    );
  return result as T;
}

export const labels: Record<string, [string, string]> = {
  draft: ["待启动", "Draft"],
  running: ["研究中", "Running"],
  paused: ["已暂停", "Paused"],
  completed: ["执行完成", "Completed"],
  completed_with_gaps: ["完成，有缺口", "Completed with gaps"],
  cancelled: ["已取消", "Cancelled"],
  interrupted: ["中断，需检查", "Interrupted"],
  provider_paused: ["服务暂停", "Provider paused"],
  deadline_exceeded: ["已到截止时间", "Deadline reached"],
  repeated_supported: ["复测支持，待审核", "Repeated, awaiting review"],
  confirming: ["独立复测中", "Confirming"],
  not_supported: ["未支持假设", "Not supported"],
  incomplete: ["证据不完整", "Incomplete"],
  awaiting_annotation: ["等待逐对语义标注", "Awaiting semantic annotation"],
  suspicious: ["可疑行为", "Suspicious"],
  needs_review: ["需要人工复核", "Needs review"],
  not_observed: ["未观察到异常", "Not observed"],
  injection: ["指令与来源边界", "Instruction boundaries"],
  facts: ["事实与来源冲突", "Facts and sources"],
  identity: ["身份与位置差异", "Identity and position"],
  planning: ["规划与评审", "Planning & review"],
  exploration: ["探索", "Exploration"],
  confirmation: ["独立确认", "Confirmation"],
  defense: ["防御比较", "Defense"],
  baseline: ["原始配置", "Baseline"],
  system: ["系统提示词", "System prompt"],
  rules: ["确定性规则", "Rules"],
  combined: ["组合防御", "Combined"],
  run_seconds: ["任务时限（秒）", "Task deadline (seconds)"],
  request_seconds: ["请求超时（秒）", "Request timeout (seconds)"],
  input_chars: ["输入字符上限", "Input character cap"],
  output_tokens: ["目标输出 token 上限", "Target output token cap"],
  max_depth: ["变体最大深度", "Maximum variant depth"],
  children_per_case: ["每节点子变体数", "Children per case"],
  beam_width: ["每方向活跃分支数", "Active branches per direction"],
  stagnation_limit: ["无新证据停止阈值", "Stagnation limit"],
  confirmation_repeats: [
    "每条件确认重复数",
    "Confirmation repeats per condition",
  ],
  min_failures: ["确认最低异常数", "Minimum confirmation violations"],
  max_candidates: ["候选上限", "Candidate cap"],
  max_turns: ["每会话最大轮数", "Maximum conversation turns"],
  authority: ["伪权威指示", "False authority"],
  quoted_instruction: ["引用中的指令", "Quoted instructions"],
  urgency: ["紧急语气", "Urgency framing"],
  false_premise: ["错误前提", "False premise"],
  source_conflict: ["来源冲突", "Source conflict"],
  reported_claim: ["报告式陈述", "Reported claim"],
  matched_identity: ["匹配身份对照", "Matched identity"],
  position_reversal: ["身份与位置反转", "Position reversal"],
  education_open: ["开放式教育评价", "Open education assessment"],
  pending: ["等待执行", "Pending"],
};
export function label(key: string, en: boolean) {
  return labels[key]?.[en ? 1 : 0] ?? key;
}
export function rate(n: number, d: number) {
  return d ? `${n}/${d} · ${Math.round((n / d) * 100)}%` : "—";
}
