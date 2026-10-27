import { useEffect, useRef, useState, type ReactNode } from "react";
import { ChevronRight, CircleHelp, X } from "lucide-react";
import { label, pretty, type Evidence, type Outcome } from "./types";
export function Status({ value }: { value: string }) {
  const tone = [
    "AWAITING_REVIEW",
    "VALIDATING",
    "COLLECTING",
    "INCOMPLETE",
    "INCONCLUSIVE",
    "STALE",
    "unknown",
    "error",
    "resisted",
  ].includes(value)
    ? "amber"
    : ["APPROVED", "pass", "accepted", "complete"].includes(value)
      ? "green"
      : ["REJECTED", "fail", "disputed"].includes(value)
        ? "red"
        : "blue";
  return (
    <span className={`status status-${tone}`}>
      <span />
      {label(value)}
    </span>
  );
}
export function Notice({ children, error = false }: { children: ReactNode; error?: boolean }) {
  return (
    <div className={`notice ${error ? "notice-error" : ""}`} role={error ? "alert" : undefined}>
      <CircleHelp size={17} />
      <div>{children}</div>
    </div>
  );
}
export function EvidenceBody({ evidence }: { evidence: Evidence }) {
  return (
    <>
      <div className="panel-heading">
        <div>
          <span className="section-label">Source record</span>
          <h2>{label(evidence.kind)}</h2>
        </div>
        <span className="status status-blue">Version {evidence.source_version}</span>
      </div>
      <dl className="metadata">
        <div>
          <dt>Evidence ID</dt>
          <dd>{evidence.evidence_id}</dd>
        </div>
        <div>
          <dt>Source locator</dt>
          <dd>{evidence.source_locator}</dd>
        </div>
        <div>
          <dt>Content SHA-256</dt>
          <dd>{evidence.content_sha256}</dd>
        </div>
      </dl>
      <h4>Source content</h4>
      <pre className="source-content">{pretty(evidence.payload)}</pre>
      <h4>Query receipt</h4>
      <pre>
        {evidence.query_receipt
          ? pretty(evidence.query_receipt)
          : "No query receipt available for this record."}
      </pre>
      <p className="fine-print">
        Source content is displayed as escaped text. An application receipt is a report by that
        application, not independent attestation.
      </p>
    </>
  );
}

export function OutcomeRow({
  outcome: o,
  baseline: b,
}: {
  outcome: Outcome;
  baseline: Outcome | undefined;
}) {
  const [expanded, setExpanded] = useState(false);
  return (
    <>
      <tr>
        <td>
          <strong>{label(o.scenario_id)}</strong>
          <small>
            {o.category === "unsafe" ? "Unsafe action" : "Legitimate task"} ·{" "}
            {label(o.execution_mode)}
          </small>
        </td>
        <td>
          {b ? (
            <>
              <Status value={b.outcome} />
              <small>{label(b.observed_behavior)}</small>
            </>
          ) : (
            "Unavailable"
          )}
        </td>
        <td>
          <Status value={o.outcome} />
          <small>{label(o.observed_behavior)}</small>
        </td>
        <td className="mono small">{o.duration_ms.toFixed(1)} ms</td>
        <td>
          <button
            className="source-link"
            aria-expanded={expanded}
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? "Close" : "Inspect"}
            <ChevronRight size={12} />
          </button>
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={5}>
            <div className="scenario-detail">
              <p>
                <strong>Expected:</strong> {o.expected_behavior} · <strong>Observed:</strong>{" "}
                {o.observed_behavior}
              </p>
              <p>
                <strong>Policy rule:</strong> {o.policy_rule || "Not returned"}
              </p>
              <pre>
                {o.application_receipt
                  ? pretty(o.application_receipt)
                  : "No application receipt available."}
              </pre>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
export function Modal({
  title,
  children,
  onClose,
  wide = false,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    d?.showModal();
    return () => d?.close();
  }, []);
  return (
    <dialog
      ref={ref}
      aria-label={title}
      className={`workspace-dialog ${wide ? "dialog-wide" : ""}`}
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          const r = e.currentTarget.getBoundingClientRect();
          if (
            e.clientX < r.left ||
            e.clientX > r.right ||
            e.clientY < r.top ||
            e.clientY > r.bottom
          )
            onClose();
        }
      }}
    >
      <div className="dialog-heading">
        <h2>{title}</h2>
        <button className="icon-button" aria-label="Close dialog" onClick={onClose}>
          <X size={19} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
