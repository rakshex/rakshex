# Decision log

| Date | Decision / authority | Reason and consequences |
|---|---|---|
| 2026-10-20 | Latest user: only push to rakshex/rakshex | Akshu1245 source read-only; preserve source provenance and license |
| 2026-10-20 | Supplied master directive resolves Self-Repair as first customer milestone | Budget Lock/LeakShield next; broker remains separate; no scope deletion |
| 2026-10-20 | Preserve FastAPI/SQLAlchemy/PostgreSQL/Next.js (ADR-001) | reuse validated code, avoid wholesale legacy TS branch merge |
| 2026-10-20 | Source baseline import on working branch; LICENSE-only initial main | destination empty; no existing main overwritten; human review before merge |
| 2026-10-20 | Selectively reuse team protection from 55f9cd1 | focused diff inspected; no legacy branch merge; add accepted-membership and missing-role guards |
| 2026-10-20 | First analysis input: consented bounded inline OpenAPI JSON | useful deterministic intake without unsafe code execution, model upload or URL fetch |
| 2026-10-20 | Retain hashes and fixed result metadata only; operator deletion | minimize source/secret storage; no claim of legal zero retention or immutable audit |
| 2026-10-20 | Unique additive Alembic revision after 002 | legacy Drizzle 0003–0005 cannot be transplanted; reconcile future PR schemas explicitly |
| 2026-10-20 | No provider mutation, financial broker, deployment or merge | mandatory safety controls and production evidence are not complete |

No newer founder decision reverses Self-Repair-first. Privacy retention across
infrastructure, production runtime, supported provider coverage, real GitHub App
permissions and commercial cost model still require release/design-partner decisions.
These do not block the local, no-egress intake implementation.

Follow-up on 2026-10-20: replace unsupported legacy landing-page savings/adoption
claims with accurate current capabilities and roadmap statuses. Update the inherited
v4.0 branding browser assertion to the approved RaksHex identity; preserve its
purpose rather than skip or remove the test. No security modules are removed.

## Native credential storage and bounded security scope

Reuse reviewed PR #248/#249 behavior selectively in the active FastAPI runtime, not the
old edge/monorepo runtime. Preserve legacy authenticated reads and require explicit
review before any persistent ciphertext migration. Treat scanners as static heuristics
and CI budget/compatibility as not_run. Make account ownership explicit without claiming
workspace policy coverage. Preserve an honest incomplete product state.
