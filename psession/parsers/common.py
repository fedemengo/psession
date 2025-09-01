from datetime import datetime, timedelta
from ..util.util import short_id

MEASUREMENT_ID = "measurement_id"


def ticks_to_date(ticks):
    dt = datetime(1, 1, 1) + timedelta(microseconds=ticks / 10)
    return dt


def parse_common(measurement):
    title = measurement.get("Title", "")
    date = ticks_to_date(measurement.get("TimeStamp", 0)).isoformat()

    return {
        "title": title,
        "date": date,
        MEASUREMENT_ID: short_id([title, date]),
    }


def parse_method(text):
    out = {}
    for raw in text.strip().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, val = line.split("=", 1)
        else:
            parts = line.split(None, 1)
            if len(parts) != 2:
                continue
            key, val = parts
        key, val = key.strip(), val.strip()
        # basic type coercion
        low = val.lower()
        if low in ("true", "false"):
            val = low == "true"
        else:
            try:
                val = int(val)
            except ValueError:
                try:
                    val = float(val)
                except ValueError:
                    pass
        if key in out:
            if isinstance(out[key], list):
                out[key].append(val)
            else:
                out[key] = [out[key], val]
        else:
            out[key] = val
    return out
