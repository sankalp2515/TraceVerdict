import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type DecisionRow } from "../api";
import { DecisionBadge, Empty, Label, Section } from "../components/ui";

const LABELS = [
  "", "Instruction Override", "Role Change", "Secret Extraction", "Tool Abuse", "Credential Theft",
  "Context Poisoning", "Multi-Step Jailbreaks", "Encoded Instructions", "Indirect Prompt Injection",
];

export function Decisions() {
  const [filters, setFilters] = useState({ decision: "", label: "", agent: "" });
  const [rows, setRows] = useState<DecisionRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setError(null);
    try {
      setRows(await api.decisions({ ...filters, limit: "200" }));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);

  return (
    <Section title="Decisions" subtitle="Every inspection and tool-call decision, newest first. Content is shown as a redacted preview.">
      <div className="mb-3 flex flex-wrap gap-2">
        <label className="flex flex-col gap-1 text-sm">
          <span className="muted">Decision</span>
          <select className="input" value={filters.decision} onChange={(e) => setFilters((f) => ({ ...f, decision: e.target.value }))}>
            {["", "ALLOW", "NEUTRALISE", "BLOCK", "ESCALATE"].map((d) => <option key={d} value={d}>{d || "Any"}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="muted">Attack type</span>
          <select className="input" value={filters.label} onChange={(e) => setFilters((f) => ({ ...f, label: e.target.value }))}>
            {LABELS.map((l) => <option key={l} value={l}>{l || "Any"}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="muted">Agent</span>
          <input className="input" placeholder="research-agent" value={filters.agent} onChange={(e) => setFilters((f) => ({ ...f, agent: e.target.value }))} />
        </label>
        <button className="btn self-end" onClick={load}>Refresh</button>
      </div>
      {error && <p className="mb-2 text-sm" style={{ color: "var(--block)" }}>{error}</p>}
      {rows && rows.length === 0 && <Empty>No decisions match these filters.</Empty>}
      {rows && rows.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-sm">
            <thead>
              <tr className="muted text-left text-xs uppercase tracking-wide">
                <th className="py-2 pr-3 font-medium">Time</th>
                <th className="py-2 pr-3 font-medium">Decision</th>
                <th className="py-2 pr-3 font-medium">Source</th>
                <th className="py-2 pr-3 font-medium">Rule · reason</th>
                <th className="py-2 pr-3 font-medium">Types</th>
                <th className="py-2 font-medium">Session</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.event_id} className="border-t align-top" style={{ borderColor: "var(--border)" }}>
                  <td className="muted py-2 pr-3 whitespace-nowrap">{new Date(r.created_at * 1000).toLocaleTimeString()}</td>
                  <td className="py-2 pr-3"><DecisionBadge decision={r.decision} />{r.enforced !== r.decision && <span className="muted block text-xs">monitor mode</span>}</td>
                  <td className="py-2 pr-3">{r.source.replace("tool:", "tool · ")}</td>
                  <td className="py-2 pr-3"><span className="mono">{r.policy_rule}</span><span className="muted block text-xs">{r.reason}</span></td>
                  <td className="py-2 pr-3"><div className="flex flex-wrap gap-1">{r.labels.map((l) => <Label key={l}>{l}</Label>)}</div></td>
                  <td className="py-2"><Link className="mono underline" to={`/replay?session=${r.session_id}`}>{r.session_id.slice(0, 8)}</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Section>
  );
}
