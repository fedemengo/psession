from datetime import datetime, timedelta
import pandas as pd

MEASUREMENT_ID = "measurement_id"
METHOD_ID = "method_id"
SWEEP_ID = "sweep_id"
SORT_KEYS = ["date", "channel"]

DATE_FMT = "%y%m%d%H%M%S"


def must_get(d, key, msg=None):
    if key not in d:
        raise KeyError(msg or f"Key '{key}' not found in dict")
    return d[key]


def pick_keys(data, keys):
    return {k: data[k] for k in keys if k in data}


def ticks_to_date(ticks):
    dt = datetime(1, 1, 1) + timedelta(microseconds=ticks / 10)
    return dt


def parse_common(measurement):
    title = measurement.get("Title", "")
    date = ticks_to_date(measurement.get("TimeStamp", 0))

    return {
        "title": title,
        "date": date,
        MEASUREMENT_ID: date.strftime(DATE_FMT),
    }


def with_sweep_id(data):
    out = data.copy()
    out[SWEEP_ID] = out.get(MEASUREMENT_ID) + "_ch" + str(out.get("channel"))
    return out


def method_to_dict(text):
    out = {}
    for raw in text.strip().lower().splitlines():
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


def parse_method(text, select_keys=None, match_method_id=None):
    m_dict = method_to_dict(text)
    if match_method_id and m_dict.get(METHOD_ID, "").lower() != match_method_id.lower():
        return None

    out = m_dict
    if select_keys is not None:
        out = pick_keys(m_dict, select_keys)

    out[METHOD_ID] = m_dict.get(METHOD_ID, "").lower()

    return out


def flatten_measurements(measurements, sort_keys=SORT_KEYS):
    frames = []
    for data, meta in measurements:
        df_run = data.assign(**meta)
        frames.append(df_run)

    df = pd.concat(frames, ignore_index=True, sort=False)

    meta_cols = list(measurements[0][1].keys())
    other = [c for c in df.columns if c not in meta_cols]
    df = df[meta_cols + other]

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    if sort_keys:
        keys = [c for c in sort_keys if c in df.columns]
        if keys:
            df = df.sort_values(keys).reset_index(drop=True)

    return df
