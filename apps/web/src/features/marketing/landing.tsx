import { useState } from "react";
import {
  ArrowRight,
  Check,
  FileText,
  GitBranch,
  ShieldCheck,
  Menu,
  X,
  Search,
  LockKeyhole,
  Fingerprint,
  ChevronDown,
  ArrowUpRight,
} from "lucide-react";
import { Brand } from "@/components/tv/brand";
import heroImg from "@/assets/hero-evidence.jpg";

const faq = [
  [
    "What does TraceVerdict investigate?",
    "Suspicious tool actions by connected AI agents. A case connects the authorized task, untrusted input, attempted action, available policy snapshots and application receipts, then compares bounded policy recommendations.",
  ],
  [
    "Can I try it without connecting my agent?",
    "Yes. Open the recorded sample workspace without an account. The supplied synthetic reports contain real results from deterministic local sandbox tests. Recorded samples do not run a model or contact a real recipient.",
  ],
  [
    "Does an evidence graph prove what caused the action?",
    "No. The graph distinguishes observed records, inferred influence and case context. A document appearing before a tool call is not proof of causation. Every relationship exposes its basis and source records.",
  ],
  [
    "Will an approved repair change production?",
    "No. Approval binds the exact base policy, candidate and validation report. It produces a recommendation that a human can export. Applying it to a production system remains a separate operation.",
  ],
  [
    "What happens when evidence or a provider is unavailable?",
    "Missing snapshots, unknown execution outcomes and provider errors stay visible. A live case never silently becomes a sample. Incomplete validation cannot become an approved recommendation.",
  ],
  [
    "How do I connect an existing deployment?",
    "Use a scoped workspace access key in the workspace sign-in. The browser communicates only with the TraceVerdict backend using an HttpOnly session. Sponsor credentials remain on the server.",
  ],
];
export function Landing() {
  const [menu, setMenu] = useState(false);
  return (
    <div className="landing">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <div className="gate-line" />
      <header className="site-header">
        <div className="site-container header-inner">
          <Brand />
          <nav aria-label="Main navigation" className={menu ? "site-nav is-open" : "site-nav"}>
            <a href="#product" onClick={() => setMenu(false)}>
              The product
            </a>
            <a href="#workflow" onClick={() => setMenu(false)}>
              How it works
            </a>
            <a href="#assurance" onClick={() => setMenu(false)}>
              Built on evidence
            </a>
            <a href="#access" onClick={() => setMenu(false)}>
              Access
            </a>
          </nav>
          <a
            className="button button-dark header-cta"
            href="/workspace?mode=recorded&case=supplier-contact"
          >
            Open workspace <ArrowUpRight size={15} />
          </a>
          <button
            className="menu-toggle icon-button"
            aria-label={menu ? "Close menu" : "Open menu"}
            aria-expanded={menu}
            onClick={() => setMenu(!menu)}
          >
            {menu ? <X /> : <Menu />}
          </button>
        </div>
      </header>
      <main id="main">
        <section className="site-container hero">
          <div className="hero-copy">
            <div className="intro-line">
              <span />
              Agent investigation, with a paper trail
            </div>
            <h1>
              A conclusion
              <br />
              you can inspect.
            </h1>
            <p>
              Know what your AI agent attempted. Understand what actually ran. Test a policy repair
              before a human approves it.
            </p>
            <div className="button-row">
              <a
                className="button button-dark"
                href="/workspace?mode=recorded&case=supplier-contact"
              >
                Start the guided demo <ArrowRight size={17} />
              </a>
              <a className="text-link" href="#workflow">
                See how it works <ChevronDown size={15} />
              </a>
            </div>
            <div className="hero-footnote">
              <LockKeyhole size={14} />
              No sign-up. Guided example. No production changes.
            </div>
          </div>
          <figure className="hero-art">
            <div className="figure-corner">The evidence, connected.</div>
            <img
              src={heroImg.replace(/\?.*$/, "")}
              width="1600"
              height="1000"
              fetchPriority="high"
              alt="A forensic dossier with a magnifying lens and connected evidence records"
            />
            <figcaption>
              <span>
                <Fingerprint size={16} /> Traceable by design
              </span>
              <span>Evidence → explanation → review</span>
            </figcaption>
          </figure>
        </section>
        <section className="principle-strip">
          <div className="site-container">
            <span>
              <FileText />
              Every claim carries its source
            </span>
            <span>
              <GitBranch />
              Uncertainty stays visible
            </span>
            <span>
              <ShieldCheck />
              Every recommendation ends with a human
            </span>
          </div>
        </section>
        <section className="site-container story-section" id="product">
          <div className="section-intro">
            <p className="section-label">The gap between a log and an answer</p>
            <h2>
              Your agent acted.
              <br />
              Now make sense of it.
            </h2>
            <p>
              One suspicious action can leave a trail across prompts, documents, policies and tools.
              TraceVerdict brings that trail into one case, so you can decide what to do next.
            </p>
          </div>
          <div className="story-rows">
            {[
              {
                Icon: Search,
                title: "Reconstruct the incident",
                text: "Read the user’s original intent beside the document, attempted tool call and execution receipt. An attempt and an execution stay separate.",
              },
              {
                Icon: GitBranch,
                title: "Challenge the explanation",
                text: "Follow each claim back to its sources. Inspect the critic’s challenge, competing explanations and what the evidence cannot establish.",
              },
              {
                Icon: ShieldCheck,
                title: "Repair without disabling the task",
                text: "Compare exact policy changes against both unsafe actions and legitimate work. A repair has to earn its place in review.",
              },
            ].map(({ Icon, title, text }) => (
              <article key={title}>
                <span className="line-icon">
                  <Icon size={23} />
                </span>
                <div>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </div>
              </article>
            ))}
          </div>
        </section>
        <section className="workflow-section" id="workflow">
          <div className="site-container">
            <div className="split-heading">
              <div>
                <p className="section-label">From incident to informed decision</p>
                <h2>
                  Follow the evidence.
                  <br />
                  Keep the judgment.
                </h2>
              </div>
              <p>
                A focused investigation workflow.
                <br />
                Every step leaves something you can inspect.
              </p>
            </div>
            <div className="workflow-steps">
              {[
                ["Collect", "Gather the task, source records, policy and application receipt."],
                ["Explain", "Build source-linked claims and distinguish fact from inference."],
                ["Challenge", "Expose unsupported conclusions and missing evidence."],
                ["Validate", "Replay bounded repairs against unsafe and legitimate tasks."],
                ["Review", "Approve the exact artifact. Export the recommendation."],
              ].map(([title, text], i) => (
                <article key={title}>
                  <span className="step-number">0{i + 1}</span>
                  <h3>{title}</h3>
                  <p>{text}</p>
                  {i < 4 && <ArrowRight className="step-arrow" size={18} />}
                </article>
              ))}
            </div>
            <div className="workflow-note">
              <LockKeyhole size={17} />
              <p>
                Models investigate and propose. Deterministic tests gate review. Humans approve.
              </p>
            </div>
          </div>
        </section>
        <section className="site-container sample-section">
          <div className="sample-dossier">
            <div className="dossier-top">
              <span>
                <span className="status-dot" />
                Recorded sample
              </span>
              <span>Supplier contact</span>
            </div>
            <div className="dossier-body">
              <p className="section-label">The task</p>
              <blockquote>
                “Summarize the supplier report.
                <br />
                Do not contact anyone.”
              </blockquote>
              <div className="dossier-event">
                <FileText size={18} />
                <div>
                  <strong>A document asks the agent to send.</strong>
                  <p>The sandbox application reports execution.</p>
                </div>
              </div>
              <div className="dossier-result">
                <GitBranch size={18} />
                <span>
                  The broad restriction fails utility.
                  <br />
                  <strong>The intent-contract repair passes its configured tests.</strong>
                </span>
              </div>
            </div>
            <a href="/workspace?mode=recorded&case=supplier-contact" className="dossier-link">
              Inspect the supplied report <ArrowUpRight size={18} />
            </a>
          </div>
          <div className="sample-copy">
            <p className="section-label">A case you can open</p>
            <h2>
              The best proof
              <br />
              is the record itself.
            </h2>
            <p>
              A supplier report contains an instruction the user never authorized. See how the
              recorded investigation qualifies the explanation and compares two policy repairs.
            </p>
            <ul className="check-list">
              <li>
                <Check />
                Inspect the source and execution receipt
              </li>
              <li>
                <Check />
                See why the disruptive repair was rejected
              </li>
              <li>
                <Check />
                Read paired safety and legitimate-task results
              </li>
            </ul>
            <p className="fine-print">
              Synthetic local sandbox. Recorded deterministic results, no live model inference.
              Passing a configured suite is not a universal safety guarantee.
            </p>
            <a className="text-link" href="/workspace?mode=recorded&case=supplier-contact">
              Open the investigation <ArrowRight size={16} />
            </a>
          </div>
        </section>
        <section className="assurance-section" id="assurance">
          <div className="site-container">
            <div className="section-intro">
              <p className="section-label">Trust is a design constraint</p>
              <h2>
                Nothing hidden
                <br />
                between fact and finding.
              </h2>
              <p>
                Designed for the engineer who has to explain the decision, and the reviewer who has
                to stand behind it.
              </p>
            </div>
            <div className="assurance-grid">
              {[
                [
                  "Sources, not just summaries",
                  "Open source locators, versions, hashes and available query receipts behind the finding.",
                ],
                [
                  "Clear execution outcomes",
                  "Withheld, unconfirmed, application-reported executed and contradiction have distinct meanings.",
                ],
                [
                  "Exact artifacts, explicit approval",
                  "Review the base policy, candidate patch and report hashes together. Approval produces a recommendation.",
                ],
                [
                  "Failure stays visible",
                  "Unavailable providers and missing evidence remain incomplete. Live failures never turn into passing samples.",
                ],
              ].map(([title, text]) => (
                <article key={title}>
                  <ShieldCheck size={22} />
                  <h3>{title}</h3>
                  <p>{text}</p>
                </article>
              ))}
            </div>
            <div className="foundation-line">
              <span>Built on IntentSeal</span>
              <span>Zetaris evidence access</span>
              <span>Meterless World Model</span>
              <span>Nightshift reasoning in live mode</span>
            </div>
          </div>
        </section>
        <section className="site-container access-section" id="access">
          <div>
            <p className="section-label">Start with a case</p>
            <h2>
              Inspect first.
              <br />
              Connect when you’re ready.
            </h2>
            <p>Choose the path that fits your evaluation.</p>
          </div>
          <div className="access-options">
            <article>
              <span className="section-label">Explore</span>
              <h3>Recorded samples</h3>
              <p>
                Three synthetic cases. Evidence, policy comparisons and the supplied test reports.
              </p>
              <span className="access-price">No account required</span>
              <a
                className="button button-dark"
                href="/workspace?mode=recorded&case=supplier-contact"
              >
                Explore samples <ArrowUpRight size={16} />
              </a>
            </article>
            <article>
              <span className="section-label">Connect</span>
              <h3>Your workspace</h3>
              <p>
                Use an existing TraceVerdict deployment with a scoped project or reviewer access
                key.
              </p>
              <span className="access-price">Deployment access required</span>
              <a className="button button-outline" href="/workspace?connect=true">
                Connect workspace <ArrowUpRight size={16} />
              </a>
            </article>
            <p className="fine-print">
              Commercial pricing has not been published. No subscription or payment is collected
              here.
            </p>
          </div>
        </section>
        <section className="site-container faq-section">
          <div>
            <p className="section-label">Before you investigate</p>
            <h2>
              A few things
              <br />
              worth knowing.
            </h2>
          </div>
          <div className="faq-list">
            {faq.map(([q, a]) => (
              <details key={q}>
                <summary>
                  {q}
                  <ChevronDown size={17} />
                </summary>
                <p>{a}</p>
              </details>
            ))}
          </div>
        </section>
        <section className="final-cta">
          <div className="site-container">
            <Fingerprint size={36} strokeWidth={1} />
            <h2>
              Give your next conclusion
              <br />a paper trail.
            </h2>
            <a
              className="button button-paper"
              href="/workspace?mode=recorded&case=supplier-contact"
            >
              Open a sample investigation <ArrowUpRight size={17} />
            </a>
            <p>Evidence you can open. A decision you can explain.</p>
          </div>
        </section>
      </main>
      <footer className="site-container site-footer">
        <Brand />
        <p>Evidence-backed investigation for AI agents.</p>
        <div>
          <a href="/workspace?mode=recorded&case=supplier-contact">
            Workspace <ArrowUpRight size={13} />
          </a>
        </div>
        <span>© {new Date().getFullYear()} TraceVerdict</span>
      </footer>
    </div>
  );
}
