# Current verified feature matrix — 2026-10-20

This describes implemented behavior and its exact coverage. Operator configuration,
live external verification and production readiness are separate gates.

| Capability | Current implementation | Evidence / limits |
|---|---|---|
| Workspace roles/owner safeguards | Implemented | Transactional role rechecks and dedicated PostgreSQL locking tests |
| Inline OpenAPI comparison | Implemented | Consented bounded inputs, operation fingerprints and workspace-scoped persisted history |
| Python request impact analysis | Implemented | Explicit file scope and AST resolution of literal requests POST/PUT/PATCH JSON calls |
| Repair patch generation | Implemented for this adapter | Schema-confirmed single property rename; deterministic diff; dynamic/rebound/semantic cases refused |
| Source/patch evidence lifecycle | Implemented | Encrypted identity-bound job bundles; authorized artifact/history/delete; no model egress |
| Isolated validation | Implemented and exercised in real Docker CI | Non-root, read-only, no network/forwarded secrets, pinned image, CPU/memory/PID/time/output limits; requires separate worker |
| Acceptance gate | Implemented and container-tested | Baseline must fail; candidate passes; same nonzero test count; bad/empty/green-baseline/unrun checks reject |
| Approval gate | Implemented | Current accepted admin/owner approves exact patch/report evidence; worker rechecks membership and contract/patch hashes |
| GitHub App draft publisher | Implemented; live connection required | JWT, narrowed token, scoped source/test/base/tree-mode checks, retry/idempotency and no merge/force push; fake-HTTP protocol tests only until an App installation/key is supplied |
| Repair workbench | Implemented | Consented manifest intake, persisted jobs, migration reference/fingerprints, diff/evidence review, guarded publish/delete; browser CI covers real API behavior |
| Responsive navigation | Implemented | Mobile drawer, Escape/focus containment/return, desktop collapse padding, skip link and labels; 320/375/768/1024/1440 browser checks and automated axe checks added |
| Credential storage | Implemented security increment | Standard AESGCM v2 writes and compatible authenticated legacy reads; metadata-only ordinary responses |
| Credential lifecycle | Incomplete | Managed key IDs/rotation, live provider revocation and broker bindings remain |
| Security scanner | Real static heuristics | Known-field redaction and account-scoped history/cache; not comprehensive vulnerability assurance or full workspace LeakShield |
| Static CI security / signed events | Implemented bounded scope | Compatibility/budget explicitly not_run; no claim of repository test execution through that older endpoint |
| JS/TS/Stripe/Firebase SDK and semantic repairs | Unsupported | Need separately verified adapters/rules/fixtures; Python test success does not establish provider compatibility |
| Budget Lock / controlled broker | Incomplete | Atomic ledger, exposure, idempotency/reconciliation and execution-time controls not yet built |
| Whole-product manual a11y/performance clearance | Incomplete | Automated repair-page checks are not a full screen-reader/Lighthouse/load audit |
| Deployment | Not performed | Draft branch only; main unchanged; no application App key or worker deployment provisioned here |

See TEST_RESULTS.md and the draft PR's immutable CI links for revision-specific results.
See devpulse-backend/SELF_REPAIR_OPERATIONS.md for worker and GitHub App prerequisites.
