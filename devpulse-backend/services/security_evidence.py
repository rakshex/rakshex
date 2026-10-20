"""Copy and redact known source-bearing scan fields, including historical JSON.

This is a scan-schema boundary, not universal DLP for arbitrary prose. New context
fields must be explicitly reviewed. Historical storage/backups are not rewritten.
"""
import json

REDACTED = '[REDACTED]'
SENSITIVE_FIELDS = frozenset(('matched_text','snippet','code','source_code','original_code',
                              'fix_code','api_key','password','authorization','secret','token'))


def redact_scan_evidence(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (ValueError, TypeError, RecursionError):
            return REDACTED
    if not isinstance(value, (dict, list)):
        return REDACTED
    remaining = 50000
    def redact(item, depth=0):
        nonlocal remaining
        remaining -= 1
        if depth > 40 or remaining < 0:
            return REDACTED
        if isinstance(item, dict):
            return {key: REDACTED if str(key).lower().replace('-', '_') in SENSITIVE_FIELDS else redact(child, depth+1)
                    for key, child in item.items()}
        if isinstance(item, list):
            return [redact(child,depth+1) for child in item]
        return item
    return redact(value)
