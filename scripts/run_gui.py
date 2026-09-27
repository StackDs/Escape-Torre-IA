#!/usr/bin/env python3
"""Lanzador directo de la interfaz gráfica de usuario (GUI) PyQt5."""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.gui.app import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
