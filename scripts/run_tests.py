#!/usr/bin/env python3
"""Ejecuta la suite de pruebas unitarias del proyecto."""

import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


def main():
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(RAIZ / "tests"), pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    resultado = runner.run(suite)
    return 0 if resultado.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
