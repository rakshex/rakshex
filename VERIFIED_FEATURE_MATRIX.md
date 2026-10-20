# Verified feature matrix — 2026-10-20

Status describes bounded implemented behavior, not a product-wide guarantee. Consult TEST_RESULTS.md for revision-specific evidence.

| Feature | Status | Evidence / boundary |
|---|---|---|
| Workspace roles and owner safeguards | Implemented and tested | Membership/owner concurrency tests; dedicated PostgreSQL CI exists |
| Inline OpenAPI comparison | Implemented and tested | Consented, bounded upload; operation fingerprints; authorized persisted history and delete |
| Complete Self-Repair | Incomplete | No integrated impact→patch→isolated test→draft PR pipeline |
| Credential storage | Partial, security regression tested | Standard v2 writes and preserved legacy reads; metadata-only ordinary responses |
| Credential lifecycle | Incomplete | No complete rotation, principal binding, live broker revocation or key management service |
| Static security scan | Implemented heuristics | Actual submitted source scanned; redacted findings persisted; not comprehensive vulnerability assurance |
| Scanner history/cache isolation | Account-scoped and tested | Legacy history and cached findings redacted; workspace policies pending |
| CI security check | Implemented static rules | Budget/compatibility explicitly not_run; no repository test execution |
| CI events | Partial | Authenticated signed event persistence and replay conflict; no provider App installation |
| Budget Lock | Incomplete | Key limits are not atomic ledger enforcement/reconciliation |
| LeakShield | Incomplete | Redaction is a prerequisite, not end-to-end provider revocation |
| Premium responsive UX / accessibility | Incomplete | Existing shell/mobile/a11y review and repair required |
| Production deployment | Not approved or performed | Main untouched; draft PR only |

## Repair workflow increment — 2026-10-20 (supersedes earlier pipeline row)

| Capability | Implemented boundary | Verification |
|---|---|---|
| Code impact and patch | Deterministic Python requests JSON-key rename, schema-confirmed, scoped AST locations/diff | New repair-engine tests; refuses dynamic/ambiguous calls |
| Artifact lifecycle | Consented encrypted source/patch bundle, workspace history/read/delete | Real DB/API ownership tests |
| Isolated tests | Separate Docker worker, pinned image, no network/credentials/host fallback, bounded resources/output/time | Dedicated real-container CI job; unavailable locally |
| Acceptance gate | Baseline must fail; candidate must pass; same nonzero test count | Real-container CI plus negative cases |
| Draft-PR publisher | Operator-bound GitHub App; admin exact-evidence approval; immutable snapshot/base checks; idempotent draft branch/PR | Fake-transport protocol tests; live App installation/key not available |
| UI workflow | Source manifest, consent, jobs, exact diff, before/after evidence, guarded publish/delete | Unit tests and new real API browser flow |
| Responsive shell | Mobile drawer, desktop collapse/padding, focus trap/Escape/restore, skip link | Five-viewport and axe browser checks added; verify CI results |

This is a functional supported repair pipeline, not universal SDK repair. JS/TS,
Stripe/Firebase adapters, semantic changes and full-repository test coverage remain
unsupported. A separate worker and GitHub App connection are operator prerequisites,
not evidence that this development environment has been deployed/connected.
