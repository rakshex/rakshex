# Practical implementation architecture / ADR-001

Decision date: 2026-10-20. Preserve Next.js/React and FastAPI/SQLAlchemy/PostgreSQL.
Use a modular monolith and isolated job runners; no new microservices or framework
replacement. Historical TS repair engine can be invoked through a constrained
worker interface after audit, rather than transplanted into authenticated API code.

- Control plane: Next.js forms/history backed by authenticated FastAPI endpoints.
- Identity: database-backed user; accepted workspace membership for every repair
  list/create/get/delete; owner/admin/member write, viewer read. Existing JWT is
  reused but requires broader hardening before release.
- Persistence: PostgreSQL source of truth, workspace FK and indexes, versioned
  additive Alembic migration. SQLite is local/test only. New analysis entity is
  immutable except explicit operator deletion; not a cryptographically immutable
  audit ledger. Analysis evidence records actor, UTC time, input hashes and ruleset.
- Self-Repair: intake → canonical contract/SDK analysis → authorized local impact
  scan → bounded candidate patch → isolated validation → evidence → scoped GitHub
  draft PR. Only intake/operation analysis is activated in this milestone.
- Runner boundary: no subprocess from uploaded spec, no fetching spec $ref or URL,
  no executing repo commands in the API container. Future ephemeral runner has
  no provider financial credentials and no broad network access.
- Provider adapters: least-privilege connections, encrypted secrets, active/revoked
  versions; a separate broker alone may execute allowed external actions. Never
  share source-analysis permissions with financial mutation permissions.
- Policy/money: PostgreSQL atomic budget reservations/counts and idempotency,
  one-use intent-bound approvals, live policy/revocation/freeze checks at egress;
  unknown provider results reconcile. Redis is cache only.
- LeakShield: authorized sources, workspace-specific findings, pre-storage redaction,
  hashed deduplication, explicit operator rotation; no automatic provider revocation.
- Observability: structured event IDs/status/timings only; no raw specs/source/
  credentials or validation input echoes. Sentry/alerts need separate verification.
- Deployment: retain configurations as historical options. No deployment in this
  branch. Before launch: select runtime, run PG migrations/restore twice, verify
  CI, key management, telemetry, tenant tests, costs and rollback with owner review.

## Intake privacy and limitations
Input processing on the server requires an explicit consent flag; UI explains it.
No source repository is cloned by intake. Spec bodies exist only during the request;
retained hashes/operation references exclude descriptions/examples/raw paths. These
hashes are pseudonymous metadata, not proof that inputs cannot be guessed. Operators
can delete analysis evidence. Backups follow future documented retention controls;
do not claim legal zero retention across infrastructure.
Only inline OpenAPI 3.0/3.1 paths/operations are supported initially. References,
callbacks and webhooks are rejected rather than fetched/treated as validated.
Any changed operation requires human review; no semantic completeness claim,
impact result, patch validation, provider monitoring or draft PR success is implied.

## Migration / rollback
New revision follows 002_onboarding_progress with a unique date-based revision ID;
it does not import old Drizzle migrations 0003–0005 or unmerged PR schema changes.
Reconcile Alembic branches before future integrations. Upgrade adds one table;
downgrade drops only that table (export retained evidence first). Production
execution requires separate approval and backup. Code rollback leaves table
unused; existing workflows and security features remain intact.
