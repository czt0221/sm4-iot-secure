from __future__ import annotations

from cryptography.hazmat.primitives import hashes, hmac


def derive_hour_key(master_key: bytes, hour_index: int) -> bytes:
    mac = hmac.HMAC(master_key, hashes.SM3())
    mac.update(hour_index.to_bytes(4, "big", signed=False))
    # SM4 requires a 128-bit key, so the derived HMAC output is truncated to 16 bytes.
    return mac.finalize()[:16]
