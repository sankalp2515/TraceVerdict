import { Link } from "react-router-dom";
import { AGENT, api, PRODUCT_NAME, type Summary } from "../api";
import { Arrow, Dot, pct, useAsync } from "../components/ui";

function headline(s: Summary | null) {
  const e = s?.e2e.find((x) => x.suite === "headline") ?? s?.e2e[0];
  return e ?? null;
}

function ProofStrip({ s }: { s: Summary | null }) {
  const e = headline(s);
  const items = [
    { v: e ? pct(e.on.asr) : "—", l: e ? `Protected attack success · ${e.on.scored} tests` : "Protected attack success · pending" },
    { v: s?.utility ? `${Math.round(s.utility.on * s.utility.n)}/${s.utility.n}` : "—", l: "Legitimate tasks completed" },
    { v: s?.latency_isolated ? `${Math.round(s.latency_isolated.p95_ms)} ms` : "—", l: "Added latency · fast path p95" },
  ];
  return (
    <div className="mt-14 flex max-w-[640px] flex-wrap gap-y-6" aria-label="Measured evaluation results">
      {items.map((it, i) => (
        <div key={i} className={`pr-7 ${i < items.length - 1 ? "mr-7 border-r hairline" : ""}`}>
          <b className="num block text-[30px] font-normal tracking-tight" style={{ color: "var(--accent-soft)" }}>{it.v}</b>
          <small className="subtle mt-1 block text-[11px]">{it.l}</small>
        </div>
      ))}
    </div>
  );
}

function Hero({ s }: { s: Summary | null }) {
  return (
    <section className="hero canvas dark -mx-1 min-h-[680px] px-6 pb-8 pt-14 sm:px-12 md:pt-20" aria-labelledby="hero-title">
      <svg className="circuit" viewBox="0 0 1400 800" preserveAspectRatio="none" aria-hidden>
        <path d="M0 185H235L290 130H730L775 175H1400M0 207H285L340 152H680L723 196H1400M0 600H205L260 545H590M0 628H225L280 573H635M890 630H1090L1160 560H1400" />
      </svg>
      <div className="relative max-w-[680px] md:w-[58%]">
        <span className="eyebrow"><i /> Intelligent agent security</span>
        <h1 id="hero-title" className="display my-6">Keep AI agents inside{" "}<span className="md:block">the user’s intent.</span></h1>
        <p className="lede m-0 mb-7 max-w-[500px]">
          Let your agents work. Keep their boundaries intact. {PRODUCT_NAME} inspects untrusted content, contains hidden
          instructions and shows the evidence behind every decision.
        </p>
        <div className="flex flex-wrap items-center gap-6">
          <Link to="/playground" className="pill pill-primary">See protection in action<Arrow /></Link>
          <a href="#how" className="text-link">How it works</a>
        </div>
        <ProofStrip s={s} />
      </div>
      <picture>
        <source media="(max-width: 860px)" srcSet={`${import.meta.env.BASE_URL}intentseal-gate-900.webp`} />
        <img className="hero-art" src={`${import.meta.env.BASE_URL}intentseal-gate.webp`} alt="A dimensional security gate of frosted lavender tiles, with light passing through its protected centre." />
      </picture>
      <span className="floating-label absolute right-8 top-10 hidden md:inline-block">Untrusted content in. Authorized actions out.</span>
      <div className="relative mt-12 flex flex-wrap justify-between gap-4 border-t pt-5 text-[11px] hairline" style={{ color: "var(--subtle)" }}>
        <span>Rules decide. AI advises.</span>
        <span className="tracking-wide">Inspect → Contain → Prove</span>
      </div>
    </section>
  );
}

function Lanes() {
  return (
    <section id="demo" className="scroll-mt-24 pt-24" aria-labelledby="demo-title">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="section-label mb-4">01 / Protection in action</p>
          <h2 id="demo-title" className="h2">One task. Two very<br />different outcomes.</h2>
        </div>
        <p className="lede m-0 max-w-[340px] text-[13px]">
          An instruction hidden in a document asks the agent to send data outside the company. The user only asked for a summary.
        </p>
      </div>
      <div className="mt-9 flex flex-wrap items-center justify-between gap-3 border-b py-4 text-xs hairline" style={{ color: "var(--muted)" }}>
        <span>Same task. Same agent. Same input.</span>
        <span className="tag">Illustrative · run it live in the Playground</span>
      </div>
      <div className="grid gap-10 py-8 md:grid-cols-2 md:gap-11">
        <article>
          <div className="flex items-center gap-2 text-[13px]"><Dot tone="block" />Without protection</div>
          <h3 className="h3 my-4">A hidden instruction<br />becomes an unauthorized action.</h3>
          <div className="flow"><span>Document received</span><span className="arrow">→</span><span>Agent steered</span><span className="arrow">→</span><span>Data sent out</span></div>
          <p className="mt-5 text-xs" style={{ color: "var(--block)" }}>Secret leaked: YES · sandbox outbox</p>
        </article>
        <article className="border-t pt-8 hairline md:border-l md:border-t-0 md:pl-11 md:pt-0">
          <div className="flex items-center gap-2 text-[13px]"><Dot tone="allow" />With {PRODUCT_NAME}</div>
          <h3 className="h3 my-4">The attack is contained.<br />The legitimate work continues.</h3>
          <div className="flow"><span>Finding detected</span><span className="arrow">→</span><span>Neutralised</span><span className="arrow">→</span><span>Summary completed</span></div>
          <p className="mt-5 text-xs" style={{ color: "var(--allow)" }}>Secret leaked: NO · unauthorized action blocked</p>
          <span className="mono mt-3 block" style={{ color: "var(--accent-soft)" }}>rule: recipient-not-allowed · reason: outside the authorized domain</span>
        </article>
      </div>
      <Link to="/playground" className="pill">Run S1–S9 live<Arrow /></Link>
    </section>
  );
}

const STEPS = [
  { n: "01 — Inspect", t: "Know what entered.", d: "Extract what the model will actually read from PDFs, web pages, email, code, APIs, records and images, including text a human cannot see." },
  { n: "02 — Contain", t: "Keep the intent intact.", d: "Quarantine only the offending span. Check every tool call against deterministic rules, pinned fields and the user’s own request." },
  { n: "03 — Prove", t: "Leave nothing unexplained.", d: "Connect source, finding, rule, decision and action in one ordered record a reviewer can replay." },
];

function How() {
  return (
    <section id="how" className="scroll-mt-24 pt-24" aria-labelledby="how-title">
      <p className="section-label mb-4">02 / The control layer</p>
      <h2 id="how-title" className="h2">Every boundary has a reason.</h2>
      <div className="mt-11 grid gap-10 md:grid-cols-3">
        {STEPS.map((s) => (
          <article key={s.n} className="border-t pt-5 hairline">
            <span className="subtle text-[11px]">{s.n}</span>
            <h3 className="h3 mb-3 mt-5">{s.t}</h3>
            <p className="lede m-0 text-[13px]">{s.d}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function Results({ s }: { s: Summary | null }) {
  const e = headline(s);
  const fp = s?.fpr.holdout ?? s?.fpr.dev ?? null;
  return (
    <section id="results" className="mt-24 grid scroll-mt-24 gap-12 border-t pt-20 hairline md:grid-cols-2" aria-labelledby="results-title">
      <div>
        <p className="section-label mb-4">03 / Measured results</p>
        <h2 id="results-title" className="h2">The evidence behind<br />the promise.</h2>
        <p className="lede my-5 max-w-[400px] text-[13px]">
          {s ? <>Generated from the evaluation of {s.date} (commit <span className="mono">{s.git_sha}</span>). These figures describe the evaluated conditions; they do not guarantee protection against every attack.</>
             : "The latest evaluation summary is not available yet."}
        </p>
        <Link to="/results" className="text-link">Every number, with its method and limits</Link>
      </div>
      <div>
        <div className="num flex items-center gap-6 text-[clamp(40px,4vw,60px)] font-light tracking-tight">
          <span className="subtle">{e ? pct(e.off.asr) : "—"}</span>
          <i className="subtle text-[26px] not-italic">→</i>
          <span style={{ color: "var(--accent-soft)" }}>{e ? pct(e.on.asr) : "—"}</span>
        </div>
        <p className="subtle text-xs">Attack success · without protection → with protection{e ? ` · ${e.models.join(", ")}` : ""}</p>
        <div className="mt-7 grid grid-cols-3 gap-4 border-t pt-6 hairline">
          <div><b className="num block text-[23px] font-normal" style={{ color: "var(--accent-soft)" }}>{s?.utility ? pct(s.utility.retention, 0) : "—"}</b><small className="subtle text-[10px]">Legitimate work retained</small></div>
          <div><b className="num block text-[23px] font-normal" style={{ color: "var(--accent-soft)" }}>{pct(fp?.fpr)}</b><small className="subtle text-[10px]">False alarms · held-out set</small></div>
          <div><b className="num block text-[23px] font-normal" style={{ color: "var(--accent-soft)" }}>{e ? e.canary_leaks_on : "—"}</b><small className="subtle text-[10px]">Secrets leaked with protection</small></div>
        </div>
      </div>
    </section>
  );
}

const INTEGRATIONS = [
  { t: "Python SDK", d: "Inspection and action checks inside your agent’s own flow; LangChain / LangGraph tools in one line.", c: "tools = guard.protect_tools(tools)" },
  { t: "OpenAI-compatible proxy", d: "Point an unmodified agent at the gateway by changing one setting.", c: "OPENAI_BASE_URL=…/proxy/research-agent/v1" },
  { t: "REST API", d: "Inspect content and check actions from any language and runtime.", c: "POST /v1/inspect · POST /v1/actions/check" },
];

function Integrate() {
  return (
    <section id="integrate" className="mt-4 scroll-mt-24 border-t pt-14 hairline" aria-labelledby="integrate-title">
      <p className="section-label mb-4">04 / Built around your agent</p>
      <h2 id="integrate-title" className="h2">A boundary, wherever you build.</h2>
      <div className="mt-9 grid gap-8 md:grid-cols-3">
        {INTEGRATIONS.map((i) => (
          <article key={i.t}>
            <h3 className="text-[18px] font-normal">{i.t}</h3>
            <p className="lede my-3 text-xs">{i.d}</p>
            <code className="mono well block px-3 py-2" style={{ color: "var(--accent-text)" }}>{i.c}</code>
          </article>
        ))}
      </div>
    </section>
  );
}

export function Overview() {
  const { data } = useAsync(() => api.scorecard(AGENT).then((r) => r.summary), []);
  const s = data ?? null;
  return (
    <div>
      <Hero s={s} />
      <Lanes />
      <How />
      <Results s={s} />
      <Integrate />
      <aside className="mt-16 flex flex-col gap-4 border-t py-6 hairline md:flex-row md:gap-10">
        <b className="shrink-0 text-sm font-normal md:w-48" style={{ color: "var(--accent-text)" }}>Designed with honest limits.</b>
        <p className="subtle m-0 text-xs leading-7">
          Prompt injection is not solved. Every outcome carries a rule and evidence. “Degraded” means an AI check was
          unavailable and the rules held the content safely. Numbers below target are shown as they are.
        </p>
      </aside>
    </div>
  );
}
