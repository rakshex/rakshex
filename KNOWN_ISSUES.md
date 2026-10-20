# Known issues / release blockers

1. Inherited credential service describes AES-GCM but implements a custom HMAC
   stream. No new financial/provider execution is enabled. Review #248 preserving
   legacy ciphertext; verify production keys/rotation/restore separately.
2. Legacy scanners store anonymous/shared findings and need tenant scoping plus
   pre-storage redaction (#249). Legacy change alerts need #240 review. New repair
   analysis scoping does not fix every legacy endpoint.
3. PostgreSQL locking test is added with isolated schema and CI service, but local
   PostgreSQL was unavailable. Local results use SQLite only.
4. Cypress and Playwright Chromium downloads returned truncated/non-ZIP archives.
   Browser E2E is included but unrun; frontend unit tests/build do not replace it.
5. Existing Node 20 engines versus Node 24 Cloudflare configuration/Vercel issue
   (#241) unresolved. Requirements are ranges, not a Python lockfile. Existing
   pytest custom event-loop fixture emits deprecation/unclosed-loop warnings.
6. Self-Repair intake handles only inline operation analysis. It is not complete
   semantic OpenAPI validation, SDK compatibility, impacted code detection, repair,
   sandbox validation or draft-PR publication. Hashed references intentionally hide
   paths; a local scope-aware impact mapper must later supply actionable locations.
7. Existing JWT localStorage, distributed throttling, proxy trust, error logging,
   startup create_all/fail-open initialization and telemetry need deeper hardening.
   New analysis input checks actual streamed byte length; older middleware only
   checks Content-Length. New API does not imply global protection.
8. No production deployment, migrations, backup/restore or live external integrations
   verified. No immutable audit, formal security certification, customer-count,
   savings, compliance or absolute-security claims are supported.
9. Historical branch trees and selected focused code inspected; all old engine
   implementations/migrations/fixtures need deeper review. Private sandbox not
   accessed; reported Stripe/Firebase results not reproduced.
10. Destination main is LICENSE-only initialization; all code is on development
    branch pending review. Do not deploy main or merge without owner authorization.
11. Existing dashboard shell has limited mobile navigation; full responsive/accessibility
    review remains required. New form uses accessible labels and responsive columns,
    but browser/device verification is pending.
