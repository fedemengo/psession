#!/usr/bin/env python3
"""Enable `python -m psession` to run the CLI."""

from .cli import main

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
