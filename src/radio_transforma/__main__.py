"""Module entry point: ``python -m radio_transforma``."""

from __future__ import annotations

import sys

from radio_transforma.cli import main

if __name__ == "__main__":
    sys.exit(main())
