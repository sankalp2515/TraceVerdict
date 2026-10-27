# Experience TraceVerdict in under four minutes

The guided route targets 3½ minutes. This is a suggested reading pace, not a measured usability result. It uses recorded synthetic evidence and computed sandbox results; it never pretends to run live inference.

## No account or credentials

With Docker installed, run from a clean repository checkout:

```powershell
docker compose up -d --build --wait
```

Open http://localhost:5174/workspace?mode=recorded&case=supplier-contact directly. This separate demo container needs no `.env`, account, application key, database, Zetaris or Nightshift. Use `TRACEVERDICT_DEMO_PORT` to select another free loopback port. Stop with `docker compose -f compose.demo.yml stop`.

If the full local stack is already running, use http://localhost:5173/workspace?mode=recorded&case=supplier-contact instead. This explicit recorded link also bypasses a previously selected connected-workspace mode.

| Suggested time | Experience | Evidence to inspect |
| --- | --- | --- |
| 0:00–0:40 | Incident | Original task, untrusted document and actual sandbox receipt |
| 0:40–1:20 | Evidence | Select a graph node and inspect its source |
| 1:20–2:00 | Explanation | Cited finding and the critic's causal uncertainty |
| 2:00–3:00 | Repairs | Rejected restriction versus the targeted repair; inspect failed legitimate tasks |
| 3:00–3:30 | Review and export | Exact artifact hashes and downloadable report |

Approval is deliberately disabled in the recorded example. A reviewer uses the live workspace to approve a real recommendation; neither path deploys production policy automatically.

## Bring an original agent incident

Any agent framework can produce the supported JSON capture contract. This is an evidence adapter, not a universal autonomous tool executor. Start with [the capture example](../examples/traceverdict/capture/incident.json); replace it with the original task, document, historical policy, attempted action and matching execution receipt.

Validate its schema without a key or network:

```powershell
python scripts/traceverdict_import.py my-incident.json --check
```

Then use the configured live product and a private reviewer key:

```powershell
python scripts/traceverdict_import.py my-incident.json --register-policy my-current-policy.json --publish --investigate
```

Omit `--register-policy` for an already registered agent. Keys stay in the private environment. `--publish` uses only the operator-configured source stores. Investigation reads those records back through Zetaris. Follow [the complete capture contract](CUSTOM_INTEGRATIONS.md).

Live intake requires operator-provisioned workspace access and sponsor services. Deployment removes installation friction but does not replace capture mapping, scoped authorization or supported replay adapters. Arbitrary customer tools, payments and external message delivery are not enabled by the current local replay executors.
