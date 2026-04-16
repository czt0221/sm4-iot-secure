from __future__ import annotations

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def decrypt(key: bytes, iv: bytes, aad: bytes, ciphertext: bytes, tag: bytes) -> bytes:
    decryptor = Cipher(
        algorithms.SM4(key),
        modes.GCM(iv, tag, min_tag_length=12),
    ).decryptor()
    decryptor.authenticate_additional_data(aad)
    return decryptor.update(ciphertext) + decryptor.finalize()
