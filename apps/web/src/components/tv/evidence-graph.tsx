import { useState } from "react";
import { cn } from "@/lib/utils";
import { Chip, type ChipTone } from "./primitives";
import { nodeIconPaths, type NodeIconKey } from "./icons";

/**
 * The evidence graph is the primary interaction of the product.
 * Line style carries meaning and is always paired with text:
 * solid = an observed record links the two ends,
 * dashed ink = case context, related but not causal,
 * dashed amber = inferred — a hypothesis, never shown as established causation.
 */

type NodeKey = "task" | "document" | "action" | "policy" | "receipt" | "claim";

interface GraphNode {
  key: NodeKey;
  icon: NodeIconKey;
  x: number;
  y: number;
  title: string;
  statusLabel: string;
  statusTone: ChipTone;
  kind: string;
  rows: { label: string; value: string }[];
  note: string;
}

interface GraphEdge {
  id: string;
  from: NodeKey;
  to: NodeKey;
  label: string;
  style: "solid" | "dashed-context" | "dashed-inferred";
  basis: string;
  records: string[];
}

const NODE_W = 184;
const NODE_H = 56;

const NODES: GraphNode[] = [
  {
    key: "task",
    icon: "task",
    x: 120,
    y: 96,
    title: "Summarize report",
    statusLabel: "Authorized",
    statusTone: "neutral",
    kind: "Authorized task",
    rows: [
      { label: "origin", value: "user prompt · session 8f31" },
      { label: "locator", value: "prompt#1" },
    ],
    note: "What the user actually asked for. The fixed point every other record is read against.",
  },
  {
    key: "document",
    icon: "document",
    x: 330,
    y: 64,
    title: "supplier_report.pdf",
    statusLabel: "Untrusted",
    statusTone: "uncertain",
    kind: "Untrusted document",
    rows: [
      { label: "content_sha256", value: "c41d…9e07" },
      { label: "source_version", value: "v2 · agent inbox" },
    ],
    note: "Read in full, never trusted. Its embedded instruction is evidence of the attack — not a command.",
  },
  {
    key: "action",
    icon: "action",
    x: 540,
    y: 150,
    title: "send.summary → ext.",
    statusLabel: "Withheld",
    statusTone: "verified",
    kind: "Attempted action",
    rows: [
      { label: "tool", value: "smtp.send" },
      { label: "arguments", value: "rendered as escaped text" },
      { label: "guard decision", value: "BLOCK · intent contract" },
    ],
    note: "What the agent attempted — distinct from what the application reports executing.",
  },
  {
    key: "policy",
    icon: "policy",
    x: 330,
    y: 396,
    title: "Intent contract v3",
    statusLabel: "Snapshot",
    statusTone: "neutral",
    kind: "Policy snapshot",
    rows: [
      { label: "base_policy_sha256", value: "9f2c…e41a" },
      { label: "captured", value: "at case intake · immutable" },
    ],
    note: "The version captured at intake. Its presence in the case does not prove it governed every historical action — source versions stay visible.",
  },
  {
    key: "receipt",
    icon: "receipt",
    x: 688,
    y: 64,
    title: "No execution",
    statusLabel: "App-reported",
    statusTone: "reported",
    kind: "Application receipt",
    rows: [
      { label: "receipt_id", value: "rcp#5" },
      { label: "reported_by", value: "application — not attested" },
    ],
    note: "The application's own account of what ran. A report, not independent attestation.",
  },
  {
    key: "claim",
    icon: "claim",
    x: 688,
    y: 396,
    title: "Send was withheld",
    statusLabel: "Supported",
    statusTone: "verified",
    kind: "Verdict claim",
    rows: [
      { label: "written_by", value: "investigator" },
      { label: "critique_rounds", value: "2 · unresolved: 0" },
    ],
    note: "Written by the investigator, challenged by the critic — and only as strong as the evidence it cites.",
  },
];

const EDGES: GraphEdge[] = [
  {
    id: "e-task-doc",
    from: "task",
    to: "document",
    label: "case_context",
    style: "dashed-context",
    basis: "Case context link — the task frames the document, it does not cause it.",
    records: ["case_ctx#7"],
  },
  {
    id: "e-doc-action",
    from: "document",
    to: "action",
    label: "supports",
    style: "solid",
    basis: "Observed support — the untrusted instruction is the proximate cause recorded for the attempt.",
    records: ["ev_doc#3", "ev_act#11"],
  },
  {
    id: "e-policy-action",
    from: "policy",
    to: "action",
    label: "supports",
    style: "solid",
    basis: "Observed support — the guard decision cites this policy snapshot.",
    records: ["ev_pol#2"],
  },
  {
    id: "e-receipt-action",
    from: "receipt",
    to: "action",
    label: "application_reports",
    style: "solid",
    basis: "Observed record — the application reports no execution for this action.",
    records: ["ev_rcp#5"],
  },
  {
    id: "e-receipt-claim",
    from: "receipt",
    to: "claim",
    label: "supports",
    style: "solid",
    basis: "Observed support — the claim rests on this recorded receipt.",
    records: ["ev_rcp#5"],
  },
  {
    id: "e-policy-claim",
    from: "policy",
    to: "claim",
    label: "inferred · caused_by",
    style: "dashed-inferred",
    basis: "Inferred relation — plausible, but never displayed as established causation.",
    records: [],
  },
];

const nodeByKey = new Map(NODES.map((n) => [n.key, n]));

type Selection = { kind: "node"; key: NodeKey } | { kind: "edge"; id: string };

function edgePath(e: GraphEdge) {
  const a = nodeByKey.get(e.from)!;
  const b = nodeByKey.get(e.to)!;
  return `M ${a.x} ${a.y} L ${b.x} ${b.y}`;
}

function edgeMid(e: GraphEdge) {
  const a = nodeByKey.get(e.from)!;
  const b = nodeByKey.get(e.to)!;
  return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
}

function edgeStroke(e: GraphEdge, selected: boolean) {
  if (selected)
    return {
      stroke: "var(--color-foreground)",
      opacity: 1,
      width: 2.25,
      dash: e.style === "solid" ? undefined : "4 6",
    };
  switch (e.style) {
    case "solid":
      return {
        stroke: "var(--color-foreground)",
        opacity: 0.55,
        width: 1.5,
        dash: undefined,
      };
    case "dashed-context":
      return {
        stroke: "var(--color-muted-foreground)",
        opacity: 0.85,
        width: 1.25,
        dash: "4 6",
      };
    case "dashed-inferred":
      return {
        stroke: "var(--color-uncertain)",
        opacity: 0.9,
        width: 1.5,
        dash: "4 6",
      };
  }
}

function edgeMarker(e: GraphEdge) {
  switch (e.style) {
    case "solid":
      return "url(#tv-arrow-ink)";
    case "dashed-context":
      return "url(#tv-arrow-muted)";
    case "dashed-inferred":
      return "url(#tv-arrow-amber)";
  }
}

function Legend() {
  const items = [
    {
      line: (
        <svg width="34" height="10" aria-hidden="true">
          <line
            x1="1"
            y1="5"
            x2="33"
            y2="5"
            stroke="var(--color-foreground)"
            strokeOpacity="0.55"
            strokeWidth="1.75"
          />
        </svg>
      ),
      title: "Observed",
      text: "an actual record links the two ends",
    },
    {
      line: (
        <svg width="34" height="10" aria-hidden="true">
          <line
            x1="1"
            y1="5"
            x2="33"
            y2="5"
            stroke="var(--color-muted-foreground)"
            strokeWidth="1.5"
            strokeDasharray="4 4"
          />
        </svg>
      ),
      title: "Context",
      text: "related, not causal",
    },
    {
      line: (
        <svg width="34" height="10" aria-hidden="true">
          <line
            x1="1"
            y1="5"
            x2="33"
            y2="5"
            stroke="var(--color-uncertain)"
            strokeWidth="1.75"
            strokeDasharray="4 4"
          />
        </svg>
      ),
      title: "Inferred",
      text: "a hypothesis — never established causation",
    },
  ];
  return (
    <ul className="flex flex-wrap gap-x-8 gap-y-3">
      {items.map((it) => (
        <li key={it.title} className="flex items-center gap-2.5">
          {it.line}
          <span className="text-sm">
            <span className="font-medium text-foreground">{it.title}</span>{" "}
            <span className="text-muted-foreground">— {it.text}</span>
          </span>
        </li>
      ))}
    </ul>
  );
}

export function EvidenceGraph() {
  const [sel, setSel] = useState<Selection>({ kind: "node", key: "action" });

  const selectedNode = sel.kind === "node" ? nodeByKey.get(sel.key)! : null;
  const selectedEdge = sel.kind === "edge" ? EDGES.find((e) => e.id === sel.id)! : null;

  const select = (s: Selection) => setSel(s);

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
      <div>
        {/* The graph itself: horizontal scroll keeps it legible on small screens */}
        <div className="overflow-x-auto rounded-lg border border-border bg-card">
          <div className="min-w-[720px]">
            <svg
              viewBox="0 0 800 460"
              className="block h-auto w-full"
              role="group"
              aria-label="Evidence graph: six nodes with observed, context and inferred relations"
            >
              <defs>
                <marker
                  id="tv-arrow-ink"
                  viewBox="0 0 10 10"
                  refX="9"
                  refY="5"
                  markerWidth="7"
                  markerHeight="7"
                  orient="auto-start-reverse"
                >
                  <path d="M0 0 L10 5 L0 10 z" fill="var(--color-foreground)" />
                </marker>
                <marker
                  id="tv-arrow-muted"
                  viewBox="0 0 10 10"
                  refX="9"
                  refY="5"
                  markerWidth="7"
                  markerHeight="7"
                  orient="auto-start-reverse"
                >
                  <path
                    d="M0 0 L10 5 L0 10 z"
                    fill="var(--color-muted-foreground)"
                  />
                </marker>
                <marker
                  id="tv-arrow-amber"
                  viewBox="0 0 10 10"
                  refX="9"
                  refY="5"
                  markerWidth="7"
                  markerHeight="7"
                  orient="auto-start-reverse"
                >
                  <path d="M0 0 L10 5 L0 10 z" fill="var(--color-uncertain)" />
                </marker>
              </defs>

              {/* Edges first: nodes are drawn on top so lines terminate at the cards */}
              {EDGES.map((e) => {
                const s = edgeStroke(e, sel.kind === "edge" && sel.id === e.id);
                const mid = edgeMid(e);
                const isSel = sel.kind === "edge" && sel.id === e.id;
                return (
                  <g key={e.id}>
                    <path
                      d={edgePath(e)}
                      fill="none"
                      stroke={s.stroke}
                      strokeOpacity={s.opacity}
                      strokeWidth={s.width}
                      strokeDasharray={s.dash}
                      markerEnd={edgeMarker(e)}
                      className={cn(
                        e.style === "dashed-inferred" && "tv-dash",
                        !isSel && "transition-[stroke,stroke-width] duration-200",
                      )}
                    />
                    {/* invisible wide hit area */}
                    <path
                      d={edgePath(e)}
                      fill="none"
                      stroke="transparent"
                      strokeWidth={18}
                      className="cursor-pointer"
                      tabIndex={0}
                      role="button"
                      aria-label={`Relation ${e.label}: ${nodeByKey.get(e.from)!.title} to ${nodeByKey.get(e.to)!.title}`}
                      onClick={() => select({ kind: "edge", id: e.id })}
                      onKeyDown={(ev) => {
                        if (ev.key === "Enter" || ev.key === " ") {
                          ev.preventDefault();
                          select({ kind: "edge", id: e.id });
                        }
                      }}
                    />
                    <g
                      className="cursor-pointer"
                      onClick={() => select({ kind: "edge", id: e.id })}
                    >
                      <rect
                        x={mid.x - e.label.length * 3.4 - 7}
                        y={mid.y - 9}
                        width={e.label.length * 6.8 + 14}
                        height={18}
                        rx={4}
                        fill="var(--color-card)"
                        stroke="var(--color-border)"
                      />
                      <text
                        x={mid.x}
                        y={mid.y + 4}
                        textAnchor="middle"
                        fontSize="10.5"
                        fontFamily="var(--font-mono)"
                        fill="var(--color-muted-foreground)"
                        style={{ pointerEvents: "none" }}
                      >
                        {e.label}
                      </text>
                    </g>
                  </g>
                );
              })}

              {/* Nodes */}
              {NODES.map((n) => {
                const isSel = sel.kind === "node" && sel.key === n.key;
                const left = n.x - NODE_W / 2;
                const top = n.y - NODE_H / 2;
                return (
                  <g
                    key={n.key}
                    className="cursor-pointer"
                    tabIndex={0}
                    role="button"
                    aria-label={`${n.kind}: ${n.title} — ${n.statusLabel}`}
                    onClick={() => select({ kind: "node", key: n.key })}
                    onKeyDown={(ev) => {
                      if (ev.key === "Enter" || ev.key === " ") {
                        ev.preventDefault();
                        select({ kind: "node", key: n.key });
                      }
                    }}
                  >
                    <rect
                      x={left}
                      y={top}
                      width={NODE_W}
                      height={NODE_H}
                      rx={10}
                      fill={isSel ? "var(--color-accent)" : "var(--color-card)"}
                      stroke={isSel ? "var(--color-foreground)" : "var(--color-border)"}
                      strokeWidth={isSel ? 1.75 : 1}
                    />
                    <g
                      transform={`translate(${left + 14}, ${top + 16})`}
                      color="var(--color-foreground)"
                    >
                      {nodeIconPaths(n.icon, 1.6)}
                    </g>
                    <text
                      x={left + 46}
                      y={top + 24}
                      fontSize="12.5"
                      fontWeight="600"
                      fontFamily="var(--font-sans)"
                      fill="var(--color-foreground)"
                      style={{ pointerEvents: "none" }}
                    >
                      {n.title}
                    </text>
                    <circle
                      cx={left + 50}
                      cy={top + 39}
                      r="3"
                      fill={`var(--color-${n.statusTone === "neutral" ? "muted-foreground" : n.statusTone})`}
                      style={{ pointerEvents: "none" }}
                    />
                    <text
                      x={left + 60}
                      y={top + 43}
                      fontSize="9.5"
                      letterSpacing="0.08em"
                      fontFamily="var(--font-mono)"
                      fill="var(--color-muted-foreground)"
                      style={{ pointerEvents: "none" }}
                    >
                      {n.statusLabel.toUpperCase()}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>
        </div>

        <div className="mt-5 border-t border-border pt-5">
          <Legend />
          <p className="mt-3 font-display text-lg text-muted-foreground italic">
            “Never display an inferred edge as established causation.”
          </p>
        </div>
      </div>

      {/* Detail drawer + synchronized record index */}
      <div className="flex flex-col gap-4">
        <div className="rounded-lg border border-border bg-card p-5" aria-live="polite">
          {selectedNode && (
            <div>
              <p className="font-mono text-[11px] tracking-[0.16em] text-muted-foreground uppercase">
                {selectedNode.kind}
              </p>
              <h3 className="mt-1.5 font-display text-xl font-semibold text-foreground">
                {selectedNode.title}
              </h3>
              <div className="mt-2.5">
                <Chip tone={selectedNode.statusTone} dot>
                  {selectedNode.statusLabel}
                </Chip>
              </div>
              <dl className="mt-4 space-y-2 border-t border-border pt-4">
                {selectedNode.rows.map((r) => (
                  <div key={r.label} className="flex justify-between gap-4 text-xs">
                    <dt className="font-mono text-muted-foreground">{r.label}</dt>
                    <dd className="text-right font-mono text-foreground">
                      {r.value}
                    </dd>
                  </div>
                ))}
              </dl>
              <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
                {selectedNode.note}
              </p>
            </div>
          )}
          {selectedEdge && (
            <div>
              <p className="font-mono text-[11px] tracking-[0.16em] text-muted-foreground uppercase">
                Relation
              </p>
              <h3 className="mt-1.5 font-mono text-base font-medium text-foreground">
                {selectedEdge.label}
              </h3>
              <p className="mt-1.5 text-sm text-muted-foreground">
                {nodeByKey.get(selectedEdge.from)!.title}
                <span className="mx-1.5 text-foreground">→</span>
                {nodeByKey.get(selectedEdge.to)!.title}
              </p>
              <p className="mt-4 border-t border-border pt-4 text-sm leading-relaxed text-muted-foreground">
                {selectedEdge.basis}
              </p>
              {selectedEdge.records.length > 0 ? (
                <div className="mt-4">
                  <p className="font-mono text-[11px] tracking-[0.16em] text-muted-foreground uppercase">
                    Supporting records
                  </p>
                  <ul className="mt-2 space-y-1">
                    {selectedEdge.records.map((r) => (
                      <li
                        key={r}
                        className="font-mono text-xs text-foreground underline decoration-border underline-offset-4"
                      >
                        {r}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <p className="mt-4 text-xs text-uncertain">
                  No supporting record — this relation stays visibly inferred.
                </p>
              )}
            </div>
          )}
        </div>

        {/* Every node and edge reachable from a plain list — the graph is never
            the only access path (keyboard, screen readers, small screens). */}
        <div>
          <p className="font-mono text-[11px] tracking-[0.16em] text-muted-foreground uppercase">
            Record index
          </p>
          <div className="mt-2.5 flex flex-wrap gap-1.5">
            {NODES.map((n) => (
              <button
                key={n.key}
                type="button"
                onClick={() => select({ kind: "node", key: n.key })}
                className={cn(
                  "rounded-sm border px-2 py-1 font-mono text-[11px] transition-colors duration-150",
                  sel.kind === "node" && sel.key === n.key
                    ? "border-foreground bg-foreground text-primary-foreground"
                    : "border-border bg-card text-muted-foreground hover:border-muted-foreground hover:text-foreground",
                )}
              >
                {n.title}
              </button>
            ))}
            {EDGES.map((e) => (
              <button
                key={e.id}
                type="button"
                onClick={() => select({ kind: "edge", id: e.id })}
                className={cn(
                  "rounded-sm border px-2 py-1 font-mono text-[11px] transition-colors duration-150",
                  sel.kind === "edge" && sel.id === e.id
                    ? "border-foreground bg-foreground text-primary-foreground"
                    : "border-border bg-card text-muted-foreground hover:border-muted-foreground hover:text-foreground",
                )}
              >
                {e.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
