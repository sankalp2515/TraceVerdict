import { useEffect, useState } from "react";
import { api, type RateRow, type Report } from "../api";
import { Empty, pct, Section } from "../components/ui";

const TYPES = [
  "Instruction Override", "Role Change", "Secret Extraction", "Tool Abuse", "Credential Theft",
  "Context Poisoning", "Multi-Step Jailbreaks", "Encoded Instructions", "Indirect Prompt Injection",
];

function reduction(off?: RateRow, on?: RateRow): string {
  if (!off?.asr || on?.asr === null || on?.asr === undefined) return "—";
  return `${(((off.asr - on.asr) / off.asr) * 100).toFixed(0)}%`;
}

function Bar({ value, color }: { value: number | null | undefined; color: string }) {
  const w = value ? Math.max(2, Math.round(value * 100)) : 0;
  return (
    <div className="h-2 w-full rounded-full" style={{ background: "var(--panel-2)" }} aria-hidden>
      <div className="h-2 rounded-full" style={{ width: `${w}%`, background: color }} />
    </div>
  );
}

function CompareTable({ title, rows, off, on }: { title: string; rows: string[]; off?: Record<string, RateRow>; on?: Record<string, RateRow> }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[520px] text-sm">
        <caption className="sr-only">{title}</caption>
        <thead>
          <tr className="muted text-left text-xs uppercase tracking-wide">
            <th className="py-2 pr-3 font-medium">{title}</th>
            <th className="py-2 pr-3 font-medium">Tests</th>
            <th className="w-40 py-2 pr-3 font-medium">Attack success · OFF</th>
            <th className="w-40 py-2 pr-3 font-medium">Attack success · ON</th>
            <th className="py-2 font-medium">Reduction</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((k) => {
            const a = off?.[k];
            const b = on?.[k];
            return (
              <tr key={k} className="border-t" style={{ borderColor: "var(--border)" }}>
                <td className="py-2 pr-3">{k}</td>
                <td className="muted py-2 pr-3">{a?.scored ?? b?.scored ?? "—"}</td>
                <td className="py-2 pr-3"><div className="flex items-center gap-2"><span className="w-12 tabular-nums">{pct(a?.asr)}</span><Bar value={a?.asr} color="var(--block)" /></div></td>
                <td className="py-2 pr-3"><div className="flex items-center gap-2"><span className="w-12 tabular-nums">{pct(b?.asr)}</span><Bar value={b?.asr} color="var(--allow)" /></div></td>
                <td className="py-2 tabular-nums">{reduction(a, b)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Stat({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="panel p-4">
      <p className="muted text-xs uppercase tracking-wide">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
      {note && <p className="muted mt-1 text-xs">{note}</p>}
    </div>
  );
}

export function Scorecard() {
  const [reports, setReports] = useState<Record<string, Report> | null>(null);
  const [suite, setSuite] = useState("headline");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.scorecard("research-agent").then((r) => setReports(r.reports)).catch((e) => setError((e as Error).message));
  }, []);

  const suites = reports ? Array.from(new Set(Object.values(reports).map((r) => r.suite))) : [];
  const off = reports?.[`${suite}:off`];
  const on = reports?.[`${suite}:on`];

  return (
    <>
      <Section
        title="Scorecard · research-agent"
        subtitle="Measured on the reference agent with generated attack suites (promptfoo, garak). Attack success counts only harm we can verify, so it is a lower bound."
        actions={
          suites.length > 1 ? (
            <label className="flex items-center gap-2 text-sm">
              <span className="muted">Suite</span>
              <select className="input" value={suite} onChange={(e) => setSuite(e.target.value)}>
                {suites.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </label>
          ) : undefined
        }
      >
        {error && <Empty>No evaluation report available yet ({error}).</Empty>}
        {reports && !off && !on && <Empty>No results for suite “{suite}” yet.</Empty>}
        {(off || on) && (
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat label="Attack success · unprotected" value={pct(off?.overall.asr)} note={off ? `${off.overall.scored} tests · ${off.date}` : "not run"} />
            <Stat label="Attack success · protected" value={pct(on?.overall.asr)} note={on ? `${on.overall.scored} tests · ${on.date}` : "pending"} />
            <Stat label="Relative reduction" value={reduction(off?.overall, on?.overall)} note="target ≥ 80%" />
            <Stat label="Benign tasks completed · protected" value={on?.benign ? pct(on.benign.success_rate) : "—"} note="utility, target ≥ 90%" />
          </div>
        )}
      </Section>

      {(off || on) && (
        <Section title="By attack type" subtitle="The nine categories from the hackathon brief.">
          <CompareTable title="Attack type" rows={TYPES} off={off?.by_category} on={on?.by_category} />
        </Section>
      )}
      {(off || on) && (
        <Section title="By input channel">
          <CompareTable title="Channel" rows={Array.from(new Set([...Object.keys(off?.by_channel ?? {}), ...Object.keys(on?.by_channel ?? {})]))} off={off?.by_channel} on={on?.by_channel} />
        </Section>
      )}
      <Section title="Grid position (F / D)" subtitle="Declared only from a completed, dated evaluation run (PRD §15).">
        <p className="text-sm">Pending the full evaluation. The claim, its evidence and the run date will appear here.</p>
      </Section>
    </>
  );
}
