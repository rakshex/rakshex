# Test results — security increment, 2026-10-20

| Check | Observed result |
|---|---|
| Baseline full backend | 202 passed, 1 failed, 1 skipped; shared-connection SQLite concurrency regression investigated |
| Corrected full backend: python -m pytest -q --tb=short | 234 passed, 1 PostgreSQL-only skip, 3 dependency/event-loop warnings; 128.41s |
| Final security remediation file after two added regressions | 32 passed, 3 warnings; 5.25s; includes cache isolation and historical copy-on-read redaction |
| Initial focused security/team run | 38 passed, 1 test assertion error (AsyncEngine property); corrected to sync_engine.hide_parameters before full green run |
| Frontend Jest | 9 suites, 34 tests passed |
| TypeScript: npx tsc --noEmit | Passed |
| Frontend npm run build | Exit 0; fresh .next/BUILD_ID produced; multiple-lockfile root warning |
| git diff --check | Passed |

Logs were captured locally as session2-*.log. New tests use only synthetic credentials.
The full run preceded the final two added tests; both were subsequently verified in the
32-test security file. The PostgreSQL-only lock case requires CI; local SQLite is not
presented as PostgreSQL evidence. Event-loop deprecation warnings remain open.

Prior revision 523c786 had green remote PostgreSQL smoke/lock+migration, frontend build,
Cypress (20), and Cloudflare checks. Those historical checks are not a rerun against
this increment. See the draft PR checks for current revision status. No production
load, delivery, provider mutation, model request, repair sandbox or deployment was tested.
