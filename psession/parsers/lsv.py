import re
from .common import parse_common, flattened_measurements, short_id, SWEEP_ID


# parse title in the form "LSV i vs E Channel 1"
def parse_lsv_ch_title(title):
    assert len(title) > 0, "LSV channel title is empty"

    regex = r"LSV i vs E Channel (\d+)"
    match = re.match(regex, title)
    assert match, f"Could not parse EIS channel title: {title}"
    channel = int(match.group(1))

    return {"channel": channel}


def parse_dataset(measurement, metadata):
    meta = metadata.copy()
    meta[SWEEP_ID] = short_id(meta)

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
        }
        measurements.append(
            parse_dataset(lsv_measurement, metadata),
        )

    return flattened_measurements(
        measurements,
    )
