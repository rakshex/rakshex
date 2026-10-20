# Current-to-target gap analysis

Approved order: secure shared core → Self-Repair first customer workflow → hardening
→ Budget Lock/LeakShield → separately controlled agent execution. No product scope
is removed; this branch is an incremental foundation, not the complete platform.

| Gap | Current → target | Work/dependencies | Risk | Priority | Acceptance |
|---|---|---|---|---|---|
| Membership authorization | role checks outside mutation → one transaction rechecks actor/target | selectively reuse reviewed team fix; PG row lock; accepted membership | stale privilege/owner loss | P0 | co-owner/admin abuse denied; demotion race denied; no mutation on outage |
| Contract intake | global probes → consented workspace analysis | actual-byte bound, validated inline OpenAPI, stable hashes, evidence entity/API/UI | hostile input/tenant data disclosure | P0 | auth required; viewers read only; outsider denied; no raw spec retained; oversized/ref inputs rejected |
| Contract breadth | sampled schemas → semantic versioned contracts | review historical oasdiff adapter; references/SDK adapters; fixture provenance | missed breaking change | P0 | Stripe/Firebase independent before/after fixtures; explicit unsupported states |
| Source impact | standalone compatibility output → authorized call sites | local CLI/TS engine, repo/file scope, consent | source exfiltration | P0 | only approved files inspected; no model upload without consent |
| Repair | generic generator → narrow patch with tests/draft PR | impact evidence, isolated runner, reviewed historical self-repair module, GitHub App | malicious patch/runner escape | P0 | before fails/after passes; rejected failed patch; human merge only |
| Credential protection | custom stream → standard AES-GCM with legacy read | review #248, key lifecycle, migration fixtures | unrecoverable credentials | P0 | old ciphertext preserved; tamper/wrong-key rejected; rotation rehearsal |
| Secret findings | global anonymous history → scoped redacted LeakShield | review #249; authenticated findings/migrations | disclosure | P0 security | no raw seeded credential in API/storage/logs; cross-tenant reads denied |
| Alerts | global change feed → workspace-owned auditable events | review #240 and its migrations independently | IDOR and incompatible migration histories | P0 | scoped list/ack/resolve; audit on change; PG rollback |
| Budget Lock | reporting/counters → atomic reserve/commit/reconcile | PG ledger, stable prices, principal/policy IDs | overspend/duplicates | P1, mandatory before financial mutation | concurrent cap; same idempotency key executes at most once; ledger outage denies |
| Agent broker | design → bounded test-mode capability | credential revocation, exact intent approvals, policy, ledger, freeze | unauthorized provider writes | P1 | denial=no egress; approved revoked credential denied; timeout unknown and reconciled |
| Operations | several configs → verified supported deployment | migration rehearsal, backups/restore, CI, secrets/telemetry review | loss/exposure | P0 release | staging/restore/rollback evidence and founder release authorization |

## First executable milestone
1. Apply only the reviewed team-membership transaction patch, add accepted-membership
checks and regression coverage; preserve all other modules.
2. Ship an honest contract-analysis intake: authenticated workspace operator submits
an explicitly authorized pair of inline OpenAPI 3 JSON documents; backend computes
bounded deterministic operation deltas and persists only hashes and redacted change
metadata. UI loads workspaces/history and shows real results/errors. No repository
content, model calls, test commands, provider requests or PR publication.
3. Record unmet full Self-Repair gates; do not call analysis a repaired integration.

## Dependencies and external services
This milestone needs the existing database and identity only. Provider monitoring,
GitHub App publication, isolated customer-code execution, Stripe mutations, email
and billing require additional separately verified integrations. No fake success
or production mock substitutes are introduced.
