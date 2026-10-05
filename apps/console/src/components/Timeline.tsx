import { useState } from "react";
import type { EventRow } from "../api";
import { DecisionBadge, Empty, Label } from "./ui";

function sourceLabel(e: EventRow): string {
  if (e.kind === "action") return `Tool call · ${e.action?.tool ?? e.source.replace("tool:", "")}`;
  if (e.source === "user") return "User message";
  return `Content in · ${e.source.replace("tool:", "")}`;
}

export function Timeline({ events }: { events: EventRow[] }) {
  const [open, setOpen] = useState<string | null>(null);
  if (!events.length) return <Empty>No events recorded for this session yet.</Empty>;
  return (
    <ol className="relative space-y-2" aria-label="Session timeline">
      {events.map((e) => {
        const isOpen = open === e.id;
        const notable = e.decision && e.decision !== "ALLOW";
        return (
          <li key={e.id} className="rounded-lg border" style={{ borderColor: notable ? "color-mix(in srgb, var(--block) 35%, var(--border))" : "var(--border)" }}>
            <button
              className="flex w-full flex-wrap items-center gap-2 px-3 py-2 text-left"
              aria-expanded={isOpen}
              onClick={() => setOpen(isOpen ? null : e.id)}
            >
              <span className="mono muted w-6 shrink-0">{e.seq}</span>
              <span className="text-sm font-medium">{sourceLabel(e)}</span>
              <DecisionBadge decision={e.decision} />
              {e.degraded ? <Label>degraded</Label> : null}
              <span className="muted ml-auto text-xs">
                {e.policy_rule && e.policy_rule !== "allow" ? `rule: ${e.policy_rule}` : ""}
                {e.latency_ms !== null ? ` · ${Math.round(e.latency_ms)} ms` : ""}
              </span>
            </button>
            {isOpen && (
              <div className="space-y-2 border-t px-3 py-3 text-sm" style={{ borderColor: "var(--border)" }}>
                {e.reason && <p><span className="muted">Reason: </span>{e.reason}</p>}
                {e.labels?.length ? (
                  <p className="flex flex-wrap items-center gap-1"><span className="muted">Attack types: </span>{e.labels.map((l) => <Label key={l}>{l}</Label>)}</p>
                ) : null}
                {e.tier !== null && <p><span className="muted">Deepest tier used: </span>{["Tier 0 · structure", "Tier 1 · classifier", "Tier 2 · AI judge"][e.tier] ?? e.tier}</p>}
                {e.action && (
                  <div className="space-y-1">
                    <p className="muted">Requested arguments</p>
                    <pre className="mono overflow-x-auto rounded-md p-2" style={{ background: "var(--panel-2)" }}>{e.action.args_redacted}</pre>
                    {e.action.pinned_overrides && (
                      <>
                        <p className="muted">Pinned fields rewritten from trusted context</p>
                        <pre className="mono overflow-x-auto rounded-md p-2" style={{ background: "var(--panel-2)" }}>{e.action.pinned_overrides}</pre>
                      </>
                    )}
                  </div>
                )}
                {e.findings?.length ? (
                  <div className="space-y-1">
                    <p className="muted">Findings ({e.findings.length})</p>
                    <ul className="space-y-1">
                      {e.findings.slice(0, 12).map((f, i) => (
                        <li key={i} className="rounded-md p-2" style={{ background: "var(--panel-2)" }}>
                          <div className="flex flex-wrap items-center gap-2 text-xs">
                            <Label>{f.signal}</Label>
                            <span className="muted">{f.origin}</span>
                            {f.span_start !== null && <span className="muted mono">span {f.span_start}–{f.span_end}</span>}
                            {f.score ? <span className="muted">score {f.score.toFixed(2)}</span> : null}
                            {f.labels.map((l) => <Label key={l}>{l}</Label>)}
                          </div>
                          {f.span_preview && <p className="mono mt-1 break-words">{f.span_preview}</p>}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {e.preview && !e.findings?.length && <p className="mono muted break-words">{e.preview}</p>}
              </div>
            )}
          </li>
        );
      })}
    </ol>
  );
}
