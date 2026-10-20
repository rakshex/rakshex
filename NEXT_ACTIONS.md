# Next actions in dependency order

1. Review this branch/import. Run GitHub CI, isolated PostgreSQL row-lock test and
   actual Cypress browser flow. The dedicated PG job and Self-Repair browser flow
   already passed remotely; verify the follow-up branding/landing rerun. Do not merge/deploy automatically.
2. Review #248 and #249 independently; preserve ciphertext compatibility, add
   standard authenticated encryption, redact before persistence/disclosure, scope
   security findings to accepted workspace members. Resolve critical legacy issues.
3. Audit PR #240 schema changes and migrations; integrate only after reconciling
   Alembic heads with 20261020_repair_analysis; add PG up/down/re-up tests.
4. Inspect `integration/self-repair-engine@083501a` and four yc13 branches at file
   and test level. Reproduce oasdiff/CLI/static-impact benchmark cases in an isolated
   environment. Do not import the old monorepo wholesale or assume sandbox success.
5. Extend contract intake with supported parser/schema/SDK adapters and provenance;
   unsupported coverage must stay explicit. Add Stripe and Firebase failing fixtures.
6. Introduce consented repository/file scope, local impact scanner and minimization;
   no private source access/model upload without explicit informed consent.
7. Add narrow patch artifacts, isolated bounded no-secret test runner, before/after
   evidence and failed-patch rejection; never execute untrusted code in API process.
8. Implement least-privilege GitHub App draft-PR publisher; review permissions,
   signed webhooks, replay, retries and scope. Human merge always required.
9. Complete repair UI and real browser/device/error workflows. Reconcile Node
   runtime, dependency locking, sessions, proxy trust, rate limits and logging.
10. Build Budget Lock atomic PG ledger, principal/action policies, frozen status,
    idempotency and reconciliation before enabling any test-mode broker mutation.
11. Extend LeakShield/credential lifecycle and separately gated agent identity,
    bound one-use approvals, live revocation and restricted Stripe test broker.
12. Before production: privacy/retention/processing decisions, backup/restore and
    staged deployment/rollback drills, observability and signed release review.

Definition of done is the supplied feature matrix plus real end-to-end evidence;
a working analysis screen is not a complete RaksHex release.
