"""Native AES-256-GCM writes with authenticated, non-destructive legacy reads.

v2 wire format matches reviewed historical PR #248/#239. No edge-runtime branch
is activated here. This module neither migrates rows nor contacts a provider.
"""
import asyncio
import base64
import hashlib
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from services import encryption as legacy

AAD = b'devpulse-api-key:v2'


async def _key(*, writing=False):
    if writing and os.getenv('ENV') == 'production' and not legacy._MASTER_KEY_ENV:
        raise ValueError('A dedicated encryption master is required for production writes')
    if writing and legacy._MASTER_KEY_ENV:
        try:
            configured = base64.b64decode(legacy._MASTER_KEY_ENV, validate=True)
            if len(configured) != 32:
                raise ValueError()
        except (ValueError, TypeError):
            raise ValueError('New writes require canonical base64 of 32 master bytes') from None
    master = await asyncio.to_thread(legacy._get_master_key)
    if len(master) != 32:
        raise ValueError('Encryption master must resolve to 32 bytes')
    return hashlib.sha256(master).digest()


async def encrypt_for_storage(plaintext: str) -> str:
    if not isinstance(plaintext, str) or not plaintext:
        raise ValueError('A non-empty credential is required')
    key = await _key(writing=True)
    nonce = secrets.token_bytes(12)
    encrypted = AESGCM(key).encrypt(nonce, plaintext.encode('utf-8'), AAD)
    return 'v2:' + base64.b64encode(nonce + encrypted).decode('ascii')


async def decrypt_from_storage(encrypted: str) -> str:
    if not isinstance(encrypted, str) or not encrypted:
        raise ValueError('Invalid encrypted record')
    if ':' in encrypted and not encrypted.startswith('v2:'):
        raise ValueError('Unsupported ciphertext version')
    if not encrypted.startswith('v2:'):
        # Historical master interpretation and authenticated reader remain intact.
        # Never rewrite ciphertext on read or discard the original key material.
        try:
            base64.b64decode(encrypted, validate=True)
            return await asyncio.to_thread(legacy.decrypt_aes256, encrypted)
        except Exception:
            raise ValueError('Invalid encrypted record') from None
    try:
        value = base64.b64decode(encrypted[3:], validate=True)
        if len(value) < 28:
            raise ValueError('Invalid encrypted record')
        key = await _key()
        return AESGCM(key).decrypt(value[:12], value[12:], AAD).decode('utf-8')
    except Exception:
        raise ValueError('Invalid encrypted record') from None


async def upgrade_ciphertext(encrypted: str) -> str:
    """Create a verified migration candidate in memory; no persistent mutation."""
    plaintext = await decrypt_from_storage(encrypted)
    candidate = encrypted if encrypted.startswith('v2:') else await encrypt_for_storage(plaintext)
    if await decrypt_from_storage(candidate) != plaintext:
        raise ValueError('Ciphertext verification failed')
    return candidate
