from __future__ import annotations

from cryptography.hazmat.primitives import hashes, hmac


def derive_hour_key(master_key: bytes, hour_index: int) -> bytes:
    mac = hmac.HMAC(master_key, hashes.SM3())
    mac.update(hour_index.to_bytes(4, "big", signed=False))
    return mac.finalize()[:16]
