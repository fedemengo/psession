from .common import parse_common, MEASUREMENT_ID


def parse_cv(measurement, method_info=None):
    print("Parsing CV measurement...")

    assert len(measurement.get("Curves", [])) > 0, "No channels found in CV measurement"

    return {}

