# TraceVerdict web application

This is the canonical product frontend in the TraceVerdict repository. It contains the landing page, no-sign-in guided sample and authenticated investigation workspace. The separate Lovable export is an archived design reference, not a release or submission source.

Run from the **repository root** with Node.js 22.14 or later:

```powershell
npm run frontend:install
npm run frontend:dev
```

Open http://127.0.0.1:5173. Start the guided demo without credentials, or connect to the case API on the same hostname at port 8000. Use a scoped workspace key only in the sign-in form. Never put application or sponsor credentials in Vite variables.

To use another API location, copy `.env.example` to `.env.local` in this directory and set the public `VITE_API_URL`. Real credentials remain in the backend's ignored `.env`.

```powershell
npm run frontend:check
npm run frontend:build
```

The check runs TypeScript, lint for the implemented product surfaces, and the nine frontend tests. The existing Lovable UI primitive library is retained without a broad formatting rewrite. The production build retains TanStack Start server rendering and the supplied Cloudflare/Nitro target. See [architecture and deployment](docs/FRONTEND_ARCHITECTURE.md) for runtime requirements; `.output/public` alone is not a standalone deployment of the server-rendered routes.

`apps/console` remains the pre-existing IntentSeal console. It is separate from this product surface but belongs to the same Git repository. Neither frontend requires a separate repository or Git submodule.

- [Design and UX rationale](docs/DESIGN.md)
- [Architecture and session contract](docs/FRONTEND_ARCHITECTURE.md)
- [Browser verification and screenshots](docs/VERIFICATION.md)
- [Single-repository integration](../../docs/FRONTEND_REPOSITORY.md)

Public sample artifacts are labeled synthetic recordings from deterministic sandbox execution. New investigations, live reasoning, validation jobs and reviewer approval use the application backend. Approval exports a recommendation and never applies a production policy.
