#!/usr/bin/env python3
"""Run the isolated standard-library test suite."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    suite = unittest.defaultTestLoader.discover(
        str(ROOT / "scripts" / "tests"),
        top_level_dir=str(ROOT),
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
