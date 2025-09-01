import re
from .common import parse_common, flattened_measurements, short_id, SWEEP_ID


def parse_cv_ch_title(title):
    assert len(title) > 0, "CV channel title is empty"
    regex = r"CV i vs E Scan (\d+) Channel (\d+)"
    match = re.match(regex, title)
    assert match, f"Could not parse CV channel title: {title}"
    cycle = int(match.group(1))
    channel = int(match.group(2))

    return {"cycle": cycle, "channel": channel}


def parse_dataset(measurement, metadata):
    meta = metadata.copy()
    meta[SWEEP_ID] = short_id(meta)

    xs = measurement.get("XAxisDataArray", [])
    ys = measurement.get("YAxisDataArray", [])

    data = {}
    for out_key, in_data in zip(["voltage", "current"], [xs, ys]):
        data[out_key] = [x.get("V") for x in in_data.get("DataValues", [])]

    return {
        "metadata": meta,
        "data": data,
    }


wanted = ["e_begin", "e_end", "e_step", "scan_rate", "cycle_count"]


def method_params(data):
    return {k: data[k] for k in wanted if k in data}


def parse_cv(measurement, method_info=None):
    assert len(measurement.get("Curves", [])) > 0, "No channels found in CV measurement"

    measurement_info = parse_common(measurement)
    method_meta = method_params(method_info)

    measurements = []
    for cv_measurement in measurement["Curves"]:
        metadata = {
            **measurement_info,
            **parse_cv_ch_title(cv_measurement.get("Title", "")),
            **method_meta,
        }

        measurements.append(parse_dataset(cv_measurement, metadata))

    return flattened_measurements(measurements)
