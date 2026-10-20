# Current codebase audit — 20 October 2026

## Scope and evidence
Source: Akshu1245/Rakshex-complete-codebase main, commit
`b8590fb0b408b10cbd06eb66be1caf30a39e8300`. Destination:
`rakshex/rakshex`, initially empty; working branch
`codex/rakshex-foundation-20261020`. Source push URL disabled locally.
All 242 source files were recovered and verified against Git blob hashes.
This is a repository-level inventory and focused security review, not a complete
penetration test or evidence of production readiness. No deployment, production
migration, provider write, branch merge, or change to the source repository.

## As-is architecture
Next.js App Router/React/TypeScript control plane in `devpulse-dashboard-ui`;
FastAPI in `devpulse-backend/main.py`, 23 route modules and 112 route decorators.
28 SQLAlchemy mapped model classes in `models/tables.py`, and 21 frontend pages; PostgreSQL is required by production
configuration; SQLite supports local tests. Alembic mainline ends at
`002_onboarding_progress`. Redis cache/in-memory fallback is not a money ledger.
JWT auth resolves a database user; teams expose owner/admin/member/viewer.
Middleware supplies body-length-header checks, rate limits, security headers.
Sentry, PostHog, Stripe and SendGrid are dependencies, not proof of deployed services.
Docker Compose, Vercel and Cloudflare configurations coexist; active deployment
and credentials are unknown. CI has backend, frontend, Cypress and stack jobs.
Root Node engines require 20 while Cloudflare CI uses 24: reconcile before release.

## Baseline
Python 3.12: `python -m pytest tests/ -q --tb=short`: **157 passed**, 3 warnings,
131.28s. Requirements use ranges, not a reproducible lock. Frontend clean install
completed under Node 24.19.0/npm 11.9.0 with Node-engine warnings; Jest/typecheck
results are recorded in IMPLEMENTATION_LOG after execution. No live integration
success is inferred from unit tests. SQLite tests do not prove PostgreSQL locking.

## Feature inventory
| Feature | Existing code | Working status | Current requirement | Required changes | Priority |
|---|---|---|---|---|---|
| Auth | routes/auth.py | Partially functional; baseline tests | trusted identity | session/token hardening and failure tests | P0 |
| Workspace roles | routes/teams.py, services/team_manager.py, database.py | Broken: co-owner demotion/admin peer management; stale auth | tenant-scoped safe membership | locked transaction, accepted actor, primary/last-owner protection | P0 |
| Change detection | services/change_detector.py, routes/changes.py | Present but untested externally | authorized contract change intake | workspace ownership, provenance, consent | P0 |
| Self-Repair | compatibility/code generation are different workflows | Missing from main | change → impact → patch → isolated validation → draft PR | integrate reviewed engine incrementally | P0 |
| Repair analysis evidence | no scoped entity | Missing | durable, bounded analysis | auth, scoped persistence, deterministic diff, UI | P0 |
| Secret storage | services/encryption.py, routes/budget.py | Broken security claim: custom HMAC stream is not AES-GCM | standard authenticated encryption, legacy read | review draft #248, migration/rotation rehearsal | P0 |
| Scanning | routes/security.py, security_scanner.py | Partially functional; public history and evidence exposure risk | LeakShield with scoped/redacted findings | review #249; auth, tenancy, retention | P0 security/P1 product |
| Budgets/kill switch | budget.py, cost_intelligence.py, database.py | Partially functional; no safe broker proof | atomic hard denial before provider write | durable reservations, counts, freeze, reconciliation | P0 before mutation |
| Gateway/agent/approval broker | no demonstrated chain in main | Missing | scoped identity, exact authorization, live revocation | separate deny-first subsystem | P1; mandatory controls before launch |
| Dashboard | existing pages, api.ts, transport.ts | Partially functional | real state/loading/errors | prioritize repair; remove unsupported claims incrementally | P0/P1 |
| Billing/email/analytics | Stripe, SendGrid, PostHog paths | Present but untested externally | explicit configured integration states | verify webhook, consent, deliveries | P1/P2 |
| Migrations | 001_initial, 002_onboarding_progress | Present but untested on PostgreSQL | safe evolution and rollback | compare branch schemas before integration | P0 |
| Deployments/backups | Compose, Vercel, Cloudflare configs | Unknown live state | repeatable staging, restore/rollback | operational drill and review | P0 before launch |
| Marketplace/mock/docs/codegen | historical modules | Obsolete for first-release priority; retained | avoid broad MVP | keep isolated; do not remove controls | P2 |

## Branch/PR evidence
GitHub branch inventory spans 128 branches (two pages). Reviewed relevant file trees:
- archive/rakshex-pre-devpulse-20261013 (`9ca85cf`): old TypeScript monorepo,
  CLI/oasdiff, Cloudflare and Drizzle schemas. Not the Python mainline.
- feat/yc13-cli-api-diff-20261012 (`1776ae1`), feat/yc13-oasdiff-engine-20261012
  (`8e548de`), feat/yc13-static-callsite-impact-20261013 (`c197a89`), and
  feature/yc13-contract-diff-mvp-20261012 (`ea896ef`): experimental TS code;
  trees inspected, implementation not certified or copied wholesale.
- Their Drizzle migrations 0003–0005 concern the old monorepo. They cannot be
  applied as Python Alembic migrations. Schema reconciliation remains pending.
- integration/self-repair-engine (`083501a`): contains `engine/` with contract
  diff, impact/patch pipeline and benchmark fixtures. Selective integration is
  preferable to rebuilding it; security and benchmark execution remain pending.
- fix/teams-owner-protection (`55f9cd1`): focused routes/service/transaction/tests;
  reviewed as reusable secure-core work. SQLite process locks alone do not
  establish multiprocess guarantees; production uses PostgreSQL row locks.
- #237 and #238: verified merged. #239: open, not draft, not merged.
- #240: open draft, **workspace change-alert ownership/role-gated resolution/audit**.
  This differs from the handover description; do not assume broader fixes landed.
- #241: open draft; Vercel/Node engine issue. #248: open draft; standard AES-GCM
  with legacy preservation. #249: open draft; server-side evidence redaction.
- Private sandbox was not ingested; Stripe/Firebase reported results are not
  reproduced here. None of these branches/PRs were merged by this work.

## Important findings and reuse
Retain FastAPI, SQLAlchemy, PostgreSQL, Next.js, auth, workspace models and existing
tests. Team deletion already filters role=owner; the exploitable gap is demotion of
co-owners, admin peer control and authorization outside the write transaction.
Legacy scanner APIs persist anonymous findings and expose shared history; release
blocked until tenancy/redaction is fixed. Existing custom encryption must not be
advertised as AES-GCM. Money-related counters are not an execution-time ledger.
SecurityHeadersMiddleware checks Content-Length, not actual streamed length;
new upload endpoints must enforce their own actual-byte bound.
