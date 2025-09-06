import re
from .common import parse_common, pick_keys, flatten_measurements, with_sweep_id

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


def parse_dataset(measurement, metadata):
    meta = with_sweep_id(metadata)

    xs = measurement.get("XAxisDataArray", [])
    ys = measurement.get("YAxisDataArray", [])

    data = {}
    for out_key, in_data in zip(["current", "voltage"], [xs, ys]):
        data[out_key] = [x.get("V") for x in in_data.get("DataValues", [])]

    return {
        "metadata": meta,
        "data": data,
    }


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
        measurements.append(
            parse_dataset(lsv_measurement, metadata),
        )

    return flatten_measurements(
        measurements,
    )
