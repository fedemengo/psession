"""Built-in enrichment helpers.

Default enrichments mirror the prior CLI behavior: derive `device` and `block`
from the measurement title and offset `channel` by +16 for bottom (BOT).
"""

from __future__ import annotations

from typing import Callable, Dict, List, Tuple

Row = Dict[str, object]


def _parse_title(row: Row) -> Dict[str, object]:
    try:
        title = str(row.get("title", ""))
        parts = title.split(" ")
        # Expect: <date> <animal> <implant> <N##> <TOP|BOT>
        if len(parts) >= 5:
            _, _, _, device_n, block = parts[:5]
            device_int = int(str(device_n).lstrip("Nn"))
            two_digit_dev = f"N{device_int:02d}"
            return {"device": two_digit_dev, "block": block}
    except Exception:
        pass
    return {}


def default_enrichments() -> (
    List[Tuple[Callable[[Row], bool], Callable[[Row], Dict[str, object]]]]
):
    return [
        (lambda row: True, _parse_title),
        (
            lambda row: row.get("block") == "BOT",
            lambda row: {"channel": int(row.get("channel", 0)) + 16},
        ),
    ]
