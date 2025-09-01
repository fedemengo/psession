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

from .parser import parse, info
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

    opts = {}
    if os.getenv("PSESS_PRESORT") is not None:
        opts["presort"] = os.getenv("PSESS_PRESORT").split(",")

    eis, cv, lsv = parse(
        str(args.file),
        enrichments=default_enrichments(),
        opts=opts,
    )

    if args.head:
        if eis is not None:
            print("EIS:")
            print(eis.head())
        if cv is not None:
            print("CV:")
            print(cv.head())
        if lsv is not None:
            print("LSV:")
            print(lsv.head())

    if args.output:
        if eis is None:
            print("No EIS data to write", file=sys.stderr)
            return 2
        if args.output == "-":
            # Make SIGPIPE behave like in shells (quietly terminate writers)
            try:
                signal.signal(signal.SIGPIPE, signal.SIG_DFL)  # type: ignore[attr-defined]
            except Exception:
                pass
            try:
                eis.to_csv(sys.stdout, index=False)
            except BrokenPipeError:
                return 0
        else:
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            eis.to_csv(out_path, index=False)
            print(f"Wrote EIS CSV -> {out_path}")

    # If nothing printed or written, provide a tiny summary
    if not args.head and not args.output:
        found = [
            name
            for name, df in (("EIS", eis), ("CV", cv), ("LSV", lsv))
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
