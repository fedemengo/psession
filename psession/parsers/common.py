import pandas as pd
from datetime import datetime, timedelta
from ..util.util import short_id

MEASUREMENT_ID = "measurement_id"
SWEEP_ID = "sweep_id"
SORT_KEYS = ["date", "channel"]


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
    clean_text = text.strip().lower()
    for raw in clean_text.strip().splitlines():
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


def flattened_measurements(measurements, sort_keys=SORT_KEYS):
    df = pd.concat(
        (pd.DataFrame(run["data"]).assign(**run["metadata"]) for run in measurements),
        ignore_index=True,
    )

    # metadata first
    meta_cols = list(measurements[0]["metadata"].keys())
    other = [c for c in df.columns if c not in meta_cols]
    df = df[meta_cols + other]

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.sort_values(sort_keys).reset_index(drop=True)

    return df
