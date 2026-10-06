# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Security reviewer (approver / buyer)** at a company deploying LLM agents. Situation: asked to approve an agent
  that reads outside content and can act (email, files, databases, web). Job: decide on evidence, investigate
  incidents, set policy. Needs measurable numbers on *their* agent and an end-to-end replay of any session.
- **Agent builder (primary user)**: developer or platform lead. Job: protect an existing agent without rebuilding
  it and without breaking legitimate work, then hand the reviewer proof.
- **Hackathon judges and investors** (ET AI Hackathon 2026, Problem 2; finale and investor conversations).
  Situation: a short live demo, a 2–4 minute video, and a public link. Job: understand the product and see it
  work in under three minutes.

## Product Purpose

A security gateway that wraps any LLM agent. It inspects everything the agent reads, from every channel, removes
only the malicious part, checks every action the agent tries to take, and records every decision so a security
team can replay it. Success: hidden instructions lose influence, hijacks do not become tool misuse or leaks,
legitimate work still gets done, and every decision is explainable.

Promise: catch what can be caught, limit what a hijacked agent can do, and prove what happened. The product does
not claim prompt injection is solved.

## Positioning

Not another prompt classifier. Three things together: (1) inbound inspection on every channel, including what is
hidden in files ("see what the model sees"), with span-level removal instead of blocking whole documents;
(2) an action checkpoint that contains a hijacked agent (allow-lists, pinned identity fields, outbound secret
scan, "this target came from untrusted content"); (3) an evidence layer: a named rule and reason for every
decision, full session replay, and a scorecard measured on the customer's own agent. Rules decide; AI advises.

## Operating Context

- Surfaces: Python SDK, Gateway API, OpenAI-compatible LLM proxy (one setting to adopt), and this web Console.
- The Console talks to the Gateway API with a read-only public key (`apps/console/src/api.ts` is the contract).
- Demos run on a sandboxed reference research agent: a local fixture website, a fake customer database, a local
  outbox, and fake "canary" secrets. Nothing real is ever sent.
- Free hosting may sleep; first load can take up to a minute ("waking up").
- Monitor mode first, then enforce; humans are asked rarely, with a clear reason.

## Capabilities and Constraints

- Input channels: user messages, web pages, HTML, PDFs, Word, Markdown, email, API/JSON responses, source code,
  OCR text, images (via OCR), database records.
- Decisions: Allowed, Neutralised (span removed, rest kept), Blocked, Needs approval. Tiers: structure,
  classifier, AI judge. "Degraded" means an AI tier was unavailable and rules held the content safely.
- The nine attack types (exact names, required by the hackathon): Instruction Override, Role Change, Secret
  Extraction, Tool Abuse, Credential Theft, Context Poisoning, Multi-Step Jailbreaks, Encoded Instructions,
  Indirect Prompt Injection. Attack content is referred to only by these category names.
- Static front-end build; React + TypeScript + Tailwind v4 in `apps/console`.
- Undecided: product name (owner is generating candidates), hosting provider, grid claim (pending full evaluation).

## Brand Commitments

**IntentSeal** — “Keep AI agents inside the user’s intent.” (set in `VITE_PRODUCT_NAME`). Visual
language: the IntentSeal material design (night-violet canvas, frosted lavender gate, one blue-violet-magenta
gradient for the primary action), implemented in `apps/console/src/index.css`.

## Evidence on Hand

Measured results only, from `eval/reports/` (dated, commit-stamped). Measured figures are generated, never hand-typed: see `docs/EVALUATION.md` and the README results block. No customers, testimonials,
pricing, logos, press, or production deployments exist; never fabricate them. Numbers on screen must come from the
API, never be hard-coded.

## Product Principles

1. Evidence over assertion: every claim on screen traces to a measured report or a logged decision.
2. Contain, don't just detect: show what was stopped and why, not only scores.
3. Never break legitimate work: false alarms are a product failure; show utility next to protection.
4. Explain everything in plain language: rule, reason, span, attack type, tier.
5. Honest limits: degraded states, lower-bound metrics, and pending results are shown as such.

## Accessibility & Inclusion

WCAG 2.1 AA: contrast, visible keyboard focus, full keyboard navigation, reduced motion respected, works at phone
width and on a 1080p projector, light and dark themes.
