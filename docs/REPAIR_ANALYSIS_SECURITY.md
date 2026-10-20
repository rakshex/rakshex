# Repair-analysis threat model and test matrix

| Threat | Control | Verification |
|---|---|---|
| Cross-workspace access / pending invite | accepted membership on every read/write | real DB/API outsider, pending, viewer tests |
| Stale writer authorization | same PostgreSQL workspace row lock as team mutations | optional isolated-schema PostgreSQL locking test; local SQLite coverage |
| Body flooding / chunked bypass | actual streamed bytes capped at 256 KiB | oversized chunked input test |
| Malformed/ambiguous JSON | reject duplicates, non-finite numbers, excessive depth/nodes | malformed/deep/duplicate tests |
| Spec SSRF / injected instructions | no URL fetch, subprocess or model calls; reject refs/callbacks/webhooks | reference rejected; egress tripwire test |
| Secret persistence / reflection | retain only hashes, fixed enums/methods/counts; generic errors | synthetic secret in path/docs absent from response and DB |
| False compatibility or repair success | conservative changed status plus explicit limitations | API/UI assertions; no patch/test/PR claim |
| Dependency failure | storage exception → 503; no success record | failure injection test |
| Evidence retention | only owner/admin explicit delete; no raw spec columns | read/delete/reload tests |

Residual risks: inline analysis is not full OpenAPI validation or SDK semantics;
metadata hashes can be guessed; existing global scanner/auth/logging issues remain;
JWT stored in localStorage by existing UI; no claims about external telemetry,
backups or legal zero retention. No immutability guarantee: owner/admin deletion
is intentional, and database operators remain trusted. PostgreSQL runtime and
browser tests must pass in CI before release. No production release is authorized.
