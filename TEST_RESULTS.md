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

## Repair workflow increment

- Full local backend: **264 passed, 5 skipped, 3 warnings**, 90.59s. Skips include the
  existing PostgreSQL-only case and four dedicated Docker cases (Docker unavailable).
- New frontend: **37 tests / 10 suites passed**. TypeScript was run from the frontend
  workspace; no compiler errors. An initial root-directory tsc printed usage and is not
  counted as a successful type check.
- Isolated migration upgrade/downgrade/re-upgrade passed with the new repair_jobs head.
- New CI: real Docker baseline/candidate, network/credential/read-only tests, timeout,
  output cap and rejection of failed/green-baseline patches; actual PostgreSQL and browser
  checks must be read on the final head. No local container success is claimed.
- New browser spec exercises real queued job creation, artifact review, persisted reload
  and deletion, plus five viewport widths, keyboard drawer behavior and axe A/AA checks.
- GitHub App JWT/signature, source/base binding, least-privilege token request, refusal
  paths and idempotent draft creation are protocol-tested with fake HTTP, not a live App.

Initial new test setup incorrectly expected existing workspace creation to return 201;
corrected to its actual 200 contract. Dependency installation hit a truncated Cypress
binary; installation was repeated with binary download disabled. CI supplies the browser.
Final immutable CI run links and any failures/fixes will be recorded in the draft PR.

### First repair CI result and browser preflight fix

At 3b12bd1, isolated Self-Repair CI passed **35 tests**, including actual Docker
baseline/candidate, egress/read-only/environment, timeout/output and negative patch
gates (run 39390636256). Backend, frontend, Cloudflare, full-stack PostgreSQL and
membership/migration jobs passed. Browser preflight crashed on a shorthand body
property in the existing TypeScript request extractor before any Cypress test ran.
Fixed its property-assignment guard without disabling checks; rerunning full browser CI.
Added publisher tree-mode verification to refuse symlinks/submodules/executable files;
its protocol tests passed (10). Final-head results are recorded in the PR.
