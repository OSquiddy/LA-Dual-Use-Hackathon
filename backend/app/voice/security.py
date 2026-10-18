"""Retell raw-body HMAC verification, including the provider's five-minute freshness window.

Reference: https://github.com/RetellAI/retell-python-sdk/blob/main/src/retell/lib/webhook_auth.py
"""
import hashlib
import hmac
import re
import time


def verify_signature(body: bytes, signature: str, key: str) -> bool:
    if not key:
        return False
    match = re.fullmatch(r"v=(\d{1,16}),d=([0-9a-f]{64})", signature)
    if match is None:
        return False
    timestamp, digest = match.groups()
    if abs(int(time.time() * 1000) - int(timestamp)) > 300_000:
        return False
    expected = hmac.new(key.encode(), body + timestamp.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, digest)
