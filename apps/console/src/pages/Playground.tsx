import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, PRODUCT_NAME, type DemoResult, type Scenario } from "../api";
import { Timeline } from "../components/Timeline";
import { Card, CardTitle, DecisionBadge, Dot, Empty, ErrorNote, Loading, PageHeader, Tag } from "../components/ui";

type Mode = "off" | "on";
const HOLDS = new Set(["budget-hold", "judge-unavailable-hold", "extraction-failed"]);

function Lane({ mode, result, loading, error, proxy }: { mode: Mode; result: DemoResult | null; loading: boolean; error: string | null; proxy: boolean }) {
  const on = mode === "on";
  const leaked = result ? result.canary_leaked || result.external_sends > 0 : null;
  const steps = result?.steps ?? [];
  const stopped = steps.filter((s) => !s.allowed).length;
  const events = result?.events ?? [];
  const held = events.some((e) => HOLDS.has(e.policy_rule ?? ""));
  const contained = events.filter((e) => e.decision && e.decision !== "ALLOW" && !HOLDS.has(e.policy_rule ?? "")).length;
  const headline = leaked ? "Data left the sandbox."
    : !on ? "Nothing left the sandbox this time."
    : held ? "Held safely: an AI check was unavailable."
    : contained ? `Contained by policy (${contained} decision${contained > 1 ? "s" : ""}).`
    : "Allowed. Nothing needed containing.";
  return (
    <article className={on ? "border-t pt-8 hairline md:border-l md:border-t-0 md:pl-10 md:pt-0" : ""} aria-busy={loading}>
      <div className="flex items-center gap-2 text-[13px]"><Dot tone={on ? "allow" : "block"} />{on ? `With ${PRODUCT_NAME}` : proxy ? "Monitor mode (logged, not enforced)" : "Without protection"}</div>
      {loading && <p className="subtle mt-5 text-sm" aria-live="polite">Running the agent… free models can take 10–40 s.</p>}
      {error && <div className="mt-5"><ErrorNote>{error}</ErrorNote></div>}
      {!loading && !result && !error && <p className="subtle mt-5 text-sm">Not run yet.</p>}
      {result && !loading && (
        <>
          <h3 className="h3 my-4" style={{ color: leaked ? "var(--block)" : held ? "var(--neutralise)" : "var(--allow)" }}>{headline}</h3>
          {held && <p className="subtle text-xs">Fail-safe: flagged content is held until it can be assessed (judge unavailable or daily budget reached). See the replay for the rule.</p>}
          <p className="text-xs" style={{ color: leaked ? "var(--block)" : "var(--allow)" }}>
            Secret leaked: {result.canary_leaked ? "YES" : "NO"} · external sends: {result.external_sends}{stopped ? ` · ${stopped} action(s) stopped` : ""}
          </p>
          <div className="mt-6">
            <p className="section-label mb-2">Agent answer</p>
            <p className="m-0 whitespace-pre-wrap text-[13px] leading-6">{result.answer || <span className="subtle">(no answer{result.error ? `: ${result.error}` : ""})</span>}</p>
          </div>
          {!proxy && (
            <div className="mt-6">
              <p className="section-label mb-2">Tool calls</p>
              {steps.length === 0 ? <p className="subtle text-[13px]">None</p> : (
                <ul className="m-0 list-none space-y-2 p-0">
                  {steps.map((s, i) => (
                    <li key={i} className="well p-3">
                      <div className="flex flex-wrap items-center gap-2"><span className="mono">{s.tool}</span><DecisionBadge decision={s.allowed ? "ALLOW" : "BLOCK"} /></div>
                      <p className="mono subtle mt-1 break-words">{JSON.stringify(s.args)}</p>
                      {s.notice && <p className="mt-1 text-xs" style={{ color: "var(--block)" }}>{s.notice}</p>}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
          <div className="mt-6">
            <p className="section-label mb-2">Sandbox outbox ({result.outbox.length})</p>
            {result.outbox.length === 0 ? <p className="subtle text-[13px]">Empty</p> : (
              <ul className="m-0 list-none space-y-2 p-0">
                {result.outbox.map((m, i) => <li key={i} className="mono well p-3">to: {m.to} · {m.subject}</li>)}
              </ul>
            )}
          </div>
          <p className="subtle mt-6 text-xs">
            {result.model ? `Model: ${result.model}` : result.agent_id ? `Agent policy: ${result.agent_id}` : ""}
            {result.session_id && <> · <Link className="text-link" to={`/replay?session=${result.session_id}`}>Replay this session</Link></>}
          </p>
        </>
      )}
    </article>
  );
}

export function Playground() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selected, setSelected] = useState("");
  const [res, setRes] = useState<Record<Mode, DemoResult | null>>({ off: null, on: null });
  const [loading, setLoading] = useState<Record<Mode, boolean>>({ off: false, on: false });
  const [err, setErr] = useState<Record<Mode | "list", string | null>>({ off: null, on: null, list: null });
  const [listLoading, setListLoading] = useState(true);

  useEffect(() => {
    api.scenarios()
      .then((s) => { setScenarios(s); if (s.length) setSelected(s[0].id); })
      .catch((e) => setErr((x) => ({ ...x, list: (e as Error).message })))
      .finally(() => setListLoading(false));
  }, []);

  const scenario = scenarios.find((s) => s.id === selected);
  const proxy = scenario?.surface === "proxy";
  const busy = loading.off || loading.on;

  async function run(mode: Mode) {
    setLoading((l) => ({ ...l, [mode]: true }));
    setErr((x) => ({ ...x, [mode]: null }));
    try {
      const r = await api.run(selected, mode);
      setRes((x) => ({ ...x, [mode]: r }));
    } catch (e) {
      setErr((x) => ({ ...x, [mode]: (e as Error).message }));
    } finally {
      setLoading((l) => ({ ...l, [mode]: false }));
    }
  }

  async function runBoth() {
    setRes({ off: null, on: null });
    await run("off");
    await run("on");
  }

  return (
    <div className="space-y-10">
      <PageHeader index="01" label="Protection in action" title={<>One task. Two very<br />different outcomes.</>}
        lede="Run the same scenario on the same agent, unprotected and protected. Everything runs in a sandbox with fake secrets: no real email, no external calls." />

      <Card>
        {err.list && <ErrorNote>Could not load scenarios: {err.list}</ErrorNote>}
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end">
          <label className="flex min-w-0 flex-1 flex-col gap-2 text-xs">
            <span className="section-label">Scenario</span>
            <select className="input" value={selected} onChange={(e) => { setSelected(e.target.value); setRes({ off: null, on: null }); }}>
              {scenarios.map((s) => <option key={s.id} value={s.id}>{s.id} · {s.title}</option>)}
            </select>
          </label>
          <div className="flex flex-wrap gap-3">
            <button className="pill pill-primary" disabled={!selected || busy} onClick={runBoth}>Run without, then with</button>
            <button className="pill" disabled={!selected || loading.off} onClick={() => run("off")}>{proxy ? "Monitor only" : "Without"}</button>
            <button className="pill" disabled={!selected || loading.on} onClick={() => run("on")}>With {PRODUCT_NAME}</button>
          </div>
        </div>
        {scenario && (
          <div className="mt-5 flex flex-wrap items-center gap-2 text-xs">
            <Tag>{proxy ? "LLM proxy · unmodified OpenAI-SDK agent" : `channel: ${scenario.channel ?? "user"}`}</Tag>
            {scenario.attack_types?.map((t) => <Tag key={t}>{t}</Tag>)}
            {scenario.task && <p className="subtle m-0 w-full pt-2">Task: “{scenario.task}”</p>}
            {scenario.source && <p className="subtle m-0 w-full">Content: {scenario.source}</p>}
          </div>
        )}
        {listLoading && <div className="mt-4"><Loading>Loading scenarios…</Loading></div>}
        {!listLoading && !scenarios.length && !err.list && <div className="mt-4"><Empty>No scenarios installed yet (eval/scenarios/*.yaml).</Empty></div>}
      </Card>

      <section aria-label="Comparison">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b pb-4 text-xs hairline" style={{ color: "var(--muted)" }}>
          <span>Same task. Same agent. Same input.</span>
          {scenario?.expected && <span className="tag">Expected: {scenario.expected.on}</span>}
        </div>
        <div className="grid gap-10 py-8 md:grid-cols-2">
          <Lane mode="off" result={res.off} loading={loading.off} error={err.off} proxy={proxy} />
          <Lane mode="on" result={res.on} loading={loading.on} error={err.on} proxy={proxy} />
        </div>
      </section>

      {res.on && res.on.events.length > 0 && (
        <Card>
          <CardTitle meta="Open any step for the exact span, attack type, tier and rule.">What {PRODUCT_NAME} saw and decided</CardTitle>
          <Timeline events={res.on.events} />
        </Card>
      )}
    </div>
  );
}
