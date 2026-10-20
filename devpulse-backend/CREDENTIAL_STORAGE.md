# Credential storage and legacy compatibility

New records use `v2:` + base64(nonce12 + AES-256-GCM ciphertext/tag16), matching
reviewed source PR #248/#239. Native `cryptography` AESGCM is used; no custom
cipher writes, Worker/WebCrypto adapter or provider execution is enabled.
AAD is `devpulse-api-key:v2`; the AES key is SHA-256 of the historically resolved
32-byte master. The old master interpretation is preserved for existing records.
The format is not row/tenant/key-ID bound. New authenticated envelope versions and
managed key rotation remain separate release work, not implicit guarantees.

Production writes require a dedicated `DEVPULSE_ENCRYPTION_KEY` that resolves to
32 bytes (base64 of 32 random bytes); no JWT fallback for new production writes.
Development fallback remains for local-only testing. Do not log or commit key values.
Legacy authenticated reads are retained; the old writer fails explicitly.
`upgrade_ciphertext` creates/verifies a candidate in memory only and never updates
stored values. Do not replace original ciphertext or retire old key material.

Before production migration: inventory formats and key provenance without printing
values; back up DB and keys separately; rehearse restore with synthetic/staging data;
roll compatible readers out before writers; use separately reviewed sidecar/CAS
migration; preserve old ciphertext and key material until retirement is approved.
Old-only readers cannot read v2; rolling back past compatible readers is unsafe.

Ordinary key and budget APIs return metadata and a fixed masked value, never
ciphertext or decrypted secret. Existing disable/re-enable is account-scoped; no
broker is activated, so no provider-side revocation or execution-time containment
claim is made. Tests use synthetic credentials only.
