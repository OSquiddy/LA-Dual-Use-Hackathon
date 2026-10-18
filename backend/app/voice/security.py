"""Raw-body verification using the official Retell Python SDK.

Only the Retell API key marked for webhooks can authenticate provider deliveries.
"""
from functools import lru_cache
import re

from retell import Retell


@lru_cache(maxsize=1)
def _retell_client(key: str) -> Retell:
    # Constructing a client makes no API request. Verification is entirely local.
    return Retell(api_key=key)


def verify_signature(body: bytes, signature: str, key: str) -> bool:
    if not key or not re.fullmatch(r"v=\d{1,16},d=[0-9a-f]{64}", signature):
        return False
    try:
        return bool(_retell_client(key).verify(
            body.decode("utf-8"), api_key=key, signature=signature,
        ))
    except (UnicodeError, ValueError, TypeError):
        return False
