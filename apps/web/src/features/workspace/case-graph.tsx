import { useState } from "react";
import { FileText, List, Network, Search } from "lucide-react";
import type { Evidence, Graph, GraphNode } from "./types";
import { label, pretty } from "./types";

const names: Record<string, string> = {
  task: "Authorized task",
  document: "Untrusted document",
  action: "Attempted action",
  receipt: "Application receipt",
  policy: "Policy snapshot",
  tools: "Tool configuration",
  reference: "Trusted reference",
  claim: "Cited claim",
};
export function CaseGraph({
  graph,
  evidence,
  onEvidence,
}: {
  graph: Graph;
  evidence: Record<string, Evidence>;
  onEvidence: (id: string) => void;
}) {
  const [view, setView] = useState("graph");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const node = graph.nodes.find((n) => n.id === selected);
  const edge = graph.edges.find((e) => e.id === selected);
  const positions = new Map(
    graph.nodes.map((n, i) => [n.id, { x: 35 + (i % 3) * 265, y: 35 + Math.floor(i / 3) * 140 }]),
  );
  const rows = graph.nodes.filter((n) =>
    `${n.type} ${n.statement || ""} ${n.source_locator || ""} ${n.id}`
      .toLowerCase()
      .includes(query.toLowerCase()),
  );
  function selectNode(n: GraphNode) {
    setSelected(n.id);
  }
  return (
    <div className="evidence-workbench">
      <div className="panel-toolbar">
        <div className="segmented" aria-label="Evidence view">
          <button className={view === "graph" ? "active" : ""} onClick={() => setView("graph")}>
            <Network size={15} />
            Graph
          </button>
          <button className={view === "list" ? "active" : ""} onClick={() => setView("list")}>
            <List size={15} />
            Record index
          </button>
        </div>
        <span className="muted small">
          {graph.nodes.length} nodes · {graph.edges.length} relations
        </span>
      </div>
      {view === "graph" ? (
        <div className="graph-scroll">
          <svg
            className="case-graph"
            viewBox={`0 0 850 ${Math.ceil(graph.nodes.length / 3) * 140 + 25}`}
            role="group"
            aria-label="Evidence relationships. Select a node or relation, or use the record index."
          >
            <defs>
              <marker
                id="graph-arrow"
                markerWidth="7"
                markerHeight="7"
                refX="6"
                refY="3"
                orient="auto"
              >
                <path d="M0,0 L0,6 L6,3 z" fill="currentColor" />
              </marker>
            </defs>
            {graph.edges.map((e) => {
              const a = positions.get(e.from);
              const b = positions.get(e.to);
              if (!a || !b) return null;
              const x1 = a.x + 105,
                y1 = a.y + 38,
                x2 = b.x + 105,
                y2 = b.y + 38;
              return (
                <g
                  key={e.id}
                  className={`graph-edge ${e.basis === "observed" ? "observed" : "inferred"} ${selected === e.id ? "selected" : ""}`}
                  role="button"
                  tabIndex={0}
                  aria-label={`${label(e.relation)}, ${label(e.basis)}: ${names[graph.nodes.find((n) => n.id === e.from)?.type || ""] || e.from} to ${names[graph.nodes.find((n) => n.id === e.to)?.type || ""] || e.to}`}
                  onClick={() => setSelected(e.id)}
                  onKeyDown={(ev) => {
                    if (ev.key === "Enter" || ev.key === " ") {
                      ev.preventDefault();
                      setSelected(e.id);
                    }
                  }}
                >
                  <path
                    d={`M${x1},${y1} C${x1},${(y1 + y2) / 2 + 30} ${x2},${(y1 + y2) / 2 + 30} ${x2},${y2}`}
                    fill="none"
                    strokeWidth="16"
                    stroke="transparent"
                  />
                  <path
                    d={`M${x1},${y1} C${x1},${(y1 + y2) / 2 + 30} ${x2},${(y1 + y2) / 2 + 30} ${x2},${y2}`}
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={selected === e.id ? 3 : 1.5}
                    strokeDasharray={e.basis === "observed" ? undefined : "5 5"}
                    markerEnd="url(#graph-arrow)"
                  />
                  <title>
                    {label(e.relation)} · {label(e.basis)}
                  </title>
                </g>
              );
            })}
            {graph.nodes.map((n) => {
              const p = positions.get(n.id)!;
              return (
                <g
                  key={n.id}
                  transform={`translate(${p.x},${p.y})`}
                  className={`graph-node ${selected === n.id ? "selected" : ""}`}
                  tabIndex={0}
                  role="button"
                  aria-label={`${names[n.type] || n.type}: ${n.statement || n.source_locator || n.id}`}
                  onClick={() => selectNode(n)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      selectNode(n);
                    }
                  }}
                >
                  <rect width="215" height="76" rx="5" />
                  <rect className={`node-band band-${n.type}`} width="4" height="76" rx="2" />
                  <text x="18" y="29" className="node-title">
                    {names[n.type] || n.type}
                  </text>
                  <text x="18" y="52" className="node-caption">
                    {n.type === "claim"
                      ? label(n.status || "proposed")
                      : `Source version ${n.source_version || "unknown"}`}
                  </text>
                  <circle cx="194" cy="24" r="3" />
                </g>
              );
            })}
          </svg>
        </div>
      ) : (
        <div className="record-index">
          <label className="search-field">
            <Search size={16} />
            <input
              placeholder="Search evidence and claims…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Search evidence and claims"
            />
          </label>
          {rows.map((n) => (
            <button
              className={`record-row ${selected === n.id ? "active" : ""}`}
              key={n.id}
              onClick={() => selectNode(n)}
            >
              <FileText size={18} />
              <span>
                <strong>{names[n.type] || n.type}</strong>
                <small>{n.statement || n.source_locator}</small>
              </span>
              <span className="mono small">
                {n.source_version ? `v${n.source_version}` : label(n.status || "")}
              </span>
            </button>
          ))}
          {!rows.length && (
            <p className="empty-state">No records match. Try a source type or claim keyword.</p>
          )}
          <h4 className="index-heading">Relationships</h4>
          {graph.edges.map((e) => (
            <button key={e.id} className="record-row" onClick={() => setSelected(e.id)}>
              <Network size={17} />
              <span>
                <strong>{label(e.relation)}</strong>
                <small>
                  {label(e.basis)} · {e.support_evidence_ids.length} source records
                </small>
              </span>
            </button>
          ))}
        </div>
      )}
      <div className="graph-legend">
        <span>
          <i className="solid-line" />
          Observed relation
        </span>
        <span>
          <i className="dashed-line" />
          Inference or case context
        </span>
        <span>Relations do not establish causation.</span>
      </div>
      <div className="graph-detail" aria-live="polite">
        {node ? (
          <>
            <div className="panel-heading">
              <div>
                <span className="section-label">Selected record</span>
                <h3>{names[node.type] || node.type}</h3>
              </div>
              {node.type !== "claim" && (
                <button
                  className="button button-outline button-small"
                  onClick={() => onEvidence(node.id)}
                >
                  Open source
                </button>
              )}
            </div>
            {node.statement && <p>{node.statement}</p>}
            <dl className="metadata">
              <div>
                <dt>Record ID</dt>
                <dd>{node.id}</dd>
              </div>
              <div>
                <dt>Source</dt>
                <dd>{node.source_locator || "Investigation claim"}</dd>
              </div>
              {node.content_sha256 && (
                <div>
                  <dt>Content SHA-256</dt>
                  <dd>{node.content_sha256}</dd>
                </div>
              )}
            </dl>
            {evidence[node.id] && <pre>{pretty(evidence[node.id]?.payload)}</pre>}
          </>
        ) : edge ? (
          <>
            <span className="section-label">Selected relationship</span>
            <h3>{label(edge.relation)}</h3>
            <p>
              Basis: <strong>{label(edge.basis)}</strong>.{" "}
              {edge.basis === "observed"
                ? "An observed record supports this relation."
                : "This relation does not establish causal influence or historical enforcement."}
            </p>
            <dl className="metadata">
              <div>
                <dt>From</dt>
                <dd>{edge.from}</dd>
              </div>
              <div>
                <dt>To</dt>
                <dd>{edge.to}</dd>
              </div>
            </dl>
            <div className="button-row">
              {edge.support_evidence_ids.map((id) => (
                <button className="source-link" key={id} onClick={() => onEvidence(id)}>
                  {evidence[id]?.kind || id} <FileText size={12} />
                </button>
              ))}
            </div>
          </>
        ) : (
          <p className="muted">
            Select a record or relationship to inspect its source, basis and supporting evidence.
          </p>
        )}
      </div>
    </div>
  );
}
