# IntentSeal backlog

Updated 7 Oct 2026 (Day 3 of 7) · deadline Sat 11 Oct, 11:59 PM IST. Frontend rebuilt first (D-032); everything
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
| B7 | Commit today's and yesterday's work (≈ 80 files) on a branch; open a PR | Eng (on your go-ahead) | S |

## C. Evaluation gaps (honest reporting needs these)

| # | Item | Size |
|---|---|---|
| C1 | G7b cost overhead measured on protected end-to-end runs only (current window mixes detection-only runs) | S |
| C2 | Multi-Step Jailbreaks: only 5 end-to-end cases (insufficient evidence); needs multi-turn generated cases | M |
| C3 | EVAL-4 adaptive round (generator choice per D-005/D-014; feedback/memory backend is ready) | M |
| C4 | PDF renderer: embed a Unicode font so look-alike attacks survive PDF delivery (today "not delivered", D-031) | S |
| C5 | Verify S1–S6 and S9 demo scenarios against the unprotected demo model (only S7 verified) so the OFF lane shows a real compromise | S |
| C6 | Garak `run.sh` full run against the agent (harvest is done; scored garak run is not) | S |

## D. Frontend follow-ups (after the rebuild)

| # | Item | Size |
|---|---|---|
| D1 | Reviewer actions in the Console (approve/deny, confirm attack, mark false positive, edit policy) behind an admin sign-in; today the Console is read-only by design (public key only) | M |
| D2 | Cost panel (CON-6) and live metrics panel (`/v1/metrics`) on the Results page | S |
| D3 | Decisions feed: pagination and "since" filter | S |
| D4 | Accessibility pass with a screen reader and keyboard-only run of the Playground; contrast check of light theme accents | S |
| D5 | Real Console screenshots and a short screen recording for the deck/video | S |

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
