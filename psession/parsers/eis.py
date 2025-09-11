import re
import pandas as pd
from typing import List
from .common import parse_common, pick_keys, flatten_measurements, with_sweep_id

METHOD_ID = "eis"
SORT_KEYS = ["date", "channel"]
METHOD_KEYS = ["method_id", "min_freq", "max_freq", "n_freq"]
INFO_KEYS: List[str] = []

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
    try:
        assert len(title) > 0, "EIS channel title is empty"

        regex = r"CH (\d+): (\d+) freqs.*"
        match = re.match(regex, title)
        assert match, f"Could not parse EIS channel title: {title}"
        channel = int(match.group(1))
        assert channel > 0, f"Invalid channel number in title: {title}"

        return {
            "channel": channel,
        }
    except Exception as e:
        raise RuntimeError(e)


def parse_dataset(measurement, metadata):
    dataset = measurement.get("DataSet", {})

    data = {}
    for ds_value in dataset.get("Values", []):
        ds_type = ds_value.get("Description", "").lower()
        ds_value = ds_value.get("DataValues", [])
        ds_type = labels_mapping(ds_type)
        if ds_type in UNITS:
            data[ds_type] = [x.get("V") for x in ds_value]

    df = pd.DataFrame(data)

    return df, metadata


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
            **pick_keys(method_info, METHOD_KEYS),
        }
        metadata = with_sweep_id(metadata)

        measurements.append(
            parse_dataset(eis_measurement, metadata),
        )

    return flatten_measurements(measurements, sort_keys=SORT_KEYS)
