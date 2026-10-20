# Synthetic code audit — 2026-10-20

Method: source searches for demo/mock/simulated/random/placeholder plus call-site review of the entries below. This is not a claim that every file has been manually audited. Fixtures and explicit offline tooling must not be mistaken for customer evidence.

| Location | Classification | Action / limitation |
|---|---|---|
| services/cost_intelligence.py:get_demo_cost_data | Deterministic demo helper; no production caller found in reviewed tree | Do not wire into live cost UI; keep synthetic evidence separate |
| services/ai_security_engine.py:get_threat_feed | Simulated helper retained for existing tests; runtime threat route reads database | Remove obsolete helper or move to fixtures in follow-up |
| services/mock_server.py | Explicit offline/mock responses and generated sample code | Retains mock:true; not provider connectivity proof |
| services/health_monitor.py initial state | Unknown/placeholder when no observation | Not an uptime measurement; review last_checked semantics |
| services/marketplace.py weather demo key | External demo request configuration | Replace with unavailable/configuration-required state before production |
| services/email_service.py | Missing provider formerly reported success | Fixed to return false; delivery integration not verified |
| routes/cicd.py | Old unexecuted checks implied pass | Compatibility and budget now explicitly not_run; only static security score evaluates |
| tests/fixtures/legacy_synthetic_credential.json | Synthetic compatibility evidence | Preserve, never use as a production credential |
| Self-Repair UI | Real bounded analysis | Does not claim patches, sandbox passes or PR publication |

Raw legacy scan evidence remains in historical storage until a separately reviewed retention migration. Redaction on read does not erase backups. Generated security suggestions are advice, not tested repairs.

## Repair fixtures

repair-fixtures/python-json-rename is an explicitly synthetic regression against
api.example.com. Its baseline actually fails the new request-key assertion; the generated
candidate is intended to pass in the isolated CI container. No provider compatibility is
inferred from this fixture. GitHub publisher tests use an in-process fake HTTP transport;
there is no fabricated live App installation or PR result in the application UI.
