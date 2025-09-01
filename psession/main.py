#!/usr/bin/env python3
"""Backwards-compatible shim for the CLI.

Kept for users calling `python -m psession.main` directly.
Prefer the console script `psession` or `python -m psession`.
"""

from .cli import main

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
