import { useEffect, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { AGENT, api, PRODUCT_NAME, type Summary } from "../api";
import { SectionLink } from "../components/LandingNav";
import { useBackendAvailability } from "../components/Layout";
import { Arrow, Dot, pct, useAsync } from "../components/ui";

function headline(s: Summary | null) {
  return s?.e2e.find((x) => x.suite === "headline") ?? s?.e2e[0] ?? null;
}

function DemoCTA({ children = "Try the live demo" }: { children?: ReactNode }) {
  return <Link to="/playground" className="pill pill-primary">{children}<Arrow /></Link>;
}

function Section({ id, title, label, children }: { id: string; title: ReactNode; label: string; children: ReactNode }) {
  return <section id={id} tabIndex={-1} className="landing-section" aria-labelledby={`${id}-title`}>
    <div className="landing-section-heading"><p className="landing-label">{label}</p><h2 id={`${id}-title`}>{title}</h2></div>{children}
  </section>;
}

function Hero({ s, loading, error, retry, waking }: { s: Summary | null; loading: boolean; error: string | null; retry: () => void; waking: boolean }) {
  const e = headline(s);
  const metrics = [
    { value: pct(e?.on.asr), label: e ? `Protected attack success · ${e.on.scored} scored tests` : "Protected attack success" },
    { value: s?.utility ? `${Math.round(s.utility.on * s.utility.n)}/${s.utility.n}` : "—", label: "Legitimate tasks completed" },
    { value: s?.latency_isolated ? `${Math.round(s.latency_isolated.p95_ms)} ms` : "—", label: "Isolated fast-path latency · p95" },
  ];
  return <section className="hero canvas dark landing-hero" aria-labelledby="hero-title">
    <svg className="circuit" viewBox="0 0 1400 800" preserveAspectRatio="none" aria-hidden><path d="M0 185H235L290 130H730L775 175H1400M0 207H285L340 152H680L723 196H1400M0 600H205L260 545H590M0 628H225L280 573H635M890 630H1090L1160 560H1400" /></svg>
    <div className="landing-hero-copy">
      <span className="eyebrow"><i />Runtime security for AI agents</span>
      <h1 id="hero-title" className="display">Keep AI agents inside <span>the user’s intent.</span></h1>
      <p className="lede">Let your agents work. Keep their boundaries intact. {PRODUCT_NAME} inspects untrusted content, checks intercepted tool calls against your policy, and records the evidence behind every decision.</p>
      <div className="landing-actions"><DemoCTA>See protection in action</DemoCTA><SectionLink id="how" className="text-link">How it works</SectionLink></div>
      <p className="landing-microcopy">No sign-in required for the sandbox. Fake secrets. No real sends.</p>
      <div className="landing-hero-metrics" aria-label="Measured reference-agent evaluation results">{metrics.map((m) => <div key={m.label}><b className="num">{m.value}</b><small>{m.label}</small></div>)}</div>
      <div className="landing-provenance" aria-live="polite">
        {waking ? <span>{s ? "Showing last loaded figures. " : ""}The backend is waking up. This can take 2–3 minutes; figures refresh automatically when it is online.</span>
          : error ? <><span>{s ? "Showing last loaded figures. " : ""}Evaluation service unavailable.</span> <button className="text-link" onClick={retry} disabled={loading}>{loading ? "Retrying…" : "Retry"}</button></>
          : loading && !s ? "Loading the evaluation…" : !s ? "No evaluation report published for this agent yet."
          : <>{e?.suite} suite · evaluated {s.date} · <Link to="/results" className="text-link">Method and limits</Link></>}
      </div>
    </div>
    <picture><source media="(max-width: 860px)" srcSet={`${import.meta.env.BASE_URL}intentseal-gate-900.webp`} /><img className="hero-art" src={`${import.meta.env.BASE_URL}intentseal-gate.webp`} alt="A dimensional security gate of frosted lavender tiles, with light passing through its protected centre." fetchPriority="high" /></picture>
    <span className="floating-label landing-hero-label">Untrusted content in. Policy-checked actions out.</span>
    <div className="landing-hero-bottom"><span>Rules decide. AI advises.</span><span>Inspect → Contain → Prove</span></div>
  </section>;
}

const PILLARS = [
  { label: "Inspect", title: "See what the model sees.", copy: "Extract supported documents, pages, email, code, records and API responses, including hidden text and image OCR.", benefit: "Fewer overlooked input surfaces.", limit: "Extraction and OCR have limits; coverage is evaluated by channel." },
  { label: "Contain", title: "Enforce declared boundaries.", copy: "Check intercepted tool calls, recipients, domains, trusted identity fields and outbound sensitive values. Quarantine offending spans where they can be isolated safely.", benefit: "Limit the consequence of a hijacked agent.", limit: "Configured policy enforcement, not universal understanding of intent." },
  { label: "Prove", title: "Make the decision reviewable.", copy: "Connect the source finding, reason, named rule and action in an ordered session replay. Review eligible high-risk requests with context.", benefit: "Give reviewers evidence they can follow.", limit: "Reference-agent results do not automatically approve a production agent." },
];

function How() {
  return <Section id="how" label="One gateway. Three jobs." title={<>Inspect what enters. Constrain what leaves.<br />Prove what happened.</>}>
    <div className="landing-flow-panel" aria-label="Illustrative product flow"><div className="landing-flow-intro"><span className="tag">Illustrative flow</span><p>The user’s task: “Summarise the research report.”</p></div><ol>
      <li><span>01</span><div><b>Inspect the content</b><p>Extract what the model will actually read.</p></div></li>
      <li><span>02</span><div><b>Check the action boundary</b><p>Apply the configured tool and data policy.</p></div></li>
      <li><span>03</span><div><b>Follow the evidence</b><p>Source → finding → rule → decision → action.</p></div></li>
    </ol><p className="landing-microcopy">Only reads and actions routed through {PRODUCT_NAME} are checked.</p></div>
    <div className="landing-grid-three">{PILLARS.map((p) => <article key={p.label} className="landing-feature"><p className="landing-label">{p.label}</p><h3>{p.title}</h3><p>{p.copy}</p><div className="landing-benefit">{p.benefit}</div><p className="landing-microcopy">{p.limit}</p></article>)}</div>
  </Section>;
}

function Evidence({ s, error, loading, retry, waking }: { s: Summary | null; error: string | null; loading: boolean; retry: () => void; waking: boolean }) {
  const e = headline(s);
  const f = s?.fpr.holdout;
  return <Section id="evidence" label="Trust through transparency" title={<>Evidence you can inspect.<br />Limits you can see.</>}>
    <p className="landing-intro">A protection number means little without its test conditions. Compare attack outcomes, legitimate work and false alarms together.</p>
    <div className="landing-evidence-panel">
      {waking ? <p role="status" className="landing-warning">{s ? "These are the last loaded figures. " : ""}The backend is waking up. Results refresh automatically when it is online.</p>
        : error && <p role="status" className="landing-warning">{s ? "These are the last loaded figures. " : ""}The evaluation service is unavailable. <button className="text-link" disabled={loading} onClick={retry}>{loading ? "Retrying…" : "Retry evaluation"}</button></p>}
      <div className="landing-grid-three">
        <div><h3>Attack outcomes</h3><div className="landing-evidence-number num">{pct(e?.off.asr)} <span>→</span> {pct(e?.on.asr)}</div><p>Without → with protection</p><small>{e ? `${e.off.compromised}/${e.off.scored} → ${e.on.compromised}/${e.on.scored} successful attacks · ${e.suite} suite` : loading ? "Loading results…" : "No scored suite available"}</small></div>
        <div><h3>Legitimate work</h3><div className="landing-evidence-number num">{pct(s?.utility?.retention, 0)}</div><p>Benign task utility retained</p><small>{s?.utility ? `${s.utility.n} tasks · completion ${pct(s.utility.off, 0)} → ${pct(s.utility.on, 0)}` : "No utility report available"}</small></div>
        <div><h3>False alarms</h3><div className="landing-evidence-number num" style={{ color: f?.fpr != null && f.fpr > 0.05 ? "var(--neutralise)" : undefined }}>{pct(f?.fpr)}</div><p>Held-out benign set</p><small>{f ? `${f.false_alarms}/${f.n} cases · ${f.fpr == null ? "rate unavailable" : f.fpr > 0.05 ? "above the ≤5% target" : "within the ≤5% target"}` : "Held-out results unavailable; development results are not substituted"}</small></div>
      </div>
      <p className="landing-evidence-meta">{s ? <>Evaluated {s.date} · commit <code>{s.git_sha ?? "unavailable"}</code>{e && <> · {e.models.join(", ")}</>}</> : !error && !loading ? "No evaluation report has been published for this agent yet." : "Measured figures appear when the evaluation service is available."}</p>
      <p className="landing-warning">Finite reference-agent evaluation, not a guarantee against every attack.{s?.git_sha?.endsWith("-dirty") ? " A final release-commit run is pending." : ""}{s?.claim.F === "none" ? " Current results do not meet the PRD’s F/D claim rule." : ""} Fast-path latency is measured separately from AI judge latency.</p>
      <Link to="/results" className="pill">Every result, with its method and limits<Arrow /></Link>
    </div>
  </Section>;
}

const STORIES = [
  { id: "S7", label: "Secret Extraction", title: "A request for secrets.", copy: "Compare the sandbox runs, inspect any content or outbound decision, and open the protected replay. The unprotected model can resist." },
  { id: "S1", label: "Document inspection", title: "Hidden content in a report.", copy: "Review what extraction reveals and how non-visible content is handled. Follow any named quarantine or withholding rule." },
  { id: "S8", label: "Legitimate work", title: "A security article to summarise.", copy: "Check whether ordinary discussion of attacks remains usable. Inspect the actual output and any false alarm honestly." },
];

const FAQS = [
  ["Does IntentSeal solve prompt injection?", "No. It combines inspection, configured action boundaries and evidence. The evaluation is finite, and attacks can be missed."],
  ["What traffic is protected?", "Content and actions routed through the SDK, API or proxy. Uninstrumented reads and tool calls are outside the boundary. Proxy support applies to compatible clients."],
  ["Will legitimate content be blocked?", "It can be. The evaluation publishes false alarms and utility. Start in monitor mode, review outcomes, and test your workflows before enforcing."],
  ["What is the difference between monitor and enforce?", "Monitor records decisions without applying them. Enforce applies decisions to intercepted content and actions. Monitor is observation, not prevention."],
  ["What happens when an AI check is unavailable?", "The rules continue. Content requiring an unavailable assessment can be held and marked degraded. Inspect the named rule in replay; behavior depends on the policy and integration."],
  ["Are hidden document text and images supported?", "Supported document formats have extractors, including hidden text. Images are covered through OCR text, not full visual understanding. Coverage and limitations vary by channel."],
  ["Does protection add latency or model cost?", "Yes. Fast-path and judge-path overhead differ. Results show measured conditions. Fast-path latency is not a guarantee for the full judged request, and free quotas do not mean deployment has no costs."],
  ["Where does inspected data go?", "Content is extracted locally; suspicious or policy-selected text can be sent to a configured judge provider. Logs store hashes and redacted previews, and preview storage can be disabled. This is not an all-data-stays-local promise."],
  ["Can a reviewer override every block?", "No. Eligible escalated requests can be approved once for the same session and arguments. Approval cannot override a block."],
  ["Can I use it in production today?", "Review the published coverage and limitations. Evaluate compatibility, policy coverage, privacy, reliability and false alarms on your agent before a production decision. Commercial service commitments are not announced."],
];

function Integrate() {
  return <Section id="integrate" label="Built around your workflow" title={<>Start at the boundary<br />that fits your agent.</>}>
    <p className="landing-intro">Choose the integration that fits your application. Configure the gateway and your agent’s policy, then make a monitored request before enforcing.</p>
    <div className="landing-grid-three">
      <article className="landing-card"><p className="landing-label">Compatible clients</p><h3>LLM proxy</h3><p>Point an OpenAI-compatible client at the gateway. Inspect messages and returned tool calls passing through it.</p><code className="landing-code">OPENAI_BASE_URL=&lt;gateway&gt;/proxy/research-agent/v1</code><p className="landing-microcopy">Verify client and tool compatibility. Use your own configured project key.</p></article>
      <article className="landing-card"><p className="landing-label">Deep instrumentation</p><h3>Python SDK</h3><p>Add session context, inspect each relevant loader, and wrap the tools that can act.</p><code className="landing-code">guard.inspect(raw, source="pdf")<br />guard.protect_tools(tools)</code><p className="landing-microcopy">Input inspection and tool wrapping protect their respective checkpoints.</p></article>
      <article className="landing-card"><p className="landing-label">Any language</p><h3>REST API</h3><p>Call the gateway from your application. Apply the returned decision before content or actions proceed.</p><code className="landing-code">POST /v1/inspect<br />POST /v1/actions/check</code><p className="landing-microcopy">The caller must enforce the decision before executing an action.</p></article>
    </div>
    <div className="landing-setup"><h3>Your first protected session</h3><ol><li><b>Configure the gateway.</b> Run your deployment, configure provider credentials and issue a project key. Keep project keys on your application server.</li><li><b>Set your agent’s policy.</b> Declare allowed tools, recipients, domains and trusted fields. Start in monitor mode.</li><li><b>Connect and test.</b> Use the proxy base URL, SDK or API. Inspect the recorded session and false alarms before enforcing.</li></ol><Link to="/policy" className="text-link">Explore the reference agent’s policy</Link><p className="landing-microcopy">The public sandbox uses the reference agent. It does not issue project keys or connect your own agent.</p></div>
  </Section>;
}

export function Overview() {
  const backendStatus = useBackendAvailability();
  const waking = backendStatus === "checking" || backendStatus === "waking";
  const { data, error, loading, reload } = useAsync(() => api.scorecard(AGENT).then((r) => r.summary), []);
  useEffect(() => {
    // Also refresh successful-but-empty responses and previously loaded figures.
    if (backendStatus === "ok") reload();
  }, [backendStatus, reload]);
  useEffect(() => {
    if (!error) return;
    const timer = setInterval(() => { if (!document.hidden) reload(); }, 15000);
    return () => clearInterval(timer);
  }, [error, reload]);
  const s = data ?? null;
  return <div className="landing-page">
    <Hero s={s} loading={loading} error={error} retry={reload} waking={waking} />
    <div className="landing-content">
      <div className="landing-trust" aria-label="Verifiable product capabilities">{["Reproducible evaluation", "Named policy rules", "Redacted session replay", "Monitor before enforce"].map((text) => <span key={text}><span aria-hidden>✓</span>{text}</span>)}</div>
      <p className="landing-microcopy landing-trust-note">Results and limitations are published together.</p>
      <Section id="problem" label="The problem is a change of direction" title={<>The user asked for a summary.<br />Outside content can ask for something else.</>}>
        <p className="landing-intro">Documents, web pages, emails and tool results can contain instructions the user never authorized. When an agent can act, that change of direction can become a send, a fetch, a record access or a file write.</p>
        <div className="landing-grid-two landing-story-lanes"><article><span className="landing-lane-label"><Dot tone="block" />Without an enforced boundary · conceptual</span><h3>An input can become an action.</h3><p className="landing-flow">Outside content → Agent interpretation → Possible unauthorized action</p><p>The model may resist. A policy boundary gives you another control.</p></article><article><span className="landing-lane-label"><Dot tone="allow" />{PRODUCT_NAME} in the path · conceptual</span><h3>Every intercepted action meets a policy.</h3><p className="landing-flow">Inspect content → Enforce tool policy → Record the decision</p><p>Inspect the actual outcome in a sandbox comparison and replay.</p></article></div><DemoCTA>Compare a sandbox run</DemoCTA>
      </Section>
      <How />
      <section className="landing-section landing-grid-two" aria-label="Benefits for builders and reviewers"><article><p className="landing-label">For agent builders</p><h2>Protect the agent<br />you already have.</h2><p>Choose the integration that fits. Observe in monitor mode, review false alarms, then test your workflows before enforcing.</p><SectionLink id="integrate" className="text-link">Explore integration paths</SectionLink></article><article><p className="landing-label">For security reviewers</p><h2>Review a decision,<br />with its evidence.</h2><p>See the source finding, exact rule and redacted action arguments. Eligible escalated actions can be approved once, with context.</p><Link to="/review" className="text-link">Explore the review console</Link></article></section>
      <Evidence s={s} loading={loading} error={error} retry={reload} waking={waking} />
      <Section id="stories" label="Reference-agent evaluation stories" title={<>Explore the decisions<br />behind the outcome.</>}><p className="landing-intro">These are sandbox scenarios, not customer case studies. Run a scenario and inspect what actually happens.</p><div className="landing-grid-three">{STORIES.map((story) => <article className="landing-card landing-story-card" key={story.id}><p className="landing-label">{story.id} · {story.label}</p><h3>{story.title}</h3><p>{story.copy}</p><Link to={`/playground?scenario=${story.id}`} className="text-link">Explore scenario {story.id}</Link></article>)}</div></Section>
      <Integrate />
      <Section id="pricing" label="Availability and pricing status" title={<>Try the sandbox.<br />Know what is available.</>}><p className="landing-intro">Commercial plans and pricing have not been announced. There is no payment form in the public sandbox.</p><div className="landing-grid-two"><article className="landing-card"><span className="tag">Explore the product</span><h3 className="landing-plan-title">Public sandbox demo</h3><ul><li>No sign-in required</li><li>Reference agent and fake data</li><li>Sandboxed actions and replay</li></ul><p>Availability depends on backend and model quotas.</p><DemoCTA /></article><article className="landing-card"><span className="tag">Assess the fit</span><h3 className="landing-plan-title">Your own integration</h3><ul><li>SDK, proxy and REST paths implemented</li><li>Test in monitor mode before enforcing</li><li>Commercial pricing not announced</li></ul><p>Hosting and model use may incur costs outside the sandbox. Confirm deployment and license terms before adoption.</p><SectionLink id="integrate" className="pill">Read integration steps<Arrow /></SectionLink></article></div></Section>
      <Section id="faq" label="Before you decide" title="The questions worth asking."><div className="landing-faq">{FAQS.map(([question, answer]) => <details key={question}><summary>{question}<span aria-hidden>+</span></summary><p>{answer}</p></details>)}</div></Section>
      <section className="landing-closing" aria-labelledby="closing-title"><p className="landing-label">Inspect. Contain. Prove.</p><h2 id="closing-title">See the boundary.<br />Follow the evidence.</h2><p>Run a sandbox comparison, then open the session replay to see what {PRODUCT_NAME} checked and why.</p><div className="landing-actions"><DemoCTA /><Link to="/results" className="pill">Read the evaluation<Arrow /></Link></div><p className="landing-microcopy">Fake secrets. No real sends. No sign-in required.</p></section>
    </div>
  </div>;
}
