#!/usr/bin/env python3
"""Command-line interface for psession.

Provides a `psession` command to inspect and export data
from PalmSens `.pssession` files using the library functions.
"""

from __future__ import annotations

import argparse
import os
import sys
import signal
from pathlib import Path
from typing import Optional

import json
from .parse import parse, info, parse_pssession_file
from .enrichments import default_enrichments


def _positive_path(p: str) -> Path:
    path = Path(p)
    if not path.exists():
        raise argparse.ArgumentTypeError(f"No such file: {p}")
    return path


def build_parser() -> argparse.ArgumentParser:
    # Let argparse infer the program name from the invoked entry point.
    p = argparse.ArgumentParser(
        description="Parse PalmSens .pssession files to pandas DataFrames",
    )
    p.add_argument("file", type=_positive_path, help="Path to the .pssession file")
    p.add_argument(
        "-o",
        "--output",
        type=str,
        help="Write EIS CSV to path or '-' for stdout",
    )
    p.add_argument(
        "--info",
        action="store_true",
        help="Print measurement titles/methods and exit",
    )
    p.add_argument(
        "--head",
        action="store_true",
        help="Print a short preview of parsed tables",
    )
    p.add_argument(
        "--explore",
        action="store_true",
        help=(
            "Dump method parameter keys/values grouped by method (EIS/LSV/CV). "
            "Writes JSON files if --explore-out is a directory, or prints a single JSON to stdout with '-'"
        ),
    )
    p.add_argument(
        "--explore-out",
        type=str,
        default=None,
        help="Output directory for exploration dumps, or '-' for stdout",
    )
    return p


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.info:
        rows = info(str(args.file))
        if not rows:
            print("No measurements found", file=sys.stderr)
            return 1
        for i, r in enumerate(rows):
            print(
                f"{i:02d} | {r.get('method_id','?').upper():<4} | {r.get('title','')}"
            )
        return 0

    if args.explore:
        # Raw exploration: parse the file JSON and group full Method params by method_id
        data = parse_pssession_file(str(args.file))
        measurements = data.get("Measurements", [])

        # Group by method id
        by_method: dict[str, dict] = {}
        from .parsers.common import (
            parse_method,
        )  # local import to avoid cycles at import time

        for m in measurements:
            # Full method parsing with all keys
            params = (
                parse_method(
                    m.get("Method", ""), select_keys=None, match_method_id=None
                )
                or {}
            )
            mid = params.get("method_id", "unknown")
            # Common metadata
            meta = {
                "Title": m.get("Title", ""),
                "TimeStamp": m.get("TimeStamp", 0),
            }

            entry = {
                "metadata": meta,
                "params": params,
            }

            if mid not in by_method:
                by_method[mid] = {"keys": set(), "records": []}
            by_method[mid]["keys"].update(params.keys())
            by_method[mid]["records"].append(entry)

        # Convert sets to sorted lists for JSON serialization
        serializable = {
            k: {"keys": sorted(list(v["keys"])), "records": v["records"]}
            for k, v in by_method.items()
        }

        # Output handling
        out_spec = args.explore_out
        if out_spec is None or out_spec == "-":
            print(json.dumps(serializable, indent=2))
            return 0
        else:
            out_dir = Path(out_spec)
            out_dir.mkdir(parents=True, exist_ok=True)
            for mid, payload in serializable.items():
                out_path = out_dir / f"explore_{mid}.json"
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2)
                print(f"Wrote exploration JSON -> {out_path}")
            return 0

    opts = {}
    if os.getenv("PSESS_PRESORT") is not None:
        opts["presort"] = os.getenv("PSESS_PRESORT").split(",")

    opts["cv"] = {
        "base_sort": ["date"],
    }

    measurements = parse(
        str(args.file),
        enrichments=default_enrichments(),
        opts=opts,
    )

    if args.head:
        print("EIS:")
        print(measurements.EIS.head())
        print("CV:")
        # subset = measurements.CV.groupby(["cycle", "channel"], as_index=False).head(1)
        # print(subset)
        print(measurements.CV.head())
        print("LSV:")
        print(measurements.LSV.head())

    for data, dtype in [
        (measurements.EIS, "eis"),
        (measurements.CV, "cv"),
        (measurements.LSV, "lsv"),
    ]:
        if args.output:
            if data is None:
                print("No data data to write", file=sys.stderr)
                continue
            if args.output == "-":
                # Make SIGPIPE behave like in shells (quietly terminate writers)
                try:
                    signal.signal(signal.SIGPIPE, signal.SIG_DFL)  # type: ignore[attr-defined]
                except Exception:
                    pass
                try:
                    data.to_csv(sys.stdout, index=False)
                except BrokenPipeError:
                    return 0
            else:
                out_path = Path(args.output + f"_{dtype}.csv")
                out_path.parent.mkdir(parents=True, exist_ok=True)
                data.to_csv(out_path, index=False)
                print(f"Wrote data CSV -> {out_path}")

    # If nothing printed or written, provide a tiny summary
    if not args.head and not args.output:
        found = [
            name
            for name, df in (
                ("EIS", measurements.EIS),
                ("CV", measurements.CV),
                ("LSV", measurements.LSV),
            )
            if df is not None
        ]
        if found:
            print("Parsed tables:", ", ".join(found))
        else:
            print("No data parsed", file=sys.stderr)
            return 3

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
