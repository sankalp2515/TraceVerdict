# Single-repository frontend integration

The canonical product frontend is `apps/web` in this repository. Backend, SDK, fixtures, product UI, frontend tests, build configuration and submission material share the same Git history and submission URL. The previous standalone Lovable directory is not required to install, build, run or submit TraceVerdict.

## Repository boundaries

| Path | Ownership and purpose |
|---|---|
| `apps/web` | Current TraceVerdict landing page, guided judge sample and investigation workspace |
| `apps/console` | Pre-existing IntentSeal operational console, retained as declared foundation |
| `services/gateway/intentseal_gateway/cases` | Case/session/evidence/jobs/validation/review API |
| `packages` and `agents` | Existing runtime, SDK and agent foundation |
| `examples/traceverdict` | Checked-in backend example and live-run evidence |
| `apps/web/public/samples` | Synthetic recorded case aggregates used by the no-account UI |
| `submission` | Demo script and submission copy for this one repository |

`apps/web` is an ordinary tracked directory, not a nested repository, a submodule or a symlink. It has a pinned npm lockfile. Root npm commands delegate to its manifest so the Python and frontend toolchains can remain independent inside one repository. No root npm dependency installation is necessary.

## Clean-clone startup

Prerequisite: Node.js 22.14 or later. From the repository root:

```powershell
npm run frontend:install
npm run frontend:dev
```

The landing page runs at http://127.0.0.1:5173. Its guided sample works with no backend credential. The backend setup and launch instructions remain in the root README. For connected work, run the case API on port 8000 and use the same hostname in both URLs. The default CORS configuration includes the local frontend origins. Local HTTP needs `TRACEVERDICT_COOKIE_SECURE=false`; production needs HTTPS and secure cookies.

Enter a scoped project or reviewer credential through the workspace form. Vite configuration contains only the public API URL. Browser cookies are HttpOnly and mutating requests carry the session's CSRF token. Sponsor credentials never enter the frontend.

## Checks and release

```powershell
npm run frontend:check
npm run frontend:build
```

The root entry points execute the frontend's TypeScript check, scoped product lint, nine tests and production SSR build. `.github/workflows/frontend.yml` installs from the checked-in lockfile, runs these checks and retains the build as a CI artifact. The Python CI remains intact. The supplied TanStack/Lovable build helper is an ordinary package dependency and does not require a separate Lovable repository, account or synchronization step.

The build emits `.output` under `apps/web`. It retains the existing Cloudflare/Nitro server target. Deploy its server and public assets together; do not treat it as a static-only site. Production hosting and actual live sponsor readiness are separate from repository consolidation.

## Migration and preservation

Copied the complete application source, tests, assets, build/tool configuration, npm lockfile, design/architecture/verification notes and screenshot evidence. Excluded installed dependencies, build output, Vite/Wrangler caches, browser profiles, editor project identity, local databases and credential-bearing QA runners. Existing backend edits and the legacy console were preserved. No external Git remote or Git history was copied into `apps/web`.

The original Lovable directory remains on disk as a reference, but active development and the local product preview now use `apps/web`. Future changes and the submission should be pushed from this repository only. Design artifacts remain in developer documentation; the old user-facing design-system URL redirects to the guided sample.


## Executed consolidation verification

- Installed 504 packages into `apps/web/node_modules` using `npm ci --legacy-peer-deps` and the copied lockfile; no dependency on the old export's installed modules.
- SHA-256 comparison: all 90 source/public-asset files match the completed frontend.
- Root `npm run frontend:check`: TypeScript and product lint passed; nine tests passed.
- Root `npm run frontend:build`: client, SSR and Cloudflare/Nitro build passed.
- Stopped the old export's preview. The active Vite process resolves from this repository's `apps/web/node_modules` and serves port 5173.
- Browser checks from this checkout: landing → five guided steps, recorded approval disabled, old design-system URL redirect, no login requirement, no mobile page overflow, and no page runtime errors. Evidence: `apps/web/output/playwright/consolidated-workspace.png` and `consolidated-mobile.png`.
- Repository secret scan and `git diff --check` passed. Local environment files, dependencies, build output and browser state are ignored; `.env.example` remains included. No nested `.git` directory exists.

The CI workflow was added but has not been run on GitHub; no remote push or production deployment is claimed by these local checks.
