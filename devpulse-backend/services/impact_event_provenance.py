"""Conservative binding of scanner events to exact verified OpenAPI contract pairs.

This is NOT authorization for repository access or proof of provider provenance.
The scanner dispatcher must independently validate membership, repository,
commit, and allowed paths before inspecting any customer source.
"""
from __future__ import annotations
import re
from services.contract_analysis import analyze_contracts, digest

class ImpactEventRefused(ValueError):
    pass

def bind_internal_impact_event(*, before, after, report, change, path,
                               workspace_id, repository, commit_sha):
    if not isinstance(workspace_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", workspace_id):
        raise ImpactEventRefused("Invalid workspace identity")
    if (not isinstance(repository, str)
        or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository)
        or any(x in (".", "..") or x.startswith(".") for x in repository.split("/"))):
        raise ImpactEventRefused("Invalid repository identity")
    if not isinstance(commit_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
        raise ImpactEventRefused("Full commit SHA required")
    if not isinstance(path, str) or not path.startswith("/") or len(path) > 200 or any(c.isspace() for c in path):
        raise ImpactEventRefused("Invalid operation path")
    if not isinstance(change, dict) or change.get("kind") != "operation_removed" or change.get("compatibility") != "breaking":
        raise ImpactEventRefused("Only removed operations are supported")
    method = change.get("method")
    if method not in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE"):
        raise ImpactEventRefused("Invalid HTTP method")
    if change.get("operation_ref") != digest([method.lower(), path]):
        raise ImpactEventRefused("Method/path fingerprint mismatch")
    try:
        actual = analyze_contracts(before, after)
    except (ValueError, TypeError, RecursionError, AttributeError) as exc:
        raise ImpactEventRefused("Unsupported contract input") from exc
    if report != actual or change not in actual["changes"]:
        raise ImpactEventRefused("Event not grounded in the contract pair")
    if method.lower() not in before["paths"].get(path, {}) or method.lower() in after["paths"].get(path, {}):
        raise ImpactEventRefused("Operation is not removed")
    return {
        "schema_version": "rakshex.impact-event.v1",
        "source_type": "internal_contract_analysis",
        "provenance_level": "contract_pair_verified_only",
        "workspace_id": workspace_id, "repository": repository,
        "commit_sha": commit_sha,
        "before_hash": actual["before_hash"], "after_hash": actual["after_hash"],
        "change_ref": change["operation_ref"], "method": method,
        "old_path": path, "change_kind": "operation_removed",
        "authorization_status": "not_verified", "scan_status": "not_started",
    }
