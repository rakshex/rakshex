# RaksHex — API Change Intelligence

RaksHex's approved first product is **API Self-Repair**: upstream change → contract
analysis → code impact → narrow patch → isolated validation → GitHub **draft PR**
→ human review and merge. Budget Lock, LeakShield and the Dashboard/Gateway remain
part of the product roadmap. Controlled agent execution is a separate design track;
its credential, approval, policy, financial and revocation controls must all exist
before enabling a real provider mutation.

**Status: early implementation, not production-ready.** This branch preserves the
DevPulse source at `Akshu1245/Rakshex-complete-codebase@b8590fb` and implements the
first secure-core and contract-analysis slice. It does not claim the complete
Self-Repair pipeline, provider monitoring, SDK migration repair or money broker.

## Available in this milestone
- Team membership writes recheck accepted actor/target roles in one locked
  transaction, protecting primary/last owners and preventing admin peer escalation.
- `/self-repair` creates a workspace, accepts explicit authorization/processing
  consent, compares two bounded **inline OpenAPI 3.0/3.1 JSON** contracts, and shows
  saved analysis history and evidence. Owner/admin can delete saved evidence.
- Operation additions/removals/structural changes are deterministic; changed
  operations require review. This is not comprehensive semantic compatibility.
- Raw specifications, raw endpoint paths, descriptions and example secrets are
  not saved by this intake. Only hashes and result metadata are retained. No
  repository clone, model call, provider mutation, patch execution or PR publishing.
- References, callbacks and webhooks are rejected; combined request limit is
  256 KiB. No spec URLs are fetched.

| API | Authorization |
|---|---|
| `POST /api/repair-analyses` | accepted owner/admin/member; explicit consent |
| `GET /api/repair-analyses?workspace_id=...` | accepted workspace member, including viewer |
| `GET /api/repair-analyses/{id}` | accepted member of the owning workspace |
| `DELETE /api/repair-analyses/{id}` | accepted owner/admin only |

## Run locally
Python 3.12 and Node are required. Existing Node 20 engine declarations and Node 24
Cloudflare configuration need reconciliation before release; this milestone was
verified locally under Node 24.19.0/npm 11.9.0. Do not use production credentials.

Backend, from `devpulse-backend`:
```sh
python -m pip install -r requirements.txt
# Copy .env.example to .env and configure local values; never commit secrets.
# Local-only persistence: DATABASE_URL=sqlite+aiosqlite:///devpulse.db
python -m alembic upgrade head
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```
Frontend, from `devpulse-dashboard-ui`:
```sh
npm ci
# BACKEND_URL defaults to the local backend; dev server uses port 5000.
npm run dev
```
Sign up/sign in through the account menu, open `/self-repair`, create a workspace,
and submit two authorized inline contracts. A removed operation yields review
required, never a claim that customer code has been repaired.

## Verify
```sh
# devpulse-backend
python -m pytest tests/ -q --tb=short
# devpulse-dashboard-ui
npm test -- --runInBand
npx tsc --noEmit
npm run build
# Requires a complete Cypress binary and both applications running:
CYPRESS_BASE_URL=http://localhost:5000 npm run test:e2e
```
A PostgreSQL lock test runs only when `TEST_PG_URL` points to an isolated test
instance. It uses a unique schema and cleans up only that schema. CI provisions
its own PostgreSQL service. Local SQLite tests do not prove PostgreSQL locking.
See `IMPLEMENTATION_LOG.md` for actual results and unrun checks.

## Engineering handoff
- [Current audit](CURRENT_CODEBASE_AUDIT.md)
- [Current-to-target gaps](RAKSHEX_CURRENT_TO_TARGET_GAP_ANALYSIS.md)
- [Architecture and migration boundary](RAKSHEX_IMPLEMENTATION_ARCHITECTURE.md)
- [Feature status](FEATURE_STATUS.md), [project state](PROJECT_STATE.md)
- [Decisions](DECISION_LOG.md), [next actions](NEXT_ACTIONS.md), [known issues](KNOWN_ISSUES.md)
- [Intake threat model](docs/REPAIR_ANALYSIS_SECURITY.md)
- [Legacy DevPulse documentation](docs/DEVPULSE_README_LEGACY.md): historical claims,
  not evidence of current production readiness.

No automatic merge, production deployment, secret rotation or financial mutation
is authorized by this work. Original MIT license is retained.
