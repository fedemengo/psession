import re
import pandas as pd
from .common import parse_common, MEASUREMENT_ID
from ..util.util import short_id, deep_get

SWEEP_ID = "sweep_id"
SORT_KEYS = ["date", "channel"]

UNITS = ["frequency", "z", "phase", "zre", "zim", "c", "cre", "cim"]


def labels_mapping(label):
    if label == "capacitance":
        return "c"
    if label == "capacitance'":
        return "cre"
    if label == "capacitance''":
        return "cim'"

    return label


# parse tutles in the form "CH 1: 13 freqs"
def parse_eis_ch_title(title, annotations={}, opts={}):
    assert len(title) > 0, "EIS channel title is empty"

    regex = r"CH (\d+): (\d+) freqs"
    match = re.match(regex, title)
    assert match, f"Could not parse EIS channel title: {title}"
    channel = int(match.group(1))

    return channel


def parse_frequency(ds_value):
    return [x.get("V") for x in ds_value.get("DataValues", [])]


def parse_dataset(measurement, metadata):
    dataset = measurement.get("DataSet", {})
    meta = metadata.copy()
    meta[SWEEP_ID] = short_id(meta)

    data = {}
    for ds_value in dataset.get("Values", []):
        ds_type = ds_value.get("Description", "").lower()
        ds_value = ds_value.get("DataValues", [])
        ds_type = labels_mapping(ds_type)
        if ds_type in UNITS:
            data[ds_type] = [x.get("V") for x in ds_value]

    return {
        "metadata": meta,
        "data": data,
    }


def flattened_measurements(measurements):
    df = pd.concat(
        (pd.DataFrame(run["data"]).assign(**run["metadata"]) for run in measurements),
        ignore_index=True,
    )

    # metadata first
    meta_cols = list(measurements[0]["metadata"].keys())
    other = [c for c in df.columns if c not in meta_cols]
    df = df[meta_cols + other]

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.sort_values(SORT_KEYS).reset_index(drop=True)

    return df


def parse_eis(measurement, annotations={}, opts={}):
    # print("Parsing EIS measurement...")

    assert (
        len(measurement.get("EISDataList", [])) > 0
    ), "No channels found in EIS measurement"

    measurement_info = parse_common(measurement)

    measurements = []
    for eis_measurement in measurement["EISDataList"]:
        channel = parse_eis_ch_title(
            eis_measurement.get("Title", ""), annotations=annotations, opts=opts
        )
        metadata = {
            **measurement_info,
            **annotations,
            "channel": channel,
        }

        measurements.append(
            {
                **parse_dataset(eis_measurement, metadata),
            }
        )

    return flattened_measurements(measurements)
