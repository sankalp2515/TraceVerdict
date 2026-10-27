# Frontend architecture and operation

## Retained stack

React 19, TypeScript, TanStack Start/Router, Vite, Tailwind 4, the existing Lovable configuration, Lucide icons, and the existing accessible UI primitives. The current stack already provides server rendering, route splitting and the Cloudflare Nitro build target; a rewrite to another framework adds migration risk without product benefit. CSS handles the modest motion requirements; a second animation runtime is unnecessary here.

`src/routes` composes route entry points. `src/features/marketing` owns the public visitor journey. `src/features/workspace` owns typed API contracts, session calls, outcome interpretation, evidence graph and case workspace. `src/components/tv` holds retained concept components and the shared brand. `src/product.css` extends existing tokens for the finished product surfaces. The generated route tree must not be edited manually.

## Data and authentication

By default the API hostname matches the browser's hostname on port 8000. Override with `VITE_API_URL` at build/dev startup for a different deployment. This is a public API location, never a credential. Use the same site and HTTPS in production; configure allowed origins on the backend.

Sign-in sends the entered workspace access key once to `/v1/auth/session`, clears the form, then uses an HttpOnly cookie with `credentials: include`. CSRF tokens live in memory and are restored from the session endpoint after refresh. Neither access keys nor CSRF tokens are written to localStorage/sessionStorage. Session storage contains only a case identifier and selected source mode. Logout revokes the server session.

The browser never receives sponsor tokens. All Zetaris and Nightshift access remains behind the application API. Evidence and tool arguments are rendered as escaped strings; no source HTML executes.

Cases are loaded through `/v1/cases` with the returned cursor. Search is explicitly limited to the loaded page(s), because full-text server search is not implemented. Mode remains immutable on the server. Failures never switch a case to sample mode.

Case creation uses a UUID idempotency key. Investigation and validation start persisted jobs and poll the original job URL with bounded deadlines (210 seconds investigation, 660 seconds validation; server limits are authoritative). Navigation aborts browser polling, not the persisted server job. Refresh retrieves persisted case state and results and resumes monitoring an already queued/running job without starting a duplicate. `401`, `403`, `409`, `422`, `429` and unavailable backend errors have explicit messages. Approval sends the displayed base policy, patch and validation report hashes and is enabled only for a completed passing candidate and reviewer session. The backend remains the authority for stale data, permissions and the validation gate.

## Recorded samples and provenance

`public/samples/*-world.json` are synthetic outputs of the current real backend's deterministic sample runner. They include actual evidence, critique, candidate operations and paired replay receipts. They are labeled recorded everywhere and have no local approval or fake execution action. The report download is explicitly recorded and `applied: false`.

Fresh reports were generated with `scripts/traceverdict_sample.py --include-world` from the repository root using the existing Python environment. All three scenarios produced a broad candidate rejected with 18/20 passed checks and a targeted candidate awaiting review with 20/20 passed checks. The suite is shared across scenarios; these are not three independent robustness measurements. The deterministic summary artifact is not an evaluated language-model summarizer.

Never put real customer payloads, environment files, session cookies or credentials into the public sample directory. Replace sample artifacts only using the backend runner and retain the visible execution-mode explanation.

## Performance and assets

The existing 128 KB evidence illustration is reused with explicit width/height and high fetch priority because it is above the fold. No extra raster backgrounds or decorative video downloads are added. Public case JSON is fetched only after a sample opens. The graph is native SVG, not a large graph runtime. Route-level code splitting separates marketing, workspace and the public landing page. Fonts use `display=swap`, preconnects and readable system fallbacks.

The production build reports the workspace route at approximately 16 KB gzip . Shared React/router code is separate. Further optimization should follow real traffic/LCP measurements: self-host licensed Plex/Spectral font files, cache hashed assets for a year, and serve public JSON compressed. Do not lazy-load the hero image; future below-the-fold photos should use `loading=lazy` and explicit dimensions.

## Accessibility and SEO

The public route is server rendered with product metadata and semantic sections. The workspace is `noindex, nofollow`. Set the production canonical host and absolute social preview URLs once a real domain exists; none is invented here. The product favicon replaces the Lovable default.

Use semantic headings, visible focus, labels on all form controls, keyboard graph actions, list alternatives, native dialog focus containment, status text in addition to color and reduced-motion rules. Horizontal table/graph scrolling is localized. Browser QA should check mobile reading, keyboard review and high zoom after future modifications.

## Commands and deployment

From this directory:

```powershell
npm install --legacy-peer-deps
npm run dev -- --host 127.0.0.1 --port 5173
npx tsc --noEmit
npm test
npm run build
```

The legacy peer resolution flag avoids npm trying to reconcile optional cross-framework toolchain peers in the supplied Lovable package. The generated `package-lock.json` makes the completed install reproducible; use `npm ci --legacy-peer-deps` subsequently. The npm manifest and lockfile are canonical for this application. The old standalone export and its Bun lock are not part of the release workflow.

The existing build emits Cloudflare-compatible server code to `.output/server` and public assets to `.output/public`. Retain the server build for SSR; copying public assets alone does not implement server routes. Production deployment should provide HTTPS, backend reachability, explicit CORS origins, secure session cookies, CDN cache rules and appropriate server logs. Do not embed an API key in a Vite variable. No public deployment was requested or performed for this local project.

## Release boundaries

The frontend can be inspected with no account using recorded cases. Connected workflow correctness requires a running compatible backend and scoped credentials. Actual sponsor uptime, enterprise SSO, commercial billing, production apply/rollback and domain/name clearance are separate product concerns. A successful frontend build does not certify production readiness of those services.


## Repository ownership

This application now lives at `apps/web` in the same Git repository as the backend. Use root `frontend:install`, `frontend:dev`, `frontend:check` and `frontend:build` commands. The retained Lovable build helper is a package dependency, not a separate repository or publishing requirement. See `docs/FRONTEND_REPOSITORY.md` at the repository root for the migration record.


## Customer capture onboarding update

Reviewer-only agent registration and original capture import are now available on Agents. The Overview page can publish live collecting cases to operator-enabled managed sources. See docs/CUSTOM_INTEGRATIONS.md at the repository root. New intake controls passed component/API checks and a real nonfixture Zetaris/Nightshift integration. A new browser walkthrough was unavailable because browser use is disabled in Work settings.
