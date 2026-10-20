# Production readiness — 2026-10-20

**Not production ready. Do not merge or deploy automatically.**

The development branch contains a genuine bounded analysis feature and targeted security fixes. It does not provide the complete Self-Repair, Budget Lock, LeakShield or agent broker product.

Release blockers: finish known critical/high authorization and session/proxy/logging review; reconcile schema evolution and operational migrations; workspace-scope inherited global data; managed encryption keys/rotation/restore; consent and retention controls; hardened isolated repair runner and tested patch evidence; least-privilege GitHub App publisher; atomic budget ledger and idempotent test-mode broker; responsive/a11y validation; staged backup/restore/rollback and observability drills.

Required gate: reproducible positive and negative end-to-end evidence against the exact release commit, a documented unresolved-risk review, and explicit human merge/deploy approval. A green CI suite covers its assertions, not all product requirements.
