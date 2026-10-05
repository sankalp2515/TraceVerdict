# Design brief for an external design/build tool (Lovable, Codex, or any designer)

Paste everything below the line. It states facts, goals and constraints only. It deliberately contains no visual
direction (no colours, fonts, metaphors, layouts or reference brands): that creative work is yours.

---

## What we are building

A web front end (public landing page + product console) for a security product for AI agents.
Product name is not decided yet: use the placeholder **[Product Name]** in one configurable place.

**The product in plain words.** Companies now let AI agents read outside content (web pages, PDFs, Word files,
emails, API responses, code, images) and act on it (send emails, query databases, fetch URLs). Text hidden in
that content can take over the agent. Our product sits around any agent: it inspects everything the agent reads,
removes only the malicious part, stops actions the user never asked for, and records every decision so a
security team can replay exactly what happened.

**Promise:** catch what can be caught, limit what a hijacked agent can do, and prove what happened.
**Principle:** rules decide, AI advises. Every decision has a named rule and a plain-language reason.
We never claim the problem is "solved".

## Who it is for

1. **Hackathon judges and investors** (national-level AI hackathon, then investor meetings): a 3-minute live demo,
   a recorded video, a public link. They must understand the product and see it work fast.
2. **Security reviewers** at companies deploying AI agents: they approve agents and investigate incidents. They
   need measured numbers and a step-by-step replay of any session.
3. **Agent builders** (developers): they need proof it doesn't break legitimate work.

## What the experience must achieve

- A first-time visitor understands what this is and reaches a working demo in under 30 seconds.
- The core "aha": the **same task on the same agent, run without protection and then with protection**. Without
  it, the agent is hijacked (a fake secret leaves through a sandboxed outbox). With it, the malicious part is
  removed or the action is stopped, and the agent still finishes the legitimate task. This contrast must be
  unmistakable without reading paragraphs.
- Every decision shown can be opened to see: what came in (source/channel), the exact part that was flagged, the
  attack type, which check caught it, the rule that decided, and the reason.
- Credible on a 1080p projector and on a phone.

## Surfaces and content

**1. Landing page.** Explain the product, prove it, and lead to the live demo. Content available: the promise,
how it works (inspect → contain → prove), measured results (below), the ways to adopt it (Python SDK,
OpenAI-compatible proxy where you change one setting, REST API), honest limits.

**2. Console** (four areas):
- **Playground:** pick a demo scenario (each has a title, the input channel, attack-type tags), run it without
  protection, with protection, or both; show for each run the agent's answer, the tool calls it tried (allowed or
  blocked, with the reason), the sandbox outbox, "secret leaked: yes/no", the model used; then the decision
  timeline for the protected run.
- **Session replay:** the ordered events of one session: message in → content in → finding (flagged part,
  attack types, score) → decision (rule, reason, latency) → tool call (requested arguments, any rewritten
  arguments, final arguments).
- **Scorecard:** results without vs with protection: overall and per attack type and per input channel; legitimate
  tasks completed; false-alarm rate; latency; and a pending "grid position" claim with its evaluation date.
- **Decisions feed:** a filterable list (by decision, attack type, agent) linking to the replay.

Global needs: backend status (online / waking up — free hosting can take up to a minute / unavailable),
light and dark themes, product name from one config value.

## Vocabulary (use exactly)

- Decisions: **Allowed**, **Neutralised** (malicious part removed, rest kept), **Blocked**, **Needs approval**.
- Attack types (exact names, required by the hackathon): Instruction Override, Role Change, Secret Extraction,
  Tool Abuse, Credential Theft, Context Poisoning, Multi-Step Jailbreaks, Encoded Instructions, Indirect Prompt
  Injection.
- Input channels: user message, web page, HTML, PDF, Word, Markdown, email, API response, source code, OCR text,
  image, database record.
- "Degraded": an AI check was unavailable and the rules held the content safely.

## Real numbers available (measured; show as measured, never invent others)

Attack success 4.3% without protection → 0.0% with protection (231 tests); a second suite shows 25% without
protection (protected run pending). Legitimate tasks completed with protection: 20/20. False alarms on tricky but
legitimate content: 4%. Added latency (fast path, 95th percentile): 196 ms. Secrets leaked with protection: 0.
On the live product these come from the API; do not hard-code them.

There are **no customers, logos, testimonials, pricing or press**. Do not invent any.

## Things that would make the result wrong (from the founder)

- **Aesthetics over usability:** heavy gradients and micro-animations, trendy low-contrast type, cards that look
  like headers, non-clickable things that look like buttons, navigation hidden behind obscure icons.
- **Disconnected flows:** dropping people into a complex workspace with no context, progress or sensible defaults;
  forced autoplay or laggy transitions; any dark pattern.
- **Flawed hierarchy:** everything shouting with equal weight; vague or ambiguous labels and error messages;
  failing accessibility (contrast, keyboard, focus, screen readers).
- **Generic AI SaaS template; hacker/fear aesthetic; too dense for investors; toy-like or playful.**

## Constraints

- React + TypeScript, static build (hosted on Vercel/Netlify/Cloudflare Pages). Tailwind is fine.
- WCAG 2.1 AA, full keyboard use, visible focus, respects reduced-motion; works from phone width to 1080p.
- All states designed: loading, empty, error, waking up, degraded, pending result.
- The back end already exists (FastAPI). If you connect to it: base URL and a read-only public key come from env
  (`VITE_API_BASE`, `VITE_API_KEY`, sent as `Authorization: Bearer <key>`). Endpoints: `GET /healthz`,
  `GET /demo/scenarios`, `POST /demo/run {scenario_id, protection: "on"|"off"}`,
  `GET /v1/sessions/{id}/events`, `GET /v1/decisions?decision=&label=&agent=`, `GET /v1/scorecard/{agent}`.
  We can share exact response types; until then, use realistic mock data clearly marked as mock.

## What we want from you

1. **Propose 2–3 genuinely different visual directions** for the landing page first view and one Console screen,
   each with a one-paragraph rationale tied to this audience and product. Do not build everything until we pick.
2. Then build the chosen direction: landing page + the four Console areas, with all states, light and dark,
   responsive.
3. Tell us any product question this brief leaves open instead of guessing.
