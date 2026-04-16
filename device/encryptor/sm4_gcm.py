from __future__ import annotations

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def encrypt(key: bytes, iv: bytes, aad: bytes, plaintext: bytes) -> tuple[bytes, bytes]:
    encryptor = Cipher(algorithms.SM4(key), modes.GCM(iv, min_tag_length=12)).encryptor()
    encryptor.authenticate_additional_data(aad)
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    return ciphertext, encryptor.tag[:12]
