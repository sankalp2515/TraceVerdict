# TraceVerdict frontend integration

The product frontend now lives in `apps/web` in this repository. Start it from the repository root with `npm run frontend:install` and `npm run frontend:dev`. See [repository integration](FRONTEND_REPOSITORY.md).

Backend: `http://127.0.0.1:8000`. Local origins currently allowed: localhost/127.0.0.1 on ports 5173 and 3001. Zetaris occupies port 3000. Set `INTENTSEAL_CORS_ORIGINS` on the backend for any different origin.

The existing case/repair routes are unchanged. Additive routes now include `GET /v1/cases`, `GET /v1/agents`, `GET /v1/connections`, and browser-session endpoints. The live schema is `/openapi.json`; a copy is checked in at `docs/traceverdict-openapi.json`.

## Browser authentication

Use a workspace access-key login form. The user enters a scoped application credential, not a Zetaris/NVIDIA/Nightshift credential. Project and reviewer credentials are separate. The private local backend `.env` contains `TRACEVERDICT_PROJECT_KEY` and `TRACEVERDICT_ADMIN_KEY`. Never send the whole `.env` to an agency or embed either key in frontend source, build variables, localStorage or a public bundle.

```javascript
const API = 'http://127.0.0.1:8000';
let csrf;
async function login(accessKey) {
  const response = await fetch(`${API}/v1/auth/session`, {
    method: 'POST', credentials: 'include',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({api_key: accessKey}),
  });
  if (!response.ok) throw new Error('Workspace sign-in failed');
  const session = await response.json();
  csrf = session.csrf_token;
  return session; // name, scope, org, expires_at; never the access key
}
async function call(path, {method = 'GET', body} = {}) {
  const response = await fetch(`${API}${path}`, {
    method, credentials: 'include',
    headers: {'Content-Type': 'application/json', ...(method !== 'GET' ? {'X-CSRF-Token': csrf} : {})},
    ...(body !== undefined ? {body: JSON.stringify(body)} : {}),
  });
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  return response.json();
}
```

On refresh, `GET /v1/auth/session` with `credentials: 'include'` returns the session and CSRF token. On sign-out, `POST /v1/auth/logout` with the CSRF header invalidates the session. The cookie is HttpOnly, SameSite=Lax, expiring and database-backed. Mutating cookie-authenticated requests require both an allowed Origin and the CSRF token. Existing Authorization bearer headers remain supported for trusted server/CLI clients.

For local HTTP only, the local installation sets `TRACEVERDICT_COOKIE_SECURE=false`. Production must use HTTPS and `TRACEVERDICT_COOKIE_SECURE=true` (the default). Sessions are invalidated when their originating application credential is removed/rotated.

Use one hostname consistently for the frontend and backend during local cookie testing: either localhost for both or 127.0.0.1 for both. Crossing those sites can invoke browser SameSite rules. Set `API='http://localhost:8000'` for a frontend at `http://localhost:5173`.

## Cases and jobs

- `GET /v1/cases?limit=20&cursor=...` returns `{items, next_cursor}` with tenant/agent filtering. Ordering is a stable case-ID cursor, not a promise of chronological order.
- `GET /v1/agents` returns `{agents: [{agent_id, tenant_id}]}` visible to the caller.
- `GET /v1/connections` checks the application database, real Nightshift discovery and the real Zetaris evidence view. It returns status metadata only.
- Long work returns a persisted job. Poll its existing job URL and stop at `complete`/`incomplete`. Investigation is bounded at 180 seconds; the larger replay validation suite defaults to a separate 600-second deadline.
- Case history schema 2 stores compact observation manifests in the case; use the existing `/history/{version}` endpoint for full historical projections.
- Candidate `origin` distinguishes `model`, `api`, and `sample-template`. An explicit disruptive comparison supplied through the API must not be presented as a model recommendation.
- Only a passing validation can reach approval. Render `INCOMPLETE`, `INCONCLUSIVE`, `REJECTED` and `STALE` honestly.

Continue using the product brief for screen design. No frontend code has been changed by this backend work.


## Customer capture onboarding update

Reviewer-only agent registration and original capture import are now available on Agents. The Overview page can publish live collecting cases to operator-enabled managed sources. See docs/CUSTOM_INTEGRATIONS.md at the repository root. New intake controls passed component/API checks and a real nonfixture Zetaris/Nightshift integration. A new browser walkthrough was unavailable because browser use is disabled in Work settings.
