import { ArrowLeft, ArrowRight, Check, X } from "lucide-react";
import type { CaseData } from "./types";

const stages = [
  {
    tab: "Overview",
    seconds: 40,
    question: "What happened?",
    explanation:
      "Compare what the user authorized with what the agent attempted and what the application reports executing.",
    action:
      "Read the task and execution outcome below. The send in this example went only to a local sandbox outbox.",
    next: "Follow the evidence",
  },
  {
    tab: "Evidence",
    seconds: 40,
    question: "What supports the finding?",
    explanation:
      "The task, document, attempted action, policy and receipt are connected source records, not just a generated summary.",
    action:
      "Select a graph node and open its source, or use Record index. Solid lines show observed relations; dashed lines show inference or context.",
    next: "Read the explanation",
  },
  {
    tab: "Explanation",
    seconds: 40,
    question: "What can we actually conclude?",
    explanation:
      "Review the critic's checks and any disputed claims. A sequence of events alone does not prove that the document caused the action.",
    action:
      "Read the cited claims and critic review below. A sequence of events alone does not prove causation.",
    next: "Compare the repairs",
  },
  {
    tab: "Repairs & validation",
    seconds: 60,
    question: "Which repair preserves useful work?",
    explanation:
      "Stopping an unsafe action is only half the job. A repair must also preserve tasks the user actually authorized.",
    action:
      "Select Restrict recipients and filter Failed results to inspect the broken tasks. Then select Enforce user intent to compare its exact change and results.",
    next: "See the human decision",
  },
  {
    tab: "Review",
    seconds: 30,
    question: "What does a human approve?",
    explanation:
      "A reviewer approves the exact policy change and test report. Approval produces a recommendation; it does not change production.",
    action:
      "Inspect the reviewed artifacts below or download the report. Approval is disabled in this recorded sample; a connected reviewer performs it on the backend.",
    next: "Download the sample report",
  },
];

export function CaseGuide({
  tab,
  data,
  onTab,
  onHide,
  onExport,
}: {
  tab: string;
  data: CaseData;
  onTab: (tab: string) => void;
  onHide: () => void;
  onExport: () => void;
}) {
  const index = Math.max(
    0,
    stages.findIndex((s) => s.tab === tab),
  );
  const stage = stages[index]!;
  const targeted = data.candidates.find((c) => c.diff.some((d) => d.path === "contract.mode"));
  const broad = data.candidates.find(
    (c) =>
      c.candidate_id !== targeted?.candidate_id &&
      c.diff.some((d) => d.path.includes("allowed_recipients")),
  );
  const broadReport = broad && data.validations[broad.candidate_id];
  const report = targeted && data.validations[targeted.candidate_id];
  const brokenTasks = broadReport?.outcomes.filter(
    (o) => o.category === "utility" && o.outcome === "fail",
  ).length;
  function go(next: string) {
    onTab(next);
    document.getElementById("case-guide")?.scrollIntoView({ block: "start", behavior: "instant" });
  }
  return (
    <section className="case-guide" id="case-guide" aria-label="Guided sample walkthrough">
      <div className="guide-top">
        <span>
          Guided sample{" "}
          <span>
            Step {index + 1} of {stages.length}
            {" · "}
            {stage.seconds}s suggested pace
          </span>
        </span>
        <button className="text-link" onClick={onHide}>
          Explore freely <X size={13} />
        </button>
      </div>
      <ol className="guide-progress" aria-label="Walkthrough steps">
        {stages.map((s, i) => (
          <li key={s.tab}>
            <button onClick={() => go(s.tab)} aria-current={i === index ? "step" : undefined}>
              <span>{i < index ? <Check size={12} /> : i + 1}</span>
              {s.tab === "Repairs & validation" ? "Compare repairs" : s.tab}
            </button>
          </li>
        ))}
      </ol>
      <div className="guide-content">
        <div>
          <h2 id="guide-question">{stage.question}</h2>
          <p>{stage.explanation}</p>
          {index === 0 && (
            <p>
              Follow five steps to a downloadable report. Suggested total: 3½ minutes. No account
              required.
            </p>
          )}
          <p className="guide-instruction">{stage.action}</p>
          {tab === "Repairs & validation" && report && broadReport && (
            <div className="guide-result">
              Recorded result: the recipient restriction failed {brokenTasks} legitimate tasks. The
              intent-contract repair passed{" "}
              {report.outcomes.filter((o) => o.outcome === "pass").length} of{" "}
              {report.outcomes.length} configured checks.
            </div>
          )}
        </div>
        <div className="guide-actions">
          <button
            className="button button-dark"
            onClick={() => (index === stages.length - 1 ? onExport() : go(stages[index + 1]!.tab))}
          >
            {stage.next}
            <ArrowRight size={15} />
          </button>
          {index > 0 && (
            <button className="text-link" onClick={() => go(stages[index - 1]!.tab)}>
              <ArrowLeft size={13} />
              Previous step
            </button>
          )}
          {index === stages.length - 1 && (
            <a className="text-link" href="/workspace?mode=recorded&case=nemotron-live">
              Inspect the recorded Nemotron run <ArrowRight size={13} />
            </a>
          )}
          {index === stages.length - 1 && (
            <a
              className="text-link"
              href="https://github.com/sankalp2515/TraceVerdict/blob/main/docs/CUSTOM_INTEGRATIONS.md"
              target="_blank"
              rel="noreferrer"
            >
              Investigate your own agent or data <ArrowRight size={13} />
            </a>
          )}
        </div>
      </div>
    </section>
  );
}
