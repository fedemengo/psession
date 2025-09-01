import re
import pandas as pd
from .common import parse_common, flattened_measurements, SWEEP_ID
from ..util.util import short_id

SORT_KEYS = ["date", "channel"]

UNITS = ["frequency", "z", "phase", "zre", "zim", "c", "cre", "cim", "idc"]


def labels_mapping(label):
    if label == "capacitance":
        return "c"
    if label == "capacitance'":
        return "cre"
    if label == "capacitance''":
        return "cim"

    return label


# parse title in the form "CH 1: 13 freqs"
def parse_eis_ch_title(
    title,
):
    assert len(title) > 0, "EIS channel title is empty"

    regex = r"CH (\d+): (\d+) freqs"
    match = re.match(regex, title)
    assert match, f"Could not parse EIS channel title: {title}"
    channel = int(match.group(1))

    return {
        "channel": channel,
    }


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


def parse_eis(measurement, method_info=None):
    assert (
        len(measurement.get("EISDataList", [])) > 0
    ), "No channels found in EIS measurement"

    measurement_info = parse_common(measurement)

    measurements = []
    for eis_measurement in measurement["EISDataList"]:
        metadata = {
            **measurement_info,
            **parse_eis_ch_title(eis_measurement.get("Title", "")),
        }

        measurements.append(
            parse_dataset(eis_measurement, metadata),
        )

    return flattened_measurements(measurements, sort_keys=SORT_KEYS)
