// Typed client for the Gateway API. Uses the public read-only key (never an admin key in the browser).

export const API_BASE: string = (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://localhost:8000";
const API_KEY: string = (import.meta.env.VITE_API_KEY as string | undefined) ?? "";
export const PRODUCT_NAME: string = (import.meta.env.VITE_PRODUCT_NAME as string | undefined) ?? "[Product Name]";

export type Decision = "ALLOW" | "NEUTRALISE" | "BLOCK" | "ESCALATE";

export interface Scenario {
  id: string;
  title: string;
  attack_types?: string[];
  channel?: string;
  task?: string;
  expected?: Record<string, string>;
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
  answer: string;
  error: string | null;
  model: string | null;
  steps: Step[];
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

export interface RateRow {
  n: number;
  scored: number;
  errors: number;
  compromised: number;
  asr: number | null;
}

export interface Report {
  file: string;
  name: string;
  protection: "on" | "off";
  date: string;
  git_sha: string | null;
  agent_role: string;
  suite: string;
  overall: RateRow;
  by_category: Record<string, RateRow>;
  by_channel: Record<string, RateRow>;
  benign: { success_rate: number; n: number; errors: number } | null;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(API_KEY ? { Authorization: `Bearer ${API_KEY}` } : {}), ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError(0, "Backend unreachable");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
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
  scorecard: (agent: string) => call<{ agent: string; reports: Record<string, Report> }>(`/v1/scorecard/${agent}`),
};
