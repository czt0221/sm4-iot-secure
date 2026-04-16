from __future__ import annotations

import os


def generate_iv() -> bytes:
    return os.urandom(12)
