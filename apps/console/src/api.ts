// Typed client for the IntentSeal Gateway API. Uses the public read-only key (never an admin key in the browser).

export const API_BASE: string = (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://localhost:8000";
const API_KEY: string = (import.meta.env.VITE_API_KEY as string | undefined) ?? "";
export const PRODUCT_NAME: string = (import.meta.env.VITE_PRODUCT_NAME as string | undefined) ?? "IntentSeal";
export const TAGLINE = "Keep AI agents inside the user’s intent.";
export const AGENT = "research-agent";

export type Decision = "ALLOW" | "NEUTRALISE" | "BLOCK" | "ESCALATE";

export interface Scenario {
  id: string;
  title: string;
  attack_types?: string[];
  channel?: string;
  task?: string;
  expected?: Record<string, string>;
  surface?: "proxy";
  source?: string;
}

export interface Step {
  tool: string;
  args: Record<string, unknown>;
  allowed: boolean;
  notice: string | null;
}

export interface FindingRow {
  span_start: number | null;
  span_end: number | null;
  span_preview: string;
  origin: string;
  signal: string;
  labels: string[];
  score: number;
  tier: number;
}

export interface EventRow {
  id: string;
  seq: number;
  kind: string;
  source: string;
  preview: string;
  created_at: number;
  decision: Decision | null;
  enforced: Decision | null;
  policy_rule: string | null;
  reason: string | null;
  labels: string[];
  tier: number | null;
  latency_ms: number | null;
  degraded: number | null;
  session_risk: number | null;
  findings: FindingRow[];
  action: { tool: string; args_redacted: string; final_args_redacted: string | null; pinned_overrides: string | null } | null;
}

export interface DemoResult {
  scenario_id: string;
  protection: "on" | "off";
  surface?: "proxy";
  agent_id?: string;
  answer: string;
  error: string | null;
  model?: string | null;
  steps?: Step[];
  outbox: Record<string, string>[];
  canary_leaked: boolean;
  external_sends: number;
  session_id: string | null;
  events: EventRow[];
}

export interface DecisionRow {
  event_id: string;
  agent_id: string;
  session_id: string;
  decision: Decision;
  enforced: Decision;
  policy_rule: string;
  reason: string;
  labels: string[];
  tier: number;
  latency_ms: number;
  degraded: number;
  created_at: number;
  source: string;
  kind: string;
  preview: string;
}

export interface Rate { n: number; detected?: number; recall: number | null }
export interface AsrRow { n: number; scored: number; compromised: number; asr: number | null }
export interface Fpr {
  n: number; held: number; false_alarms: number; fpr: number | null; disruptive: number; fpr_disruptive: number | null;
  escalation_rate: number | null; alarms: string[];
}
export interface Overhead {
  runs: number; agent_tokens: number; security_tokens: number; token_ratio: number | null;
  agent_usd: number; security_usd: number; cost_ratio: number | null;
}
export interface E2E {
  suite: string; models: string[]; off: AsrRow; on: AsrRow; relative_reduction: number | null; canary_leaks_on: number;
  caught: { n: number; caught: number; recall: number | null };
  overhead?: Overhead | null;
}
export interface CostRow {
  role: string; provider: string; model: string; calls: number; cached: number | null; input_tokens: number | null;
  output_tokens: number | null; est_cost_usd: number | null; avg_latency_ms: number | null; errors?: number | null;
}
export interface Costs {
  days: number; by_model: CostRow[];
  overhead: { security_tokens: number; agent_tokens: number; token_ratio: number | null; cost_ratio: number | null; unpriced_models: string[] };
}
export interface Summary {
  kind: "summary";
  file: string;
  date: string;
  git_sha: string | null;
  corpus_version: string;
  settings: { engine_versions: Record<string, Record<string, number>> };
  content_detection: {
    scored: number; held: number; recall: number | null; raw_recall_incl_not_delivered: number | null;
    not_delivered: Record<string, { n: number; detected: number; reason: string }>;
    by_type: Record<string, Rate>; by_channel: Record<string, Rate>;
    matrix: Record<string, Record<string, number | null>>; matrix_n: Record<string, Record<string, number>>;
  };
  fpr: { dev: Fpr | null; holdout: Fpr | null; all_channel_stress: { dev: Fpr | null; holdout: Fpr | null } };
  latency_isolated: { n: number; p50_ms: number; p95_ms: number; note: string } | null;
  e2e: E2E[];
  utility: { off: number; on: number; n: number; retention: number | null } | null;
  claim: {
    F: string; D: string; types_meeting: number; fpr_used: number | null; rule: string;
    types: { type: string; checkpoint: string; n: number; recall: number | null; status: string }[];
    text_channels: Record<string, boolean>; rich_channels: Record<string, boolean>;
  };
}

export interface Approval {
  event_id: string; session_id: string; agent_id: string; tool: string; reason: string; status: string;
  reviewer: string | null; note: string | null; created_at: number; resolved_at: number | null; used_at: number | null;
  args_redacted: string | null; policy_rule: string | null; labels: string[];
}

export interface MemoryEntry {
  id: string; kind: "attack" | "benign"; agent_id: string; labels: string[]; n: number; origin: string; note: string; created_at: number;
}

export interface ToolPolicy {
  risk: string; failure: string; pinned: string[]; allowed_recipients: string[]; allowed_domains: string[];
  escalate_if_uncertain: boolean;
}
export interface Policy {
  agent: string; mode: string; version: string; task_scope: string; unknown_tools: string; decision_model: string;
  tools: Record<string, ToolPolicy>;
  thresholds: { neutralise: number; block: number; escalate_band: [number, number]; judge_untrusted: string };
  session: { risk_decay_per_turn: number; block_at: number; escalate_at: number };
  sensitive_data: { patterns: string[]; drop_non_visible: boolean };
  budgets: { daily_tokens_tier2: number | null };
}

export interface Metrics {
  window_hours: number; decisions: number; by_decision: Record<string, number>; by_rule: Record<string, number>;
  by_label: Record<string, number>;
  inspections: { n: number; escalated_to_judge: number; escalation_rate: number | null; degraded: number };
  latency_ms: {
    fast_path: { n: number; p50: number | null; p95: number | null };
    judge_path: { n: number; p50: number | null; p95: number | null };
  };
  memory: Record<string, number>;
  approvals_pending: number;
  providers: { provider: string; status: string; n: number }[];
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function call<T>(path: string, init?: RequestInit, key: string = API_KEY): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(key ? { Authorization: `Bearer ${key}` } : {}), ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError(0, "Backend unreachable");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      /* not JSON */
    }
    throw new ApiError(res.status, String(detail));
  }
  return (await res.json()) as T;
}

export const api = {
  health: () => call<{ ok: boolean; uptime_s: number }>("/healthz"),
  scenarios: () => call<Scenario[]>("/demo/scenarios"),
  run: (scenario_id: string, protection: "on" | "off") =>
    call<DemoResult>("/demo/run", { method: "POST", body: JSON.stringify({ scenario_id, protection }) }),
  events: (sessionId: string) => call<EventRow[]>(`/v1/sessions/${encodeURIComponent(sessionId)}/events`),
  decisions: (params: Record<string, string>) => {
    const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== ""));
    return call<DecisionRow[]>(`/v1/decisions?${q.toString()}`);
  },
  scorecard: (agent: string) =>
    call<{ agent: string; summary: Summary | null; reports: Record<string, unknown> }>(`/v1/scorecard/${agent}`),
  approvals: (status = "pending") => call<Approval[]>(`/v1/approvals?status=${status}`),
  memory: () => call<{ stats: Record<string, number>; entries: MemoryEntry[] }>("/v1/memory"),
  policy: (agent: string) => call<Policy>(`/v1/policies/${encodeURIComponent(agent)}`),
  metrics: (hours = 24) => call<Metrics>(`/v1/metrics?hours=${hours}`),
  costs: (days = 7) => call<Costs>(`/v1/costs?days=${days}`),
  whoami: (key: string) => call<{ name: string; scope: string }>("/v1/whoami", undefined, key),
};

/** Reviewer (admin-key) actions. The key is the reviewer's own, typed at sign-in; it is never part of the build. */
export const admin = {
  resolve: (key: string, eventId: string, approve: boolean, note = "") =>
    call<{ status: string }>(`/v1/approvals/${encodeURIComponent(eventId)}`, { method: "POST", body: JSON.stringify({ approve, note }) }, key),
  feedback: (key: string, verdict: "attack" | "false_positive", eventId: string, labels: string[] = [], note = "") =>
    call<{ memory_id: string }>("/v1/feedback", { method: "POST", body: JSON.stringify({ verdict, event_id: eventId, labels, note }) }, key),
  forget: (key: string, memoryId: string) =>
    call<{ removed: boolean }>(`/v1/memory/${encodeURIComponent(memoryId)}`, { method: "DELETE" }, key),
  putPolicy: (key: string, agent: string, body: unknown) =>
    call<{ version: string; mode: string }>(`/v1/policies/${encodeURIComponent(agent)}`, { method: "PUT", body: JSON.stringify(body) }, key),
};
