import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type DecisionRow } from "../api";
import { Card, DecisionBadge, Empty, ErrorNote, Loading, PageHeader, Tag } from "../components/ui";

const LABELS = [
  "", "Instruction Override", "Role Change", "Secret Extraction", "Tool Abuse", "Credential Theft",
  "Context Poisoning", "Multi-Step Jailbreaks", "Encoded Instructions", "Indirect Prompt Injection",
];

export function Decisions() {
  const [filters, setFilters] = useState({ decision: "", label: "", agent: "" });
  const [rows, setRows] = useState<DecisionRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setRows(await api.decisions({ ...filters, limit: "200" }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);

  return (
    <div className="space-y-8">
      <PageHeader index="04" label="Decisions" title={<>Every boundary<br />has a reason.</>}
        lede="Every inspection and tool-call decision, newest first. Content appears only as a redacted preview." />
      <Card>
        <div className="flex flex-col gap-4 md:flex-row md:items-end">
          <label className="flex flex-col gap-2"><span className="section-label">Decision</span>
            <select className="input" value={filters.decision} onChange={(e) => setFilters((f) => ({ ...f, decision: e.target.value }))}>
              {["", "ALLOW", "NEUTRALISE", "BLOCK", "ESCALATE"].map((d) => <option key={d} value={d}>{d || "Any decision"}</option>)}
            </select></label>
          <label className="flex flex-col gap-2"><span className="section-label">Attack type</span>
            <select className="input" value={filters.label} onChange={(e) => setFilters((f) => ({ ...f, label: e.target.value }))}>
              {LABELS.map((l) => <option key={l} value={l}>{l || "Any type"}</option>)}
            </select></label>
          <label className="flex flex-1 flex-col gap-2"><span className="section-label">Agent</span>
            <input className="input" placeholder="research-agent" value={filters.agent} onChange={(e) => setFilters((f) => ({ ...f, agent: e.target.value }))} /></label>
          <button className="pill" onClick={load}>Refresh</button>
        </div>
      </Card>
      {error && <ErrorNote>{error}</ErrorNote>}
      {loading && !rows && <Loading />}
      {rows && rows.length === 0 && <Empty>No decisions match these filters.</Empty>}
      {rows && rows.length > 0 && (
        <Card>
          <div className="overflow-x-auto">
            <table className="table min-w-[860px]">
              <thead><tr><th>Time</th><th>Decision</th><th>Source</th><th>Rule · reason</th><th>Attack types</th><th>Session</th></tr></thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.event_id}>
                    <td className="subtle whitespace-nowrap text-xs">{new Date(r.created_at * 1000).toLocaleTimeString()}</td>
                    <td><DecisionBadge decision={r.decision} />{r.enforced !== r.decision && <span className="subtle mt-1 block text-[11px]">monitor mode</span>}</td>
                    <td className="text-xs">{r.source.replace("tool:", "tool · ")}</td>
                    <td><span className="mono" style={{ color: "var(--accent-soft)" }}>{r.policy_rule}</span><span className="subtle mt-1 block text-xs">{r.reason}</span></td>
                    <td><div className="flex flex-wrap gap-1.5">{r.labels.map((l) => <Tag key={l}>{l}</Tag>)}</div></td>
                    <td><Link className="text-link mono" to={`/replay?session=${r.session_id}`}>{r.session_id.slice(0, 10)}</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
