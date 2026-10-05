# UI/UX brief: [Product Name] Security Console

> For the designer/builder (Codex, Lovable, or Claude Code with design skills). Owner: Sankalp.
> Everything below is product truth from the PRD (docs/11), system design (docs/09) and measured results
> (eval/reports). The back end is built and stable; this brief is about the experience on top of it.

## 1. What the product is (one breath)

**[Product Name] is a security gateway that sits around any AI agent.** It inspects everything the agent reads
(web pages, PDFs, Word files, emails, API responses, code, images), removes only the malicious part, checks
every action the agent tries to take (send an email, fetch a URL, query a database), and records every decision
so a security team can replay exactly what happened.

Promise: *catch what can be caught, limit what a hijacked agent can do, and prove what happened.*
Principle shown everywhere: **rules decide, AI advises** (every decision has a named rule and a reason).

## 2. Who looks at it, and what they must feel

| Audience | Context | In 3 minutes they must… | Feeling |
|---|---|---|---|
| Hackathon judges / investors | Live demo, video, public link | See an agent get hijacked, then see the same attack stopped, with evidence | "This works, and it's real" |
| Security reviewer (buyer) | Approving an agent for production | Trust the numbers; replay any incident | "I can sign off on this" |
| Agent builder (user) | Integrating SDK/proxy | See it does not break legitimate work (no false alarms) | "Safe to switch on" |

Tone: serious enterprise security product (think Wiz, Datadog Security, Linear-level polish), calm and precise,
evidence-first. Not hacker-aesthetic, not cartoonish. Green/red are for decisions, not decoration.

## 3. The "aha" moment to design around

Same task, same agent, side by side:
- **Protection OFF:** the agent follows hidden instructions: a fake secret leaves through the (sandboxed) outbox.
- **Protection ON:** the malicious span is removed or the tool call is stopped; the agent still finishes the
  legitimate task; a timeline shows *exactly* which span, which attack type, which tier, which rule.

Make the OFF→ON contrast unmistakable (e.g. outbox and "Secret leaked: YES/NO" as the visual climax).

## 4. Screens (information architecture)

| Screen | Purpose | Content (all from the API) | Key states |
|---|---|---|---|
| **Overview / landing** (new, recommended for investors) | Explain the product in 20 s; route to the demo | One-line promise, 3-step "how it works" (inspect → contain → prove), headline metrics from the scorecard, CTA "Run the live demo" | Backend waking up (free hosting cold start) |
| **Playground** (CON-1) | The live demo | Scenario picker (S1–S9, each with attack-type tags and channel), Run OFF / Run ON / Run both; per side: agent answer, tool calls (allowed/blocked with reason), sandbox outbox, secret leaked yes/no, model used; below: decision timeline | Idle, running (10–40 s, show progress per step), success, backend error, degraded decision |
| **Session replay** (CON-2) | Reconstruct an incident | Ordered events: user message → content in (source/channel) → finding (span preview, attack-type labels, score, tier) → decision (rule, reason, latency) → tool call (requested args, pinned-field rewrites, final args) | Empty, loading, not found |
| **Scorecard** (CON-3) | Evidence for reviewers and the grid claim | Attack success OFF vs ON (overall, per 9 attack types, per channel), relative reduction, benign utility, false-alarm rate, latency p95, cost overhead, static vs adaptive, F/D grid claim with evaluation date | Suite switch (headline / broad), "pending" values |
| **Decisions feed** (CON-4) | Monitor live traffic | Table: time, decision, source, rule + reason, attack types, session link; filters by decision / type / agent | Empty, filtered-empty |
| Later (P1): Policy view, Approvals inbox, Cost panel | | | |

Global: backend status (online / waking up / unavailable), light and dark themes, works at phone width,
keyboard accessible, product name and logo from one config value.

## 5. Vocabulary (use consistently)

- Decisions: **Allowed**, **Neutralised** (malicious span removed, rest kept), **Blocked**, **Needs approval**.
- The 9 attack types (exact names): Instruction Override, Role Change, Secret Extraction, Tool Abuse, Credential
  Theft, Context Poisoning, Multi-Step Jailbreaks, Encoded Instructions, Indirect Prompt Injection.
- Channels: user, web, html, pdf, docx, markdown, email, api, code, ocr_text, image, db.
- Tiers: Tier 0 structure · Tier 1 classifier · Tier 2 AI judge. "Degraded" = an AI tier was unavailable and the
  rules held the content safely.

## 6. Data contract (do not change the API; build on it)

- Base URL from `VITE_API_BASE`; read-only public key from `VITE_API_KEY` sent as `Authorization: Bearer <key>`.
  Product name from `VITE_PRODUCT_NAME`. CORS allows the Console origin (`ASG_CORS_ORIGINS` on the server).
- **Exact TypeScript types and calls already exist in `apps/console/src/api.ts`** — reuse that file as the
  contract. Endpoints: `GET /healthz`, `GET /demo/scenarios`, `POST /demo/run {scenario_id, protection}`,
  `GET /v1/sessions/{id}/events`, `GET /v1/decisions?decision=&label=&agent=`, `GET /v1/scorecard/{agent}`,
  `GET /v1/costs`, `GET /v1/policies/{agent}`. Interactive docs at `/docs` when the gateway runs.
- Run locally: `.venv/Scripts/python scripts/dev_gateway.py` (port 8000, dev key `dev-public-key`).
- Never display canary/secret values (the API already masks them as `[CANARY]`); never show raw attack text
  beyond the redacted previews the API returns.

## 7. Constraints

- Static build (Vercel/Netlify/Cloudflare Pages); no server-side code in the Console.
- React + TypeScript + Tailwind are already in place; shadcn/ui is a good fit for tables, dialogs, tabs.
- WCAG AA contrast, visible focus, keyboard navigation, `prefers-reduced-motion` respected.
- Free hosting sleeps: design the "waking up" state (up to ~60 s) so the demo never looks broken.
- Numbers on screen must come from the API (no hard-coded metrics): claims must match the evaluation report.

## 8. Definition of done for the UI

1. A first-time visitor understands the product and reaches a running demo in under 30 seconds.
2. OFF vs ON difference is obvious without reading paragraphs.
3. Every decision on screen can be clicked through to its reason, span, attack type, tier and rule.
4. Looks credible on a projector (1080p) and on a phone; light and dark.
5. All states designed: loading, empty, error, waking up, degraded.
