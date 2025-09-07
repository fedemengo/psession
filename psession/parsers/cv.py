import re
import numpy as np
import pandas as pd
from functools import partial
from .common import (
    parse_common,
    pick_keys,
    flatten_measurements,
    with_sweep_id,
    must_get,
)

METHOD_ID = "cv"
SORT_KEYS = ["date", "channel", "cycle"]
METHOD_KEYS = [
    "method_id",
    "e_begin",
    "e_end",
    "e_step",
    "e_vtx1",
    "e_vtx2",
    "scan_rate",
    "n_scans",
]
INFO_KEYS = ["e_vtx1", "e_vtx2", "scan_rate", "n_scans"]


def parse_cv_ch_title(title):
    try:
        assert len(title) > 0, "CV channel title is empty"
        regex = r"CV i vs E Scan (\d+) Channel (\d+)"
        match = re.match(regex, title)
        assert match, f"Could not parse CV channel title: {title}"
        cycle = int(match.group(1))
        channel = int(match.group(2))

        return {"cycle": cycle, "channel": channel}
    except Exception:
        return {}


def add_sweep_direction(df):
    dE = np.diff(df["voltage"], prepend=df["voltage"].iloc[0])
    sweep_direction = np.sign(dE).astype(np.int8)
    sweep_direction[0] = np.where(df["voltage"].iloc[1] >= df["voltage"].iloc[0], 1, -1)
    df.insert(0, "sweep_dir", sweep_direction)
    return df


def compute_charge(df, scan_rate):
    dE = df["voltage"].diff().fillna(0.0)
    prev_i = df["current"].shift().fillna(df["current"])
    Imid = 0.5 * (df["current"] + prev_i)

    # Time step is positive regardless of sweep direction
    dt = np.abs(dE) / abs(float(scan_rate))
    dQ = Imid * dt  # units: (current units) * s

    df["charge"] = dQ.cumsum()
    df["charge_segment"] = dQ.groupby(df["sweep_dir"]).cumsum()

    return df


def normalize_charge(q):
    q_min, q_max = q.min(), q.max()
    return (q - q_min) / (q_max - q_min) if q_max > q_min else 0.0


def parse_dataset(measurement, metadata):
    xs = measurement.get("XAxisDataArray", [])
    ys = measurement.get("YAxisDataArray", [])

    volt = [x.get("V") for x in xs.get("DataValues", [])]
    curr = [y.get("V") for y in ys.get("DataValues", [])]

    df = pd.DataFrame(
        {
            "voltage": volt,
            "current": curr,
        }
    )

    df = add_sweep_direction(df)
    df = compute_charge(df, must_get(metadata, "scan_rate"))
    df["q_norm"] = df.groupby("sweep_dir")["charge_segment"].transform(normalize_charge)

    return df, metadata


def parse_cv(measurement, method_info=None):
    assert len(measurement.get("Curves", [])) > 0, "No channels found in CV measurement"

    measurement_info = parse_common(measurement)

    measurements = []
    for cv_measurement in measurement["Curves"]:
        metadata = {
            **measurement_info,
            **parse_cv_ch_title(cv_measurement.get("Title", "")),
            **pick_keys(method_info, METHOD_KEYS),
        }
        metadata = with_sweep_id(metadata)

        measurements.append(parse_dataset(cv_measurement, metadata))

    return flatten_measurements(measurements)
