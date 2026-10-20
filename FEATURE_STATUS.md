# Approved feature status

Legend: Verified = named local behavior demonstrated by tests, never a deployment
claim. Partial = some code/tests but module not complete. Pending = target not
implemented here. Unknown = needs external/operational evidence.

| Module / capability | Status | Evidence / missing gate | Priority |
|---|---|---|---|
| User JWT/password authentication | Partial | existing backend baseline; session/key/privacy hardening remains | P0 |
| Workspaces and owner/admin/member/viewer | Partial | mutation protections verified locally; dedicated PostgreSQL row-lock CI passed | P0 |
| Tenant isolation across all legacy modules | Pending | new analysis APIs scoped; global scanner/change paths remain | P0 |
| Credential encryption/storage/rotation/revocation | Partial, release blocker | inherited custom cipher; review #248 + lifecycle | P0 |
| Audit foundation | Partial | analysis actor/time/hashes; no central append-only ledger | P0 |
| CI/database/deployment foundation | Partial | local builds/tests/SQLite round trip; CI/PG/deploy not verified | P0 |
| Self-Repair authorized contract intake | Verified locally | consent/limits/roles/privacy/outage/readback tests; real Self-Repair browser flow passed in CI | P0 |
| Self-Repair change detection/provenance | Partial | manual pair hashes + ruleset; no upstream monitoring integration | P0 |
| Full semantic contract/SDK analysis | Pending | bounded inline operation fingerprints only; refs rejected | P0 |
| Source scope and impacted-callsite mapping | Pending | historical TS engine/fixtures to audit and reproduce | P0 |
| Minimal patch generation | Pending | no fake patch or generic codegen substitution | P0 |
| Isolated test/security validation | Pending | no customer-code runner activated | P0 |
| Evidence-backed GitHub draft PR workflow | Pending | no installed app adapter; no merge automation | P0 |
| Repair dashboard/history/errors | Partial | analysis workflow/UI and real browser flow verified; end-to-end repair pipeline absent | P0 |
| Budget Lock workspace/user/agent/provider ceilings | Pending | legacy budgets retained; authoritative policy redesign needed | P1/P0 before money |
| Atomic cumulative exposure, counts and reservations | Pending | PostgreSQL ledger needed | P0 before money |
| Financial idempotency and unknown-outcome reconciliation | Pending | no real broker enabled | P0 before money |
| Emergency freeze at egress | Pending | legacy kill switch is not proof of broker enforcement | P0 before money |
| LeakShield authorized scanning/detection | Partial | legacy scanner; tenant scope/redaction first | P1/P0 security |
| Finding severity/dedup/alerts/history | Partial | existing modules, not safe tenant-scoped proof | P1 |
| Safe redaction/evidence/retention/rotation guidance | Pending | review #249; intake avoids retaining raw specs | P0/P1 |
| Automatic provider revocation | Pending, not enabled | only after narrowly authorized verified adapter | Later |
| Agent registration/scoped identity/action authorization | Pending | separate subsystem | P1 |
| Intent-bound one-use approvals and revocation checks | Pending | must not bypass live policy/funds/freeze | P0 before execution |
| Restricted provider execution broker | Pending | Stripe test-mode pilot only after controls | P1 |
| Tamper-evident execution evidence/receipts | Pending | analysis hash is not immutable execution audit | P1 |
| Dashboard/Gateway real provider state and analytics | Partial | legacy pages retained; no fabricated new metrics | P0/P1 |
| Team administration, onboarding and provider connections | Partial | workspace create available; full admin UX/connectors incomplete | P0/P1 |
| Billing/reporting/observability/alerts | Unknown externally | dependencies/routes do not prove active integrations | P1/P2 |
| SDK/MCP/CLI/Postman import/provider failover | Pending | consented destinations, secrets handling and policy required | P1/P2 |
| Enterprise IAM/SSO/regional controls/scale | Pending | approved extensions after demand and reliable core | P2 |
| Marketplace/mock/codegen/forecasts | Retained legacy; deferred | outside first launch wedge; no security features removed | P2 |

No completion percentage is asserted. Full Self-Repair, Budget Lock, LeakShield,
controlled execution and commercial production readiness remain incomplete.
