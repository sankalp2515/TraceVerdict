import type { ReactNode } from "react";
import type { Decision } from "../api";

const DECISION_COLOR: Record<Decision, string> = {
  ALLOW: "var(--allow)",
  NEUTRALISE: "var(--neutralise)",
  BLOCK: "var(--block)",
  ESCALATE: "var(--escalate)",
};

const DECISION_TEXT: Record<Decision, string> = {
  ALLOW: "Allowed",
  NEUTRALISE: "Neutralised",
  BLOCK: "Blocked",
  ESCALATE: "Needs approval",
};

export function DecisionBadge({ decision }: { decision: Decision | null | undefined }) {
  if (!decision) return null;
  const c = DECISION_COLOR[decision];
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold"
      style={{ color: c, background: `color-mix(in srgb, ${c} 14%, transparent)`, border: `1px solid color-mix(in srgb, ${c} 40%, transparent)` }}
    >
      <span aria-hidden className="h-1.5 w-1.5 rounded-full" style={{ background: c }} />
      {DECISION_TEXT[decision]}
    </span>
  );
}

export function Label({ children }: { children: ReactNode }) {
  return (
    <span className="inline-block rounded-md px-1.5 py-0.5 text-xs" style={{ background: "var(--panel-2)", border: "1px solid var(--border)" }}>
      {children}
    </span>
  );
}

export function Section({ title, subtitle, children, actions }: { title: string; subtitle?: string; children: ReactNode; actions?: ReactNode }) {
  return (
    <section className="panel p-4 sm:p-5">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold">{title}</h2>
          {subtitle && <p className="muted text-sm">{subtitle}</p>}
        </div>
        {actions}
      </div>
      {children}
    </section>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="muted rounded-lg border border-dashed p-4 text-sm" style={{ borderColor: "var(--border)" }}>{children}</p>;
}

export function pct(v: number | null | undefined): string {
  return v === null || v === undefined ? "—" : `${(v * 100).toFixed(1)}%`;
}
