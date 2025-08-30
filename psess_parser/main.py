#!/usr/bin/env python3

import argparse
import numpy as np
from .parser import parse, gen_annotation


def main():
    """Main function to parse command line arguments and run the parser."""
    parser = argparse.ArgumentParser(
        description="Parse PalmSens .pssession files to pandas DataFrame"
    )
    parser.add_argument("input_file", help="Path to the .pssession file")
    args = parser.parse_args()

    def parse_title(row):
        try:
            title = row.get("title")
            parts = title.split(" ")
            data, animal, implant, device_n, block = parts

            device_int = int(device_n[1:])
            two_digit_dev = f"N{device_int:02d}"

            return {
                "device": two_digit_dev,
                "block": block,
            }
        except Exception as e:
            print(f"Error annotating row {row}: {e}")
            return {}

    enrichments = [
        (lambda row: True, parse_title),
        (
            lambda row: row.get("block") == "BOT",
            lambda row: {"channel": row.get("channel", 0) + 16},
        ),
    ]

    eis, cv, lsv = parse(
        args.input_file,
        enrichments=enrichments,
        opts={"presort": ["device", "channel"]},
    )
    print(np.unique(eis["device"]))
    print(eis)


if __name__ == "__main__":
    main()
