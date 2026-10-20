# Self-Repair operations and coverage

This is a real, bounded adapter for Python requests POST/PUT/PATCH with literal HTTPS
URLs and inline JSON dicts. Submitted inline OpenAPI schemas must confirm exactly the
reviewer-selected property rename with equal schemas and no other target-operation or
global changes. A public migration reference and explicit source consent are required.
Unsupported JS/TS/provider SDKs, refs, dynamic/rebound calls and semantic migrations stop
for manual review. Test success covers submitted scope, not the whole repository.

## Operator setup (not a deployment performed in this session)

- Apply reviewed migrations with `alembic upgrade head` after backup approval.
- Configure a dedicated canonical 32-byte base64 ENCRYPTION_MASTER_KEY for API/worker;
  preserve historical keys. See CREDENTIAL_STORAGE.md. Source/patch bundles are encrypted.
- Provision a disposable dedicated Linux worker host with Docker and scoped database
  access. Never mount the daemon socket into the API or candidate. Daemon access is
  privileged: do not share the worker host with production workloads or network access.
- Build `docker build -t rakshex-repair-sandbox repair-sandbox` out of band. Set
  REPAIR_SANDBOX_IMAGE to the immutable `docker image inspect --format '{{.Id}}'
  rakshex-repair-sandbox` result. Runtime pulls and dependency installs are disabled;
  mutable tags are rejected. Review/rebuild image provenance regularly.
- Run `python -m repair_worker --watch` from devpulse-backend on this separate host.
  One worker only with dev SQLite; PostgreSQL row claims support multiple workers.
  Supervise the process and allow at least 180 seconds for shutdown.
- Submit 1–40 explicit relative .py paths (at most 256 KiB source; 768 KiB total),
  including existing tests/test_*.py. Optional source_root maps to a repository subfolder.
  Paths are bounded to 240 characters/eight components. No archives, symlinks, Git clone hooks or arbitrary host commands are accepted.

Snapshots run non-root, read-only, network-disabled, capability-free, no new privileges,
64 PIDs, 256 MiB, 1 CPU, 30 seconds and 128 KiB captured output; /tmp is a 16 MiB noexec
tmpfs. Worker environment/secrets are not passed. Containers are a restriction layer,
not VM isolation. Raw output is not persisted: only hash, exit code and observed count.
A failing baseline (exit 1), passing candidate and equal nonzero test counts are required.
Green-on-green, timeout, output limit, infrastructure errors and failed patches reject.
Repository-authored tests still require reviewer judgement.

## Publication connection

Install a GitHub App for selected repositories, with Contents and Pull requests read/write.
Store GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY only in the operator secret store. Bind:

`REPAIR_REPOSITORIES={"WORKSPACE_ID":{"repository":"rakshex/rakshex","installation_id":123}}`

This binding is server/operator-owned. Tokens are short-lived and narrowed to this one
repository/permissions. A connected ChatGPT GitHub account does not supply this App key.
No App installation/key was provisioned here; live App publication requires these values.
Mock-transport protocol tests are explicitly not live integration evidence.

Accepted owners/admins approve the exact diff/evidence hash. Worker rechecks permission,
patch integrity, source/tests against the immutable repository base and unchanged base
branch. It creates one deterministic branch and idempotent draft PR, without force push,
merge or deployment. Retry recognizes matching tree/parent and an existing open draft;
human branch edits or closed/ready PRs require review. Publication has a 120-second worker deadline. A partial failure may leave a branch.

## Recovery and deletion

UI polls every five seconds. Queued means waiting, never validated. Owner/admin deletion
removes the encrypted bundle/local evidence but not GitHub PRs/backups. Active stages block
deletion. No automatic retention promise: configure cleanup/backups before production.
Artifact responses are authorized/no-store. Avoid credentials; there is no universal DLP.
A crashed worker can leave an active stage: stop its containers, inspect job/branch/PR,
recheck authorization and reconcile through an operator change procedure. Automatic lease
recovery/dead-letter handling remains an operational blocker. Never manually mark success.
