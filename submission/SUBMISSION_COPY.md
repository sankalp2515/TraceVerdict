# Submission copy for review

The portal was inspected on 27 October 2026. It currently has no saved submission. Track, description, video and GitHub repository are required fields. Sponsor explanation has a 4000-character limit; description requires 150–2000 characters. The UI labels the deck optional, while the supplied submission guide and organizer announcement request it, so include the deck.

## Description

TraceVerdict helps teams investigate why an AI agent took an unauthorized action and validate a bounded policy repair before human review. It connects the user's task, untrusted content, historical configuration, attempted tool call and execution receipt in a source-linked evidence graph. An investigator proposes cited explanations and a critic challenges unsupported claims. The system tests exact policy diffs against unsafe and legitimate tasks, rejects repairs that break authorized work, and exports a recommendation bound to the reviewed policy and validation hashes. Our demonstration uses synthetic incidents, real sponsor services and local-only executors. TraceVerdict extends our pre-existing IntentSeal enforcement foundation with the new case investigation, sponsor integration, World Model graph and repair-validation workflow.

## Sponsor explanation

Zetaris is the live evidence-access layer. Three independent PostgreSQL databases hold operational events/receipts, historical configuration and trusted reference records. A native activated USL unifies the evidence using tenant, agent and case membership joins. The backend executes scoped SELECT templates and preserves query receipts and source versions. A native data-quality rule checks payload/kind validity, with additional source and completeness queries retained in the repository.

We implement the Meterless World Model Engine in Python and use it in the product's evidence graph and model context. Canonical provenance-bearing events rebuild stable entities and temporal relationships. The unchanged upstream conformance runner invokes this actual Python implementation through a bridge and passed all eight checks. This is an application implementation of the published specification, not a claimed vendor Python SDK.

Nightshift is the primary runtime for investigator, critic, repair and model-driven replay inference. Requests use the Runtime token and retain actual response IDs, returned model attribution and usage. Explicitly configured NVIDIA Nemotron routes provide inference through Nightshift. The repository's latest report identifies the exact primary and replay routes and generation settings. There is no silent direct-provider or synthetic fallback when live execution fails.

Models propose explanations and repairs. Deterministic validation and a human reviewer control promotion. A disruptive API-origin comparison demonstrates rejection when legitimate work fails. Application receipts are local executor reports, not independent attestations. The agent graph supports evidence review without overstating causal certainty.

Pre-existing components: IntentSeal action guard, intent compiler, policy models, SDK and foundational gateway/runtime. New hackathon work: TraceVerdict case workflow, Zetaris/Nightshift integration, Python World Model and conformance bridge, critic revision, immutable replay captures, repair gate and reviewer export. Baseline and new work are documented in NEW_WORK.md.

## Items requiring final inputs

- Repository completed: https://github.com/sankalp2515/TraceVerdict. Public access verified; backend and apps/web share this repository.
- Real 1–4 minute demo video URL or file.
- Final deck link/upload with frontend visuals where available.
- Cursor is optional per the current official FAQ. This backend used Codex; mention Cursor only if actually used.
- Confirm team roster before creating the first saved submission; the supplied guide says this locks the roster. Helios currently shows one member.
- Track 2 eligibility is confirmed by the team.

No submission has been saved or sent. The organizer announcement says 23:45 UTC on 27 October. One dashboard tile says 23:59 UTC, so use the earlier 23:45 deadline.

The current explicit model allocation is Lightning for investigation/critique/planning and Ultra for replay, through Nightshift. docs/NVIDIA_NEMOTRON_EVIDENCE.md contains the 48-trial comparison and returned model receipts.
