import { useState } from "react";
import { Link } from "react-router-dom";
import { api, PRODUCT_NAME } from "../api";
import { ago, Card, CardTitle, Empty, ErrorNote, Loading, PageHeader, Stat, Tag, useAsync } from "../components/ui";

const STATUSES = ["pending", "approved", "denied"] as const;

function Approvals() {
  const [status, setStatus] = useState<(typeof STATUSES)[number]>("pending");
  const { data, error, loading } = useAsync(() => api.approvals(status), [status]);
  return (
    <Card>
      <CardTitle meta="An approval lets the same call in the same session run once. It can never override a block.">Approvals inbox</CardTitle>
      <div className="mb-5 flex flex-wrap gap-2" role="tablist" aria-label="Approval status">
        {STATUSES.map((s) => (
          <button key={s} role="tab" aria-selected={status === s} className={`pill pill-sm ${status === s ? "pill-primary" : ""}`} onClick={() => setStatus(s)}>
            {s[0].toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>
      {loading && <Loading />}
      {error && <ErrorNote>{error}</ErrorNote>}
      {data && data.length === 0 && <Empty>No {status} approvals.</Empty>}
      {data && data.length > 0 && (
        <ul className="m-0 list-none border-t p-0 hairline">
          {data.map((a) => (
            <li key={a.event_id} className="grid gap-3 border-b py-5 hairline md:grid-cols-[1fr_1.2fr]">
              <div>
                <p className="m-0 text-[15px]">The agent wants to use <span className="mono" style={{ color: "var(--accent-text)" }}>{a.tool}</span></p>
                <p className="subtle m-0 mt-1 text-xs">{a.agent_id} · {ago(a.created_at)} · <Link className="text-link" to={`/replay?session=${a.session_id}`}>session</Link></p>
                <p className="m-0 mt-3 text-[13px]">{a.reason}</p>
                <div className="mt-3 flex flex-wrap gap-1.5">{a.labels.map((l) => <Tag key={l}>{l}</Tag>)}</div>
              </div>
              <div>
                <span className="section-label block pb-2">Exact request (redacted)</span>
                <pre className="mono well m-0 whitespace-pre-wrap break-words p-3">{a.args_redacted ?? "—"}</pre>
                {a.status !== "pending" && (
                  <p className="subtle m-0 mt-2 text-xs">{a.status} by {a.reviewer ?? "—"}{a.note ? ` · “${a.note}”` : ""}{a.used_at ? " · used once" : ""}</p>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
      <p className="subtle mt-5 text-xs leading-6">
        Approving or denying needs an admin key and is done through <span className="mono">POST /v1/approvals/&lt;event_id&gt;</span>.
        This Console only holds a public read-only key.
      </p>
    </Card>
  );
}

function Memory() {
  const { data, error, loading } = useAsync(() => api.memory(), []);
  return (
    <Card>
      <CardTitle meta="Stored as fingerprints only, never as text.">Learned from review</CardTitle>
      {loading && <Loading />}
      {error && <ErrorNote>{error}</ErrorNote>}
      {data && (
        <>
          <div className="mb-6 flex flex-wrap gap-10">
            <Stat value={data.stats.attack ?? 0} label="Confirmed attacks: blocked by rules on sight, no AI call" />
            <Stat value={data.stats.benign ?? 0} label="Reviewed false alarms: exact content, per agent" />
          </div>
          {data.entries.length === 0 ? <Empty>Nothing confirmed yet. Reviewers mark decisions with POST /v1/feedback (admin).</Empty> : (
            <div className="overflow-x-auto">
              <table className="table min-w-[560px]">
                <thead><tr><th>Kind</th><th>Labels</th><th>Agent</th><th>Origin</th><th>Added</th></tr></thead>
                <tbody>
                  {data.entries.map((m) => (
                    <tr key={m.id}>
                      <td><Tag tone={m.kind === "attack" ? "var(--block)" : "var(--allow)"}>{m.kind === "attack" ? "confirmed attack" : "false alarm"}</Tag></td>
                      <td><div className="flex flex-wrap gap-1.5">{m.labels.map((l) => <Tag key={l}>{l}</Tag>)}</div></td>
                      <td className="text-xs">{m.agent_id === "*" ? "all agents" : m.agent_id}</td>
                      <td className="subtle text-xs">{m.origin}</td>
                      <td className="subtle text-xs">{ago(m.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </Card>
  );
}

export function Review() {
  return (
    <div className="space-y-8">
      <PageHeader index="05" label="Human review" title={<>People decide<br />the hard cases.</>}
        lede={`${PRODUCT_NAME} asks humans rarely and with a clear reason. Confirmed attacks and false alarms make the next decision better.`} />
      <Approvals />
      <Memory />
    </div>
  );
}
