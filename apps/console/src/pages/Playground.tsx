import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type DemoResult, type Scenario } from "../api";
import { DecisionBadge, Empty, Label, Section } from "../components/ui";
import { Timeline } from "../components/Timeline";

function RunPanel({ title, result, loading, error }: { title: string; result: DemoResult | null; loading: boolean; error: string | null }) {
  const leaked = result?.canary_leaked;
  const blocked = result?.steps.filter((s) => !s.allowed) ?? [];
  return (
    <div className="panel flex min-w-0 flex-1 flex-col gap-3 p-4">
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-semibold">{title}</h3>
        {result && (
          <span
            className="rounded-full px-2 py-0.5 text-xs font-semibold"
            style={{ color: leaked ? "var(--block)" : "var(--allow)", border: `1px solid ${leaked ? "var(--block)" : "var(--allow)"}` }}
          >
            Secret leaked: {leaked ? "YES" : "NO"}
          </span>
        )}
      </div>
      {loading && <p className="muted text-sm" aria-live="polite">Running the agent… (free models can take 10–40 s)</p>}
      {error && <p className="text-sm" style={{ color: "var(--block)" }}>{error}</p>}
      {!loading && !result && !error && <Empty>Not run yet.</Empty>}
      {result && (
        <>
          <div>
            <p className="muted mb-1 text-xs uppercase tracking-wide">Agent answer</p>
            <p className="whitespace-pre-wrap text-sm">{result.answer || <span className="muted">(no answer{result.error ? `: ${result.error}` : ""})</span>}</p>
          </div>
          <div>
            <p className="muted mb-1 text-xs uppercase tracking-wide">Tool calls</p>
            {result.steps.length === 0 ? (
              <p className="muted text-sm">None</p>
            ) : (
              <ul className="space-y-1">
                {result.steps.map((s, i) => (
                  <li key={i} className="rounded-md p-2 text-sm" style={{ background: "var(--panel-2)" }}>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="mono font-semibold">{s.tool}</span>
                      <DecisionBadge decision={s.allowed ? "ALLOW" : "BLOCK"} />
                    </div>
                    <p className="mono muted mt-1 break-words">{JSON.stringify(s.args)}</p>
                    {s.notice && <p className="mt-1 text-xs" style={{ color: "var(--block)" }}>{s.notice}</p>}
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div>
            <p className="muted mb-1 text-xs uppercase tracking-wide">Sandbox outbox ({result.outbox.length})</p>
            {result.outbox.length === 0 ? (
              <p className="muted text-sm">Empty</p>
            ) : (
              <ul className="space-y-1">
                {result.outbox.map((m, i) => (
                  <li key={i} className="mono rounded-md p-2" style={{ background: "var(--panel-2)" }}>
                    to: {m.to} · {m.subject}
                  </li>
                ))}
              </ul>
            )}
          </div>
          <p className="muted text-xs">
            Model: {result.model ?? "—"}
            {blocked.length ? ` · ${blocked.length} action(s) stopped` : ""}
            {result.session_id && (
              <>
                {" · "}
                <Link className="underline" to={`/replay?session=${result.session_id}`}>Open full replay</Link>
              </>
            )}
          </p>
        </>
      )}
    </div>
  );
}

export function Playground() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [off, setOff] = useState<DemoResult | null>(null);
  const [on, setOn] = useState<DemoResult | null>(null);
  const [loading, setLoading] = useState<{ off: boolean; on: boolean }>({ off: false, on: false });
  const [err, setErr] = useState<{ off: string | null; on: string | null; list: string | null }>({ off: null, on: null, list: null });

  useEffect(() => {
    api.scenarios()
      .then((s) => {
        setScenarios(s);
        if (s.length) setSelected(s[0].id);
      })
      .catch((e) => setErr((x) => ({ ...x, list: String(e.message) })));
  }, []);

  const scenario = scenarios.find((s) => s.id === selected);

  async function run(mode: "off" | "on") {
    setLoading((l) => ({ ...l, [mode]: true }));
    setErr((x) => ({ ...x, [mode]: null }));
    try {
      const r = await api.run(selected, mode);
      (mode === "off" ? setOff : setOn)(r);
    } catch (e) {
      setErr((x) => ({ ...x, [mode]: (e as Error).message }));
    } finally {
      setLoading((l) => ({ ...l, [mode]: false }));
    }
  }

  async function runBoth() {
    setOff(null);
    setOn(null);
    await run("off");
    await run("on");
  }

  return (
    <>
      <Section
        title="Playground"
        subtitle="Run the same task on the same agent, unprotected and protected. Everything runs in a sandbox with fake secrets."
      >
        {err.list && <p className="text-sm" style={{ color: "var(--block)" }}>Could not load scenarios: {err.list}</p>}
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex w-full min-w-0 flex-col gap-1 text-sm sm:w-auto sm:flex-1">
            <span className="muted">Scenario</span>
            <select className="input" value={selected} onChange={(e) => { setSelected(e.target.value); setOff(null); setOn(null); }}>
              {scenarios.map((s) => (
                <option key={s.id} value={s.id}>{s.id} · {s.title}</option>
              ))}
            </select>
          </label>
          <button className="btn btn-primary" disabled={!selected || loading.off || loading.on} onClick={runBoth}>Run OFF then ON</button>
          <button className="btn" disabled={!selected || loading.off} onClick={() => run("off")}>Protection OFF</button>
          <button className="btn" disabled={!selected || loading.on} onClick={() => run("on")}>Protection ON</button>
        </div>
        {scenario && (
          <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
            <span className="muted">Channel:</span> <Label>{scenario.channel ?? "user"}</Label>
            {scenario.attack_types?.length ? <span className="muted">Attack types:</span> : null}
            {scenario.attack_types?.map((t) => <Label key={t}>{t}</Label>)}
            {scenario.task && <p className="muted w-full">Task: “{scenario.task}”</p>}
          </div>
        )}
        {!scenarios.length && !err.list && <div className="mt-3"><Empty>No scenarios installed yet (eval/scenarios/*.yaml).</Empty></div>}
      </Section>

      <div className="flex flex-col gap-4 md:flex-row">
        <RunPanel title="Protection OFF" result={off} loading={loading.off} error={err.off} />
        <RunPanel title="Protection ON" result={on} loading={loading.on} error={err.on} />
      </div>

      {on && on.events.length > 0 && (
        <Section title="What the gateway saw and decided" subtitle="Click any step for the exact span, attack type, tier and rule.">
          <Timeline events={on.events} />
        </Section>
      )}
    </>
  );
}
