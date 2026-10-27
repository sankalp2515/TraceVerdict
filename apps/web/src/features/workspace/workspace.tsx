import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronRight,
  Database,
  Download,
  FileText,
  GitBranch,
  Layers,
  LoaderCircle,
  LockKeyhole,
  LogOut,
  Network,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  X,
} from "lucide-react";
import { Brand } from "@/components/tv/brand";
import { api, download, login, logout, restoreSession } from "./api";
import { CaseGraph } from "./case-graph";
import { CaseGuide } from "./case-guide";
import { Connections } from "./connections";
import { IntegrationIntake } from "./onboarding";
import { LiveReplay } from "./live-replay";
import { Status, Notice, EvidenceBody, OutcomeRow, Modal } from "./case-ui";
import { deriveGraph, executionState } from "./data";
import {
  fixtures,
  label,
  pretty,
  type CaseData,
  type CaseSummary,
  type Evidence,
  type Graph,
  type Job,
  type Session,
} from "./types";

const tabs = ["Overview", "Evidence", "Explanation", "Repairs & validation", "Review"];
export function Workspace() {
  const [source, setSource] = useState<"recorded" | "backend">("recorded");
  const [session, setSession] = useState<Session | null>(null);
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [current, setCurrent] = useState<CaseData | null>(null);
  const [graph, setGraph] = useState<Graph | null>(null);
  const [tab, setTab] = useState("Overview");
  const [showGuide, setShowGuide] = useState(true);
  const [screen, setScreen] = useState("Cases");
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [modal, setModal] = useState<"login" | "create" | null>(null);
  const [detail, setDetail] = useState<Evidence | null>(null);
  const [selectedRepair, setSelectedRepair] = useState("");
  const [outcomeFilter, setOutcomeFilter] = useState("all");
  const [connections, setConnections] = useState<unknown>(null);
  const [agents, setAgents] = useState<{ agent_id: string; tenant_id: string }[]>([]);
  const [job, setJob] = useState<Job | null>(null);
  const [reviewed, setReviewed] = useState(false);
  const activeController = useRef<AbortController | null>(null);
  const mounted = useRef(true);
  const requestVersion = useRef(0);
  const monitoredJobs = useRef(new Set<string>());
  useEffect(() => {
    mounted.current = true;
    const params = new URLSearchParams(location.search);
    if (params.get("connect") === "true") setModal("login");
    const id = params.get("case");
    const fixture = params.get("fixture");
    const saved = params.has("case") ? id : sessionStorage.getItem("traceverdict.case");
    const savedMode = params.get("mode") || sessionStorage.getItem("traceverdict.mode");
    if (savedMode === "backend") {
      const controller = new AbortController();
      activeController.current = controller;
      restoreSession(controller.signal)
        .then(async (s) => {
          if (!mounted.current || controller.signal.aborted) return;
          setSession(s);
          setSource("backend");
          if (params.get("connect") !== "true") setModal(null);
          await loadCases();
          if (saved) await openCase(saved, "backend");
        })
        .catch(() => {
          if (mounted.current && !controller.signal.aborted) {
            setModal("login");
            setMessage("Sign in to reopen the connected case.");
          }
        });
    } else if (saved) void openCase(saved, "recorded", fixture || undefined);
    return () => {
      mounted.current = false;
      activeController.current?.abort();
    };
    // Bootstrap reads the URL once; subsequent navigation is handled by case actions.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    if (source !== "backend" || !current) return;
    const pending = Object.values(current.jobs).find(
      (j) => ["queued", "running"].includes(j.status) && !monitoredJobs.current.has(j.job_id),
    );
    if (!pending) return;
    monitoredJobs.current.add(pending.job_id);
    const controller = new AbortController();
    activeController.current?.abort();
    activeController.current = controller;
    void task(() => monitorJob(current.case_id, pending, controller));
    // One monitor per persisted job; the ref prevents restarts as case state changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current, source]);
  async function task(action: () => Promise<void>) {
    setError("");
    setMessage("");
    setLoading(true);
    try {
      await action();
    } catch (e) {
      if (mounted.current && !(e instanceof DOMException && e.name === "AbortError"))
        setError(
          e instanceof Error ? e.message : "Unable to complete the request. Please try again.",
        );
    } finally {
      if (mounted.current) setLoading(false);
    }
  }
  async function loadCases(next?: string) {
    const result = await api<{ items: CaseSummary[]; next_cursor: string | null }>(
      `/v1/cases?limit=20${next ? `&cursor=${encodeURIComponent(next)}` : ""}`,
    );
    setCases((old) => (next ? [...old, ...result.items] : result.items));
    setCursor(result.next_cursor);
  }
  async function openCase(id: string, mode: "recorded" | "backend" = source, fixture?: string) {
    activeController.current?.abort();
    const version = ++requestVersion.current;
    setError("");
    setLoading(true);
    setDetail(null);
    setReviewed(false);
    try {
      let data: CaseData;
      let nextGraph: Graph;
      if (mode === "recorded") {
        const match = fixture || id;
        if (![...fixtures.map((f) => f.id), "nemotron-live"].includes(match))
          throw new Error("Choose one of the available recorded cases.");
        const response = await fetch(`/samples/${match}-world.json`);
        if (!response.ok)
          throw new Error("The recorded case could not be loaded. Refresh and try again.");
        data = await response.json();
        nextGraph = deriveGraph(data);
      } else {
        [data, nextGraph] = await Promise.all([
          api<CaseData>(`/v1/cases/${encodeURIComponent(id)}`),
          api<Graph>(`/v1/cases/${encodeURIComponent(id)}/graph`),
        ]);
      }
      if (!mounted.current || version !== requestVersion.current) return;
      setCurrent(data);
      setGraph(nextGraph);
      setSource(mode);
      setScreen("Cases");
      setSelectedRepair(
        data.candidates.find((c) => c.status === "AWAITING_REVIEW")?.candidate_id ||
          data.candidates[0]?.candidate_id ||
          "",
      );
      setTab("Overview");
      setShowGuide(mode === "recorded");
      sessionStorage.setItem(
        "traceverdict.case",
        mode === "recorded" ? fixture || id : data.case_id,
      );
      sessionStorage.setItem("traceverdict.mode", mode);
      history.replaceState(
        null,
        "",
        `/workspace?mode=${mode}&case=${encodeURIComponent(mode === "recorded" ? fixture || id : data.case_id)}`,
      );
    } catch (e) {
      if (version === requestVersion.current)
        setError(e instanceof Error ? e.message : "Unable to open case.");
    } finally {
      if (version === requestVersion.current) setLoading(false);
    }
  }
  async function refreshCase() {
    if (!current) return;
    const data = await api<CaseData>(`/v1/cases/${current.case_id}`);
    const g = await api<Graph>(`/v1/cases/${current.case_id}/graph`);
    setCurrent(data);
    setGraph(g);
    setReviewed(false);
    return data;
  }
  async function evidence(id: string) {
    const local = current?.entities[id];
    if (local) {
      setDetail(local);
      return;
    }
    if (source === "backend" && current)
      await task(async () =>
        setDetail(await api<Evidence>(`/v1/cases/${current.case_id}/evidence/${id}`)),
      );
    else setError("This source record is not available in the recorded case.");
  }
  async function runJob(path: string) {
    if (!current) return;
    activeController.current?.abort();
    const controller = new AbortController();
    activeController.current = controller;
    const cid = current.case_id;
    const result = await api<Job>(
      path,
      { idempotency_key: crypto.randomUUID() },
      controller.signal,
    );
    monitoredJobs.current.add(result.job_id);
    await monitorJob(cid, result, controller);
  }
  async function monitorJob(cid: string, result: Job, controller: AbortController) {
    setJob(result);
    const deadline = Date.now() + (result.kind === "validate" ? 660000 : 210000);
    let status = result;
    while (!["complete", "incomplete"].includes(status.status)) {
      if (Date.now() > deadline)
        throw new Error(
          "Polling stopped after the time limit. The server job is persisted; refresh the case to check its result.",
        );
      await new Promise<void>((resolve, reject) => {
        const timer = setTimeout(resolve, 1800);
        controller.signal.addEventListener(
          "abort",
          () => {
            clearTimeout(timer);
            reject(new DOMException("Cancelled", "AbortError"));
          },
          { once: true },
        );
      });
      status = await api<Job>(
        `/v1/cases/${cid}/jobs/${result.job_id}`,
        undefined,
        controller.signal,
      );
      if (mounted.current) setJob(status);
    }
    const [data, nextGraph] = await Promise.all([
      api<CaseData>(`/v1/cases/${cid}`, undefined, controller.signal),
      api<Graph>(`/v1/cases/${cid}/graph`, undefined, controller.signal),
    ]);
    if (controller.signal.aborted || !mounted.current) return;
    setCurrent(data);
    setGraph(nextGraph);
    setReviewed(false);
    if (!selectedRepair)
      setSelectedRepair(
        data.candidates.find((c) => c.status === "AWAITING_REVIEW")?.candidate_id ||
          data.candidates[0]?.candidate_id ||
          "",
      );
    if (status.status === "incomplete")
      throw new Error(
        status.error ||
          "The job is incomplete. Inspect case errors and missing evidence before retrying.",
      );
    setMessage("The persisted job completed. The case now shows the returned results.");
  }
  async function signIn(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const values = new FormData(form);
    const key = String(values.get("key") || "");
    form.reset();
    await task(async () => {
      const s = await login(key);
      setSession(s);
      setSource("backend");
      sessionStorage.setItem("traceverdict.mode", "backend");
      setCurrent(null);
      sessionStorage.removeItem("traceverdict.case");
      history.replaceState(null, "", "/workspace?mode=backend");
      setModal(null);
      await loadCases();
      const a = await api<{ agents: { agent_id: string; tenant_id: string }[] }>("/v1/agents");
      setAgents(a.agents);
      setMessage("Connected to your workspace. Select a case or create an investigation.");
    });
  }
  async function createCase(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    await task(async () => {
      const mode = String(f.get("mode"));
      const fixture = String(f.get("fixture"));
      const body = {
        agent_id: String(f.get("agent")),
        execution_mode: mode,
        idempotency_key: crypto.randomUUID(),
        ...(mode === "sample" || !String(f.get("sessions") || "").trim()
          ? { fixture_id: fixture }
          : {
              session_ids: String(f.get("sessions") || "")
                .split(",")
                .map((s) => s.trim())
                .filter(Boolean),
            }),
      };
      const result = await api<CaseData>("/v1/cases", body);
      setModal(null);
      await loadCases();
      await openCase(result.case_id, "backend");
    });
  }
  async function approve() {
    const c = current?.candidates.find((c) => c.candidate_id === selectedRepair);
    const v = c && current?.validations[c.candidate_id];
    if (!c || !v) return;
    await task(async () => {
      await api(`/v1/repairs/${c.candidate_id}/approve`, {
        base_policy_sha256: c.base_policy_sha256,
        patch_sha256: c.patch_sha256,
        validation_report_sha256: v.report_sha256,
      });
      await refreshCase();
      setMessage("Recommendation approved for the reviewed hashes. No policy was deployed.");
    });
  }
  async function exportCase() {
    if (!current) return;
    await task(async () => {
      const report =
        source === "backend"
          ? await api(`/v1/cases/${current.case_id}/export`)
          : { ...current, recorded: true, applied: false };
      download(report, `traceverdict-${current.case_id}.json`);
      setMessage("Report downloaded. Approval and production application remain separate.");
    });
  }
  function back() {
    requestVersion.current++;
    activeController.current?.abort();
    setJob(null);
    setLoading(false);
    setCurrent(null);
    setDetail(null);
    setScreen("Cases");
    history.replaceState(null, "", "/workspace");
    sessionStorage.removeItem("traceverdict.case");
    if (source === "backend") void task(() => loadCases());
  }
  const candidate = current?.candidates.find((c) => c.candidate_id === selectedRepair);
  const alreadyApproved =
    current?.approvals.some((a) => a.candidate_id === selectedRepair) || false;
  const validation = candidate && current?.validations[candidate.candidate_id];
  const recordedCases = fixtures.map((f) => ({
    case_id: f.id,
    agent_id: "research-agent",
    status: "AWAITING_REVIEW",
    execution_mode: "sample",
    created_at: 0,
    fixture_id: f.id,
  }));
  const visibleCases = (source === "recorded" ? recordedCases : cases).filter(
    (c) =>
      `${c.case_id} ${c.agent_id} ${c.fixture_id || ""}`
        .toLowerCase()
        .includes(search.toLowerCase()) &&
      (filter === "all" || c.status === filter),
  );
  const outcomeRows = (validation?.outcomes || []).filter(
    (o) => outcomeFilter === "all" || o.category === outcomeFilter || o.outcome === outcomeFilter,
  );
  const {
    action,
    receipt,
    label: actionState,
  } = executionState({ entities: current?.entities || {} });
  return (
    <div className="workspace">
      <a className="skip-link" href="#workspace-main">
        Skip to workspace
      </a>
      <aside className="workspace-sidebar">
        <Brand />
        <div className="workspace-name">
          <span className="workspace-avatar">TV</span>
          <div>
            Investigation workspace<small>{session?.name || "Sample environment"}</small>
          </div>
          <LockKeyhole size={13} />
        </div>
        <p className="nav-label">Workspace</p>
        <nav aria-label="Workspace navigation">
          <button className={screen === "Cases" ? "active" : ""} onClick={back}>
            <Layers size={18} />
            Cases<span>{source === "recorded" ? 3 : cases.length}</span>
          </button>
          {source === "backend" && (
            <>
              <button
                className={screen === "Agents" ? "active" : ""}
                onClick={() => {
                  setScreen("Agents");
                  if (session)
                    void task(async () => {
                      const r = await api<{ agents: { agent_id: string; tenant_id: string }[] }>(
                        "/v1/agents",
                      );
                      setAgents(r.agents);
                    });
                }}
              >
                <ShieldCheck size={18} />
                Agents
              </button>
              <button
                className={screen === "Connections" ? "active" : ""}
                onClick={() => {
                  setScreen("Connections");
                  if (session) void task(async () => setConnections(await api("/v1/connections")));
                }}
              >
                <Database size={18} />
                Connections
              </button>
            </>
          )}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-note">
            <GitBranch size={21} />
            <strong>A conclusion you can inspect.</strong>
            <p>
              Every source. Every test.
              <br />
              Every human decision.
            </p>
          </div>
          <a href="/">
            <ArrowLeft size={16} />
            Back to website
          </a>
          {session && (
            <button
              onClick={() =>
                void task(async () => {
                  await logout();
                  setSession(null);
                  setSource("recorded");
                  setCurrent(null);
                  setDetail(null);
                  setScreen("Cases");
                  sessionStorage.removeItem("traceverdict.case");
                  sessionStorage.removeItem("traceverdict.mode");
                  history.replaceState(null, "", "/workspace");
                  setMessage("Signed out. The server session has been revoked.");
                })
              }
            >
              <LogOut size={16} />
              Sign out
            </button>
          )}
        </div>
      </aside>
      <div className="workspace-body">
        <header className="workspace-header">
          <div className="breadcrumb">
            <span>Workspace</span>
            <ChevronRight size={13} />
            <button onClick={back}>Cases</button>
            {current && (
              <>
                <ChevronRight size={13} />
                <span className="mono">{current.case_id.slice(-8)}</span>
              </>
            )}
          </div>
          <div className="workspace-account">
            <span className="mode-label">
              <span />
              {source === "recorded" ? "Recorded samples" : `${session?.scope || "project"} access`}
            </span>
            <button
              className="button button-outline button-small"
              onClick={() => setModal("login")}
            >
              {session ? "Switch access" : "Connect workspace"}
              <LockKeyhole size={13} />
            </button>
          </div>
        </header>
        <div className="mode-banner">
          <span className="status-dot" />
          <strong>
            {source === "recorded"
              ? "Recorded sample environment"
              : current
                ? `${label(current.execution_mode)} case`
                : "Connected workspace"}
          </strong>
          <span>
            {source === "recorded"
              ? "Synthetic sandbox results. No live model inference or production changes."
              : "Requests use your scoped backend session. Approval exports a recommendation."}
          </span>
        </div>
        <main id="workspace-main" className="workspace-main">
          {error && (
            <Notice error>
              {error}
              <button className="dismiss" aria-label="Dismiss error" onClick={() => setError("")}>
                <X size={14} />
              </button>
            </Notice>
          )}
          {message && (
            <div className="success-message" role="status">
              <Check size={16} />
              {message}
              <button
                className="dismiss"
                aria-label="Dismiss message"
                onClick={() => setMessage("")}
              >
                <X size={14} />
              </button>
            </div>
          )}
          {loading && (
            <div className="loading-strip" role="status">
              <LoaderCircle className="spin" size={15} />
              {job && !["complete", "incomplete"].includes(job.status)
                ? `Job ${job.status}. Waiting for persisted server results…`
                : "Loading workspace…"}
            </div>
          )}
          {screen === "Connections" ? (
            <>
              <div className="page-title">
                <div>
                  <p className="section-label">Integration availability</p>
                  <h1>Connections</h1>
                  <p>See which data and reasoning paths are available.</p>
                </div>
                {session && (
                  <button
                    className="button button-outline"
                    disabled={loading}
                    onClick={() =>
                      void task(async () => setConnections(await api("/v1/connections")))
                    }
                  >
                    <RefreshCw size={15} />
                    Refresh status
                  </button>
                )}
              </div>
              {!session ? (
                <Notice>
                  Connect a workspace to check actual dependency status. Recorded samples do not
                  contact Zetaris or Nightshift.
                </Notice>
              ) : connections ? (
                <Connections data={connections} />
              ) : (
                <div className="empty-state">
                  {loading
                    ? "Checking backend connections…"
                    : "No connection result available. Refresh status to retry."}
                </div>
              )}
            </>
          ) : screen === "Agents" ? (
            <>
              <div className="page-title">
                <div>
                  <p className="section-label">Connected agents</p>
                  <h1>Agents</h1>
                  <p>Investigations are scoped to agents you are authorized to access.</p>
                </div>
              </div>
              {(source === "recorded"
                ? [{ agent_id: "research-agent", tenant_id: "Synthetic sample" }]
                : agents
              ).map((a) => (
                <div className="agent-row panel" key={a.agent_id}>
                  <span className="line-icon">
                    <ShieldCheck />
                  </span>
                  <div>
                    <h3>{a.agent_id}</h3>
                    <p>{a.tenant_id}</p>
                  </div>
                  <Status value={source === "recorded" ? "sample" : "connected"} />
                </div>
              ))}
              {!agents.length && source === "backend" && (
                <Notice>
                  No authorized agents returned. Ask your workspace administrator to register an
                  agent.
                </Notice>
              )}
              {source === "backend" && session?.scope === "admin" && (
                <IntegrationIntake
                  tenant={session.org}
                  onAgent={async () => {
                    const r = await api<{ agents: { agent_id: string; tenant_id: string }[] }>(
                      "/v1/agents",
                    );
                    setAgents(r.agents);
                  }}
                  onCase={(id) => openCase(id, "backend")}
                />
              )}
            </>
          ) : !current ? (
            <>
              <div className="page-title">
                <div>
                  <p className="section-label">Your investigation desk</p>
                  <h1>Cases</h1>
                  <p>From a suspicious action to a decision you can stand behind.</p>
                </div>
                <button
                  className="button button-dark"
                  disabled={loading}
                  onClick={() => {
                    if (source === "recorded") {
                      void openCase("supplier-contact", "recorded");
                      return;
                    }
                    if (session)
                      void task(async () => {
                        const r = await api<{ agents: { agent_id: string; tenant_id: string }[] }>(
                          "/v1/agents",
                        );
                        setAgents(r.agents);
                        setModal("create");
                      });
                    else setModal("login");
                  }}
                >
                  <Plus size={17} />
                  {source === "recorded" ? "Start guided demo" : "New investigation"}
                </button>
              </div>
              <div className="cases-intro">
                <div>
                  <span className="line-icon">
                    <Network size={23} />
                  </span>
                  <h2>Start with the evidence.</h2>
                  <p>
                    {source === "recorded"
                      ? "Open a recorded case to trace an incident, challenge a conclusion and compare the supplied repair results."
                      : "Open a case or create an investigation from a supported fixture or authorized session."}
                  </p>
                </div>
                <div className="intro-path">
                  <span>Evidence</span>
                  <ArrowRight size={16} />
                  <span>Explanation</span>
                  <ArrowRight size={16} />
                  <span>Validation</span>
                  <ArrowRight size={16} />
                  <span>Review</span>
                </div>
              </div>
              <div className="case-filter">
                <label className="search-field">
                  <Search size={16} />
                  <input
                    aria-label="Search loaded cases"
                    placeholder="Search loaded cases or agents…"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                </label>
                <select
                  aria-label="Filter by status"
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                >
                  <option value="all">All statuses</option>
                  {[
                    "COLLECTING",
                    "AWAITING_REVIEW",
                    "APPROVED",
                    "REJECTED",
                    "INCOMPLETE",
                    "INCONCLUSIVE",
                    "STALE",
                  ].map((s) => (
                    <option key={s} value={s}>
                      {label(s)}
                    </option>
                  ))}
                </select>
                <span className="small muted">
                  {visibleCases.length} {source === "recorded" ? "recorded cases" : "loaded cases"}
                </span>
              </div>
              <div className="case-list">
                <div className="case-list-heading">
                  <span>Investigation</span>
                  <span>Mode</span>
                  <span>Status</span>
                  <span />
                </div>
                {visibleCases.map((c, i) => {
                  const f = fixtures.find((f) => f.id === c.fixture_id);
                  return (
                    <button
                      className="case-list-row"
                      disabled={loading}
                      key={c.case_id}
                      onClick={() => void openCase(c.case_id, source, c.fixture_id)}
                    >
                      <div className="case-name">
                        <span className="case-file">
                          <FileText size={21} />
                        </span>
                        <span>
                          <strong>{f?.short || c.case_id}</strong>
                          <small>
                            {c.agent_id} <span>·</span>{" "}
                            {source === "recorded"
                              ? `Recorded example 0${i + 1}`
                              : c.created_at
                                ? new Date(c.created_at * 1000).toLocaleString()
                                : c.case_id}
                          </small>
                        </span>
                      </div>
                      <span className="sample-tag">
                        {source === "recorded" ? "Recorded sample" : label(c.execution_mode)}
                      </span>
                      <Status value={c.status} />
                      <ArrowRight size={16} />
                    </button>
                  );
                })}
                {!visibleCases.length && (
                  <div className="empty-state">
                    <Search size={26} />
                    <h3>
                      {cases.length || source === "recorded"
                        ? "No matching cases"
                        : "Your first case starts here"}
                    </h3>
                    <p>
                      {cases.length || source === "recorded"
                        ? "Change the search or status filter."
                        : "Create an investigation to collect evidence from a supported source."}
                    </p>
                  </div>
                )}
              </div>
              {cursor && source === "backend" && (
                <button
                  className="button button-outline"
                  disabled={loading}
                  onClick={() => void task(() => loadCases(cursor))}
                >
                  Load more cases
                </button>
              )}
              <div className="desk-note">
                <LockKeyhole size={16} />
                <p>
                  Review produces an exportable recommendation. No action here applies a policy to
                  production.
                </p>
                <a href="/">
                  About TraceVerdict <ArrowRight size={14} />
                </a>
              </div>
            </>
          ) : (
            <>
              <div className="case-heading">
                <button className="back-link" onClick={back}>
                  <ArrowLeft size={15} />
                  All cases
                </button>
                <div className="page-title">
                  <div>
                    <div className="button-row">
                      <span className="section-label">{current.agent_id}</span>
                      <Status value={current.status} />
                    </div>
                    <h1>
                      {fixtures.find((f) => f.id === current.fixture_id)?.short ||
                        "Agent investigation"}
                    </h1>
                    <p className="mono small">{current.case_id}</p>
                  </div>
                  <div className="button-row">
                    {source === "backend" && (
                      <button
                        className="icon-button"
                        aria-label="Refresh case"
                        disabled={loading}
                        onClick={() =>
                          void task(async () => {
                            await refreshCase();
                          })
                        }
                      >
                        <RefreshCw size={17} />
                      </button>
                    )}
                    <button
                      className="button button-outline"
                      onClick={() => void exportCase()}
                      disabled={loading}
                    >
                      <Download size={16} />
                      Export report
                    </button>
                  </div>
                </div>
              </div>
              {source === "recorded" && current.execution_mode === "live" && (
                <Notice>
                  Recorded live execution. Explanation contains the actual model response IDs;
                  Repairs contains model-driven replay receipts. Viewing this case runs no new
                  inference.
                </Notice>
              )}
              {source === "recorded" &&
                (showGuide ? (
                  <CaseGuide
                    tab={tab}
                    data={current}
                    onTab={setTab}
                    onHide={() => setShowGuide(false)}
                    onExport={() => void exportCase()}
                  />
                ) : (
                  <button className="source-link guide-reopen" onClick={() => setShowGuide(true)}>
                    Show guided walkthrough
                  </button>
                ))}
              <div
                className={
                  source === "recorded" && showGuide ? "case-tabs guided-tabs" : "case-tabs"
                }
                role="tablist"
                aria-label="Investigation sections"
              >
                {tabs.map((t, i) => (
                  <button
                    key={t}
                    id={`case-tab-${i}`}
                    aria-controls="case-tab-panel"
                    role="tab"
                    aria-selected={tab === t}
                    tabIndex={tab === t ? 0 : -1}
                    className={tab === t ? "active" : ""}
                    onKeyDown={(e) => {
                      if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
                        const next =
                          (i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length;
                        setTab(tabs[next]!);
                        document.getElementById(`case-tab-${next}`)?.focus();
                      }
                    }}
                    onClick={() => setTab(t)}
                  >
                    {t}
                    {t === "Evidence" && <span>{Object.keys(current.entities).length}</span>}
                  </button>
                ))}
              </div>
              <div
                role="tabpanel"
                id="case-tab-panel"
                aria-labelledby={
                  source === "recorded" && showGuide
                    ? "guide-question"
                    : `case-tab-${tabs.indexOf(tab)}`
                }
              >
                {current.missing_evidence.length > 0 && (
                  <Notice>Missing evidence: {current.missing_evidence.join("; ")}</Notice>
                )}
                {current.errors.length > 0 && (
                  <Notice error>
                    Case errors: <pre>{pretty(current.errors)}</pre>
                  </Notice>
                )}
                {tab === "Overview" && (
                  <>
                    <div className="overview-grid">
                      <section className="panel task-panel">
                        <span className="section-label">What the user authorized</span>
                        <h2>The task is the boundary.</h2>
                        {Object.values(current.entities)
                          .filter((e) => e.kind === "task")
                          .map((e) => (
                            <div key={e.evidence_id}>
                              <pre className="task-copy">
                                {Object.values(e.payload)
                                  .filter((v) => typeof v === "string")
                                  .join("\n")}
                              </pre>
                              <button
                                className="source-link"
                                onClick={() => void evidence(e.evidence_id)}
                              >
                                Open original task <FileText size={12} />
                              </button>
                            </div>
                          ))}
                      </section>
                      <section className="panel outcome-panel">
                        <span className="section-label">Execution outcome</span>
                        <h3>{actionState}</h3>
                        <p>
                          {receipt
                            ? "The application receipt reports its execution result. This is not independent attestation."
                            : "No confirming application receipt is available. An allowed action is not confirmed execution."}
                        </p>
                        {action && (
                          <button
                            className="source-link"
                            onClick={() => void evidence(action.evidence_id)}
                          >
                            Attempted action <FileText size={12} />
                          </button>
                        )}
                        {receipt && (
                          <button
                            className="source-link"
                            onClick={() => void evidence(receipt.evidence_id)}
                          >
                            Application receipt <FileText size={12} />
                          </button>
                        )}
                      </section>
                    </div>
                    <section className="panel">
                      <div className="panel-heading">
                        <div>
                          <span className="section-label">Case at a glance</span>
                          <h3>A connected record of the incident</h3>
                        </div>
                        <button className="text-link" onClick={() => setTab("Evidence")}>
                          Inspect evidence <ArrowRight size={15} />
                        </button>
                      </div>
                      <div className="case-facts">
                        <div>
                          <strong>{Object.keys(current.entities).length}</strong>
                          <span>Source records</span>
                        </div>
                        <div>
                          <strong>{current.claims.length}</strong>
                          <span>Cited claims</span>
                        </div>
                        <div>
                          <strong>{current.candidates.length}</strong>
                          <span>Repair candidates</span>
                        </div>
                        <div>
                          <strong>{Object.keys(current.validations).length}</strong>
                          <span>Validation reports</span>
                        </div>
                      </div>
                      <dl className="metadata">
                        <div>
                          <dt>Execution mode</dt>
                          <dd>
                            {source === "recorded"
                              ? "Recorded sample; deterministic sandbox"
                              : label(current.execution_mode)}
                          </dd>
                        </div>
                        <div>
                          <dt>Base policy SHA-256</dt>
                          <dd>{current.base_policy_sha256}</dd>
                        </div>
                        <div>
                          <dt>Case state version</dt>
                          <dd>{current.state_version}</dd>
                        </div>
                      </dl>
                    </section>
                    <div className="next-step">
                      <div>
                        <span className="section-label">Next step</span>
                        <h3>
                          {source === "recorded"
                            ? "Inspect the source records"
                            : current.candidates.length
                              ? "Inspect the repair comparison"
                              : "Begin the investigation"}
                        </h3>
                        <p>
                          {source === "recorded"
                            ? "These results are recorded. Open the test report to see what passed and what failed."
                            : "Work runs as a persisted server job. Missing evidence remains visible."}
                        </p>
                      </div>
                      <button
                        className="button button-dark"
                        disabled={loading}
                        onClick={() =>
                          source === "recorded"
                            ? setTab("Evidence")
                            : current.candidates.length
                              ? setTab("Repairs & validation")
                              : void task(() => runJob(`/v1/cases/${current.case_id}/investigate`))
                        }
                      >
                        {source === "recorded"
                          ? "Follow the evidence"
                          : current.candidates.length
                            ? "Compare repairs"
                            : "Begin investigation"}
                        <ArrowRight size={16} />
                      </button>
                    </div>
                    {source === "backend" &&
                      current.execution_mode === "live" &&
                      current.status === "COLLECTING" &&
                      session?.scope === "admin" && (
                        <section className="panel">
                          <h3>Publish captured evidence</h3>
                          <p>
                            Copy this immutable capture into the configured operational,
                            configuration and reference sources. Investigation then queries it
                            through Zetaris. This does not execute the original agent action.
                          </p>
                          <button
                            className="button button-outline"
                            disabled={loading}
                            onClick={() =>
                              void task(async () => {
                                await api(
                                  `/v1/cases/${current.case_id}/publish-source-records`,
                                  {},
                                );
                                setMessage(
                                  "Evidence published to all three sources. You can begin investigation through Zetaris.",
                                );
                              })
                            }
                          >
                            Publish to governed sources
                          </button>
                        </section>
                      )}
                    {current.uncertainty?.map((u, i) => (
                      <Notice key={i}>{u}</Notice>
                    ))}
                  </>
                )}
                {tab === "Evidence" && (
                  <>
                    <div className="section-toolbar">
                      <div>
                        <h2>Every record has a source.</h2>
                        <p className="muted">
                          Solid lines show observed relations. Dashed lines show inference or
                          context.
                        </p>
                      </div>
                    </div>
                    {graph && (
                      <CaseGraph
                        graph={graph}
                        evidence={current.entities}
                        onEvidence={(id) => void evidence(id)}
                      />
                    )}
                    <section className="panel history-panel">
                      <h3>Case history</h3>
                      <p className="muted">Immutable observations preserve earlier states.</p>
                      {current.observations?.slice(-8).map((o) => (
                        <div className="history-row" key={o.version}>
                          <span className="mono">v{o.version}</span>
                          <span>{label(o.event)}</span>
                          <time>{new Date(o.at * 1000).toLocaleString()}</time>
                          {source === "backend" && (
                            <button
                              className="source-link"
                              onClick={() =>
                                void task(async () =>
                                  download(
                                    await api(`/v1/cases/${current.case_id}/history/${o.version}`),
                                    `case-history-v${o.version}.json`,
                                  ),
                                )
                              }
                            >
                              Download projection
                            </button>
                          )}
                        </div>
                      ))}
                    </section>
                  </>
                )}
                {tab === "Explanation" && (
                  <>
                    <div className="section-toolbar">
                      <div>
                        <h2>A finding, with its limits.</h2>
                        <p className="muted">
                          Accepted claims can still describe inference. Read the basis before the
                          conclusion.
                        </p>
                      </div>
                    </div>
                    {current.claims.length === 0 ? (
                      <Notice>
                        {source === "recorded"
                          ? "No claims are present in this recorded case."
                          : "Run the investigation from Overview to produce source-linked claims."}
                      </Notice>
                    ) : (
                      current.claims.map((c) => (
                        <article className="panel claim-panel" key={c.claim_id}>
                          <div className="panel-heading">
                            <span className="mono small">{c.claim_id}</span>
                            <div className="button-row">
                              <span className="small muted">{label(c.basis)}</span>
                              <Status value={c.review_status} />
                            </div>
                          </div>
                          <h3>{c.statement}</h3>
                          <div className="button-row">
                            {c.support_evidence_ids.map((id) => (
                              <button
                                className="source-link"
                                key={id}
                                onClick={() => void evidence(id)}
                              >
                                {current.entities[id]?.kind || id}
                                <FileText size={12} />
                              </button>
                            ))}
                          </div>
                          {c.competing_explanations.map((x, i) => (
                            <p key={i} className="claim-alternative">
                              <strong>Alternative: </strong>
                              {x}
                            </p>
                          ))}
                          {c.missing_evidence.length > 0 && (
                            <Notice>Missing: {c.missing_evidence.join("; ")}</Notice>
                          )}
                        </article>
                      ))
                    )}
                    <section className="panel critique-panel">
                      <div className="panel-heading">
                        <div>
                          <span className="section-label">The critic’s review</span>
                          <h3>What the explanation had to answer</h3>
                        </div>
                        <GitBranch size={22} />
                      </div>
                      {current.critique_history?.length ? (
                        current.critique_history.map((c, i) => (
                          <div className="critique-row" key={i}>
                            <span className="step-number">0{i + 1}</span>
                            <div>
                              <strong>
                                {c.disputed_claim_ids.length
                                  ? "Conclusion challenged"
                                  : "Revised explanation reviewed"}
                              </strong>
                              <p>{c.reason}</p>
                              {c.disputed_claim_ids.length > 0 && (
                                <small>Disputed claims: {c.disputed_claim_ids.join(", ")}</small>
                              )}
                            </div>
                          </div>
                        ))
                      ) : (
                        <p>No critic review has been returned for this case.</p>
                      )}
                    </section>
                    {!!current.model_calls?.length && (
                      <section className="panel">
                        <details>
                          <summary className="text-link">
                            Inspect model attribution and request evidence (
                            {current.model_calls.length})
                          </summary>
                          <pre>{pretty(current.model_calls)}</pre>
                        </details>
                        <p className="fine-print">
                          Requested routes and returned model evidence are separate. A routing alias
                          does not independently establish the model that executed.
                        </p>
                      </section>
                    )}
                    {current.uncertainty?.map((u, i) => (
                      <Notice key={i}>{u}</Notice>
                    ))}
                  </>
                )}
                {tab === "Repairs & validation" && (
                  <>
                    <div className="section-toolbar">
                      <div>
                        <h2>A safer boundary. A useful agent.</h2>
                        <p className="muted">Compare the exact change and the work it preserves.</p>
                      </div>
                    </div>
                    {!current.candidates.length ? (
                      <Notice>
                        No candidate has been returned. Complete the investigation before
                        validation.
                      </Notice>
                    ) : (
                      <>
                        <div className="repair-options">
                          {current.candidates.map((c, i) => {
                            const v = current.validations[c.candidate_id];
                            return (
                              <button
                                className={`repair-option ${selectedRepair === c.candidate_id ? "selected" : ""}`}
                                key={c.candidate_id}
                                onClick={() => {
                                  setSelectedRepair(c.candidate_id);
                                  setOutcomeFilter("all");
                                  setReviewed(false);
                                }}
                              >
                                <div>
                                  <span className="mono small">
                                    Candidate {String.fromCharCode(65 + i)}
                                  </span>
                                  <Status value={c.status} />
                                </div>
                                <h3>
                                  {c.diff.some((d) => d.path === "contract.mode")
                                    ? "Enforce user intent"
                                    : "Restrict recipients"}
                                </h3>
                                <p>{c.request.expected_control_effect}</p>
                                <span className="fine-print">
                                  Origin:{" "}
                                  {c.origin ||
                                    (current.execution_mode === "sample"
                                      ? "sample-template"
                                      : "not supplied")}
                                </span>
                                {v && (
                                  <div className="repair-counts">
                                    {["unsafe", "utility"].map((cat) => {
                                      const results = v.outcomes.filter((o) => o.category === cat);
                                      return (
                                        <span key={cat}>
                                          <strong>
                                            {results.filter((o) => o.outcome === "pass").length}/
                                            {results.length}
                                          </strong>
                                          {cat === "unsafe" ? "Safety checks" : "Legitimate tasks"}
                                        </span>
                                      );
                                    })}
                                  </div>
                                )}
                              </button>
                            );
                          })}
                        </div>
                        {candidate && (
                          <>
                            <section className="panel">
                              <div className="panel-heading">
                                <div>
                                  <span className="section-label">Exact policy change</span>
                                  <h3>{candidate.diff.map((d) => d.path).join(", ")}</h3>
                                </div>
                                {source === "backend" && (
                                  <button
                                    className="button button-dark button-small"
                                    disabled={loading || candidate.status === "APPROVED"}
                                    onClick={() =>
                                      void task(() =>
                                        runJob(`/v1/repairs/${candidate.candidate_id}/validate`),
                                      )
                                    }
                                  >
                                    <ShieldCheck size={15} />
                                    {validation ? "Revalidate candidate" : "Run validation"}
                                  </button>
                                )}
                              </div>
                              <div className="policy-diff">
                                {candidate.diff.map((d) => (
                                  <div key={d.path}>
                                    <div className="diff-path">{d.path}</div>
                                    <pre className="diff-before">− {pretty(d.before)}</pre>
                                    <pre className="diff-after">+ {pretty(d.after)}</pre>
                                  </div>
                                ))}
                              </div>
                              <dl className="metadata">
                                <div>
                                  <dt>Rationale claims</dt>
                                  <dd>{candidate.request.rationale_claim_ids.join(", ")}</dd>
                                </div>
                                <div>
                                  <dt>Patch SHA-256</dt>
                                  <dd>{candidate.patch_sha256}</dd>
                                </div>
                              </dl>
                            </section>
                            {validation ? (
                              <>
                                <section className="panel validation-panel">
                                  <div className="panel-heading">
                                    <div>
                                      <span className="section-label">
                                        {source === "recorded"
                                          ? "Recorded validation report"
                                          : "Validation report"}
                                      </span>
                                      <h3>Safety and retained utility</h3>
                                    </div>
                                    <Status value={validation.status} />
                                  </div>
                                  <div className="validation-summary">
                                    <span>
                                      <strong>{validation.outcomes.length}</strong>scored scenarios
                                    </span>
                                    <span>
                                      <strong>
                                        {
                                          validation.outcomes.filter((o) => o.outcome === "pass")
                                            .length
                                        }
                                      </strong>
                                      passed
                                    </span>
                                    <span>
                                      <strong>
                                        {
                                          validation.outcomes.filter((o) => o.outcome === "fail")
                                            .length
                                        }
                                      </strong>
                                      failed
                                    </span>
                                    <span>
                                      <strong>
                                        {validation.complete ? "Complete" : "Incomplete"}
                                      </strong>
                                      report coverage
                                    </span>
                                  </div>
                                  <Notice>
                                    {validation.baseline_reproduced
                                      ? "The unsafe baseline was reproduced in the local sandbox."
                                      : "The unsafe baseline was not reproduced; do not infer a successful repair."}{" "}
                                    Passing this configured suite does not establish universal
                                    safety.
                                  </Notice>
                                  <div className="panel-toolbar">
                                    <h4>Paired scenario results</h4>
                                    <select
                                      value={outcomeFilter}
                                      aria-label="Filter scenario results"
                                      onChange={(e) => setOutcomeFilter(e.target.value)}
                                    >
                                      <option value="all">All scenarios</option>
                                      <option value="unsafe">Unsafe actions</option>
                                      <option value="utility">Legitimate tasks</option>
                                      <option value="fail">Failed results</option>
                                      <option value="error">Errors</option>
                                    </select>
                                  </div>
                                  <div className="table-scroll">
                                    <table className="results-table">
                                      <thead>
                                        <tr>
                                          <th>Scenario / execution mode</th>
                                          <th>Baseline</th>
                                          <th>Candidate</th>
                                          <th>Time</th>
                                          <th>Receipt</th>
                                        </tr>
                                      </thead>
                                      <tbody>
                                        {outcomeRows.map((o) => (
                                          <OutcomeRow
                                            key={`${o.scenario_id}-${o.execution_mode}`}
                                            outcome={o}
                                            baseline={validation.baseline.find(
                                              (b) =>
                                                b.scenario_id === o.scenario_id &&
                                                b.execution_mode === o.execution_mode,
                                            )}
                                          />
                                        ))}
                                        {!outcomeRows.length && (
                                          <tr>
                                            <td colSpan={5}>No scenarios match this filter.</td>
                                          </tr>
                                        )}
                                      </tbody>
                                    </table>
                                  </div>
                                  {validation.limitations.map((x, i) => (
                                    <p className="fine-print" key={i}>
                                      {x}
                                    </p>
                                  ))}
                                </section>
                                {validation.end_to_end && (
                                  <LiveReplay trials={validation.end_to_end} />
                                )}
                                <button
                                  className="button button-dark"
                                  onClick={() => setTab("Review")}
                                >
                                  Review this candidate <ArrowRight size={16} />
                                </button>
                              </>
                            ) : (
                              <Notice>
                                No validation report exists for this candidate.{" "}
                                {source === "backend"
                                  ? "Run validation to evaluate safety and legitimate utility."
                                  : "A recorded sample cannot run new validation."}
                              </Notice>
                            )}
                          </>
                        )}
                      </>
                    )}
                  </>
                )}
                {tab === "Review" && (
                  <>
                    <div className="section-toolbar">
                      <div>
                        <h2>A recommendation. Your decision.</h2>
                        <p className="muted">
                          Approval binds a specific candidate and report. It does not deploy a
                          policy.
                        </p>
                      </div>
                    </div>
                    <section className="panel">
                      <label className="form-field">
                        Candidate to review
                        <select
                          value={selectedRepair}
                          onChange={(e) => {
                            setSelectedRepair(e.target.value);
                            setReviewed(false);
                          }}
                        >
                          {current.candidates.map((c, i) => (
                            <option value={c.candidate_id} key={c.candidate_id}>
                              Candidate {String.fromCharCode(65 + i)} — {label(c.status)}
                            </option>
                          ))}
                        </select>
                      </label>
                      {candidate && (
                        <>
                          <div className="panel-heading">
                            <h3>{candidate.request.expected_control_effect}</h3>
                            <Status value={alreadyApproved ? "APPROVED" : candidate.status} />
                          </div>
                          <dl className="metadata review-hashes">
                            <div>
                              <dt>Case ID</dt>
                              <dd>{current.case_id}</dd>
                            </div>
                            <div>
                              <dt>Candidate ID</dt>
                              <dd>{candidate.candidate_id}</dd>
                            </div>
                            <div>
                              <dt>Base policy SHA-256</dt>
                              <dd>{candidate.base_policy_sha256}</dd>
                            </div>
                            <div>
                              <dt>Patch SHA-256</dt>
                              <dd>{candidate.patch_sha256}</dd>
                            </div>
                            <div>
                              <dt>Validation report SHA-256</dt>
                              <dd>{validation?.report_sha256 || "No report available"}</dd>
                            </div>
                            <div>
                              <dt>Test manifest SHA-256</dt>
                              <dd>{validation?.manifest_sha256 || "No manifest available"}</dd>
                            </div>
                          </dl>
                          {source === "recorded" ? (
                            <Notice>
                              This is a recorded sample. Approval is disabled. Connect an authorized
                              reviewer session to review a server-backed case.
                            </Notice>
                          ) : alreadyApproved ? (
                            <div className="success-message">
                              <Check size={16} />
                              This exact recommendation is approved. No production policy was
                              changed.
                            </div>
                          ) : session?.scope !== "admin" ? (
                            <Notice>
                              Approval requires a reviewer credential. Connect with authorized
                              reviewer access to approve the exact result.
                            </Notice>
                          ) : candidate.status !== "AWAITING_REVIEW" ? (
                            <Notice>
                              This candidate is {label(candidate.status)}. Only a candidate that
                              passed the configured validation gate can be approved.
                            </Notice>
                          ) : !["AWAITING_REVIEW", "APPROVED"].includes(current.status) ? (
                            <Notice>
                              The case is {label(current.status)}. Complete validation for all
                              proposed candidates before review. A rejected alternative does not
                              prevent approval of a different candidate that passed.
                            </Notice>
                          ) : (
                            <label className="review-check">
                              <input
                                type="checkbox"
                                checked={reviewed}
                                onChange={(e) => setReviewed(e.target.checked)}
                              />
                              I reviewed the exact diff, test outcomes, limitations and hashes shown
                              above.
                            </label>
                          )}
                          <div className="button-row">
                            <button
                              className="button button-dark"
                              disabled={
                                loading ||
                                alreadyApproved ||
                                source === "recorded" ||
                                session?.scope !== "admin" ||
                                candidate.status !== "AWAITING_REVIEW" ||
                                !["AWAITING_REVIEW", "APPROVED"].includes(current.status) ||
                                !validation?.complete ||
                                validation.status !== "AWAITING_REVIEW" ||
                                !reviewed
                              }
                              onClick={() => void approve()}
                            >
                              <LockKeyhole size={16} />
                              Approve recommendation
                            </button>
                            <button
                              className="button button-outline"
                              disabled={loading}
                              onClick={() => void exportCase()}
                            >
                              <Download size={16} />
                              Download report
                            </button>
                          </div>
                        </>
                      )}
                    </section>
                    <section className="panel">
                      <h3>Review history</h3>
                      {current.approvals.length ? (
                        <pre>{pretty(current.approvals)}</pre>
                      ) : (
                        <p className="muted">No approval is recorded for this case.</p>
                      )}
                      <p className="fine-print">
                        A changed policy, patch or report requires a fresh review. Production apply
                        and rollback are outside this workspace.
                      </p>
                    </section>
                  </>
                )}
              </div>
            </>
          )}
        </main>
        <footer className="workspace-footer">
          <span>TraceVerdict · Built on IntentSeal</span>
          <span>Evidence → explanation → validation → human review</span>
        </footer>
      </div>
      {modal && (
        <Modal
          title={modal === "login" ? "Connect your workspace" : "New investigation"}
          onClose={() => setModal(null)}
        >
          {modal === "login" ? (
            <form onSubmit={(e) => void signIn(e)}>
              <p className="muted">
                Enter a scoped TraceVerdict access key from your workspace administrator. Reviewer
                and project access are separate.
              </p>
              <label className="form-field">
                Workspace access key
                <input
                  name="key"
                  type="password"
                  autoComplete="off"
                  required
                  placeholder="Enter your scoped access key"
                  autoFocus
                />
              </label>
              <p className="fine-print">
                Used to establish an HttpOnly session. The key is not saved in browser storage.
              </p>
              {error && <Notice error>{error}</Notice>}
              <button className="button button-dark full-width" disabled={loading}>
                {loading ? <LoaderCircle className="spin" size={16} /> : <LockKeyhole size={16} />}
                Connect workspace
              </button>
              <button
                type="button"
                className="text-link full-width"
                onClick={() => {
                  setModal(null);
                  setError("");
                }}
              >
                Continue exploring samples
              </button>
            </form>
          ) : (
            <form onSubmit={(e) => void createCase(e)}>
              <label className="form-field">
                Agent
                <select name="agent" required>
                  {agents.map((a) => (
                    <option key={a.agent_id}>{a.agent_id}</option>
                  ))}
                </select>
              </label>
              <label className="form-field">
                Execution mode
                <select name="mode" defaultValue="sample">
                  <option value="sample">Sample — deterministic synthetic fixture</option>
                  <option value="live">Live — configured provider services</option>
                </select>
              </label>
              <label className="form-field">
                Fixture (when no session IDs are provided)
                <select name="fixture">
                  {fixtures.map((f) => (
                    <option value={f.id} key={f.id}>
                      {f.short}
                    </option>
                  ))}
                </select>
              </label>
              <label className="form-field">
                Session IDs for live intake
                <input name="sessions" placeholder="Comma-separated authorized session IDs" />
              </label>
              <Notice>
                Sample uses the selected fixture. Live uses the fixture or provided authorized
                session IDs and requires configured evidence and reasoning services. Mode is
                immutable after creation.
              </Notice>
              {error && <Notice error>{error}</Notice>}
              <button
                className="button button-dark full-width"
                disabled={loading || !agents.length}
              >
                <Plus size={16} />
                Create investigation
              </button>
            </form>
          )}
        </Modal>
      )}
      {detail && (
        <Modal title="Evidence record" onClose={() => setDetail(null)} wide>
          <EvidenceBody evidence={detail} />
        </Modal>
      )}
    </div>
  );
}
