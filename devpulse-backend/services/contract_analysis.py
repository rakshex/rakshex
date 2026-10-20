"""Bounded, network-free OpenAPI operation comparison; no repair success claims."""
import hashlib
import json
from typing import Any

RULESET = "inline-openapi-operations-v1"
METHODS = frozenset(("get", "put", "post", "delete", "options", "head", "patch", "trace"))
DOCUMENTATION = frozenset(("description", "summary", "example", "examples", "externalDocs", "tags"))


class UnsupportedContract(ValueError):
    pass


def digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def validate_contract(spec: dict) -> None:
    if not isinstance(spec.get("openapi"), str) or not spec["openapi"].startswith(("3.0.", "3.1.")):
        raise UnsupportedContract("Only inline OpenAPI 3.0/3.1 contracts are supported")
    if not isinstance(spec.get("paths"), dict) or len(spec["paths"]) > 1000:
        raise UnsupportedContract("A bounded paths object is required")
    stack = [(spec, 0)]
    nodes = 0
    while stack:
        value, depth = stack.pop()
        nodes += 1
        if nodes > 10000 or depth > 32:
            raise UnsupportedContract("Contract complexity exceeds the supported limit")
        if isinstance(value, dict):
            if "$ref" in value or "callbacks" in value or "webhooks" in value:
                raise UnsupportedContract("References, callbacks and webhooks need a later analyzer")
            stack.extend((v, depth + 1) for v in value.values())
        elif isinstance(value, list):
            stack.extend((v, depth + 1) for v in value)
    for path, item in spec["paths"].items():
        if not path.startswith("/") or not isinstance(item, dict):
            raise UnsupportedContract("Invalid path item")
        if any(method in item and not isinstance(item[method], dict) for method in METHODS):
            raise UnsupportedContract("Invalid operation")


def _structural(value: Any) -> Any:
    # Only used on operation objects. Do not remove schema properties with these names:
    # a property literally named "description" remains meaningful API structure.
    if isinstance(value, dict):
        return {key: _structural_properties(child) if key == "properties" else _structural(child)
                for key, child in value.items() if key not in DOCUMENTATION and not key.startswith("x-")}
    if isinstance(value, list):
        return [_structural(item) for item in value]
    return value


def _structural_properties(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _structural(child) for key, child in value.items()}
    return _structural(value)


def _operations(spec: dict) -> dict:
    operations = {}
    for path, item in sorted(spec["paths"].items()):
        for method in sorted(METHODS & item.keys()):
            reference = digest([method, path])
            # Persist only fingerprints, never raw paths, descriptions or example credentials.
            signature = digest(_structural({"operation": item[method],
                "path_parameters": item.get("parameters", []),
                "path_servers": item.get("servers", []),
                "security": spec.get("security", []), "servers": spec.get("servers", [])}))
            operations[reference] = {"method": method.upper(), "signature": signature}
    return operations


def analyze_contracts(before: dict, after: dict) -> dict:
    validate_contract(before)
    validate_contract(after)
    old, new = _operations(before), _operations(after)
    changes = []
    for reference in sorted(old.keys() | new.keys()):
        if reference not in new:
            kind, compatibility = "operation_removed", "breaking"
        elif reference not in old:
            kind, compatibility = "operation_added", "review_required"
        elif old[reference]["signature"] != new[reference]["signature"]:
            kind, compatibility = "operation_changed", "review_required"
        else:
            continue
        changes.append({"operation_ref": reference, "method": (new.get(reference) or old[reference])["method"],
                        "kind": kind, "compatibility": compatibility})
    return {"ruleset": RULESET, "before_hash": digest(before), "after_hash": digest(after),
            "before_operations": len(old), "after_operations": len(new), "changes": changes,
            "outcome": "review_required" if changes else "no_operation_change_detected",
            "limitations": ["Inline operations only; not a complete semantic compatibility analysis",
                            "No code impact analysis, patch, test execution or GitHub publication performed"]}
