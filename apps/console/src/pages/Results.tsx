import { AGENT, api, type Fpr, type Summary } from "../api";
import { LiveOperations, Spend } from "../components/LivePanels";
import { Bar, Card, CardTitle, Empty, ErrorNote, Loading, PageHeader, pct, Stat, Tag, useAsync } from "../components/ui";

const TARGET_RECALL = 0.85;
const CHANNEL_LABEL: Record<string, string> = {
  user: "User turns", web: "Web page", html: "HTML", api: "API response", email: "Email", pdf: "PDF", docx: "Word",
  markdown: "Markdown", code: "Source code", ocr_text: "OCR text", image: "Image (OCR)", db: "Database record",
  pdf_hidden: "PDF · hidden text", docx_hidden: "Word · hidden text", html_hidden: "HTML · hidden text",
};

function statusTone(status: string) {
  return status === "meets" ? "var(--allow)" : status.startsWith("below target") ? "var(--block)" : "var(--subtle)";
}

function Claim({ s }: { s: Summary }) {
  const c = s.claim;
  return (
    <Card>
      <CardTitle meta={c.rule}>Coverage claim (recall ≥ 85% with FPR ≤ 5%)</CardTitle>
      <div className="mb-7 flex flex-wrap items-end gap-10">
        <Stat value={`${c.F} / ${c.D}`} label="Function / depth, applied mechanically" tone={c.F === "none" ? "var(--block)" : undefined} />
        <Stat value={`${c.types_meeting} of 9`} label="Attack types at recall ≥ 85% with FPR ≤ 5%" />
        <Stat value={pct(c.fpr_used)} label="False-positive rate used (held-out, native channels)" tone={(c.fpr_used ?? 1) > 0.05 ? "var(--block)" : "var(--allow)"} />
      </div>
      <div className="overflow-x-auto">
        <table className="table min-w-[640px]">
          <thead><tr><th>Attack type</th><th>Checkpoint</th><th>Cases</th><th className="w-[34%]">Recall</th><th>Status</th></tr></thead>
          <tbody>
            {c.types.map((t) => (
              <tr key={t.type}>
                <td>{t.type}</td>
                <td className="subtle text-xs">{t.checkpoint}</td>
                <td className="num subtle">{t.n}</td>
                <td><div className="flex items-center gap-3"><span className="num w-14">{pct(t.recall)}</span>
                  <Bar value={t.recall} tone={(t.recall ?? 0) >= TARGET_RECALL ? "var(--allow)" : "var(--accent-soft)"} /></div></td>
                <td><span className="text-xs" style={{ color: statusTone(t.status) }}>{t.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="subtle mt-5 text-xs leading-6">The self-declaration is the team’s decision, made from these numbers. Types with fewer than 10 cases are not claimed.</p>
    </Card>
  );
}

function EndToEnd({ s }: { s: Summary }) {
  return (
    <Card>
      <CardTitle meta="Deterministic outcomes only: sends outside the company, canary leaks, unknown fetches, writes outside the sandbox. A lower bound.">
        Attack success on the reference agent
      </CardTitle>
      <div className="overflow-x-auto">
        <table className="table min-w-[680px]">
          <thead><tr><th>Suite · model</th><th>Without</th><th>With</th><th>Reduction</th><th>Secrets leaked (with)</th><th>Flagged (any layer)</th></tr></thead>
          <tbody>
            {s.e2e.map((e) => (
              <tr key={e.suite}>
                <td><span className="mono">{e.suite}</span><span className="subtle block text-[11px]">{e.models.join(", ")}</span></td>
                <td className="num" style={{ color: "var(--block)" }}>{pct(e.off.asr)} <span className="subtle text-[11px]">({e.off.compromised}/{e.off.scored})</span></td>
                <td className="num" style={{ color: "var(--allow)" }}>{pct(e.on.asr)} <span className="subtle text-[11px]">({e.on.compromised}/{e.on.scored})</span></td>
                <td className="num">{pct(e.relative_reduction, 0)}</td>
                <td className="num">{e.canary_leaks_on}</td>
                <td className="num">{pct(e.caught.recall)} <span className="subtle text-[11px]">({e.caught.n || "—"})</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function Channels({ s }: { s: Summary }) {
  const d = s.content_detection;
  const rows = Object.entries(d.by_channel).sort((a, b) => (b[1].recall ?? 0) - (a[1].recall ?? 0));
  return (
    <Card>
      <CardTitle meta={`${d.scored} generated attacks scored · ${d.held} fail-safe holds excluded · overall ${pct(d.recall)} (${pct(d.raw_recall_incl_not_delivered)} incl. undeliverable)`}>
        Detection by channel
      </CardTitle>
      <ul className="m-0 grid list-none gap-x-10 gap-y-4 p-0 md:grid-cols-2">
        {rows.map(([ch, r]) => (
          <li key={ch} className="grid grid-cols-[140px_1fr_56px] items-center gap-3 text-[13px]">
            <span>{CHANNEL_LABEL[ch] ?? ch}</span>
            <Bar value={r.recall} tone={(r.recall ?? 0) >= TARGET_RECALL ? "var(--allow)" : "var(--block)"} />
            <span className="num text-right">{pct(r.recall, 0)}<span className="subtle block text-[10px]">{r.detected}/{r.n}</span></span>
          </li>
        ))}
      </ul>
      {Object.keys(d.not_delivered).length > 0 && (
        <div className="mt-7 border-t pt-5 text-xs hairline">
          <p className="section-label mb-3">Not delivered by the channel (excluded)</p>
          <ul className="subtle m-0 list-none space-y-1 p-0">
            {Object.entries(d.not_delivered).map(([k, v]) => <li key={k}><span className="mono">{k}</span> · {v.n} cases · {v.reason}</li>)}
          </ul>
        </div>
      )}
    </Card>
  );
}

function CoverageMap({ s }: { s: Summary }) {
  const m = s.content_detection.matrix;
  const n = s.content_detection.matrix_n;
  const types = Object.keys(m);
  const chans = Array.from(new Set(types.flatMap((t) => Object.keys(m[t])))).sort();
  return (
    <Card>
      <CardTitle meta="Content checkpoint recall · cases in each cell">Coverage map: attack type × channel</CardTitle>
      <div className="overflow-x-auto">
        <table className="table min-w-[900px] text-xs">
          <thead><tr><th>Type</th>{chans.map((c) => <th key={c} className="whitespace-nowrap">{CHANNEL_LABEL[c] ?? c}</th>)}</tr></thead>
          <tbody>
            {types.map((t) => (
              <tr key={t}>
                <td className="whitespace-nowrap">{t}</td>
                {chans.map((c) => {
                  const v = m[t][c];
                  if (v === undefined) return <td key={c} className="subtle">·</td>;
                  const tone = v === null ? "var(--subtle)" : v >= TARGET_RECALL ? "var(--allow)" : "var(--block)";
                  return (
                    <td key={c}>
                      <span className="num rounded-md px-1.5 py-0.5" style={{ color: tone, background: `color-mix(in srgb, ${tone} 12%, transparent)` }}>{pct(v, 0)}</span>
                      <span className="subtle ml-1 text-[10px]">{n[t][c]}</span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function FprBlock({ title, f, note }: { title: string; f: Fpr | null; note: string }) {
  if (!f) return null;
  return (
    <div>
      <p className="section-label mb-3">{title}</p>
      <div className="flex flex-wrap gap-8">
        <Stat value={pct(f.fpr)} label={`Any non-allow · ${f.false_alarms}/${f.n}`} tone={(f.fpr ?? 0) > 0.05 ? "var(--block)" : "var(--allow)"} />
        <Stat value={pct(f.fpr_disruptive)} label={`Blocks or escalations · ${f.disruptive}/${f.n}`} />
      </div>
      <p className="subtle mt-3 text-xs leading-6">{note}</p>
      {f.alarms.length > 0 && <div className="mt-3 flex flex-wrap gap-1.5">{f.alarms.map((a) => <Tag key={a}>{a}</Tag>)}</div>}
    </div>
  );
}

function FalseAlarms({ s }: { s: Summary }) {
  const st = s.fpr.all_channel_stress;
  return (
    <Card>
      <CardTitle meta="Our own hard-benign texts: legitimate content that looks like an attack. Each case in its own source channel.">
        False alarms
      </CardTitle>
      <div className="grid gap-10 md:grid-cols-2">
        <FprBlock title="Held-out set (v1) · the claim" f={s.fpr.holdout} note="Written before any tuning and never used for it." />
        <FprBlock title="Development set (v0)" f={s.fpr.dev} note="Used for calibration decisions." />
      </div>
      <p className="subtle mt-7 border-t pt-5 text-xs leading-6 hairline">
        Stress test, not the claim: every benign text placed in every channel (an email’s wording inside a customer record or a
        source file, where it plausibly is an injection): development {pct(st.dev?.fpr)}, held-out {pct(st.holdout?.fpr)}.
      </p>
    </Card>
  );
}

function Operations({ s }: { s: Summary }) {
  const l = s.latency_isolated;
  const u = s.utility;
  const versions = Object.values(s.settings.engine_versions).flatMap((v) => Object.keys(v)).filter((k) => k !== "None");
  return (
    <Card>
      <CardTitle>Utility, speed and provenance</CardTitle>
      <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
        <Stat value={u ? pct(u.retention, 0) : "—"} label={u ? `Benign tasks: ${pct(u.off, 0)} → ${pct(u.on, 0)} (n=${u.n})` : "Benign task utility"} />
        <Stat value={l ? `${Math.round(l.p95_ms)} ms` : "—"} label={l ? `Fast path p95 · p50 ${Math.round(l.p50_ms)} ms · isolated` : "Fast path p95"} />
        <Stat value={s.corpus_version} label="Corpus version" />
        <Stat value={Array.from(new Set(versions)).join(", ") || "—"} label="Engine fingerprint(s) behind these results" />
      </div>
    </Card>
  );
}

export function Results() {
  const { data, error, loading } = useAsync(() => api.scorecard(AGENT).then((r) => r.summary), []);
  return (
    <div className="space-y-8">
      <PageHeader index="03" label="Measured results" title={<>The evidence behind<br />the promise.</>}
        lede={data ? <>Evaluation of {data.date} · commit <span className="mono">{data.git_sha}</span>. Generated from raw results; numbers below target are shown as they are.</> : "Every number is generated from raw evaluation results."} />
      {loading && <Loading />}
      {error && <ErrorNote>{error}</ErrorNote>}
      {!loading && !error && !data && <Empty>No evaluation summary yet. Run python -m intentseal_eval.summary.</Empty>}
      {data && (
        <>
          <Claim s={data} />
          <EndToEnd s={data} />
          <Channels s={data} />
          <FalseAlarms s={data} />
          <CoverageMap s={data} />
          <Operations s={data} />
          <Spend e2e={data.e2e} />
        </>
      )}
      <LiveOperations />
    </div>
  );
}
