# IntentSeal backlog

Updated 7 Oct 2026 (Day 3 of 7, sections C and D worked) · deadline Sat 11 Oct, 11:59 PM IST. Frontend rebuilt first (D-032); everything
below is what remains. Status of built work: `docs/STATUS.md`. Measured results: `docs/EVALUATION.md` (generated).

Legend: **Owner** = needs Sankalp's decision or account · **Eng** = engineering can do it · size S < 2 h, M ≈ half a
day, L ≈ a day.

## A. Decisions needed first (Owner)

| # | Item | Why it blocks |
|---|---|---|
| A1 | Grid self-declaration (F / D). The §15 rule currently gives **none / none** (held-out FPR 10.3%, user-turn recall 60.4%) | Deck, README and video quote it; over- and under-claiming are both penalised |
| A2 | Whether to try one detection change before the final run (pick at most one or two): judge user turns for high-risk agents · second judge opinion before blocking unflagged content · larger held-out benign set | Each needs a full rerun (≈ 2 h of free-tier quota) |
| A3 | Hosting accounts (backend: Hugging Face Spaces or Render/Fly; Console: Vercel/Netlify/Cloudflare Pages) | Public demo link is mandatory |
| A4 | Repo name, public-visibility timing, LICENSE choice (MIT or Apache-2.0) | Public repo is mandatory; PyPI and judges expect a licence |

## B. Submission must-haves

| # | Item | Who | Size |
|---|---|---|---|
| B1 | Dockerfile for the gateway (API + proxy + demo; engine, local classifier, OCR, SQLite) and a warm-up on start | Eng | M |
| B2 | Deploy backend + Console; public read-only demo key; CORS to the Console origin; "waking up" state verified | Owner + Eng | M |
| B3 | Final evaluation on the final commit: `eval/run_protected.sh` → `python -m asg_eval.summary` → `python -m asg_eval.readme`; commit reports | Eng | M (mostly waiting) |
| B4 | Pitch deck (10–12 slides) from the generated numbers, with real Console screenshots | Owner (+ Eng draft) | M |
| B5 | Demo video 2–4 min following PRD §16 storyline; record against a warm backend | Owner | M |
| B6 | Incognito link check of repo, Console, video, deck; submit on Unstop | Owner | S |
| B7 | ~~Commit and publish~~ Done 7 Oct: GitHub `sankalp2515/intentseal` (private), CI green | Eng | ✅ |

## C. Evaluation gaps (worked 7 Oct)

| # | Item | Status |
|---|---|---|
| C1 | G7b cost overhead per protected run | ✅ Measured: headline suite security cost = **35%** of agent cost (1.02 security tokens per agent token); multi-turn suite 0.26 tokens per token. Far from the < 10% stretch; reported as is (D-033) |
| C2 | Multi-Step Jailbreaks evidence | ✅ 40 split-turn variants of generated attacks (D-034): unprotected 5/40 compromised → protected 0/40; caught at any layer 82.8% over 29 multi-step cases (below the 85% target) |
| C3 | EVAL-4 adaptive round | ⏸ **Owner:** promptfoo's iterative attackers need a verified promptfoo account (D-036). Ready: `eval/promptfoo/configs/adaptive.yaml`, `python -m asg_eval.adaptive learn/report` |
| C4 | Unicode font in PDF fixtures | ✅ Look-alike text now survives PDF delivery (D-035); `pdf|homoglyph` leaves the "not delivered" list in the B3 final run |
| C5 | Verify demo scenarios against the unprotected agent | ✅ Done, honest negative: over 60 OFF runs on two free models (31 on gpt-oss-120b, 29 on Nemotron), only **S7** reproducibly compromises the unprotected agent (on Nemotron, `agent_eval`); S1–S6 and S9 resisted. Each scenario file states its status. **Owner:** pick the demo model and storyline (see below) |
| C6 | Scored garak run | ✅ garak's own detectors, unprotected vs protected, reported in `docs/EVALUATION.md` (garak sees answer text only, not tool calls) |

Demo-storyline options from C5: (a) set `ASG_DEMO_AGENT_ROLE=agent_eval` for the public demo and lead with S7;
(b) keep gpt-oss-120b and show the OFF lane honestly ("the model resisted this time") while the ON lane shows what
IntentSeal flagged; (c) both: S7 for the compromise, S2/S3 for detection on documents.

## D. Frontend follow-ups (worked 7 Oct)

| # | Item | Status |
|---|---|---|
| D1 | Reviewer actions | ✅ Reviewer sign-in with the reviewer's own admin key (`/v1/whoami`, tab-session only, D-037); approve/deny, confirm attack / false alarm, forget memory entries, switch mode / edit policy as validated JSON. Verified live |
| D2 | Cost and live metrics panels | ✅ Results page: Spend (per-run G7b + 7-day usage by model) and Live operations (1 h / 24 h / 7 days) |
| D3 | Decisions pagination and time filter | ✅ `before` cursor in the API; "Load older" and a When filter in the Console |
| D4 | Accessibility | ✅ Automated pass on all 7 pages (names, labels, alt, headings, ids, focus style, reduced motion, skip link); WCAG AA contrast computed for every text token in both themes, light accent darkened to pass. **Owner (10 min):** one keyboard-only run of the Playground and one screen-reader pass (NVDA/Narrator) |
| D5 | Screenshots for deck and video | ✅ `docs/media/console-*.png` (local, git-ignored; README uses a WebP). Screen recording left to the owner: recording the desktop would capture everything on screen |

## E. Engineering P1/P2 (only if time remains)

| # | Item | PRD | Size |
|---|---|---|---|
| E1 | PRX-6 incremental streaming (buffer tool-call chunks, stream text) | P1 | M |
| E2 | CORE-16 span re-mapping across chunks for long documents | P1 | M |
| E3 | Rename code namespace `asg_*` → `intentseal` (packages, imports, CLI) | — | M |
| E4 | PyPI: ship default config + starter policy (enforce), per-user data dir, `[embedded]` extra, LICENSE, TestPyPI dry run; publish after A4 | — | M |
| E5 | API-12 SIEM export / multi-tenant / Postgres | P2 | L |
| E6 | EVAL-6 Jev comparison | P2 | L |
| E7 | CORE-17 full taint tracking | P2 | L |
