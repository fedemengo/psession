import re
from .common import parse_common, pick_keys, flatten_measurements, with_sweep_id, Parser

METHOD_ID = "cv"
SORT_KEYS = ["date", "channel", "cycle"]
METHOD_KEYS = ["method_id", "e_begin", "e_end", "e_step", "e_vtx1", "e_vtx2", "scan_rate", "n_scans"]
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


def parse_dataset(measurement, metadata):
    meta = with_sweep_id(metadata)

    xs = measurement.get("XAxisDataArray", [])
    ys = measurement.get("YAxisDataArray", [])

    data = {}
    for out_key, in_data in zip(["voltage", "current"], [xs, ys]):
        data[out_key] = [x.get("V") for x in in_data.get("DataValues", [])]

    return {
        "metadata": meta,
        "data": data,
    }


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

        measurements.append(parse_dataset(cv_measurement, metadata))

    return flatten_measurements(measurements)


cv_parser = Parser(
    method_id=METHOD_ID,
    parse=parse_cv,
    sort_keys=SORT_KEYS,
    method_keys=METHOD_KEYS,
    info_keys=INFO_KEYS,
)
