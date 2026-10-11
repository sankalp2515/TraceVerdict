import type { ReactNode } from "react";
import { api, type ChainSource, type Contract, type ContractClause, type ProvenanceChain } from "../api";
import { Card, CardTitle, DECISION_TEXT, Empty, ErrorNote, Loading, Stat, Tag, useAsync } from "./ui";

const SOURCE: Record<string, string> = {
  web: "Web page", email: "Email", pdf: "PDF", docx: "Word document", html: "HTML page", markdown: "Markdown file",
  api: "API response", db: "Database record", image: "Image (OCR)", code: "Source code", text: "File", pasted: "Pasted material",
};
const sourceName = (s: string) => SOURCE[s] ?? (s.startsWith("tool:") ? `Tool output · ${s.slice(5)}` : s);
const TONE: Record<string, string> = {
  ALLOW: "var(--allow)", NEUTRALISE: "var(--neutralise)", BLOCK: "var(--block)", ESCALATE: "var(--escalate)",
};
const OUTCOME: Record<string, string> = {
  "not-executed": "Not executed · no side effect", executed: "Executed (receipt)", allowed: "Allowed",
  quarantined: "Quarantined before the model saw it", held: "Held before the model saw it", contradiction: "Contradiction: investigate",
};

function short(json: string | null | undefined): string {
  if (!json) return "";
  try {
    const o = JSON.parse(json) as Record<string, unknown>;
    return Object.entries(o).slice(0, 3).map(([k, v]) => `${k}: ${String(v).slice(0, 48)}`).join(" · ");
  } catch {
    return json.slice(0, 120);
  }
}

function Step({ title, sub, tone, children }: { title: ReactNode; sub?: ReactNode; tone?: string; children?: ReactNode }) {
  return (
    <div className="rounded-2xl border p-4 text-center hairline"
      style={tone ? { borderColor: `color-mix(in srgb, ${tone} 70%, transparent)`, background: `color-mix(in srgb, ${tone} 6%, transparent)` } : undefined}>
      <p className="m-0 text-[15px] font-medium">{title}</p>
      {sub && <p className="subtle m-0 mt-1 text-xs">{sub}</p>}
      {children}
    </div>
  );
}

const Down = () => <div aria-hidden className="subtle py-1 text-center text-sm">↓</div>;

function SourceStep({ s }: { s: ChainSource }) {
  const flagged = s.evidence.length > 0 || (s.decision && s.decision !== "ALLOW");
  const span = s.evidence.find((e) => e.span)?.span;
  return (
    <>
      <Step title={`${sourceName(s.source)}`} sub={<>Untrusted source · event {s.seq}{s.proven ? "" : " · context, not a proven link"}</>} />
      <Down />
      <Step title={flagged ? "Flagged content" : "Content read (no detector signal)"}
        sub={<>{s.link}{s.decision ? ` · content decision: ${DECISION_TEXT[s.decision]}` : ""}</>}
        tone={flagged ? "var(--neutralise)" : undefined}>
        {span && <p className="mono m-0 mt-2 break-words text-[11px]">“{span}”</p>}
        {s.evidence.length > 0 && <p className="subtle m-0 mt-1 text-[11px]">Signals: {[...new Set(s.evidence.map((e) => e.signal))].join(", ")}</p>}
      </Step>
    </>
  );
}

function Chain({ c }: { c: ProvenanceChain }) {
  const d = c.control.decision;
  const stopped = d && d !== "ALLOW";
  const clause = c.control.contract?.clause;
  return (
    <article className="flex flex-col">
      {c.sources.map((s, i) => <div key={s.event_id + i}>{i > 0 && <p className="subtle my-1 text-center text-[11px]">and</p>}<SourceStep s={s} /></div>)}
      {c.sources.length === 0 && <Step title="No untrusted content linked" sub="decided on the call alone" />}
      {c.action && (<><Down /><Step title={`Proposed tool call · ${c.action.tool}`} sub={short(c.action.args)} /></>)}
      <Down />
      <Step tone={stopped ? TONE[d!] : "var(--allow)"}
        title={<>{stopped ? "⛨ " : ""}{d ? DECISION_TEXT[d] : "—"} by {c.control.layer}</>}
        sub={<>{c.control.rule}{c.control.reason ? ` · ${c.control.reason}` : ""}</>}>
        {clause && <p className="m-0 mt-2 text-[12px]">Contract v{c.control.contract!.version} · clause <span className="mono">{clause.id}</span>{clause.origin !== "policy" ? <> · the user said “{clause.quote}”</> : null}</p>}
      </Step>
      <Down />
      <div className="rounded-2xl border p-3 text-center text-[13px] hairline">
        <b style={{ color: c.outcome.state === "not-executed" || c.outcome.state === "quarantined" || c.outcome.state === "held" ? "var(--allow)" : c.outcome.state === "contradiction" ? "var(--block)" : undefined }}>
          {OUTCOME[c.outcome.state] ?? c.outcome.state}
        </b>
        <ul className="subtle m-0 mt-1 list-none p-0 text-[11px] leading-relaxed">{c.outcome.evidence.map((e) => <li key={e}>{e}</li>)}</ul>
      </div>
    </article>
  );
}

function ClauseList({ title, items, tone }: { title: string; items: ContractClause[]; tone?: string }) {
  if (!items.length) return null;
  return (
    <div>
      <p className="section-label mb-2">{title}</p>
      <ul className="m-0 list-none space-y-1.5 p-0 text-[13px]">
        {items.map((c) => (
          <li key={c.id}><Tag tone={tone}>{c.capability}</Tag> <span className="ml-1">{c.origin === "policy" ? c.quote : <>“{c.quote}”</>}</span>
            <span className="subtle ml-2 text-[11px]">{c.origin} · {c.id}</span></li>
        ))}
      </ul>
    </div>
  );
}

export function ContractView({ contracts }: { contracts: Contract[] }) {
  const c = contracts[contracts.length - 1];
  if (!c) return <Empty>Intent contracts are off for this agent (policy: contract.mode).</Empty>;
  const latest = new Map<string, ContractClause>();
  for (const x of c.clauses) if (x.effect === "permit" || x.effect === "prohibit") latest.set(x.capability, x);
  const user = [...latest.values()];
  const required = c.clauses.filter((x) => x.effect === "require" && !latest.has(x.capability));
  return (
    <div className="space-y-5">
      <p className="subtle m-0 text-xs">
        Version {c.version} · hash <span className="mono">{c.hash}</span>{c.parent && <> · parent <span className="mono">{c.parent}</span></>} ·
        {" "}{contracts.length} version{contracts.length === 1 ? "" : "s"}, each from the user’s own words ({contracts.map((v) => v.origin).join(" → ")}).
        Content the agent reads never changes it.
      </p>
      <div className="grid gap-6 sm:grid-cols-2">
        <ClauseList title="Permitted by the user" items={user.filter((x) => x.effect === "permit")} tone="var(--allow)" />
        <ClauseList title="Prohibited by the user" items={user.filter((x) => x.effect === "prohibit")} tone="var(--block)" />
        <ClauseList title="Needs the user’s explicit request" items={required} tone="var(--escalate)" />
      </div>
      <details>
        <summary className="subtle cursor-pointer text-xs">Policy bounds in this contract ({c.clauses.filter((x) => x.effect === "policy").length})</summary>
        <div className="mt-3"><ClauseList title="Policy" items={c.clauses.filter((x) => x.effect === "policy")} /></div>
      </details>
      {c.targets.length > 0 && <p className="subtle m-0 text-xs">Targets the user named: <span className="mono">{c.targets.join(", ")}</span></p>}
    </div>
  );
}

export function ProvenancePanel({ sessionId }: { sessionId: string }) {
  const { data, error, loading } = useAsync(() => api.provenance(sessionId), [sessionId]);
  if (loading && !data) return <Card><Loading>Building the attack path…</Loading></Card>;
  if (error) return <Card><ErrorNote>{error}</ErrorNote></Card>;
  if (!data) return null;
  return (
    <Card>
      <CardTitle meta="from the decision log, the intent contract and execution receipts, not from what a model says">Attack to action</CardTitle>
      <div className="mb-7 grid grid-cols-2 gap-6 sm:grid-cols-4">
        <Stat value={data.summary.actions_stopped} label="Actions stopped before they ran" tone={data.summary.actions_stopped ? "var(--allow)" : undefined} />
        <Stat value={data.summary.content_stopped} label="Content stopped before the model" />
        <Stat value={data.summary.executed_with_untrusted_link} label="Executed with a link to untrusted content" tone={data.summary.executed_with_untrusted_link ? "var(--block)" : undefined} />
        <Stat value={data.summary.contradictions} label="Contradictions" tone={data.summary.contradictions ? "var(--block)" : undefined} />
      </div>
      <div className="grid gap-8 lg:grid-cols-[minmax(0,26rem)_minmax(0,1fr)]">
        <div className="space-y-10">
          {data.chains.length === 0
            ? <Empty>No attack path in this session: nothing untrusted reached an action, and nothing was stopped.</Empty>
            : data.chains.map((c, i) => <Chain key={i} c={c} />)}
        </div>
        <div>
          <h3 className="h3 mb-1">Intent contract</h3>
          <p className="subtle m-0 mb-4 text-xs">D-064 · compiled from the user’s words, enforced on every tool call</p>
          <ContractView contracts={data.contracts} />
        </div>
      </div>
    </Card>
  );
}
