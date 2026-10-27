import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { deriveGraph, executionState } from "@/features/workspace/data";
import type { CaseData, Evidence } from "@/features/workspace/types";

const recorded = JSON.parse(
  readFileSync("public/samples/supplier-contact-world.json", "utf8"),
) as CaseData;
function incident(enforced: string, executed?: boolean, linked = true) {
  const fields = {
    evidence_id: "qa",
    source_locator: "qa:record",
    source_version: "1",
    content_sha256: "qa",
  };
  const action = {
    ...fields,
    kind: "action",
    payload: { event_id: "action-1", enforced },
  } as Evidence;
  const receipt = {
    ...fields,
    kind: "receipt",
    payload: { event_id: linked ? "action-1" : "other-action", executed },
  } as Evidence;
  return { entities: executed === undefined ? { action } : { action, receipt } };
}
describe("Execution truth boundaries", () => {
  it("never presents an allowed attempt as confirmed execution", () =>
    expect(executionState(incident("ALLOW")).label).toBe("Allowed but unconfirmed"));
  it("recognizes a withheld action without a receipt", () =>
    expect(executionState(incident("BLOCK")).label).toBe("Withheld"));
  it("does not attach an unrelated execution receipt", () =>
    expect(executionState(incident("ALLOW", true, false)).label).toBe("Allowed but unconfirmed"));
  it("shows contradiction when a blocked action is reported executed", () =>
    expect(executionState(incident("BLOCK", true)).label).toBe("Contradiction"));
  it("treats an application nonexecution receipt as withheld", () =>
    expect(executionState(incident("ALLOW", false)).label).toBe("Withheld"));
  it("preserves the recorded executed incident", () =>
    expect(executionState(recorded).label).toBe("Application-reported executed"));
});
describe("Recorded evidence integrity", () => {
  it("resolves every graph endpoint and claim citation to an actual record", () => {
    const graph = deriveGraph(recorded);
    const ids = new Set(graph.nodes.map((n) => n.id));
    for (const edge of graph.edges) {
      expect(ids.has(edge.from)).toBe(true);
      expect(ids.has(edge.to)).toBe(true);
      for (const id of edge.support_evidence_ids) expect(recorded.entities[id]).toBeDefined();
    }
    for (const claim of recorded.claims)
      for (const id of claim.support_evidence_ids) expect(recorded.entities[id]).toBeDefined();
  });
  it("keeps rejected utility-breaking repairs separate from passing candidates", () => {
    const broad = recorded.candidates.find((c) =>
      c.diff.some((d) => d.path.includes("allowed_recipients")),
    )!;
    const targeted = recorded.candidates.find((c) =>
      c.diff.some((d) => d.path === "contract.mode"),
    )!;
    expect(broad.status).toBe("REJECTED");
    expect(
      recorded.validations[broad.candidate_id]!.outcomes.some(
        (o) => o.category === "utility" && o.outcome === "fail",
      ),
    ).toBe(true);
    expect(targeted.status).toBe("AWAITING_REVIEW");
    expect(recorded.validations[targeted.candidate_id]!.outcomes).toHaveLength(20);
    expect(
      recorded.validations[targeted.candidate_id]!.outcomes.every((o) => o.outcome === "pass"),
    ).toBe(true);
    expect(recorded.approvals).toHaveLength(0);
  });
});
