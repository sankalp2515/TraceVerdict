import type { CaseData, Graph } from "./types";
export function deriveGraph(data: CaseData): Graph {
  const order = ["task", "document", "policy", "tools", "action", "receipt", "reference"];
  const nodes = [
    ...Object.values(data.entities)
      .sort((a, b) => order.indexOf(a.kind) - order.indexOf(b.kind))
      .map((e) => ({
        id: e.evidence_id,
        type: e.kind,
        source_locator: e.source_locator,
        source_version: e.source_version,
        content_sha256: e.content_sha256,
      })),
    ...data.claims.map((c) => ({
      id: `claim:${c.claim_id}`,
      type: "claim",
      statement: c.statement,
      status: c.review_status,
    })),
  ];
  return {
    nodes,
    edges: data.relationships || [],
    limitations: ["Inferred links do not prove causal influence."],
  };
}
export function executionState(data: Pick<CaseData, "entities">) {
  const action = Object.values(data.entities).find((e) => e.kind === "action");
  if (!action) return { label: "Execution unknown", action: undefined, receipt: undefined };
  const receipt = Object.values(data.entities).find(
    (e) => e.kind === "receipt" && e.payload["event_id"] === action.payload["event_id"],
  );
  const withheld = /BLOCK|ESCALATE/i.test(String(action.payload["enforced"]));
  return {
    action,
    receipt,
    label:
      receipt?.payload["executed"] === true
        ? withheld
          ? "Contradiction"
          : "Application-reported executed"
        : withheld || receipt?.payload["executed"] === false
          ? "Withheld"
          : "Allowed but unconfirmed",
  };
}
