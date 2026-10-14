const state = { catalog: null, selected: null, detail: null };
const $ = (id) => document.getElementById(id);

async function getJSON(path) {
  const response = await fetch(path, { cache: "no-store" });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || data.error || `HTTP ${response.status}`);
  return data;
}

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
}
function pretty(value) {
  if (value === null || value === undefined || value === "") return "无记录";
  return typeof value === "string" ? value : JSON.stringify(value, null, 2);
}
function date(value) {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString([], { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" });
}
function statusClass(status) {
  return ["pass", "fail", "error", "inconclusive", "pending"].includes(status) ? status : "pending";
}

function showError(message) {
  $("error-banner").hidden = !message;
  $("error-banner").textContent = message || "";
}

function renderRuns() {
  const filter = $("run-filter").value.trim().toLowerCase();
  const runs = (state.catalog?.runs || []).filter((run) => `${run.experiment_id} ${run.phase} ${run.model} ${run.status}`.toLowerCase().includes(filter));
  $("run-count").textContent = String(state.catalog?.runs?.length || 0);
  $("catalog-state").hidden = runs.length > 0;
  $("catalog-state").textContent = state.catalog?.runs?.length ? "没有匹配的运行" : (state.catalog?.errors?.length ? "账本不可读，请查看错误提示" : "尚未找到 evidence.sqlite3");
  $("run-list").innerHTML = runs.map((run) => `
    <button class="run-card ${state.selected && state.selected.run_id === run.run_id && state.selected.database === run.database ? "selected" : ""}" data-db="${escapeHTML(run.database)}" data-id="${escapeHTML(run.run_id)}">
      <span class="run-card-title">${escapeHTML(run.experiment_id)}</span>
      <span class="run-card-meta"><span>${escapeHTML(run.phase)} · ${escapeHTML(run.status)}</span><span class="run-card-count">${run.reserved_calls}/${run.expected_calls}</span></span>
    </button>`).join("");
  document.querySelectorAll(".run-card").forEach((button) => button.addEventListener("click", () => selectRun(button.dataset.db, button.dataset.id)));
}

function renderMetrics(run) {
  const counts = run.counts || {};
  const metrics = [["已完成请求", `${run.reserved_calls}/${run.expected_calls}`, ""], ["通过", counts.pass || 0, "pass"], ["失败", counts.fail || 0, "fail"], ["错误", counts.error || 0, "error"], ["待处理", counts.pending || 0, "pending"]];
  $("metrics").innerHTML = metrics.map(([label, value, cls]) => `<div class="metric"><span class="metric-label">${label}</span><strong class="metric-value ${cls}">${escapeHTML(value)}</strong></div>`).join("");
}

function renderTimeline(attempts) {
  const cells = attempts.map((attempt) => `<span class="timeline-cell ${statusClass(attempt.assessment)}" data-label="${escapeHTML(`${attempt.case_id} · ${attempt.assessment}`)}"></span>`).join("");
  $("timeline").innerHTML = `<div class="timeline-track">${cells || '<span class="muted">尚无请求记录</span>'}</div><div class="timeline-legend"><span><i class="legend-dot"></i>通过</span><span><i class="legend-dot fail"></i>失败 / 错误</span><span><i class="legend-dot pending"></i>进行中</span></div>`;
}

function flagsFor(attempt) {
  const judge = attempt.judge || {};
  const flags = judge.flags || [];
  if (judge.failure_type) flags.push(judge.failure_type);
  if (attempt.transport_error) flags.push(`transport: ${attempt.transport_error}`);
  return flags;
}
function renderAttempt(attempt) {
  const flags = flagsFor(attempt);
  const judgeText = attempt.judge ? { ...attempt.judge, flags } : (attempt.reason || "无 judge 结果");
  const parsed = attempt.parsed_response || "无解析 JSON";
  const raw = attempt.raw_response || "原始响应不可用或已折叠";
  return `<details class="attempt"><summary><span class="attempt-title">${escapeHTML(attempt.case_id)}</span><span class="attempt-meta">${escapeHTML(attempt.role || "")} · batch ${escapeHTML(attempt.batch ?? "—")}</span><span class="attempt-meta">${escapeHTML(date(attempt.finished_at || attempt.reserved_at))}</span><span class="attempt-status ${statusClass(attempt.assessment)}">${escapeHTML(attempt.assessment || "pending")}</span></summary>
    <div class="attempt-body">
      <div class="evidence-block full"><div class="evidence-label">Input prompt · ${escapeHTML(attempt.pair || "single")}</div><pre class="evidence-text">${escapeHTML(attempt.prompt || "无 prompt")}</pre></div>
      <div class="evidence-block"><div class="evidence-label">Model output</div><pre class="evidence-text">${escapeHTML(attempt.text || "无文本返回")}</pre></div>
      <div class="evidence-block"><div class="evidence-label">Parsed response</div><pre class="evidence-text">${escapeHTML(pretty(parsed))}</pre></div>
      <div class="evidence-block"><div class="evidence-label">Judge</div><pre class="evidence-text">${escapeHTML(pretty(judgeText))}</pre><div class="flags">${flags.length ? flags.map((flag) => `<span class="flag">${escapeHTML(flag)}</span>`).join("") : '<span class="flag clean">clean</span>'}</div></div>
      <div class="evidence-block"><div class="evidence-label">Transport</div><pre class="evidence-text">${escapeHTML(pretty({ status: attempt.transport_status, model: attempt.response_model, finish_reason: attempt.finish_reason, usage: attempt.usage, duration_seconds: attempt.duration_seconds, error: attempt.transport_error }))}</pre></div>
      <div class="evidence-block full"><div class="evidence-label">Raw response · decoded for inspection</div><pre class="evidence-text">${escapeHTML(pretty(raw))}</pre></div>
    </div></details>`;
}

function renderDetail(run) {
  state.detail = run;
  $("empty-detail").hidden = true;
  $("detail").hidden = false;
  $("phase-badge").textContent = run.phase.toUpperCase();
  $("phase-badge").className = `status-badge ${run.phase === "confirmation" ? "confirmation" : ""}`;
  $("run-id").textContent = run.run_id;
  $("experiment-title").textContent = run.experiment_id;
  $("hypothesis").textContent = run.hypothesis || "未记录实验假设";
  $("run-status").textContent = run.status;
  $("run-progress").textContent = `${Math.round((run.progress || 0) * 100)}% · ${run.model}`;
  $("status-dot").className = `status-dot ${run.status === "in_progress" ? "running" : (["error", "interrupted"].includes(run.status) ? "error" : "")}`;
  $("batch-note").textContent = `${run.dispatch_mode} · max in flight ${run.batch}`;
  $("attempt-note").textContent = `${run.attempts.length} attempts · ${run.evaluator}`;
  renderMetrics(run); renderTimeline(run.attempts); $("attempts").innerHTML = run.attempts.map(renderAttempt).join("");
}

async function selectRun(database, runId) {
  state.selected = { database, run_id: runId }; renderRuns(); showError("");
  try { renderDetail(await getJSON(`/api/run?database=${encodeURIComponent(database)}&run_id=${encodeURIComponent(runId)}`)); }
  catch (error) { showError(`无法读取运行：${error.message}`); }
}

async function refresh() {
  try {
    const previous = state.selected;
    state.catalog = await getJSON("/api/runs");
    $("last-refresh").textContent = `更新于 ${new Date().toLocaleTimeString()}`;
    showError(state.catalog.errors?.length ? `有 ${state.catalog.errors.length} 个账本暂时不可读：${state.catalog.errors.map((item) => `${item.database} (${item.error})`).join("；")}` : "");
    renderRuns();
    if (previous) {
      const found = state.catalog.runs.find((run) => run.database === previous.database && run.run_id === previous.run_id);
      if (found) await selectRun(previous.database, previous.run_id);
    }
  } catch (error) { showError(`无法读取本地日志：${error.message}`); }
}

$("refresh").addEventListener("click", refresh);
$("run-filter").addEventListener("input", renderRuns);
refresh();
setInterval(refresh, 4000);
