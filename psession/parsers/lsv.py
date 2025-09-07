import re
import numpy as np
import pandas as pd
from .common import (
    parse_common,
    pick_keys,
    flatten_measurements,
    with_sweep_id,
    must_get,
)

METHOD_ID = "lsv"
SORT_KEYS = ["date", "channel"]
METHOD_KEYS = ["method_id", "e_begin", "e_end", "e_step", "scan_rate", "n_scans"]
INFO_KEYS = ["e_begin", "e_end"]


# parse title in the form "LSV i vs E Channel 1"
def parse_lsv_ch_title(title):
    try:
        assert len(title) > 0, "LSV channel title is empty"

        regex = r"LSV i vs E Channel (\d+)"
        match = re.match(regex, title)
        assert match, f"Could not parse EIS channel title: {title}"
        channel = int(match.group(1))

        return {"channel": channel}
    except Exception:
        return {}


def compute_charge(df, scan_rate):
    v = df["voltage"].to_numpy()
    i = df["current"].to_numpy()

    dE = np.diff(v, prepend=v[0])
    Imid = 0.5 * (i + np.r_[i[0], i[:-1]])
    dQ = (Imid * dE) / scan_rate
    df["charge"] = np.cumsum(dQ)
    return df


def parse_dataset(measurement, metadata):
    xs = measurement.get("XAxisDataArray", [])
    ys = measurement.get("YAxisDataArray", [])

    volt = [y.get("V") for y in xs.get("DataValues", [])]
    curr = [x.get("V") for x in ys.get("DataValues", [])]

    df = pd.DataFrame(
        {
            "voltage": volt,
            "current": curr,
        }
    )

    df = compute_charge(df, must_get(metadata, "scan_rate"))

    return df, metadata


def parse_lsv(measurement, method_info=None):
    assert (
        len(measurement.get("Curves", [])) > 0
    ), "No channels found in LSV measurement"

    measurement_info = parse_common(measurement)

    measurements = []
    for lsv_measurement in measurement["Curves"]:
        metadata = {
            **measurement_info,
            **parse_lsv_ch_title(lsv_measurement.get("Title", "")),
            **pick_keys(method_info, METHOD_KEYS),
        }
        metadata = with_sweep_id(metadata)
        measurements.append(
            parse_dataset(lsv_measurement, metadata),
        )

    return flatten_measurements(
        measurements,
    )
