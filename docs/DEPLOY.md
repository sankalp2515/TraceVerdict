# Deploying IntentSeal

Two parts, deployed separately:

| Part | What it is | Where it can run |
|---|---|---|
| **Gateway** (`Dockerfile`) | Gateway API, OpenAI-compatible LLM proxy, demo runner, Core Engine with the local classifier (baked into the image), OCR | Any Docker host: Hugging Face Spaces (Docker), Render, Fly.io, a VM with `docker compose` |
| **Console** (`apps/console`) | Static React site (HashRouter: no rewrite rules needed) | Any static host: Vercel, Netlify, Cloudflare Pages, GitHub Pages |

The Console only ever holds the **public read-only key**. Reviewers sign in with their own admin key, which stays in
that browser tab's session storage (D-037).

## 1. Settings

All configuration is environment variables; no secret is ever written into the image or the repository.
Settings named `ASG_*` (the names used until 7 Oct 2026) still work when the new `INTENTSEAL_*` name is unset (D-038).

| Variable | Required | Purpose |
|---|---|---|
| `GROQ_API_KEY`, `GEMINI_API_KEY`, `NVIDIA_API_KEY`, `OPENROUTER_API_KEY`, `MISTRAL_API_KEY` (`_2`, `_3`… for spares) | at least one | Free-tier LLM providers for the judge, the proxy upstream and the demo agent. Without any, flagged content is held (fail closed) |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `AZURE_OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, `XAI_API_KEY`, `TOGETHER_API_KEY` | no | Provider keys the gateway holds for agents whose policy says `upstream: {provider: …, key: gateway}`. Agents with `key: client` send their own key in `X-Upstream-Key` instead. Azure and local servers: set the base URL in `config/providers.yaml` and enable the entry |
| `INTENTSEAL_PUBLIC_URL` | recommended | The gateway's public URL, used in the Console's connection snippets (default: the URL the request came in on) |
| `INTENTSEAL_API_KEYS` | yes | `name:key:scope[:org[:agent\|agent]]`, comma separated. Scopes `project` (agents, CI, SIEM collectors) and `admin` (reviewers). Org `*` = all organisations. Use long random keys |
| `INTENTSEAL_PUBLIC_KEY` | for the Console | Read-only key built into the Console |
| `INTENTSEAL_PUBLIC_AGENTS` | recommended | Agents the public key can see, e.g. `research-agent,research-agent-monitor` (the demo agents). Without it the public key sees every agent of the default organisation |
| `INTENTSEAL_CORS_ORIGINS` | for the Console | The Console origin(s), e.g. `https://intentseal.example.app` |
| `INTENTSEAL_CANARIES` | for the demo | Canary values planted in the reference agent's sandbox (never real secrets) |
| `INTENTSEAL_DATABASE_URL` | no | `postgresql://…` for PostgreSQL; otherwise SQLite at `INTENTSEAL_DB_PATH` (image default `/data/intentseal.db`) |
| `INTENTSEAL_POLICY_DIR` | no | Image default `/data/policies`: seeded from the bundled policies on first start, so API edits persist on the volume |
| `INTENTSEAL_STORE_PREVIEWS` | no | Image default `0` (hashes only, no content previews). Set `1` for the public demo so Replay shows redacted 160-character previews of the fixture content |
| `INTENTSEAL_TRUSTED_PROXIES` | behind a proxy | Addresses whose `X-Forwarded-For` is trusted (per-client rate limits). `*` on Hugging Face Spaces / Render, where the platform proxy is the only way in |
| `INTENTSEAL_RATE_LIMIT_PER_MIN` / `INTENTSEAL_PUBLIC_RATE_LIMIT_PER_MIN` | no | Per key (default 120) / per public client (default 20) |
| `INTENTSEAL_DEMO_RUNS_PER_HOUR` | no | Global cap on live demo runs (default 60), protects the free LLM quota |
| `INTENTSEAL_DEMO_AGENT_ROLE` | no | `agent` (default) or `agent_eval` (the model on which S7 reproducibly compromises the unprotected agent; see BACKLOG C5) |
| `INTENTSEAL_SIEM_SINKS` | no | Push decisions to `jsonl:/data/siem/decisions.jsonl`, `webhook:https://…`, `syslog:udp://host:514` (see `intentseal_core/siem.py`) |
| `INTENTSEAL_MAX_BODY_BYTES`, `INTENTSEAL_MAX_TEXT_CHARS`, `INTENTSEAL_JUDGE_MAX_WINDOWS`, `INTENTSEAL_TIER1_PER_CHUNK_S`, `INTENTSEAL_TIER1_MAX_S` | no | Input and long-document limits (CORE-16; defaults 2 MB, 1,000,000 characters, 8 judge windows, 0.75 s per chunk, 30 s) |
| `PORT` | no | Listen port (default 8000) |

Generate keys with `python -c "import secrets; print(secrets.token_urlsafe(32))"`.

## 2. Gateway

### Any Docker host

```bash
cp .env.example .env            # fill in provider keys and the INTENTSEAL_* values above
docker compose up --build -d    # gateway on :8000, data in the intentseal-data volume
curl http://localhost:8000/readyz
```

With PostgreSQL on the same host: set `POSTGRES_PASSWORD` and
`INTENTSEAL_DATABASE_URL=postgresql://intentseal:<password>@postgres:5432/intentseal` in `.env`, then
`docker compose --profile postgres up --build -d`.

### Hugging Face Spaces (free CPU tier)

1. Create a Space with the **Docker** SDK (blank template), public.
2. Push this repository to the Space (or the files the image needs: `Dockerfile`, `.dockerignore`, `requirements.lock`,
   `packages/`, `agents/`, `services/`, `config/`, `policies/`, `eval/scenarios/`, `eval/reports/*.json`,
   `examples/openai_agent/`). The Space's `README.md` must start with:

   ```yaml
   ---
   title: IntentSeal Gateway
   sdk: docker
   app_port: 8000
   ---
   ```
3. In the Space settings, add the variables from §1 as **Secrets** (keys) and **Variables** (the rest). For the public
   demo: `INTENTSEAL_PUBLIC_AGENTS=research-agent,research-agent-monitor`, `INTENTSEAL_STORE_PREVIEWS=1`,
   `INTENTSEAL_TRUSTED_PROXIES=*`, `INTENTSEAL_CORS_ORIGINS=<Console URL>`.
4. Storage: the free tier has no persistent disk, so the SQLite database and policy edits reset when the Space
   restarts. For data that must survive, point `INTENTSEAL_DATABASE_URL` at a hosted PostgreSQL (for example a free
   Neon or Supabase database); policies edited through the API still reset to the bundled ones on restart.
5. Free Spaces sleep after inactivity; the first request wakes them (about a minute, including the classifier load).
   The Console shows a "waking up" banner meanwhile.

### Checks after every deployment

```bash
GW=https://<your-gateway>
curl -s $GW/healthz                       # {"ok": true, ...}: the process is up
curl -s $GW/readyz                        # ready: true; checks.database, policies, tier1_classifier; llm_providers > 0
curl -s -H "Authorization: Bearer $PUBLIC_KEY" $GW/v1/whoami            # scope public, agents = the demo agents
curl -s -o /dev/null -w "%{http_code}\n" -H "Origin: https://evil.example" -X OPTIONS \
     -H "Access-Control-Request-Method: GET" $GW/v1/decisions          # no allow-origin header for other origins
```

Then open `$GW/docs` (OpenAPI) and run one Playground scenario from the Console.

## 3. Console

```bash
cd apps/console
npm ci
VITE_API_BASE=https://<your-gateway> VITE_API_KEY=<public key> npm run build    # output: apps/console/dist
```

Deploy `apps/console/dist` to the static host (Vercel/Netlify: project root `apps/console`, build command
`npm run build`, output `dist`, and the two `VITE_*` variables set in the host's build settings). The values are public
by design: the public key is read-only and limited to `INTENTSEAL_PUBLIC_AGENTS`. Add the Console URL to
`INTENTSEAL_CORS_ORIGINS` on the gateway.

## 4. Operating it

- **Logs**: one JSON access-log line per request (`intentseal.access`: request id, path, status, ms, session id). Send
  `X-Request-Id` to correlate a client call with its log line and decisions.
- **Metrics**: `GET /v1/metrics?hours=1` (decisions by type and rule, judge escalation rate, latency p50/p95, degraded
  decisions, provider errors, approvals pending, SIEM delivery counters). Alert on: `/readyz` not 200, `inspections.degraded`
  rising, `providers` errors rising, `siem.dropped` > 0.
- **SIEM**: pull `GET /v1/export/decisions?since=<ts>&format=jsonl|cef` with a project key, or push with
  `INTENTSEAL_SIEM_SINKS`.
- **Backups**: SQLite: `sqlite3 /data/intentseal.db ".backup '/data/backup-$(date +%F).db'"` (safe while running; WAL
  mode). PostgreSQL: `pg_dump`. Policies: `/data/policies/*.yaml` (versioned by the API on every change). Restore by
  stopping the gateway, putting the file back, starting it; `/readyz` confirms the database answers.
- **Rollback**: tag every image (`docker build -t intentseal-gateway:<git sha> .`); roll back by running the previous
  tag against the same volume. Schema changes are additive (new tables/columns only), so an older image runs on a
  newer database.
- **Key rotation**: add the new key to `INTENTSEAL_API_KEYS`, restart, move clients, remove the old key, restart.
  Provider keys: add `NAME_2`, remove the old one; a rejected key (401/403) is skipped automatically.
- **Incident switches**: put an agent in `monitor` mode (`PUT /v1/policies/<agent>` with `mode: monitor`) to stop
  enforcement while keeping the log, or back to `enforce`; set `INTENTSEAL_DEMO_RUNS_PER_HOUR=0` to pause the public demo.
- **Scaling**: one worker per container (sessions, rate limits and proxy state are in process). For more capacity run
  several containers with `INTENTSEAL_DATABASE_URL` (shared PostgreSQL) and session-affinity routing on `X-Session-Id`.
