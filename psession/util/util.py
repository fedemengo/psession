import hashlib
import json
from typing import Any


def short_id(x: Any, length: int = 4) -> str:
    """Stable short id for strings, dicts, or lists."""
    if isinstance(x, (dict, list)):
        data = json.dumps(x, sort_keys=True, separators=(",", ":"))
    elif isinstance(x, str):
        data = x
    else:
        data = str(x)

    return hashlib.blake2b(data.encode(), digest_size=length).hexdigest()
