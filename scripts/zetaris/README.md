# Zetaris connection acceptance

## Current verified implementation

The earlier pending checklist below is historical. Three independent PostgreSQL sources now feed an activated native USL and native quality rule. Run `provision.py init`, `provision.py register`, seed a case using `scripts/traceverdict_live.py`, then run `native_usl.py` and `provision.py verify`. Repeated registration preserves an activated USL view. Native DQ fails on empty data or invalid rows. Verification performs three exploratory queries per source and semantic summary, kind counts and completeness checks.

Actual [native DDL/receipts](../../examples/traceverdict/zetaris/native-usl.json), [SQL](../../examples/traceverdict/zetaris/native-usl.sql), and [source/semantic checks](../../examples/traceverdict/zetaris/verification.json) are retained. The latest native rule returned 63 valid of 63 records and zero invalid. The real live case includes scoped query receipts and returned NVIDIA model evidence through Nightshift.

The unified layer presents one scoped evidence contract while keeping operational actions/receipts distinct from historical configuration and trusted recipient reference data. Membership joins and SELECT scope predicates require tenant, agent and case agreement. Native DQ checks payload presence and kind; the completeness query checks all seven fixture kinds. These checks do not authenticate compromised producers or establish source truth. Sources are synthetic; connectivity and sponsor execution are real. Separate enterprise Zetaris role provisioning remains deployment work.

The backend uses one approved SELECT template against `ZETARIS_CASE_VIEW`, default `traceverdict.case_evidence`. The official REST contract was checked against Zetaris's getting-started `scripts/zetaris_sql.py`: POST `/sql-editor/sqls/run`, bearer credential, X-Org-ID, fresh X-Request-ID, and a body containing queryId, sql, source=SqlEditor and limit. Column-array results under `data` and a named `rows` wrapper are supported. The installed platform still needs a real connectivity and shape check.

## Source preparation

Create a synthetic case in live mode through the API, then use the admin-only `/v1/cases/{id}/source-records` endpoint with `export_case_sources.py`. It generates three JSON groups: operational events/receipts, historical fixture policy/tool configuration, and the trusted reference directory. Exports contain synthetic fixture data; their local execution receipts describe a sandbox, not a production agent.

Register each group in storage reachable from Zetaris. Local Windows paths alone are not readable by the platform. Keep configuration and reference sources under administrator control. Register them using the installed platform's supported connectors and verify their schemas before creating a semantic view. A live investigation must query the actual Zetaris view; returning a local copy from this adapter is deliberately unsupported.

Each registered group needs `tenant_id`, `agent_id`, `case_id`, `evidence_kind`, and `evidence_json`. The governed view must join case membership in operational data to the corresponding historical configuration and trusted reference record on all three scope fields. Preserve each group's evidence_json when projecting the unified evidence rows. A valid view supplies all seven fixture records; configuration and reference evidence must be independently traceable.

The exact registration and USL DDL is intentionally not guessed before the installed connector/version can be inspected. Once access is available, save the proven DDL, query outputs and data-quality rule execution here. Treat three groups/tables as three independent data sources only if their actual registrations and provenance support that statement.

## Live acceptance checklist

- [x] Verify authenticated SELECT 1 against the installed API with the user's token (27 October 2026).
- [ ] Complete application source discovery and registration. An inspection of `traceverdict` returned no tables during assessment.
- [ ] Register and inspect all three source groups, retaining locations and versions.
- [ ] Execute two or three exploratory queries per source.
- [ ] Create and retain a unified semantic layer and its DDL in Zetaris.
- [ ] Execute the governed case join and confirm all scope predicates.
- [ ] Execute at least one data-quality rule and two or three semantic-layer queries.
- [ ] Run a live case report and retain the adapter query receipts and concrete model evidence.
- [ ] Write a short reflection on the semantic layer's benefits and limitations, based on observed work.

The source registration, semantic layer, quality and full case checks remain pending; mocked HTTP tests do not satisfy them. Basic connectivity passed using numeric organization ID `1` for this installation. Keep credentials private; the backend mapping is in its ignored `.env`.
