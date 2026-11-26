"""Asegura que la raíz del repositorio esté en ``sys.path`` incluso si se ejecuta ``pytest`` directo."""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = str(Path(__file__).resolve().parent.parent)
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
