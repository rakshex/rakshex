# Security remediation — 2026-10-20

Scope: this development branch only. This is a verified security increment, not a production clearance.

| Finding | Implemented boundary | Remaining limitation |
|---|---|---|
| Custom cipher mislabeled AES-GCM | Disable legacy writer; native cryptography AESGCM v2; authenticated legacy reader retained; malformed/tampered/wrong-key tests | No automatic rewrite, tenant-bound AAD, managed key IDs or rotation workflow; see backend CREDENTIAL_STORAGE.md |
| Ciphertext in ordinary key responses | ApiKey serializer emits metadata and a fixed mask; creation validates budget_period and returns 201 | Full credential revocation/rotation/provider validation is incomplete |
| Anonymous legacy scans and CI | Authentication, account-filtered history/badges and corrected persistence signatures | Account scoping is not accepted-workspace membership scoping |
| Raw matched secrets in findings/cache/storage | Scanner output redaction, copy-on-read historical JSON redaction, pre-persistence redaction and account-specific cache keys | Known field redaction is not general DLP; historical database/backups remain untouched |
| Source sent for fix suggestions | Default local suggestions; explicit model_processing_consent required; only canonical known-rule metadata sent | Provider retention/legal controls and full processing UX remain pending |
| Unsigned CI webhook/replay | Authenticated HMAC over exact body and timestamp; five-minute window; persisted unique event identity rejects exact replay | Not a GitHub App integration; independently re-signed events are distinct |
| False success / sensitive errors | DB initialization fails closed; generic request validation; SQL parameter hiding; unavailable email returns false | Full log review and all inherited false-success paths remain pending |

No production credentials were used. Crypto regressions use synthetic fixtures. No stored production rows were migrated. The test database now uses separate SQLite connections; a regression verifies that closing a reader cannot roll back another session's write. PostgreSQL lock behavior remains a distinct CI check.

Production blockers still include legacy global analytics/reporting routes, complete workspace authorization, session/cookie/proxy/rate-limit review, retention cleanup, backup/restore and operational key rotation. Do not enable a money-moving broker or deploy this branch based on these tests.
