export type Evidence = {
  evidence_id: string;
  kind: string;
  source_locator: string;
  source_version: string;
  content_sha256: string;
  payload: Record<string, unknown>;
  query_receipt?: unknown;
};
export type Claim = {
  claim_id: string;
  statement: string;
  basis: string;
  review_status: string;
  support_evidence_ids: string[];
  competing_explanations: string[];
  missing_evidence: string[];
};
export type Outcome = {
  scenario_id: string;
  category: string;
  execution_mode: string;
  expected_behavior: string;
  observed_behavior: string;
  outcome: string;
  duration_ms: number;
  application_receipt?: unknown;
  policy_rule?: string;
};
export type Candidate = {
  candidate_id: string;
  status: string;
  origin?: string;
  base_policy_sha256: string;
  patch_sha256: string;
  diff: { path: string; before: unknown; after: unknown }[];
  request: { expected_control_effect: string; rationale_claim_ids: string[] };
};
export type Validation = {
  end_to_end?: { baseline: ReplayTrial[]; candidate: ReplayTrial[] };
  status: string;
  complete: boolean;
  baseline_reproduced: boolean;
  report_sha256: string;
  manifest_sha256: string;
  outcomes: Outcome[];
  baseline: Outcome[];
  limitations: string[];
};
export type GraphNode = {
  id: string;
  type: string;
  statement?: string;
  source_locator?: string;
  source_version?: string;
  content_sha256?: string;
  status?: string;
};
export type GraphEdge = {
  id: string;
  from: string;
  to: string;
  relation: string;
  basis: string;
  style: string;
  support_evidence_ids: string[];
};
export type Graph = { nodes: GraphNode[]; edges: GraphEdge[]; limitations: string[] };
export type CaseData = {
  model_calls?: unknown[];
  case_id: string;
  agent_id: string;
  fixture_id?: string;
  execution_mode: string;
  status: string;
  state_version: number;
  created_at: number;
  entities: Record<string, Evidence>;
  relationships: GraphEdge[];
  claims: Claim[];
  candidates: Candidate[];
  validations: Record<string, Validation>;
  approvals: {
    candidate_id: string;
    reviewer: string;
    at: number;
    applied: boolean;
    [key: string]: unknown;
  }[];
  missing_evidence: string[];
  uncertainty?: string[];
  errors: unknown[];
  base_policy_sha256: string;
  critique_history: { reason: string; disputed_claim_ids: string[] }[];
  jobs: Record<string, Job>;
  observations: { version: number; event: string; at: number }[];
};
export type Job = { job_id: string; status: string; kind?: string; error?: string };
export type ReplayTrial = {
  scenario_id: string;
  category: string;
  execution_mode: string;
  outcome: string;
  duration_ms?: number;
  actions: unknown[];
  model_calls: unknown[];
  error?: unknown;
  limitation?: string;
};
export type Session = {
  name: string;
  scope: string;
  org: string;
  csrf_token: string;
  expires_at: number;
};
export type CaseSummary = Pick<
  CaseData,
  "case_id" | "agent_id" | "status" | "execution_mode" | "created_at" | "fixture_id"
>;
export const fixtures = [
  {
    id: "supplier-contact",
    title: "The supplier report that asked for a send",
    short: "Supplier contact",
    description: "A research task becomes an unauthorized outbound action.",
  },
  {
    id: "invoice-forward",
    title: "An invoice with an unexpected instruction",
    short: "Invoice forwarding",
    description: "Trace an instruction to forward data outside the task.",
  },
  {
    id: "report-notify",
    title: "A notification the user never requested",
    short: "Report notification",
    description: "Separate a document instruction from authorized intent.",
  },
];
export const pretty = (value: unknown) => JSON.stringify(value, null, 2);
export const label = (value: string) =>
  value.toLowerCase().replaceAll("_", " ").replaceAll("-", " ");
