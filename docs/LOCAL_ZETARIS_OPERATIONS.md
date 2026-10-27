# Zetaris: safe stop, memory release and restart on this PC

Installation: `E:\zetaris-platform\zetaris-platform`. Docker Desktop uses WSL 2. These are instructions for the user; the assessment did not stop or restart the services or modify WSL settings.

## Stop Zetaris while keeping data

Wait for active investigations/queries to finish, then run in PowerShell:

```powershell
Set-Location -LiteralPath 'E:\zetaris-platform\zetaris-platform'
docker compose stop -t 60
```

This preserves the containers, images, named volumes, databases, installed sample data and `.env`. The credentials remain in the existing persistent installation; no download or registry login is normally needed to restart cached images.

Live TraceVerdict investigations need Zetaris running. Frontend work using the labeled sample API can continue while Zetaris is stopped.

## Release the Docker/WSL memory as well

Stopping containers alone may leave Linux filesystem cache in the WSL VM. Docker documents this build-cache memory behavior and recommends WSL memory reclamation: [Docker Desktop WSL guidance](https://docs.docker.com/desktop/features/wsl/).

After stopping Zetaris, save work in all other Docker containers and WSL distributions, including Kali, then run:

```powershell
docker desktop stop --timeout 120
wsl --shutdown
```

The first command stops all of Docker Desktop, not just Zetaris. The second terminates all running WSL distributions and the shared WSL 2 VM. It is a full WSL shutdown, so close active WSL jobs first. Microsoft documents WSL settings and the shutdown requirement in [WSL configuration](https://learn.microsoft.com/en-us/windows/wsl/wsl-config).

## Restart

```powershell
docker desktop start --timeout 120
docker info
Set-Location -LiteralPath 'E:\zetaris-platform\zetaris-platform'
docker compose up -d --pull never
docker compose ps --all
```

If `docker info` reports the engine is still starting, wait until Docker Desktop is ready and run it again before starting the stack. The `--pull never` flag uses the images already installed. It is for restarting this existing installation, not setting up a new machine or upgrading images.

Allow the driver/API several minutes on a cold start. Long-running `postgres`, `driver`, `api` and `ui` should become healthy. The `init` and `bootstrap` jobs should exit with code 0; that is normal. Bootstrap has a persistent marker and should skip already registered sample datasets.

Run the official read-only verifier:

```powershell
& 'C:\Program Files\Git\bin\bash.exe' -lc 'cd /e/zetaris-platform/zetaris-platform && bash ./verify.sh'
```

Then open [Zetaris](http://localhost:3000). Use the same administrator account/password and existing API token. If the token has expired or was revoked, replace it through the platform's normal credential workflow; a restart does not renew an expired token.

## Optional ongoing memory reclamation

This PC reports WSL 2.5.10. Microsoft documents `autoMemoryReclaim` values `disabled`, `gradual` and `dropCache` under `[experimental]`. Current documentation lists `dropCache` as the default; do not assume retained memory necessarily means the feature is disabled.

To explicitly use gradual reclamation, merge the following into `C:\Users\sanka\.wslconfig`, preserving any existing settings:

```ini
[experimental]
autoMemoryReclaim=gradual
```

Apply it with the safe shutdown/restart sequence above. This helps reclaim unused cache; it cannot reclaim RAM actively used by a running Spark/JVM service. A global WSL memory cap is also supported, but must be sized for Zetaris plus other WSL workloads and checked with the platform preflight. Do not lower memory blindly while diagnosing startup problems.

During this assessment, container statistics were approximately 1.36 GiB driver, 617 MiB API, 158 MiB UI and 87 MiB PostgreSQL. A separate later process sample showed about 7.69 GiB for `vmmemWSL`, down from the higher build-stage sample. These are point-in-time readings, not a memory-leak diagnosis or a capacity benchmark.

## Preserve the installation

Do not use `docker compose down -v`, Docker volume prune, or Docker Desktop factory reset for routine memory relief. Removing the named volumes destroys persistent platform data and can invalidate the relationship between the database and saved configuration. A normal stop/restart is enough for this task.
