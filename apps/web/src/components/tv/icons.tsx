import { cn } from "@/lib/utils";

/**
 * Iconography: every icon is a noun from the evidence ontology
 * (task, document, action, policy, receipt, tools, reference, claim).
 * Icons map one-to-one to node types a reviewer can open — never decoration.
 * 24px grid, 1.75px stroke, round caps.
 */

export type NodeIconKey =
  | "task"
  | "document"
  | "action"
  | "policy"
  | "receipt"
  | "tools"
  | "reference"
  | "claim";

const PATHS: Record<NodeIconKey, string[]> = {
  // Authorized task: a filed order with a check — the user's actual intent
  task: [
    "M9 3h6a1 1 0 0 1 1 1v1H8V4a1 1 0 0 1 1-1Z",
    "M8 5H6.5A1.5 1.5 0 0 0 5 6.5v13A1.5 1.5 0 0 0 6.5 21h11a1.5 1.5 0 0 0 1.5-1.5v-13A1.5 1.5 0 0 0 17.5 5H16",
    "m9.5 13.5 2 2 3.5-4.5",
  ],
  // Untrusted document: a page with a folded corner — read fully, never trusted
  document: [
    "M7 3h7l4 4v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z",
    "M14 3v4h4",
    "M9 12h6",
    "M9 16h4",
  ],
  // Attempted action: a paper plane — something tried to leave the boundary
  action: ["m21 3-8.5 8.5", "M21 3l-6.5 18-3.5-8-8-3.5L21 3Z"],
  // Policy snapshot: a shield over a contract line — the enforced boundary
  policy: [
    "M12 3l7 2.6v5.2c0 4.6-3 7.7-7 9.2-4-1.5-7-4.6-7-9.2V5.6L12 3Z",
    "M9.5 11.5h5",
  ],
  // Application receipt: a slip with a torn edge — the app's own account
  receipt: [
    "M6 3h12v18l-2-1.4-2 1.4-2-1.4L10 21l-2-1.4L6 21V3Z",
    "M9 8h6",
    "M9 12h6",
  ],
  // Tools: a gear — the connected tool surface the action targeted
  tools: [
    "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z",
    "M12 2v3M12 19v3M2 12h3M19 12h3M4.6 4.6l2.1 2.1M17.3 17.3l2.1 2.1M19.4 4.6l-2.1 2.1M6.7 17.3l-2.1 2.1",
  ],
  // Trusted reference: a bookmark in the operator's own record
  reference: [
    "M7 3h10a1 1 0 0 1 1 1v17l-6-4-6 4V4a1 1 0 0 1 1-1Z",
    "M9.5 8h5",
  ],
  // Verdict claim: a speech bubble — written, challenged, cited
  claim: [
    "M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H9.5L4 20.5V6Z",
    "M8.5 8.5h7",
    "M8.5 12h4.5",
  ],
};

const LABELS: Record<NodeIconKey, string> = {
  task: "Authorized task",
  document: "Untrusted document",
  action: "Attempted action",
  policy: "Policy snapshot",
  receipt: "Application receipt",
  tools: "Tool surface",
  reference: "Trusted reference",
  claim: "Verdict claim",
};

export function nodeIconLabel(key: NodeIconKey) {
  return LABELS[key];
}

export function NodeIcon({
  name,
  className,
  strokeWidth = 1.75,
}: {
  name: NodeIconKey;
  className?: string;
  strokeWidth?: number;
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      className={cn("h-5 w-5", className)}
    >
      {PATHS[name].map((d, i) => (
        <path
          key={i}
          d={d}
          stroke="currentColor"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      ))}
    </svg>
  );
}

/** Raw path data for rendering the same icons inside a parent <svg>. */
export function nodeIconPaths(name: NodeIconKey, strokeWidth = 1.75) {
  return PATHS[name].map((d, i) => (
    <path
      key={i}
      d={d}
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  ));
}
