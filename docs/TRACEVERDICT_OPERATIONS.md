# TraceVerdict operations

Local endpoints: Zetaris UI localhost:3000, API localhost:8888; Nightshift 127.0.0.1:8088/v1; host backend localhost:8000; frontend localhost:5173; independent source databases loopback 54331–54333. Credentials remain in ignored private environment files.

## Startup

Start Docker Desktop, then the installed Zetaris stack and wait for health. Start Nightshift with its NVIDIA provider configured. From the TraceVerdict directory:

```powershell
docker compose -f compose.data.yml up -d
python -m uvicorn intentseal_gateway.cases.app:app --host 127.0.0.1 --port 8000
# Alternatively, use the container instead of the host API:
docker compose -f compose.data.yml --profile app up -d --build
```

The container uses service DNS for PostgreSQL/Zetaris and host.docker.internal for Nightshift. Set TRACEVERDICT_API_PORT=8001 when running it beside the host API. Use the installed project Python environment. The bootstrap script generates only missing credentials. Provision init/register creates this project's tables, readers and source registrations; native_usl.py activates its USL and quality rule.

## Safe stop and restart

Stop the backend process. In TraceVerdict run `docker compose -f compose.data.yml --profile app stop`; in the Zetaris installation run `docker compose stop`. These preserve named volumes. Do not delete volumes for memory relief. Follow [the detailed Docker/WSL restart guide](LOCAL_ZETARIS_OPERATIONS.md) if the shared VM also needs shutdown; that affects other WSL jobs.

Restart Docker Desktop if necessary, Zetaris, source services, Nightshift and the backend. Wait for health before checking authenticated `/v1/connections`. Restarting preserves tokens unless they expire or are revoked.

## Health and recovery

`/healthz` checks the process; `/readyz` checks storage. Authenticated `/v1/connections` probes model discovery and a real governed Zetaris query. A healthy API alone does not establish sponsor readiness.

Workers claim indexed jobs under a transactional scheduler lock. Replacement workers recover expired leases after process loss. Transient provider errors receive at most one bounded retry; structured formatting gets a bounded recovery attempt. There is no sample fallback. Missing/unknown replay results make validation INCOMPLETE; utility failures reject a candidate. Keep failed reports and create a new case after input/executor changes.

Never log authorization headers, populated environment files, credential-bearing connection DDL or raw vendor error bodies.

## Backup verification

```powershell
python scripts/zetaris/backup_restore_check.py
```

The script dumps each source, restores into a uniquely named disposable database, checks evidence counts and removes only that disposable database. Private dumps stay under ignored artifacts/traceverdict/backups. The events database also contains cases, jobs, sessions and replay snapshots. Quiesce writers when comparing counts or restoring operational data. Each dump is transactionally consistent; the three dumps are not a distributed snapshot.

Encrypt and protect off-machine backups and apply retention. Zetaris platform metadata/configuration and Nightshift settings need their own supported backups; this source script does not cover those. Whole-platform disaster recovery and deployment RPO/RTO remain unverified.

## Production deployment

Use HTTPS, TRACEVERDICT_COOKIE_SECURE=true, explicit allowed origins, private source/platform ports, restricted service roles, credential rotation, monitored queue age/error rates/provider latency and retention. Capacity limits are two global running workers and 32 active jobs, not a measured performance guarantee. Preserve local-only executors unless a separately isolated restricted executor is implemented.

Reviewer approval binds the base policy, patch and validation report hashes. It exports the recommendation and rollback policy hash; it never edits the active policy. A production integration needs its own controlled deployment and rollback.
