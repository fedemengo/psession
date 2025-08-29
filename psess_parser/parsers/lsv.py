from .common import parse_common


def parse_lsv(measurement, method_info=None):
    print("Parsing LSV measurement...")

    assert (
        len(measurement.get("Curves", [])) > 0
    ), "No channels found in LSV measurement"

    return {}
