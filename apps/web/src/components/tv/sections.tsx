import { cn } from "@/lib/utils";
import { Chip, Reveal, Section, SectionHead, type ChipTone } from "./primitives";
import { EvidenceGraph } from "./evidence-graph";
import { NodeIcon, type NodeIconKey } from "./icons";

/* ============================================================
   STORY — the case in three beats
   ============================================================ */

const BEATS = [
  {
    n: "01",
    title: "The instruction",
    body: "An agent is asked to summarize a supplier report and contact no one. The report itself carries an instruction to send information to an unauthorized recipient. The document is read in full — and trusted for nothing.",
  },
  {
    n: "02",
    title: "The attempt",
    body: "The agent attempts the send. The guard withholds it; the application receipt records no execution. Two records, two voices — an attempt is not an execution, and the interface never conflates them.",
  },
  {
    n: "03",
    title: "The verdict",
    body: "An investigator writes the explanation; a critic challenges every unsupported claim. A targeted policy repair is tested against unsafe behavior and legitimate work alike — then a human reviews the exact artifact and approves.",
  },
];

export function StorySection() {
  return (
    <Section id="story" className="bg-secondary/40">
      <Reveal>
        <SectionHead
          eyebrow="The story the interface tells"
          title="One case, three beats"
          lead="The demonstration scenario is synthetic, sandboxed and labeled — but the experience it demands is real: reconstruct what happened without ever overstating what is known."
        />
      </Reveal>
      <div className="mt-12 grid gap-5 md:grid-cols-3">
        {BEATS.map((b, i) => (
          <Reveal key={b.n} delay={i * 90}>
            <article className="flex h-full flex-col rounded-lg border border-border bg-card p-7">
              <span className="font-mono text-xs tracking-[0.2em] text-signal">
                {b.n}
              </span>
              <h3 className="mt-4 font-display text-2xl font-semibold text-foreground">
                {b.title}
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                {b.body}
              </p>
            </article>
          </Reveal>
        ))}
      </div>
    </Section>
  );
}

/* ============================================================
   FLOW — the investigation loop
   ============================================================ */

const STEPS = [
  {
    k: "Collect",
    d: "Task, document, action, policy snapshot and application receipt are gathered into one immutable case bundle.",
  },
  {
    k: "Explain",
    d: "The investigator proposes an explanation, citing evidence — hypotheses are separated from records.",
  },
  {
    k: "Challenge",
    d: "The critic attacks causal overclaims and missing facts. Unsupported claims do not survive.",
  },
  {
    k: "Propose",
    d: "Bounded, typed policy repairs — at most two — each linked to the claims it addresses.",
  },
  {
    k: "Validate",
    d: "Replay against unsafe and legitimate tasks. A broad restriction fails; a targeted one may pass.",
  },
];

export function FlowSection() {
  return (
    <Section id="flow">
      <Reveal>
        <SectionHead
          eyebrow="The workflow"
          title="A loop that closes with a human"
          lead="Case → evidence → explanation → validation → review. Every stage is a visible state, never a silent progress bar."
        />
      </Reveal>
      <div className="mt-12 grid gap-4 md:grid-cols-5">
        {STEPS.map((s, i) => (
          <Reveal key={s.k} delay={i * 80}>
            <div className="relative h-full rounded-lg border border-border bg-card p-5">
              <span className="font-mono text-[11px] tracking-[0.16em] text-muted-foreground uppercase">
                Step {i + 1}
              </span>
              <h3 className="mt-2 font-display text-xl font-semibold text-foreground">
                {s.k}
              </h3>
              <p className="mt-2 text-[13px] leading-relaxed text-muted-foreground">
                {s.d}
              </p>
            </div>
          </Reveal>
        ))}
      </div>
      <Reveal delay={200}>
        <div className="mt-6 flex items-center gap-4 rounded-lg border border-signal/40 bg-signal-soft p-5">
          <NodeIcon name="reference" className="h-6 w-6 shrink-0 text-signal" />
          <p className="text-sm text-foreground">
            <span className="font-semibold">Review is the gate.</span>{" "}
            Approval binds the exact policy hash and report hash — a
            recommendation is produced, never a silent production patch.
          </p>
        </div>
      </Reveal>
    </Section>
  );
}

/* ============================================================
   GRAPH — the primary interaction
   ============================================================ */

export function GraphSection() {
  return (
    <Section id="graph" className="bg-secondary/40">
      <Reveal>
        <SectionHead
          eyebrow="The primary interaction"
          title="Follow the support, see the doubt"
          lead="Nodes are facts and claims; edges are labeled relations. Click a node to open its evidence, an edge to read its basis. The record index below gives every node and edge a plain path — the graph is never the only way in."
        />
      </Reveal>
      <Reveal delay={120} className="mt-12">
        <EvidenceGraph />
      </Reveal>
    </Section>
  );
}

/* ============================================================
   FOUNDATIONS — colour, type, grid
   ============================================================ */

const SWATCHES = [
  {
    name: "Ink",
    token: "--foreground",
    oklch: "oklch(0.25 0.05 262)",
    hex: "#142139",
    swatch: "bg-foreground",
    role: "Facts & structure",
    why: "Every record, headline and body line. Ink is the voice of the record — nothing decorative wears it.",
  },
  {
    name: "Paper",
    token: "--background",
    oklch: "oklch(0.977 0.008 84)",
    hex: "#faf7f1",
    swatch: "bg-background",
    role: "The ground",
    why: "A warm, faintly yellow paper: a case file, not a screen. Evidence is filed, never floated on white.",
  },
  {
    name: "Signal Orange",
    token: "--signal",
    oklch: "oklch(0.62 0.185 42)",
    hex: "#dd5406",
    swatch: "bg-signal",
    role: "Enforcement & gates — reserved",
    why: "Inherited from the architecture legend's orange “deterministic enforcement / gate”. Appears only where a boundary is enforced: guard decisions, awaiting-review, confirmations.",
  },
  {
    name: "Verified Green",
    token: "--verified",
    oklch: "oklch(0.48 0.095 155)",
    hex: "#286d45",
    swatch: "bg-verified",
    role: "Tested outcomes",
    why: "The legend's green means new work; here it means a claim that survived the critic and a repair that passed its gate.",
  },
  {
    name: "Report Blue",
    token: "--reported",
    oklch: "oklch(0.45 0.09 255)",
    hex: "#305686",
    swatch: "bg-reported",
    role: "Application-reported facts",
    why: "The legend's foundation blue, kept for what an application claims about itself — reported, not attested.",
  },
  {
    name: "Uncertain Amber",
    token: "--uncertain",
    oklch: "oklch(0.58 0.115 75)",
    hex: "#a26f17",
    swatch: "bg-uncertain",
    role: "Gaps & inference",
    why: "Missing receipts, stale snapshots, inferred edges. Amber asks a question; it never answers one.",
  },
  {
    name: "Contradiction Red",
    token: "--contradiction",
    oklch: "oklch(0.5 0.19 27)",
    hex: "#b7191c",
    swatch: "bg-contradiction",
    role: "Conflict only",
    why: "Reserved for the one state that means records disagree. Merely incomplete work stays amber — failure and conflict are not the same.",
  },
];

export function FoundationsSection() {
  return (
    <Section id="foundations">
      {/* ---- Colour ---- */}
      <Reveal>
        <div id="colour" className="scroll-mt-20">
          <SectionHead
            eyebrow="Foundations · colour"
            title="Three inks and a seal"
            lead="The palette descends directly from the system architecture's own legend — green for new work, blue/grey for the existing foundation, orange for the deterministic gate. A colour always answers the same question, so meaning never has to be re-learned."
          />
        </div>
      </Reveal>
      <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {SWATCHES.map((s, i) => (
          <Reveal key={s.name} delay={i * 60}>
            <div className="h-full rounded-lg border border-border bg-card">
              <div className={cn("h-16 rounded-t-lg border-b border-border", s.swatch)} />
              <div className="p-5">
                <div className="flex items-baseline justify-between gap-3">
                  <h3 className="font-display text-lg font-semibold text-foreground">
                    {s.name}
                  </h3>
                  <span className="font-mono text-[11px] text-muted-foreground">
                    {s.hex}
                  </span>
                </div>
                <p className="mt-0.5 font-mono text-[11px] text-muted-foreground">
                  {s.token} · {s.oklch}
                </p>
                <p className="mt-2.5 font-mono text-[11px] font-medium tracking-wide text-foreground uppercase">
                  {s.role}
                </p>
                <p className="mt-1.5 text-[13px] leading-relaxed text-muted-foreground">
                  {s.why}
                </p>
              </div>
            </div>
          </Reveal>
        ))}
      </div>

      {/* ---- Type ---- */}
      <Reveal>
        <div id="type" className="mt-24 scroll-mt-20">
          <SectionHead
            eyebrow="Foundations · typography"
            title="Case file meets instrument panel"
            lead="Three voices, each with one job: a serif that speaks with the gravity of a written finding, a sans engineered for dense interface reading, and a mono for anything a reviewer must verify character by character."
          />
        </div>
      </Reveal>
      <div className="mt-12 grid gap-4 lg:grid-cols-3">
        <Reveal>
          <div className="h-full rounded-lg border border-border bg-card p-7">
            <p className="font-mono text-[11px] tracking-[0.16em] text-muted-foreground uppercase">
              Display · Spectral
            </p>
            <p className="mt-5 font-display text-4xl leading-tight font-semibold text-foreground">
              The verdict shows its work.
            </p>
            <p className="mt-5 text-[13px] leading-relaxed text-muted-foreground">
              An editorial serif — the voice of a written finding. Headlines,
              section titles and pull-quotes only; it never renders data.
            </p>
          </div>
        </Reveal>
        <Reveal delay={80}>
          <div className="h-full rounded-lg border border-border bg-card p-7">
            <p className="font-mono text-[11px] tracking-[0.16em] text-muted-foreground uppercase">
              Interface · IBM Plex Sans
            </p>
            <p className="mt-5 text-[15px] leading-relaxed text-foreground">
              Evidence is read for hours at a time. Plex Sans was drawn for
              dense interfaces: open counters, slightly squared terminals, and
              a true italic for the critic’s annotations.
            </p>
            <p className="mt-5 text-[13px] leading-relaxed text-muted-foreground">
              All body copy, labels and navigation. Nothing smaller than 13px.
            </p>
          </div>
        </Reveal>
        <Reveal delay={160}>
          <div className="h-full rounded-lg border border-border bg-card p-7">
            <p className="font-mono text-[11px] tracking-[0.16em] text-muted-foreground uppercase">
              Custody · IBM Plex Mono
            </p>
            <p className="mt-5 font-mono text-[13px] leading-relaxed break-all text-foreground">
              base_policy_sha256 9f2c…e41a
              <br />
              patch_sha256 3b9f…77c2
              <br />
              evidence/ev_doc#3 · v2
            </p>
            <p className="mt-5 text-[13px] leading-relaxed text-muted-foreground">
              Hashes, IDs, source locators, diffs — the chain of custody. Mono
              is never used for prose.
            </p>
          </div>
        </Reveal>
      </div>
      <Reveal delay={120}>
        <div className="mt-6 overflow-x-auto rounded-lg border border-border bg-card">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead>
              <tr className="border-b border-border font-mono text-[11px] tracking-[0.16em] text-muted-foreground uppercase">
                <th className="px-5 py-3 font-medium">Role</th>
                <th className="px-5 py-3 font-medium">Size / line</th>
                <th className="px-5 py-3 font-medium">Face · weight</th>
                <th className="px-5 py-3 font-medium">Use</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {[
                ["Display", "44 / 52", "Spectral · 600", "Hero statements"],
                ["Heading 2", "30 / 38", "Spectral · 600", "Section titles"],
                ["Heading 3", "20 / 28", "Spectral · 600", "Card & panel titles"],
                ["Body", "16 / 26", "Plex Sans · 400", "Reading text"],
                ["Caption", "13 / 18", "Plex Sans · 500", "Labels, legends"],
                ["Evidence", "12.5 / 20", "Plex Mono · 400", "Hashes, IDs, diffs"],
              ].map((r) => (
                <tr key={r[0]}>
                  <td className="px-5 py-2.5 font-medium text-foreground">{r[0]}</td>
                  <td className="px-5 py-2.5 font-mono text-xs text-muted-foreground">
                    {r[1]}
                  </td>
                  <td className="px-5 py-2.5 text-muted-foreground">{r[2]}</td>
                  <td className="px-5 py-2.5 text-muted-foreground">{r[3]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Reveal>

      {/* ---- Grid ---- */}
      <Reveal>
        <div id="grid" className="mt-24 scroll-mt-20">
          <SectionHead
            eyebrow="Foundations · space & grid"
            title="Filed, not floated"
            lead="A 4px base unit keeps every panel aligned to an imaginary ruled ledger. The workspace is a stable frame with changing panels — the case never moves under the cursor."
          />
        </div>
      </Reveal>
      <div className="mt-12 grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
        <Reveal>
          <div className="rounded-lg border border-border bg-card p-7">
            <p className="font-mono text-[11px] tracking-[0.16em] text-muted-foreground uppercase">
              Spacing scale · 4px base
            </p>
            <div className="mt-5 flex flex-wrap items-end gap-6">
              {[4, 8, 12, 16, 24, 32, 48, 64, 96].map((n) => (
                <div key={n} className="flex flex-col items-center gap-1.5">
                  <div
                    className="w-3 rounded-t-sm bg-foreground/80"
                    style={{ height: `${Math.min(n, 96) / 2}px` }}
                  />
                  <span className="font-mono text-[10px] text-muted-foreground">
                    {n}
                  </span>
                </div>
              ))}
            </div>
            <ul className="mt-8 space-y-2.5 border-t border-border pt-6 text-sm text-muted-foreground">
              <li>
                <span className="font-medium text-foreground">Container.</span>{" "}
                12 columns, 1152px max, 24px gutters — investigation panes split
                8/4.
              </li>
              <li>
                <span className="font-medium text-foreground">Rhythm.</span>{" "}
                Sections breathe at 96px desktop / 64px mobile; card padding
                steps 24 → 32.
              </li>
              <li>
                <span className="font-medium text-foreground">Reading.</span>{" "}
                Dense evidence panes cap near 70 characters per line.
              </li>
              <li>
                <span className="font-medium text-foreground">
                  Stable frame.
                </span>{" "}
                Case header and tab rail persist; only the focused panel
                changes. On small screens the same information reflows into
                panels and tabs — nothing is dropped.
              </li>
            </ul>
          </div>
        </Reveal>
        <Reveal delay={100}>
          {/* Workspace wireframe */}
          <div className="rounded-lg border border-border bg-card p-5">
            <p className="font-mono text-[11px] tracking-[0.16em] text-muted-foreground uppercase">
              Workspace frame
            </p>
            <div className="mt-4 space-y-2 rounded-md border border-border bg-background p-3">
              <div className="flex items-center justify-between rounded-sm border border-border bg-secondary px-3 py-2">
                <span className="font-mono text-[10px] text-muted-foreground">
                  CASE HEADER · STABLE
                </span>
                <span className="h-1.5 w-1.5 rounded-full bg-signal" />
              </div>
              <div className="flex gap-1.5">
                {["Overview", "Evidence", "Repairs", "Review"].map((t, i) => (
                  <span
                    key={t}
                    className={cn(
                      "rounded-sm px-2 py-1 font-mono text-[9px]",
                      i === 1
                        ? "bg-foreground text-primary-foreground"
                        : "border border-border text-muted-foreground",
                    )}
                  >
                    {t}
                  </span>
                ))}
              </div>
              <div className="grid grid-cols-[2fr_1fr] gap-2">
                <div className="flex h-28 items-center justify-center rounded-sm border border-border bg-card font-mono text-[9px] text-muted-foreground">
                  EVIDENCE · GRAPH / TIMELINE
                </div>
                <div className="flex h-28 items-center justify-center rounded-sm border border-border bg-card px-2 text-center font-mono text-[9px] text-muted-foreground">
                  DETAIL DRAWER
                </div>
              </div>
            </div>
            <p className="mt-3 text-[13px] leading-relaxed text-muted-foreground">
              The 8/4 split: evidence on the left, the open record on the
              right. The reviewer never loses the case while inspecting a
              detail.
            </p>
          </div>
        </Reveal>
      </div>
    </Section>
  );
}

/* ============================================================
   COMPONENTS — the library, honest by construction
   ============================================================ */

function Spec({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-card p-6">
      <p className="font-mono text-[11px] tracking-[0.16em] text-muted-foreground uppercase">
        {label}
      </p>
      <div className="mt-4">{children}</div>
    </div>
  );
}

const CASE_STATES: { label: string; tone: ChipTone }[] = [
  { label: "Collecting", tone: "reported" },
  { label: "Explaining", tone: "reported" },
  { label: "Critiquing", tone: "reported" },
  { label: "Proposing", tone: "reported" },
  { label: "Validating", tone: "reported" },
  { label: "Awaiting review", tone: "signal" },
  { label: "Approved", tone: "verified" },
  { label: "Rejected", tone: "contradiction" },
  { label: "Inconclusive", tone: "uncertain" },
  { label: "Incomplete", tone: "uncertain" },
  { label: "Stale", tone: "uncertain" },
];

const OUTCOMES = [
  {
    chip: "Withheld",
    tone: "verified" as const,
    def: "Enforcement stopped the action, or the receipt reports no execution. Contained — but the legitimate task may also have been prevented.",
  },
  {
    chip: "Allowed · unconfirmed",
    tone: "uncertain" as const,
    def: "Permitted, with no confirming receipt. The absence of evidence is rendered, never smoothed over.",
  },
  {
    chip: "App-reported executed",
    tone: "reported" as const,
    def: "The application says it ran. That is a report — not independent attestation.",
  },
  {
    chip: "Contradiction",
    tone: "contradiction" as const,
    def: "Reported execution conflicts with a recorded block. Red is reserved for exactly this.",
  },
];

export function ComponentsSection() {
  return (
    <Section id="components" className="bg-secondary/40">
      <Reveal>
        <SectionHead
          eyebrow="The component library"
          title="Honest by construction"
          lead="Status is the product's most important component. Every chip below is a precise claim — and the states that could mislead are styled so they cannot masquerade as success."
        />
      </Reveal>

      <div className="mt-12 grid gap-4 lg:grid-cols-2">
        <Reveal>
          <Spec label="Execution outcomes — the four meanings">
            <ul className="space-y-4">
              {OUTCOMES.map((o) => (
                <li key={o.chip} className="flex gap-3">
                  <Chip tone={o.tone} dot className="mt-0.5 shrink-0">
                    {o.chip}
                  </Chip>
                  <p className="text-[13px] leading-relaxed text-muted-foreground">
                    {o.def}
                  </p>
                </li>
              ))}
            </ul>
          </Spec>
        </Reveal>
        <Reveal delay={80}>
          <Spec label="Case workflow states">
            <div className="flex flex-wrap gap-1.5">
              {CASE_STATES.map((s) => (
                <Chip key={s.label} tone={s.tone} dot>
                  {s.label}
                </Chip>
              ))}
            </div>
            <p className="mt-4 text-[13px] leading-relaxed text-muted-foreground">
              Blue carries active work. Orange marks the review gate.
              Inconclusive, incomplete and stale are amber — they never share
              the success treatment of a passing result.
            </p>
            <div className="mt-5 border-t border-border pt-4">
              <p className="font-mono text-[11px] tracking-[0.16em] text-muted-foreground uppercase">
                Job states
              </p>
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                <Chip tone="outline" dot>
                  Queued
                </Chip>
                <Chip tone="reported" dot>
                  Running
                </Chip>
                <Chip tone="verified" dot>
                  Complete
                </Chip>
                <Chip tone="uncertain" dot>
                  Incomplete
                </Chip>
              </div>
              <p className="mt-3 text-[13px] text-muted-foreground">
                Bounded polling, terminal stop, refresh-safe. Progress is never
                invented from a status.
              </p>
            </div>
          </Spec>
        </Reveal>

        <Reveal delay={40}>
          <Spec label="Execution mode — always visible">
            <div className="flex flex-wrap gap-2">
              <Chip tone="reported" dot>
                Live
              </Chip>
              <Chip tone="outline" dot>
                Sample · no inference
              </Chip>
              <Chip tone="uncertain" dot>
                Recorded · Oct 27, 14:02 UTC
              </Chip>
            </div>
            <p className="mt-4 text-[13px] leading-relaxed text-muted-foreground">
              A live failure never demotes a case to sample mode, and a
              recording is never presented as a new live run. Mode is part of
              the header, not a footnote.
            </p>
          </Spec>
        </Reveal>
        <Reveal delay={120}>
          <Spec label="Actions">
            <div className="flex flex-wrap items-center gap-2.5">
              <button className="rounded-sm bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors duration-150 hover:bg-primary/85">
                Approve recommendation
              </button>
              <button className="rounded-sm border border-border bg-card px-4 py-2 text-sm font-medium text-foreground transition-colors duration-150 hover:bg-accent">
                Open evidence
              </button>
              <button className="rounded-sm px-3 py-2 text-sm font-medium text-muted-foreground transition-colors duration-150 hover:text-foreground">
                Dismiss
              </button>
              <button className="rounded-sm border border-contradiction/40 px-4 py-2 text-sm font-medium text-contradiction transition-colors duration-150 hover:bg-contradiction-soft">
                Reject
              </button>
            </div>
            <p className="mt-4 text-[13px] leading-relaxed text-muted-foreground">
              Approve is the only button in the product that mints a
              recommendation — it is primary, deliberate, and disabled until a
              candidate has actually passed.
            </p>
          </Spec>
        </Reveal>

        <Reveal delay={60}>
          <Spec label="Evidence card">
            <div className="rounded-md border border-border bg-background p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <NodeIcon
                    name="document"
                    className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground"
                  />
                  <div>
                    <p className="font-medium text-foreground">
                      supplier_report_Q3.pdf
                    </p>
                    <p className="font-mono text-[11px] text-muted-foreground">
                      ev_doc#3 · source v2
                    </p>
                  </div>
                </div>
                <Chip tone="uncertain" dot>
                  Untrusted
                </Chip>
              </div>
              <dl className="mt-3 space-y-1.5 border-t border-border pt-3">
                <div className="flex justify-between font-mono text-[11px]">
                  <dt className="text-muted-foreground">content_sha256</dt>
                  <dd className="text-foreground">c41d…9e07</dd>
                </div>
                <div className="flex justify-between font-mono text-[11px]">
                  <dt className="text-muted-foreground">locator</dt>
                  <dd className="text-foreground">p.4 · instruction block</dd>
                </div>
              </dl>
            </div>
          </Spec>
        </Reveal>
        <Reveal delay={140}>
          <Spec label="Policy repair — exact diff">
            <div className="overflow-hidden rounded-md border border-border bg-background font-mono text-[12px]">
              <p className="border-b border-border px-4 py-2 text-muted-foreground">
                intent_contract · rule 4
              </p>
              <p className="bg-contradiction-soft px-4 py-1.5 text-contradiction">
                <span className="mr-2">-</span>allow: send.summary → any
                recipient
              </p>
              <p className="bg-verified-soft px-4 py-1.5 text-verified">
                <span className="mr-2">+</span>allow: send.summary →
                approved.contacts
              </p>
              <p className="bg-verified-soft px-4 py-1.5 text-verified">
                <span className="mr-2">+</span>require: receipt.confirmed ==
                true
              </p>
              <p className="border-t border-border px-4 py-2 text-[11px] text-muted-foreground">
                patch_sha256 3b9f…77c2 · base 9f2c…e41a
              </p>
            </div>
            <p className="mt-3 text-[13px] leading-relaxed text-muted-foreground">
              A broad block-all candidate was rejected by validation — an
              authorized send failed. The targeted repair proceeds only because
              its actual tests passed.
            </p>
          </Spec>
        </Reveal>

        <Reveal delay={80}>
          <Spec label="Provider outage — explicit, never silent">
            <div className="rounded-md border border-signal/40 bg-signal-soft p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="font-medium text-foreground">
                  Nightshift is unavailable
                </p>
                <Chip tone="signal" dot>
                  Provider outage
                </Chip>
              </div>
              <p className="mt-2 text-[13px] leading-relaxed text-foreground/80">
                The case stays in Explaining. No silent fallback to sample mode;
                the intake snapshots remain immutable.
              </p>
              <button className="mt-3 rounded-sm border border-foreground/25 px-3.5 py-1.5 text-sm font-medium text-foreground transition-colors duration-150 hover:bg-card">
                Retry
              </button>
            </div>
            <p className="mt-3 text-[13px] leading-relaxed text-muted-foreground">
              Missing snapshots, stale reviews and rate limits render as first-
              class states — with the next permitted action always named.
            </p>
          </Spec>
        </Reveal>
        <Reveal delay={160}>
          <Spec label="Empty & loading — no fabricated progress">
            <div className="space-y-3">
              <div className="flex items-center gap-3 rounded-md border border-border bg-background p-4">
                <span className="h-2 w-2 animate-pulse rounded-full bg-reported" />
                <p className="text-[13px] text-foreground">
                  Validating candidate 2 of 2 — replay running
                </p>
              </div>
              <div className="rounded-md border border-dashed border-border bg-background p-4">
                <p className="text-[13px] font-medium text-foreground">
                  No application receipt for this action
                </p>
                <p className="mt-1 text-[13px] text-muted-foreground">
                  The outcome reads “allowed · unconfirmed” until a receipt
                  exists. Evidence requests are logged for the investigator.
                </p>
              </div>
            </div>
            <p className="mt-3 text-[13px] leading-relaxed text-muted-foreground">
              Loading states state what is actually happening. Empty states name
              the missing evidence and the next permitted action.
            </p>
          </Spec>
        </Reveal>
      </div>
    </Section>
  );
}

/* ============================================================
   ICONOGRAPHY
   ============================================================ */

const ICON_TILES: { key: NodeIconKey; label: string }[] = [
  { key: "task", label: "Authorized task" },
  { key: "document", label: "Untrusted document" },
  { key: "action", label: "Attempted action" },
  { key: "policy", label: "Policy snapshot" },
  { key: "receipt", label: "Application receipt" },
  { key: "tools", label: "Tool surface" },
  { key: "reference", label: "Trusted reference" },
  { key: "claim", label: "Verdict claim" },
];

export function IconsSection() {
  return (
    <Section id="icons">
      <Reveal>
        <SectionHead
          eyebrow="Iconography"
          title="Icons are nouns, not decoration"
          lead="Every icon maps one-to-one to a node type a reviewer can open. Learning the icons is learning the evidence ontology — eight marks, no more."
        />
      </Reveal>
      <div className="mt-12 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {ICON_TILES.map((t, i) => (
          <Reveal key={t.key} delay={i * 50}>
            <div className="flex h-full flex-col items-center rounded-lg border border-border bg-card px-4 py-7 text-center">
              <span className="grid h-12 w-12 place-items-center rounded-md border border-border bg-secondary text-foreground">
                <NodeIcon name={t.key} className="h-6 w-6" />
              </span>
              <p className="mt-3 text-sm font-medium text-foreground">{t.label}</p>
            </div>
          </Reveal>
        ))}
      </div>
      <Reveal delay={120}>
        <p className="mt-6 text-center font-mono text-[11px] tracking-[0.16em] text-muted-foreground uppercase">
          24px grid · 1.75px stroke · round caps · currentColor only
        </p>
      </Reveal>
    </Section>
  );
}

/* ============================================================
   MOTION
   ============================================================ */

export function MotionSection() {
  return (
    <Section id="motion" className="bg-secondary/40">
      <Reveal>
        <SectionHead
          eyebrow="Motion"
          title="Evidence arrives — it never performs"
          lead="This product earns trust by being calm. Movement exists to show where a fact came from, and then to get out of the way."
        />
      </Reveal>
      <div className="mt-12 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[
          {
            t: "120–480ms, one easing",
            d: "Nothing animates faster than it can be read, nothing lingers. A single cinematic easing — no bounces, no springs.",
          },
          {
            t: "Movement follows the chain",
            d: "Panels enter from their source edge; the detail drawer slides from the evidence that supports it.",
          },
          {
            t: "Status speaks once",
            d: "A state change pulses exactly once, then rests. Only an indeterminate job may keep breathing.",
          },
          {
            t: "Stillness is the default",
            d: "prefers-reduced-motion is honored everywhere: a static read is always complete.",
          },
        ].map((p, i) => (
          <Reveal key={p.t} delay={i * 70}>
            <div className="h-full rounded-lg border border-border bg-card p-6">
              <h3 className="font-display text-lg font-semibold text-foreground">
                {p.t}
              </h3>
              <p className="mt-2.5 text-[13px] leading-relaxed text-muted-foreground">
                {p.d}
              </p>
            </div>
          </Reveal>
        ))}
      </div>
      <Reveal delay={140}>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <div className="flex items-center gap-5 rounded-lg border border-border bg-card p-6">
            <svg width="120" height="36" aria-hidden="true">
              <line
                x1="4"
                y1="18"
                x2="116"
                y2="18"
                stroke="var(--color-uncertain)"
                strokeWidth="1.75"
                strokeDasharray="4 6"
                className="tv-dash"
              />
            </svg>
            <p className="text-[13px] text-muted-foreground">
              An inferred relation drifts — slowly enough to read as a
              hypothesis, never as a settled fact.
            </p>
          </div>
          <div className="flex items-center gap-5 rounded-lg border border-border bg-card p-6">
            <span className="tv-pulse-once inline-block">
              <Chip tone="signal" dot>
                Awaiting review
              </Chip>
            </span>
            <p className="text-[13px] text-muted-foreground">
              The review gate pulses once when it opens — then holds still
              while a human decides.
            </p>
          </div>
        </div>
      </Reveal>
    </Section>
  );
}

/* ============================================================
   HONESTY BAND — wording is a safety feature
   ============================================================ */

export function HonestySection() {
  return (
    <section className="bg-dossier px-6 py-20 text-primary-foreground sm:px-10 lg:py-28">
      <div className="tv-grain mx-auto w-full max-w-6xl">
        <Reveal>
          <div className="grid gap-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
            <div>
              <p className="font-mono text-xs font-medium tracking-[0.18em] text-primary-foreground/60 uppercase">
                The wording system
              </p>
              <h2 className="mt-3 font-display text-3xl leading-tight font-semibold sm:text-4xl">
                Wording is a safety feature.
              </h2>
              <p className="mt-4 max-w-md text-primary-foreground/75">
                In a forensic tool, a soft synonym can be an incident. The
                vocabulary is therefore fixed, and the interface is never
                allowed to be more certain than its evidence.
              </p>
              <ul className="mt-8 space-y-3 text-sm text-primary-foreground/85">
                {[
                  "Percentages appear only when derived from explicit counts and a stated denominator.",
                  "Incomplete, inconclusive and stale never wear the success treatment.",
                  "A resisted attack means the model did not attempt the unsafe action — not that a control blocked it.",
                  "A recording is never presented as a new live run.",
                  "Approval binds exact hashes — approved is not deployed.",
                ].map((r) => (
                  <li key={r} className="flex gap-3">
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-signal" />
                    {r}
                  </li>
                ))}
              </ul>
            </div>
            <div className="space-y-4">
              {OUTCOMES.map((o) => (
                <div
                  key={o.chip}
                  className="rounded-lg border border-white/10 bg-white/5 p-5"
                >
                  <Chip tone={o.tone} dot>
                    {o.chip}
                  </Chip>
                  <p className="mt-2.5 text-sm leading-relaxed text-primary-foreground/80">
                    {o.def}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

/* ============================================================
   FOOTER
   ============================================================ */

export function SiteFooter() {
  return (
    <footer className="border-t border-border px-6 py-14 sm:px-10">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 md:flex-row md:items-start md:justify-between">
        <div className="max-w-md">
          <p className="font-display text-xl font-semibold text-foreground">
            TraceVerdict<span className="text-signal">.</span>
          </p>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
            Next: the connected case-workspace prototype on the sample API —
            before any secondary dashboard is polished.
          </p>
        </div>
        <p className="max-w-md font-mono text-[11px] leading-relaxed text-muted-foreground">
          TraceVerdict is a working name; IntentSeal is the underlying runtime
          protection foundation. Naming clearance pending. No measured
          time-saving or security-effectiveness claim is established.
        </p>
      </div>
    </footer>
  );
}
