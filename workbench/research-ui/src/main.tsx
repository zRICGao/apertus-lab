import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import * as Dialog from "@radix-ui/react-dialog";
import {
  Activity,
  ArrowRight,
  BookOpen,
  Check,
  ChevronRight,
  Download,
  FileText,
  FlaskConical,
  GitBranch,
  Globe,
  Layers3,
  Link2,
  Pause,
  Play,
  Plus,
  Search,
  ShieldCheck,
  Square,
  Terminal,
  X,
} from "lucide-react";
import { api, label, rate, type Data } from "./api";
import "./style.css";

function App() {
  const [en, setEn] = useState(localStorage.getItem("lang") === "en");
  const t = (zh: string, english: string) => (en ? english : zh);
  const [tab, setTab] = useState("research");
  const [config, setConfig] = useState<Data>();
  const [health, setHealth] = useState<Data>();
  const [campaigns, setCampaigns] = useState<Data[]>([]);
  const [selected, setSelected] = useState("");
  const selectedRef = useRef("");
  const [state, setState] = useState<Data>();
  const [cards, setCards] = useState<Data[]>([]);
  const [prompts, setPrompts] = useState<Data>({});
  const [sources, setSources] = useState<Data[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [wizard, setWizard] = useState(false);
  const [spec, setSpec] = useState<Data>();
  const [preflight, setPreflight] = useState<Data>();
  const [authorized, setAuthorized] = useState(false);
  const [evidence, setEvidence] = useState<Data>();
  const [filter, setFilter] = useState("");
  const [reviewing, setReviewing] = useState<Data>();
  const [annotating, setAnnotating] = useState<Data>();
  const [sourceForm, setSourceForm] = useState(false);
  const [events, setEvents] = useState<Data[]>([]);
  const [detailTab, setDetailTab] = useState("overview");
  const lastEvent = useRef(0);
  const eventTimer = useRef<ReturnType<typeof setTimeout> | undefined>(
    undefined,
  );

  async function refresh(id = selectedRef.current) {
    const [list, h] = await Promise.all([api("/campaigns"), api("/health")]);
    setCampaigns(list.campaigns);
    setHealth(h);
    if (id) setState(await api("/campaigns/" + id));
  }
  useEffect(() => {
    Promise.all([api("/config"), api("/templates"), api("/knowledge")])
      .then(([c, templates, k]) => {
        setConfig(c);
        setCards(templates.cards);
        setPrompts(templates.prompts);
        setSources(k.sources);
      })
      .catch((e) => setError(e.message));
    refresh().catch((e) => setError(e.message));
    const source = new EventSource("/api/v1/events");
    source.onmessage = (event) => {
      lastEvent.current = Date.now();
      const item = JSON.parse(event.data);
      setEvents((previous) => [item, ...previous].slice(0, 60));
      if (!eventTimer.current)
        eventTimer.current = setTimeout(() => {
          eventTimer.current = undefined;
          refresh().catch((e) => setError(e.message));
        }, 800);
    };
    const interval = setInterval(() => {
      if (Date.now() - lastEvent.current > 6000)
        refresh().catch((e) => setError(e.message));
    }, 6000);
    return () => {
      source.close();
      clearInterval(interval);
      clearTimeout(eventTimer.current);
    };
  }, []);
  useEffect(() => {
    selectedRef.current = selected;
    if (selected) {
      setEvidence(undefined);
      refresh(selected).catch((e) => setError(e.message));
    }
  }, [selected]);
  useEffect(() => {
    localStorage.setItem("lang", en ? "en" : "zh");
    document.documentElement.lang = en ? "en" : "zh-CN";
  }, [en]);

  async function act(fn: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const calls = (state?.calls ?? []) as Data[];
  const used = Object.values(state?.usage ?? {}).reduce(
    (a: number, b) => a + Number(b),
    0,
  );
  const filtered = calls.filter((c) =>
    JSON.stringify([c.role, c.stage, c.payload, c.response?.text])
      .toLowerCase()
      .includes(filter.toLowerCase()),
  );
  const statusBadge = (status: string) => (
    <span className={"badge " + status}>{label(status, en)}</span>
  );
  const openWizard = () => {
    setSpec(structuredClone(config?.defaults));
    setWizard(true);
    setPreflight(undefined);
    setAuthorized(false);
  };
  const updateSpec = (key: string, value: unknown) => {
    setSpec((p) => ({ ...p, [key]: value }));
    setPreflight(undefined);
  };
  const changeLimit = (key: string, value: number) => {
    setSpec((p) => ({ ...p, limits: { ...p?.limits, [key]: value } }));
    setPreflight(undefined);
  };

  return (
    <div className="app">
      <aside className="sidebar">
        <a className="brand" href="#" onClick={() => setTab("research")}>
          <div className="brand-icon">
            <Layers3 size={23} />
          </div>
          <div>
            Apertus <span>Lab</span>
            <small>RESEARCH WORKBENCH</small>
          </div>
        </a>
        <div className="workspace-label">
          {t("本地研究空间", "LOCAL WORKSPACE")} <span>V3</span>
        </div>
        <nav aria-label="Main navigation">
          {[
            ["research", FlaskConical, t("研究任务", "Research")],
            ["templates", Layers3, t("研究模板", "Template library")],
            ["knowledge", BookOpen, t("知识与来源", "Knowledge")],
            ["settings", Terminal, t("配置与方法", "Configuration")],
          ].map(([key, Icon, title]) => {
            const I = Icon as typeof FlaskConical;
            return (
              <button
                key={String(key)}
                className={tab === key ? "nav active" : "nav"}
                onClick={() => setTab(String(key))}
              >
                <I size={18} />
                {String(title)}
                {key === "research" && <span>{campaigns.length}</span>}
              </button>
            );
          })}
        </nav>
        <div className="side-note">
          <GitBranch size={18} />
          <strong>
            {t("每一个结论，都能追溯。", "Every claim has a trail.")}
          </strong>
          <p>
            {t(
              "从假设到证据，从复测到改进。",
              "From hypotheses to evidence. From replay to improvement.",
            )}
          </p>
        </div>
        <div className="connection">
          <i className={health?.worker_alive ? "dot green" : "dot"} />
          <div>
            {health?.worker_alive
              ? t("执行器在线", "Worker online")
              : t("执行器待连接", "Worker offline")}
            <small>localhost · {t("全局并行", "global concurrency")} 10</small>
          </div>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div className="breadcrumb">
            APERTUS LAB <ChevronRight size={13} />{" "}
            {t("研究工作台", "Research workbench")}
          </div>
          <button className="quiet" onClick={() => setEn(!en)}>
            <Globe size={16} />
            {en ? "中文" : "English"}
          </button>
        </header>
        {error && (
          <div className="alert error" role="alert">
            {error}
            <button aria-label="Dismiss" onClick={() => setError("")}>
              <X size={15} />
            </button>
          </div>
        )}
        {notice && (
          <div className="alert" role="status">
            {notice}
            <button aria-label="Dismiss" onClick={() => setNotice("")}>
              <X size={15} />
            </button>
          </div>
        )}

        {tab === "research" && (
          <>
            <div className="page-heading">
              <div>
                <div className="eyebrow">OBSERVE. VERIFY. IMPROVE.</div>
                <h1>{t("让研究形成闭环", "Close the research loop")}</h1>
                <p>
                  {t(
                    "并行探索模型边界，用可复现的证据验证每一步。",
                    "Explore model boundaries in parallel. Verify each step with reproducible evidence.",
                  )}
                </p>
              </div>
              <button
                className="primary"
                onClick={openWizard}
                disabled={!config}
              >
                <Plus size={17} />
                {t("新建研究", "New research")}
              </button>
            </div>
            <div className="metrics">
              <Metric
                icon={<FlaskConical />}
                value={campaigns.length}
                title={t("研究任务", "Campaigns")}
                note={t("持久保存的研究记录", "Durable research records")}
              />
              <Metric
                icon={<Activity />}
                value={campaigns.filter((c) => c.status === "running").length}
                title={t("正在运行", "Active")}
                note={t(
                  "最多 10 个请求同时在途",
                  "Up to 10 requests in flight",
                )}
              />
              <Metric
                icon={<Layers3 />}
                value={cards.length}
                title={t("基础模板", "Seed templates")}
                note={t("3 个方向 · 3 种语言", "3 directions · 3 languages")}
              />
              <Metric
                icon={<ShieldCheck />}
                value="4"
                title={t("防御实验组", "Defense arms")}
                note={t(
                  "基线 / 提示词 / 规则 / 组合",
                  "Baseline / system / rules / combined",
                )}
              />
            </div>
            <div className="research-layout">
              <section className="campaign-list panel">
                <div className="panel-heading">
                  <h2>{t("研究任务", "Campaigns")}</h2>
                  <span>{campaigns.length}</span>
                </div>
                {!campaigns.length ? (
                  <div className="empty small">
                    <FlaskConical />
                    <p>
                      {t(
                        "创建你的第一个研究任务",
                        "Create your first campaign",
                      )}
                    </p>
                  </div>
                ) : (
                  campaigns.map((c) => (
                    <button
                      className={
                        "campaign-item " + (selected === c.id ? "selected" : "")
                      }
                      key={c.id}
                      onClick={() => {
                        setSelected(c.id);
                        setDetailTab("overview");
                      }}
                    >
                      <div>
                        <span className="mode">
                          {c.spec.mode.toUpperCase()}
                        </span>
                        {statusBadge(c.status)}
                      </div>
                      <strong>{c.spec.title}</strong>
                      <small>
                        {c.spec.languages.join(" / ").toUpperCase()} ·{" "}
                        {new Date(c.created * 1000).toLocaleDateString()}
                      </small>
                      <div className="tiny-meter">
                        <span
                          style={{
                            width: `${Math.min(100, (Object.values(c.usage).reduce((a: number, b) => a + Number(b), 0) / c.spec.limits.total_calls) * 100)}%`,
                          }}
                        />
                      </div>
                    </button>
                  ))
                )}
              </section>
              <section className="research-detail panel">
                {!state ? (
                  <div className="empty">
                    <div className="empty-art">
                      <GitBranch size={38} />
                    </div>
                    <h2>
                      {t(
                        "一个问题，一条完整证据链",
                        "One question. A complete evidence trail.",
                      )}
                    </h2>
                    <p>
                      {t(
                        "选择研究任务，查看探索路径、匹配对照、独立复测与防御效果。",
                        "Select a campaign to inspect exploration, controls, independent replay and defenses.",
                      )}
                    </p>
                    <button onClick={openWizard} disabled={!config}>
                      {t("创建研究任务", "Create a campaign")}
                      <ArrowRight size={16} />
                    </button>
                    <div className="flow-preview">
                      {[
                        t("定义", "Define"),
                        t("探索", "Explore"),
                        t("复测", "Replay"),
                        t("防御", "Defend"),
                        t("审核", "Review"),
                      ].map((x, i) => (
                        <React.Fragment key={x}>
                          <span>{x}</span>
                          {i < 4 && <ChevronRight size={12} />}
                        </React.Fragment>
                      ))}
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="detail-heading">
                      <div>
                        <div className="eyebrow">
                          {state.id.slice(0, 21)} ·{" "}
                          {state.spec.mode.toUpperCase()}
                        </div>
                        <h2>{state.spec.title}</h2>
                        {statusBadge(state.status)}
                      </div>
                      <div className="actions">
                        <button
                          onClick={() => {
                            setSpec({
                              ...structuredClone(state.spec),
                              title: state.spec.title + " · v2",
                              parent_campaign: selected,
                            });
                            setPreflight(undefined);
                            setAuthorized(false);
                            setWizard(true);
                          }}
                        >
                          {t("调整为新版本", "Revise as new version")}
                        </button>
                        {state.status === "draft" && (
                          <button
                            className="primary"
                            disabled={busy}
                            onClick={() =>
                              act(async () => {
                                await api(
                                  `/campaigns/${selected}/actions/start`,
                                  {},
                                );
                                await refresh();
                              })
                            }
                          >
                            <Play size={15} />
                            {t("启动", "Start")}
                          </button>
                        )}
                        {state.status === "running" && (
                          <button
                            disabled={busy}
                            onClick={() =>
                              act(async () => {
                                await api(
                                  `/campaigns/${selected}/actions/pause`,
                                  {},
                                );
                                await refresh();
                              })
                            }
                          >
                            <Pause size={15} />
                            {t("暂停", "Pause")}
                          </button>
                        )}
                        {["paused", "interrupted", "provider_paused"].includes(
                          state.status,
                        ) && (
                          <button
                            disabled={busy}
                            onClick={() =>
                              act(async () => {
                                await api(
                                  `/campaigns/${selected}/actions/resume`,
                                  {},
                                );
                                await refresh();
                              })
                            }
                          >
                            <Play size={15} />
                            {t("继续", "Resume")}
                          </button>
                        )}
                        {[
                          "draft",
                          "running",
                          "paused",
                          "interrupted",
                          "provider_paused",
                        ].includes(state.status) && (
                          <button
                            className="quiet"
                            aria-label="Cancel campaign"
                            disabled={busy}
                            onClick={() =>
                              act(async () => {
                                await api(
                                  `/campaigns/${selected}/actions/cancel`,
                                  {},
                                );
                                await refresh();
                              })
                            }
                          >
                            <Square size={15} />
                          </button>
                        )}
                        <button
                          disabled={
                            busy || ["running", "draft"].includes(state.status)
                          }
                          onClick={() =>
                            act(async () => {
                              const result = await api(
                                `/campaigns/${selected}/export`,
                                {},
                              );
                              location.assign(result.download);
                            })
                          }
                        >
                          <Download size={15} />
                          {t("导出", "Export")}
                        </button>
                      </div>
                    </div>
                    {state.spec.mode === "mock" && (
                      <div className="simulation">
                        <FlaskConical size={15} />
                        {t(
                          "离线模拟 · 用于验证架构，所有回答与防御效果均为模拟结果。",
                          "Offline simulation · Responses and defense outcomes are fixtures, not model findings.",
                        )}
                      </div>
                    )}
                    <div className="detail-tabs" role="tablist">
                      {[
                        ["overview", t("研究概览", "Overview")],
                        ["evidence", t("原始证据", "Evidence")],
                        ["defense", t("防御对比", "Defenses")],
                        ["review", t("审核队列", "Review")],
                      ].map(([k, title]) => (
                        <button
                          role="tab"
                          aria-selected={detailTab === k}
                          className={detailTab === k ? "active" : ""}
                          key={k}
                          onClick={() => setDetailTab(k)}
                        >
                          {title}
                        </button>
                      ))}
                    </div>
                    <div className="detail-content">
                      {detailTab === "overview" && (
                        <>
                          <div className="budget">
                            <div>
                              <strong>{t("调用额度", "Call budget")}</strong>
                              <span>
                                {used} / {state.spec.limits.total_calls}
                              </span>
                            </div>
                            <div className="meter">
                              <span
                                style={{
                                  width: `${(used / state.spec.limits.total_calls) * 100}%`,
                                }}
                              />
                            </div>
                            <small>
                              {t(
                                "显示额度使用量，不代表研究完成度。生成、评审与目标请求共同计数。",
                                "Budget use, not completion. Generation, scoring and target calls all count.",
                              )}
                            </small>
                            <div className="budget-stages">
                              {[
                                "planning",
                                "exploration",
                                "confirmation",
                                "defense",
                              ].map((stage) => (
                                <div key={stage}>
                                  <i className={"stage-dot " + stage} />
                                  {label(stage, en)}
                                  <strong>
                                    {state.usage[stage] ?? 0}
                                    <span> / {state.spec.limits[stage]}</span>
                                  </strong>
                                </div>
                              ))}
                            </div>
                          </div>
                          <div className="section-title">
                            <GitBranch size={17} />
                            <h3>{t("探索路径", "Exploration paths")}</h3>
                            <small>
                              {state.pairs.length} {t("组配对", "pairs")}
                            </small>
                          </div>
                          <div className="paths">
                            {state.pairs.map((p: Data) => (
                              <button
                                key={p.id}
                                className={"path depth-" + p.depth}
                                onClick={() => {
                                  setEvidence({ pair: p });
                                  setDetailTab("evidence");
                                }}
                              >
                                <span className="path-node" />
                                <div>
                                  <strong>{label(p.card.family, en)}</strong>
                                  <small>
                                    {label(p.card.direction, en)} ·{" "}
                                    {p.card.language.toUpperCase()} ·{" "}
                                    {t("深度", "depth")} {p.depth} ·{" "}
                                    {p.card.route === "ordinary"
                                      ? t("正常使用", "ordinary use")
                                      : t("对抗使用", "adversarial")}
                                  </small>
                                </div>
                                {statusBadge(p.assessment?.status ?? "pending")}
                                <ChevronRight size={15} />
                              </button>
                            ))}
                          </div>
                          <details className="event-log">
                            <summary>
                              {t(
                                "调度事件与停止原因",
                                "Scheduling events & stop reasons",
                              )}
                            </summary>
                            {events
                              .filter((e) => e.campaign === selected)
                              .slice(0, 15)
                              .map((e) => (
                                <div key={e.seq}>
                                  <code>
                                    #{e.seq} {e.kind}
                                  </code>
                                  <small>{JSON.stringify(e.payload)}</small>
                                </div>
                              ))}
                          </details>
                        </>
                      )}
                      {detailTab === "evidence" && (
                        <>
                          <div className="search">
                            <Search size={16} />
                            <input
                              aria-label="Filter evidence"
                              value={filter}
                              onChange={(e) => setFilter(e.target.value)}
                              placeholder={t(
                                "搜索角色、阶段、输入或回答…",
                                "Search role, stage, prompt or response…",
                              )}
                            />
                          </div>
                          {evidence?.pair && (
                            <div className="comparison">
                              <h3>
                                {evidence.pair.card.family} ·{" "}
                                {evidence.pair.card.language.toUpperCase()}
                              </h3>
                              <div className="pair-columns">
                                {["control", "probe"].map((part) => {
                                  const relevant = calls.filter(
                                    (c) =>
                                      c.payload.pair === evidence.pair.id &&
                                      c.payload.part === part &&
                                      c.kind === "target",
                                  );
                                  const c = relevant.at(-1);
                                  return (
                                    <div key={part}>
                                      <span className="eyebrow">
                                        {part.toUpperCase()}
                                      </span>
                                      <pre>{evidence.pair.card[part]}</pre>
                                      <label>
                                        {t("实际回答", "Actual response")}
                                      </label>
                                      <pre>
                                        {c?.response?.text ??
                                          t("暂无结果", "No response yet")}
                                      </pre>
                                    </div>
                                  );
                                })}
                              </div>
                              <details>
                                <summary>
                                  {t(
                                    "冻结标准与配对判定",
                                    "Frozen rubric & paired assessment",
                                  )}
                                </summary>
                                <pre>
                                  {JSON.stringify(
                                    {
                                      rubric: evidence.pair.card.rubric,
                                      assessment: evidence.pair.assessment,
                                    },
                                    null,
                                    2,
                                  )}
                                </pre>
                              </details>
                            </div>
                          )}
                          {evidence?.call && (
                            <div className="comparison">
                              <h3>
                                {evidence.call.role} /{" "}
                                {label(evidence.call.stage, en)}
                              </h3>
                              <pre>
                                {JSON.stringify(
                                  evidence.call.request.messages,
                                  null,
                                  2,
                                )}
                              </pre>
                              <label>{t("模型输出", "Model output")}</label>
                              <pre>
                                {evidence.call.response?.text ?? "unknown"}
                              </pre>
                              <details>
                                <summary>
                                  {t(
                                    "传输、用量与原始证据",
                                    "Transport, usage & raw evidence",
                                  )}
                                </summary>
                                <pre>
                                  {JSON.stringify(evidence.call, null, 2)}
                                </pre>
                              </details>
                            </div>
                          )}
                          <div className="table-wrap">
                            <table>
                              <thead>
                                <tr>
                                  <th>{t("角色 / 阶段", "Role / stage")}</th>
                                  <th>{t("状态", "Status")}</th>
                                  <th>{t("回答摘要", "Response excerpt")}</th>
                                  <th>{t("证据", "Evidence")}</th>
                                </tr>
                              </thead>
                              <tbody>
                                {filtered
                                  .slice(-150)
                                  .reverse()
                                  .map((c) => (
                                    <tr
                                      key={c.id}
                                      onClick={() => setEvidence({ call: c })}
                                    >
                                      <td>
                                        <strong>{c.role}</strong>
                                        <small>{label(c.stage, en)}</small>
                                      </td>
                                      <td>
                                        <span
                                          className={
                                            c.response?.valid
                                              ? "text-green"
                                              : "text-amber"
                                          }
                                        >
                                          {c.response?.reason ?? "unknown"}
                                        </span>
                                      </td>
                                      <td className="excerpt">
                                        {c.response?.text?.slice(0, 95) ?? "—"}
                                      </td>
                                      <td>
                                        <button
                                          className="icon-button"
                                          aria-label="Inspect evidence"
                                          onClick={() =>
                                            setEvidence({ call: c })
                                          }
                                        >
                                          <FileText size={15} />
                                        </button>
                                      </td>
                                    </tr>
                                  ))}
                              </tbody>
                            </table>
                          </div>
                          <small>
                            {t(
                              "最多显示最近150条；完整记录保留在导出包中。",
                              "Showing up to 150 latest calls; exports include every record.",
                            )}
                          </small>
                        </>
                      )}
                      {detailTab === "defense" && (
                        <>
                          <div className="section-title">
                            <ShieldCheck size={18} />
                            <h3>
                              {t(
                                "冻结防御后的留出集比较",
                                "Frozen defenses on held-out cases",
                              )}
                            </h3>
                          </div>
                          <p className="muted">
                            {t(
                              "开发集与留出集分开；区分模型正确回答、规则拦截、误拒与运行错误。",
                              "Separate development and holdout sets. Distinguish correct answers, blocking, false refusals and errors.",
                            )}
                          </p>
                          {!state.defense?.arms ? (
                            <div className="empty small">
                              <ShieldCheck />
                              <p>
                                {state.defense?.reason ??
                                  t(
                                    "独立复测后自动进入防御实验。",
                                    "Defense experiments follow independent confirmation.",
                                  )}
                              </p>
                            </div>
                          ) : (
                            <>
                              <div className="defense-grid">
                                {Object.entries(state.defense.arms).map(
                                  ([arm, v]) => {
                                    const a = v as Data;
                                    return (
                                      <div
                                        className={
                                          "defense-card " +
                                          (a.preliminarily_effective
                                            ? "effective"
                                            : "")
                                        }
                                        key={arm}
                                      >
                                        <h3>{label(arm, en)}</h3>
                                        <div className="big-number">
                                          {rate(a.attack_fail, a.attack_n)}
                                        </div>
                                        <small>
                                          {t(
                                            "攻击违规 / 已测攻击",
                                            "Attack failures / tested attacks",
                                          )}
                                        </small>
                                        <hr />
                                        <p>
                                          {t(
                                            "正常任务通过",
                                            "Normal task pass",
                                          )}
                                          <strong>
                                            {rate(a.normal_pass, a.normal_n)}
                                          </strong>
                                        </p>
                                        <p>
                                          {t(
                                            "拦截 / 不确定或错误",
                                            "Blocked / uncertain or error",
                                          )}
                                          <strong>
                                            {a.blocked} / {a.invalid}
                                          </strong>
                                        </p>
                                        {a.preliminarily_effective && (
                                          <span className="badge repeated_supported">
                                            <Check size={12} />
                                            {t(
                                              "达到工程初筛门槛",
                                              "Meets preliminary threshold",
                                            )}
                                          </span>
                                        )}
                                        <p>
                                          {t(
                                            "正常任务被拦截",
                                            "Normal tasks blocked",
                                          )}
                                          <strong>
                                            {a.normal_blocked ?? "—"}
                                          </strong>
                                        </p>
                                        <p>
                                          {t(
                                            "请求数 / 平均耗时",
                                            "Calls / mean request time",
                                          )}
                                          <strong>
                                            {a.calls ?? "—"} /{" "}
                                            {a.mean_request_seconds == null
                                              ? "—"
                                              : `${Number(a.mean_request_seconds).toFixed(2)}s`}
                                          </strong>
                                        </p>
                                      </div>
                                    );
                                  },
                                )}
                              </div>
                              <div className="method-note">
                                {t(
                                  "留出变体覆盖新标签、来源包装和身份顺序，泛化范围仍限于这些任务。初筛门槛不是官方安全认证，模拟效果不能作为真实防御证据。",
                                  "Holdout varies labels, source wrappers and identity ordering within these tasks only. Thresholds are engineering presets, not safety certification. Mock effects are not real defense evidence.",
                                )}
                              </div>
                            </>
                          )}
                        </>
                      )}
                      {detailTab === "review" && (
                        <>
                          <div className="section-title">
                            <Check size={17} />
                            <h3>{t("候选审核", "Candidate review")}</h3>
                          </div>
                          <p className="muted">
                            {t(
                              "复测支持不等于正式发现；需检查影响、新颖性、适用范围以及语言和领域依据。",
                              "Repetition is not a finding. Review impact, novelty, scope, language and domain evidence.",
                            )}
                          </p>
                          {!state.candidates.length && (
                            <div className="empty small">
                              <p>
                                {t(
                                  "当前没有候选。阴性结果同样会保留。",
                                  "No candidates. Negative results are preserved.",
                                )}
                              </p>
                            </div>
                          )}
                          {state.candidates.map((c: Data) => (
                            <div className="review-card" key={c.id}>
                              <div>
                                {statusBadge(c.status)}
                                <small>
                                  {c.frozen.card.language.toUpperCase()} ·{" "}
                                  {c.frozen.card.route}
                                </small>
                              </div>
                              <h3>{c.frozen.card.hypothesis}</h3>
                              <p>
                                {t("对照通过", "Control pass")}{" "}
                                {c.summary.control_pass ?? "—"}/
                                {c.summary.n_control ?? "—"} ·{" "}
                                {t("探测异常", "Probe failures")}{" "}
                                {c.summary.probe_fail ?? "—"}/
                                {c.summary.n_probe ?? "—"}
                              </p>
                              <div className="method-note">
                                {c.frozen.card.limitations}
                              </div>
                              {c.reviews.map((r: Data, i: number) => (
                                <p key={i}>
                                  <strong>
                                    {r.reviewer}: {r.decision}
                                  </strong>{" "}
                                  · {r.rationale}
                                </p>
                              ))}
                              <button onClick={() => setReviewing(c)}>
                                {t("检查并记录审核", "Review evidence")}
                                <ArrowRight size={15} />
                              </button>
                            </div>
                          ))}
                          <button
                            disabled={busy || state.status === "running"}
                            onClick={() =>
                              act(async () => {
                                const result = await api(
                                  `/campaigns/${selected}/wiki`,
                                  {},
                                );
                                setNotice(
                                  t(
                                    "已同步候选页：",
                                    "Candidate page synced: ",
                                  ) + result.page,
                                );
                              })
                            }
                          >
                            <BookOpen size={15} />
                            {t("同步到完整 Wiki", "Sync to full Wiki")}
                          </button>
                        </>
                      )}
                    </div>
                  </>
                )}
              </section>
            </div>
          </>
        )}

        {tab === "templates" && (
          <>
            <div className="page-heading">
              <div>
                <div className="eyebrow">RESEARCH STARTS WITH A QUESTION</div>
                <h1>
                  {t("可检查的研究模板", "Inspectable research templates")}
                </h1>
                <p>
                  {t(
                    "先定义什么算异常，再开始探索。每张卡保留范围、对照与审核状态。",
                    "Define a violation before exploration. Every card carries scope, controls and review status.",
                  )}
                </p>
              </div>
            </div>
            <div className="template-grid">
              {cards.map((c) => (
                <article className="template-card panel" key={c.id}>
                  <div>
                    <span className="mode">{c.language.toUpperCase()}</span>
                    <span className="badge">
                      {c.route === "ordinary"
                        ? t("正常使用", "Ordinary use")
                        : t("对抗使用", "Adversarial")}
                    </span>
                  </div>
                  <h3>{label(c.family, en)}</h3>
                  <p>{label(c.direction, en)}</p>
                  <p>{c.hypothesis}</p>
                  <details>
                    <summary>
                      {t("查看输入与判定标准", "Inputs & rubric")}
                    </summary>
                    <label>CONTROL</label>
                    <pre>{c.control}</pre>
                    <label>PROBE</label>
                    <pre>{c.probe}</pre>
                    <pre>{JSON.stringify(c.rubric, null, 2)}</pre>
                    <small>{c.limitations}</small>
                  </details>
                  <small>
                    {t(
                      "翻译与语义：待人工审阅",
                      "Translation & semantics: unreviewed",
                    )}
                  </small>
                  <button
                    className="use-template"
                    onClick={() => {
                      setSpec({
                        ...structuredClone(config?.defaults),
                        directions: [c.direction],
                        languages: [c.language],
                        families: [c.family],
                      });
                      setPreflight(undefined);
                      setAuthorized(false);
                      setWizard(true);
                    }}
                  >
                    {t("以此模板创建研究", "Use this template")}
                    <ArrowRight size={14} />
                  </button>
                </article>
              ))}
            </div>
          </>
        )}
        {tab === "knowledge" && (
          <>
            <div className="page-heading">
              <div>
                <div className="eyebrow">SOURCES BEFORE CLAIMS</div>
                <h1>{t("知识与证据来源", "Knowledge & source material")}</h1>
                <p>
                  {t(
                    "保留来源与许可，明确知识状态。资料仅进入研究角色，不自动注入目标。",
                    "Preserve provenance and rights. Sources inform research roles, never silently alter the target.",
                  )}
                </p>
              </div>
              <div className="actions">
                <a
                  className="button"
                  href="http://localhost:3000"
                  target="_blank"
                  rel="noreferrer"
                >
                  <BookOpen size={16} />
                  {t("完整 Wiki", "Full Wiki")}
                </a>
                <button className="primary" onClick={() => setSourceForm(true)}>
                  <Plus size={16} />
                  {t("导入资料", "Import source")}
                </button>
              </div>
            </div>
            <div className="panel knowledge-panel">
              {!sources.length ? (
                <div className="empty">
                  <BookOpen size={32} />
                  <h3>
                    {t(
                      "让研究从有来源的材料开始",
                      "Start with sourced material",
                    )}
                  </h3>
                  <p>
                    {t(
                      "导入你有权使用的文本与 Markdown；其他文档可通过完整 Wiki 导入。",
                      "Import text or Markdown you have rights to use. Import other formats through the full Wiki.",
                    )}
                  </p>
                </div>
              ) : (
                sources.map((s) => (
                  <article key={s.id}>
                    <span className="badge">
                      {s.review_status} · {s.freshness}
                    </span>
                    <h3>{s.title}</h3>
                    <p>
                      {s.license} · {s.source_url}
                    </p>
                    <details>
                      <summary>{t("内容与哈希", "Content & hash")}</summary>
                      <pre>{s.text}</pre>
                      <code>{s.sha256}</code>
                    </details>
                  </article>
                ))
              )}
            </div>
          </>
        )}
        {tab === "settings" && (
          <>
            <div className="page-heading">
              <div>
                <div className="eyebrow">TRANSPARENT BY DESIGN</div>
                <h1>{t("配置与研究方法", "Configuration & methodology")}</h1>
                <p>
                  {t(
                    "角色独立配置，宿主管理凭据，研究边界始终可见。",
                    "Separate role configuration. Host-managed credentials. Visible research boundaries.",
                  )}
                </p>
              </div>
            </div>
            <div className="settings-grid">
              <section className="panel settings-panel">
                <h2>{t("模型角色", "Model roles")}</h2>
                {config?.roles.map((r: Data) => (
                  <div className="provider" key={r.role}>
                    <strong>{r.role}</strong>
                    <span
                      className={
                        r.credentials_present ? "text-green" : "text-amber"
                      }
                    >
                      {r.credentials_present
                        ? t("凭据已配置", "Credential configured")
                        : t("尚未配置凭据", "Credential missing")}
                    </span>
                    <code>{r.model}</code>
                    <small>{r.endpoint}</small>
                  </div>
                ))}
                <p className="muted">
                  {t(
                    "在宿主 .env 配置 LLM_*、RESEARCH_LLM_*、JUDGE_LLM_*。界面不会读取密钥值。",
                    "Configure LLM_*, RESEARCH_LLM_* and JUDGE_LLM_* in the host .env. Secret values never reach the UI.",
                  )}
                </p>
              </section>
              <section className="panel settings-panel">
                <h2>{t("怎样理解结果", "Interpreting results")}</h2>
                <p>
                  {t(
                    "这是有目的的自适应搜索，不是代表性用户抽样。重复请求支持重复性，不证明总体发生率。",
                    "This is purposive adaptive search, not representative user sampling. Repetition supports repeatability, not population prevalence.",
                  )}
                </p>
                <p>
                  {t(
                    "自动判定区分协议、语义和传输。开放式回答需人工复核；同模型评审不等于独立专家。",
                    "Protocol, semantics and transport are separate. Open responses need human review; same-model scoring is not independent expertise.",
                  )}
                </p>
                <p>
                  {t(
                    "服务修订未知时，结论仅限托管服务、已测语言、提示与日期。",
                    "With unknown revision, scope is limited to the hosted service, tested languages, prompts and dates.",
                  )}
                </p>
              </section>
            </div>
            <section className="panel settings-panel">
              <h2>{t("版本化角色提示词", "Versioned role prompts")}</h2>
              {Object.entries(prompts).map(([role, prompt]) => (
                <details key={role}>
                  <summary>{role}</summary>
                  <pre>{String(prompt)}</pre>
                </details>
              ))}
            </section>
          </>
        )}
        <footer>
          Apertus Lab <span>·</span>{" "}
          {t("证据驱动的模型研究", "Evidence-driven model research")}{" "}
          <span>·</span> LOCAL FIRST
        </footer>
      </main>

      <Modal
        open={wizard}
        onOpenChange={setWizard}
        title={t("创建研究任务", "Create a research campaign")}
        description={t(
          "先检查目标、标准与额度。创建任务本身不会发送模型请求。",
          "Check targets, criteria and budget. Creating a draft sends no model requests.",
        )}
      >
        {spec && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              act(async () => {
                if (!preflight) {
                  setPreflight(await api("/preflight", spec));
                  return;
                }
                const result = await api("/campaigns", spec);
                setSelected(result.id);
                setWizard(false);
                setTab("research");
                await refresh(result.id);
              });
            }}
          >
            <label>
              {t("研究名称", "Title")}
              <input
                required
                maxLength={160}
                value={spec.title}
                onChange={(e) => updateSpec("title", e.target.value)}
              />
            </label>
            <label>
              {t(
                "研究要求（提供给规划器，保留冻结判定标准）",
                "Research question (for Planner; frozen rubric remains explicit)",
              )}
              <textarea
                maxLength={4000}
                value={spec.research_question ?? ""}
                onChange={(e) =>
                  updateSpec("research_question", e.target.value)
                }
              />
            </label>
            <fieldset>
              <legend>{t("运行方式", "Mode")}</legend>
              <div className="choice-row">
                {["mock", "live"].map((mode) => (
                  <button
                    type="button"
                    className={spec.mode === mode ? "choice chosen" : "choice"}
                    key={mode}
                    onClick={() => {
                      updateSpec("mode", mode);
                      setAuthorized(false);
                    }}
                  >
                    <strong>
                      {mode === "mock"
                        ? t("离线模拟", "Offline simulation")
                        : t("真实研究", "Live research")}
                    </strong>
                    <small>
                      {mode === "mock"
                        ? t(
                            "无外部请求，验证完整流程",
                            "No external calls; verify the full workflow",
                          )
                        : t(
                            "使用已配置模型，计入服务额度",
                            "Uses configured models and service quota",
                          )}
                    </small>
                  </button>
                ))}
              </div>
            </fieldset>
            <fieldset>
              <legend>{t("研究方向", "Directions")}</legend>
              <div className="checks">
                {["injection", "facts", "identity"].map((d) => (
                  <label key={d}>
                    <input
                      type="checkbox"
                      checked={spec.directions.includes(d)}
                      onChange={(e) =>
                        updateSpec(
                          "directions",
                          e.target.checked
                            ? [...spec.directions, d]
                            : spec.directions.filter((v: string) => v !== d),
                        )
                      }
                    />
                    {label(d, en)}
                  </label>
                ))}
              </div>
            </fieldset>
            <fieldset>
              <legend>{t("实验语言", "Languages")}</legend>
              <div className="checks">
                {["zh", "en", "de"].map((lang) => (
                  <label key={lang}>
                    <input
                      type="checkbox"
                      checked={spec.languages.includes(lang)}
                      onChange={(e) =>
                        updateSpec(
                          "languages",
                          e.target.checked
                            ? [...spec.languages, lang]
                            : spec.languages.filter((v: string) => v !== lang),
                        )
                      }
                    />
                    {{ zh: "中文", en: "English", de: "Deutsch" }[lang]}
                  </label>
                ))}
              </div>
            </fieldset>
            <div className="form-grid">
              <label>
                {t("全任务调用上限", "Total call cap")}
                <input
                  type="number"
                  min={20}
                  max={10000}
                  value={spec.limits.total_calls}
                  onChange={(e) => changeLimit("total_calls", +e.target.value)}
                />
              </label>
              <label>
                {t("请求并行数", "Concurrent requests")}
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={spec.limits.parallelism}
                  onChange={(e) => changeLimit("parallelism", +e.target.value)}
                />
              </label>
            </div>
            <label className="inline-check">
              <input
                type="checkbox"
                checked={spec.defense_enabled}
                onChange={(e) =>
                  updateSpec("defense_enabled", e.target.checked)
                }
              />
              {t(
                "自动进行隔离防御比较",
                "Automatically run isolated defense comparisons",
              )}
            </label>
            <details>
              <summary>
                {t("高级参数与检测标准", "Advanced parameters & criteria")}
              </summary>
              <div className="form-grid">
                {[
                  "planning",
                  "exploration",
                  "confirmation",
                  "defense",
                  "run_seconds",
                  "request_seconds",
                  "input_chars",
                  "output_tokens",
                ].map((k) => (
                  <label key={k}>
                    {label(k, en)}
                    <input
                      type="number"
                      value={spec.limits[k]}
                      onChange={(e) => changeLimit(k, +e.target.value)}
                    />
                  </label>
                ))}
                {[
                  "max_depth",
                  "children_per_case",
                  "beam_width",
                  "stagnation_limit",
                  "confirmation_repeats",
                  "min_failures",
                  "max_candidates",
                  "max_turns",
                ].map((k) => (
                  <label key={k}>
                    {label(k, en)}
                    <input
                      type="number"
                      value={spec[k]}
                      onChange={(e) => updateSpec(k, +e.target.value)}
                    />
                  </label>
                ))}
              </div>
            </details>
            {!!sources.length && (
              <fieldset>
                <legend>{t("限定研究资料", "Scoped research sources")}</legend>
                {sources.map((s) => (
                  <label className="inline-check" key={s.id}>
                    <input
                      type="checkbox"
                      disabled={s.freshness === "stale"}
                      checked={spec.knowledge_ids.includes(s.id)}
                      onChange={(e) =>
                        updateSpec(
                          "knowledge_ids",
                          e.target.checked
                            ? [...spec.knowledge_ids, s.id]
                            : spec.knowledge_ids.filter(
                                (v: string) => v !== s.id,
                              ),
                        )
                      }
                    />
                    {s.title} · {s.freshness}
                  </label>
                ))}
              </fieldset>
            )}
            {preflight && (
              <div className="method-note">
                <strong>
                  {t("预检通过：", "Preflight passed: ")}
                  {preflight.cards} {t("个模板", "templates")}
                </strong>
                <p>
                  {t("种子请求", "Seed calls")}: {preflight.seed_calls} ·{" "}
                  {t("每候选复测", "Replay per candidate")}:{" "}
                  {preflight.confirmation_per_candidate} ·{" "}
                  {t("防御请求", "Defense calls")}: {preflight.defense_calls}
                </p>
                {preflight.warnings.map((w: string) => (
                  <p className="text-amber" key={w}>
                    {w}
                  </p>
                ))}
                {preflight.self_judging && (
                  <p>
                    {t(
                      "当前目标和辅助评审为同模型，结论仍需独立人工审核。",
                      "Target and auxiliary judge use the same model. Independent human review is still required.",
                    )}
                  </p>
                )}
              </div>
            )}
            {spec.mode === "live" && (
              <label className="inline-check">
                <input
                  required
                  type="checkbox"
                  checked={authorized}
                  onChange={(e) => setAuthorized(e.target.checked)}
                />
                {t(
                  `我授权此任务启动后最多 ${spec.limits.total_calls} 次真实调用。`,
                  `I authorize up to ${spec.limits.total_calls} live calls when this campaign is started.`,
                )}
              </label>
            )}
            {error && (
              <p className="text-amber" role="alert">
                {error}
              </p>
            )}
            <div className="modal-actions">
              <button type="button" onClick={() => setWizard(false)}>
                {t("返回", "Back")}
              </button>
              <button
                className="primary"
                disabled={busy || (spec.mode === "live" && !authorized)}
              >
                {preflight
                  ? t("创建待启动任务", "Create draft")
                  : t("检查配置与额度", "Check configuration")}
                <ArrowRight size={15} />
              </button>
            </div>
          </form>
        )}
      </Modal>

      <Modal
        open={!!reviewing}
        onOpenChange={(open) => {
          if (!open) setReviewing(undefined);
        }}
        title={t("记录独立审核", "Record independent review")}
        description={t(
          "请先在证据页面核对原始回答与匹配对照。模拟结果禁止确认成正式发现。",
          "Inspect raw responses and controls first. Mock evidence cannot become a confirmed finding.",
        )}
      >
        {reviewing && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const values = new FormData(e.currentTarget);
              act(async () => {
                const payload = Object.fromEntries(values.entries());
                await api(`/campaigns/${selected}/reviews/${reviewing.id}`, {
                  ...payload,
                  language_reviewed: values.has("language_reviewed"),
                  domain_reviewed: values.has("domain_reviewed"),
                  severity: values.get("severity") || null,
                  breadth: values.get("breadth") || null,
                  evidence_call_ids: calls
                    .filter(
                      (c) => c.payload.candidate === reviewing.id && c.response,
                    )
                    .map((c) => c.id),
                });
                setReviewing(undefined);
                await refresh();
              });
            }}
          >
            {reviewing.frozen.card.rubric.kind === "open" && (
              <button
                type="button"
                onClick={() => {
                  setAnnotating(reviewing);
                  setReviewing(undefined);
                }}
              >
                {t("逐对标注开放式回答", "Annotate open-response pairs")}
              </button>
            )}
            <label>
              {t("审核人", "Reviewer")}
              <input name="reviewer" required />
            </label>
            <label>
              {t("结论", "Decision")}
              <select name="decision">
                <option value="insufficient">
                  {t("证据不足", "Insufficient evidence")}
                </option>
                <option value="rejected">{t("否定候选", "Rejected")}</option>
                <option
                  value="confirmed"
                  disabled={
                    state?.spec.mode !== "live" ||
                    reviewing.status !== "repeated_supported"
                  }
                >
                  {t("人工确认", "Human confirmed")}
                </option>
              </select>
            </label>
            {[
              ["rationale", t("依据与反例", "Rationale & counterexamples")],
              ["impact", t("影响证据", "Impact evidence")],
              ["novelty", t("新颖性与已有工作", "Novelty & prior work")],
              ["limitations", t("限制与适用范围", "Limitations & scope")],
              [
                "breadth_justification",
                t(
                  "影响范围依据（最多500字符）",
                  "Breadth justification (max 500 characters)",
                ),
              ],
            ].map(([name, title]) => (
              <label key={name}>
                {title}
                <textarea
                  name={name}
                  required={name === "rationale"}
                  minLength={name === "rationale" ? 12 : undefined}
                />
              </label>
            ))}
            <div className="form-grid">
              {["severity", "breadth"].map((name) => (
                <label key={name}>
                  {name === "severity"
                    ? t("严重性自评", "Severity self-assessment")
                    : t("影响范围自评", "Breadth self-assessment")}
                  <select name={name}>
                    <option value="">{t("未评分", "Unscored")}</option>
                    {["1", "2", "5", "10"].map((score) => (
                      <option key={score} value={score}>
                        {score}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            </div>
            <label className="inline-check">
              <input type="checkbox" name="language_reviewed" />
              {t("已完成相关语言审阅", "Relevant language review completed")}
            </label>
            <label className="inline-check">
              <input type="checkbox" name="domain_reviewed" />
              {t("已完成相关领域审阅", "Relevant domain review completed")}
            </label>
            <p className="muted">
              {t(
                "引用该候选的全部已保存确认请求；包含 control 和 probe。",
                "References all saved confirmation calls for this candidate, including control and probe.",
              )}
            </p>
            {error && (
              <p role="alert" className="text-amber">
                {error}
              </p>
            )}
            <div className="modal-actions">
              <button className="primary" disabled={busy}>
                {t("保存审核记录", "Save review")}
              </button>
            </div>
          </form>
        )}
      </Modal>

      <Modal
        open={!!annotating}
        onOpenChange={(open) => {
          if (!open) setAnnotating(undefined);
        }}
        title={t("逐对语义标注", "Pairwise semantic annotation")}
        description={t(
          "每个重复分别核对，引用原始回答中的准确片段；不把不同措辞自动当成偏见。",
          "Review each repetition and quote exact excerpts. Different wording alone is not evidence of bias.",
        )}
      >
        {annotating &&
          Array.from({ length: annotating.frozen.repetitions }, (_, repeat) => {
            const group = calls.filter(
              (c) =>
                c.payload.candidate === annotating.id &&
                c.payload.repeat === repeat &&
                c.payload.turn === state!.spec.max_turns - 1,
            );
            const control = group.find((c) => c.payload.part === "control");
            const probe = group.find((c) => c.payload.part === "probe");
            return (
              <details key={repeat}>
                <summary>
                  {t("重复", "Repeat")} {repeat + 1} ·{" "}
                  {annotating.annotations.filter(
                    (a: Data) => a.repeat === repeat,
                  ).length
                    ? t("已有标注", "Annotated")
                    : t("待标注", "Pending")}
                </summary>
                <pre>
                  CONTROL: {control?.response?.text ?? "unknown"}
                  {"\n\n"}PROBE: {probe?.response?.text ?? "unknown"}
                </pre>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const v = new FormData(e.currentTarget);
                    act(async () => {
                      await api(
                        `/campaigns/${selected}/annotations/${annotating.id}`,
                        {
                          reviewer: v.get("reviewer"),
                          repeat,
                          control_expected: v.has("control_expected"),
                          probe_violated: v.has("probe_violated"),
                          control_quote: v.get("control_quote"),
                          probe_quote: v.get("probe_quote"),
                          rationale: v.get("rationale"),
                        },
                      );
                      const next = await api("/campaigns/" + selected);
                      setState(next);
                      setAnnotating(
                        next.candidates.find(
                          (c: Data) => c.id === annotating.id,
                        ),
                      );
                    });
                  }}
                >
                  <label>
                    {t("标注人", "Annotator")}
                    <input name="reviewer" required />
                  </label>
                  <label className="inline-check">
                    <input name="control_expected" type="checkbox" />
                    {t("对照符合预期", "Control meets expected behavior")}
                  </label>
                  <label className="inline-check">
                    <input name="probe_violated" type="checkbox" />
                    {t("探测违反冻结标准", "Probe violates frozen rubric")}
                  </label>
                  <label>
                    {t("对照原文片段", "Exact control excerpt")}
                    <textarea name="control_quote" required />
                  </label>
                  <label>
                    {t("探测原文片段", "Exact probe excerpt")}
                    <textarea name="probe_quote" required />
                  </label>
                  <label>
                    {t("依据与混淆因素", "Rationale & confounders")}
                    <textarea name="rationale" required minLength={12} />
                  </label>
                  <button
                    disabled={
                      busy ||
                      !control?.response?.valid ||
                      !probe?.response?.valid
                    }
                  >
                    {t("保存本次标注", "Save annotation")}
                  </button>
                  {error && <p className="text-amber">{error}</p>}
                </form>
              </details>
            );
          })}
      </Modal>

      <Modal
        open={sourceForm}
        onOpenChange={setSourceForm}
        title={t("导入有来源的资料", "Import sourced material")}
        description={t(
          "仅导入你有权使用的文本；记录许可。资料不会自动成为已验证事实。",
          "Import text you have rights to use and record its license. Sources do not become verified facts automatically.",
        )}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const values = Object.fromEntries(
              new FormData(e.currentTarget).entries(),
            );
            act(async () => {
              await api("/knowledge", values);
              setSources((await api("/knowledge")).sources);
              setSourceForm(false);
            });
          }}
        >
          <label>
            {t("标题", "Title")}
            <input name="title" required />
          </label>
          <label>
            {t("来源网址（可选）", "Source URL (optional)")}
            <input name="source_url" type="url" />
          </label>
          <label>
            {t("许可／使用权依据", "License / usage rights")}
            <input name="license" required />
          </label>
          <label>
            {t("文本或 Markdown", "Text or Markdown")}
            <textarea rows={9} name="text" required />
          </label>
          {error && <p className="text-amber">{error}</p>}
          <div className="modal-actions">
            <button className="primary" disabled={busy}>
              {t("保存来源", "Save source")}
              <Link2 size={15} />
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

function Metric({
  icon,
  value,
  title,
  note,
}: {
  icon: React.ReactNode;
  value: string | number;
  title: string;
  note: string;
}) {
  return (
    <div className="metric panel">
      <div className="metric-top">
        <span>{title}</span>
        {icon}
      </div>
      <strong>{value}</strong>
      <small>{note}</small>
    </div>
  );
}
function Modal({
  open,
  onOpenChange,
  title,
  description,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="overlay" />
        <Dialog.Content className="modal">
          <Dialog.Title>{title}</Dialog.Title>
          <Dialog.Description>{description}</Dialog.Description>
          <Dialog.Close className="modal-close" aria-label="Close">
            <X size={20} />
          </Dialog.Close>
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
