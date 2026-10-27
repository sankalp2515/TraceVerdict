# Zetaris evidence layer

Three independent PostgreSQL sources feed an activated native USL and native data-quality rule. Operational events/receipts, historical configuration and trusted references stay in separate databases. Zetaris reads each through a SELECT-only `tv_reader` account.

The USL joins case membership across all three sources using tenant, agent and case IDs. The application queries `traceverdict.case_evidence` through a fixed scoped SELECT template. Models cannot submit SQL. Query receipts preserve request IDs and query/response hashes.

## First installation

Configure private owner/reader credentials and Zetaris REST credentials in the ignored project `.env`. Start the installed Zetaris platform and `compose.data.yml` sources, then use the configured Python environment:

```powershell
python scripts/zetaris/provision.py init
python scripts/zetaris/provision.py register
# Start the case API, create and seed the first synthetic live case:
python scripts/traceverdict_live.py --run-key first-live-run --comparison-control
python scripts/zetaris/native_usl.py
python scripts/zetaris/provision.py verify
```

Initial registration creates a governed three-source view so the first case can be seeded. Native activation then replaces the application view with the activated USL path. Run a new case key to verify that full path. Repeated registration preserves an activated USL. See [setup](../../docs/GETTING_STARTED.md) and [custom capture import](../../docs/CUSTOM_INTEGRATIONS.md).

## Restart an existing installation

Use `scripts/start-local.ps1` from the repository root. It retains data volumes, loads the existing USL, warms a real governed query and checks authenticated dependency status. No data is reseeded or replaced. Cold Spark queries can take longer than the container health checks. Nightshift must also be running with its provider configuration.

## Retained acceptance evidence

- [Native USL DDL and receipts](../../examples/traceverdict/zetaris/native-usl.json)
- [USL SQL](../../examples/traceverdict/zetaris/native-usl.sql)
- [Source queries and completeness checks](../../examples/traceverdict/zetaris/verification.json)
- [Reader permission verification](../../examples/traceverdict/zetaris/reader-permissions.json)
- [Nonfixture captured case through the live path](../../examples/traceverdict/live/imported-capture/report.json)

The retained native DQ run returned 63 valid records and zero invalid; this is that run's count, not the current total. `provision.py verify` runs three exploratory queries per source, semantic summaries and a seven-kind case-completeness check. Native DQ validates nonempty payload and evidence kind. These rules do not establish producer authenticity or prove causal truth. Captures are operator-attested and published incidents are synthetic; sponsor execution is real.

REST uses POST `/api/v1.0/sql-editor/sqls/run`, Bearer authentication, numeric `X-Org-ID`, a fresh request ID and `source=SqlEditor`. Credentials and credential-bearing DDL must never be printed or committed. Enterprise Zetaris role provisioning and whole-platform backup/recovery remain deployment responsibilities. Source restore verification is available in `backup_restore_check.py`.
