import { createFileRoute, Link } from "@tanstack/react-router";
import { cn } from "@/lib/utils";
import heroImg from "@/assets/hero-evidence.jpg";
import {
  FlowSection,
  FoundationsSection,
  GraphSection,
  HonestySection,
  IconsSection,
  MotionSection,
  SiteFooter,
  StorySection,
  ComponentsSection,
} from "@/components/tv/sections";
import { NodeIcon } from "@/components/tv/icons";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      {
        title: "TraceVerdict — A conclusion you can inspect",
      },
      {
        name: "description",
        content:
          "The design system and experience for TraceVerdict (IntentSeal Explain): an investigation workspace where every verdict shows its work — evidence, critique, tested policy repairs, and human review.",
      },
      { property: "og:title", content: "TraceVerdict — A conclusion you can inspect" },
      {
        property: "og:description",
        content:
          "An investigation workspace for suspicious AI-agent actions: evidence you can open, an explanation a critic has challenged, and a policy repair tested before a human approves.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "twitter:title", content: "TraceVerdict — A conclusion you can inspect" },
      {
        name: "twitter:description",
        content:
          "Evidence, critique, tested policy repairs, human review — a conclusion you can inspect.",
      },
    ],
    links: [],
  }),
  component: Index,
});

const NAV = [
  { href: "#story", label: "Story" },
  { href: "#flow", label: "Flow" },
  { href: "#graph", label: "Graph" },
  { href: "#foundations", label: "Foundations" },
  { href: "#components", label: "Components" },
  { href: "#motion", label: "Motion" },
];

const PRINCIPLES = [
  { icon: "receipt" as const, text: "Every claim carries its source" },
  { icon: "claim" as const, text: "Uncertainty is rendered, never hidden" },
  { icon: "policy" as const, text: "Nothing deploys without a human" },
];

function Index() {
  return (
    <div className="min-h-screen bg-background">
      {/* The gate line: signal orange is reserved for enforcement — the page
          opens under a boundary, just like the product. */}
      <div className="h-1 bg-signal" aria-hidden="true" />

      <header className="sticky top-0 z-40 border-b border-border bg-background/90 backdrop-blur">
        <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between gap-4 px-6 sm:px-10">
          <a href="#top" className="flex min-w-0 items-center gap-2">
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-sm bg-primary text-primary-foreground">
              <NodeIcon name="claim" className="h-4.5 w-4.5" />
            </span>
            <span className="truncate font-display text-lg font-semibold text-foreground">
              TraceVerdict<span className="text-signal">.</span>
            </span>
          </a>
          <nav className="hidden items-center gap-6 md:flex">
            {NAV.map((n) => (
              <a
                key={n.href}
                href={n.href}
                className="text-sm text-muted-foreground transition-colors duration-150 hover:text-foreground"
              >
                {n.label}
              </a>
            ))}
          </nav>
          <span className="hidden shrink-0 rounded-sm border border-border px-2.5 py-1 font-mono text-[11px] text-muted-foreground sm:inline-block">
            Design system · v1
          </span>
        </div>
      </header>

      <main id="top">
        {/* ---------------- HERO ---------------- */}
        <section className="px-6 pt-16 pb-20 sm:px-10 lg:pt-24 lg:pb-28">
          <div className="mx-auto grid w-full max-w-6xl items-center gap-14 lg:grid-cols-[1.02fr_0.98fr]">
            <div>
              <p className="tv-rise font-mono text-xs font-medium tracking-[0.18em] text-muted-foreground uppercase">
                IntentSeal Explain · Investigation workspace
              </p>
              <h1
                className="tv-rise mt-5 font-display text-5xl leading-[1.08] font-semibold text-foreground sm:text-6xl"
                style={{ animationDelay: "80ms" }}
              >
                A conclusion you can&nbsp;inspect.
              </h1>
              <p
                className="tv-rise mt-6 max-w-xl text-lg leading-relaxed text-muted-foreground"
                style={{ animationDelay: "160ms" }}
              >
                When an AI agent acts on an instruction it was never given,
                TraceVerdict files the case: evidence you can open, an
                explanation a critic has challenged, and a policy repair tested
                against unsafe behavior and legitimate work alike — before a
                human approves the exact artifact.
              </p>
              <div
                className="tv-rise mt-9 flex flex-wrap gap-3"
                style={{ animationDelay: "240ms" }}
              >
                <a
                  href="#foundations"
                  className="rounded-sm bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground transition-colors duration-150 hover:bg-primary/85"
                >
                  Tour the design system
                </a>
                <a
                  href="#graph"
                  className="rounded-sm border border-border bg-card px-5 py-2.5 text-sm font-medium text-foreground transition-colors duration-150 hover:bg-accent"
                >
                  Open the evidence graph
                </a>
              </div>
              <ul
                className="tv-rise mt-12 grid gap-3 border-t border-border pt-8 sm:grid-cols-3"
                style={{ animationDelay: "320ms" }}
              >
                {PRINCIPLES.map((p) => (
                  <li key={p.text} className="flex items-start gap-2.5">
                    <NodeIcon
                      name={p.icon}
                      className="mt-0.5 h-4.5 w-4.5 shrink-0 text-signal"
                    />
                    <span className="text-[13px] leading-snug font-medium text-foreground">
                      {p.text}
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="tv-rise" style={{ animationDelay: "200ms" }}>
              <figure className="rounded-lg border border-border bg-card p-3 shadow-[0_24px_60px_-30px_color-mix(in_oklab,var(--color-foreground)_35%,transparent)]">
                <img
                  src={heroImg}
                  alt="Editorial illustration: a magnifying lens over a dossier, nodes of an evidence chain sealed with a wax stamp"
                  width={1600}
                  height={1000}
                  className="h-auto w-full rounded-md"
                />
                <figcaption className="flex items-center justify-between px-2 pt-3 pb-1">
                  <span className="font-mono text-[11px] tracking-[0.16em] text-muted-foreground uppercase">
                    Fig. 01 — The evidence chain
                  </span>
                  <span className="h-1.5 w-1.5 rounded-full bg-signal" />
                </figcaption>
              </figure>
            </div>
          </div>
        </section>

        {/* ---------------- SECTIONS ---------------- */}
        <StorySection />
        <FlowSection />
        <GraphSection />
        <FoundationsSection />
        <ComponentsSection />
        <IconsSection />
        <MotionSection />
        <HonestySection />
      </main>

      <SiteFooter />
    </div>
  );
}
