import hashlib
import json
from typing import Any


def short_id(x: Any, length: int = 4) -> str:
    if isinstance(x, dict) or isinstance(x, list):
        data = json.dumps(x, sort_keys=True, separators=(",", ":"))
    if isinstance(x, str):
        data = x

    return hashlib.blake2b(data.encode(), digest_size=length).hexdigest()


def deep_get(d, keys, default=None):
    for k in keys.split("."):
        if isinstance(d, dict):
            d = d.get(k, default)
        else:
            return default
    return d
