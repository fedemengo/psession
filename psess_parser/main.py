#!/usr/bin/env python3

import argparse
from .parser import parse, gen_annotation


def main():
    """Main function to parse command line arguments and run the parser."""
    parser = argparse.ArgumentParser(
        description="Parse PalmSens .pssession files to pandas DataFrame"
    )
    parser.add_argument("input_file", help="Path to the .pssession file")
    args = parser.parse_args()

    def annotate(entry):
        try:
            title = entry.get("title")
            parts = title.split(" ")
            data, animal, implant, device_n, block = parts

            return {
                "device": device_n,
                "block": block,
            }
        except Exception as e:
            print(f"Error annotating entry {entry}: {e}")
            return {}

    annotations = gen_annotation(args.input_file, annotate)

    eis, cv, lsv = parse(
        args.input_file,
        annotations=annotations,
        opts={
            "blocks_offset": {
                "TOP": 0,
                "BOT": 16,
            },
            "presort": ["device"],
            "annotations": {"channel": {"17": "test", "24": "test", "29": "test"}},
        },
    )
    print(eis)


if __name__ == "__main__":
    main()
