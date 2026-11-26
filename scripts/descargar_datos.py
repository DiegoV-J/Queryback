"""Descarga y valida la carpeta ``data/`` desde el dataset oficial del evento.

Fuente: https://github.com/ThompsonJamesBliss/nfl-big-data-bowl-regional-event-data
Solo usa librería estándar de Python para respetar el stack bloqueado del hackathon.

Uso:
    python scripts/descargar_datos.py
    python scripts/descargar_datos.py --verify-only
"""
from __future__ import annotations

import argparse
import io
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

REPO_URL = "https://github.com/ThompsonJamesBliss/nfl-big-data-bowl-regional-event-data.git"
ZIP_URL = "https://github.com/ThompsonJamesBliss/nfl-big-data-bowl-regional-event-data/archive/refs/heads/main.zip"
ARCHIVOS_BASE = ("games.csv", "plays.csv", "players.csv", "pffScoutingData.csv")
TRACKING_ESPERADOS = 122

RAIZ = Path(__file__).resolve().parent.parent
DATA_DIR = RAIZ / "data"


def validar_datos(carpeta: Path = DATA_DIR) -> list[str]:
    """Devuelve lista de problemas encontrados en ``carpeta`` (vacía si todo está completo)."""
    errores: list[str] = []
    if not carpeta.is_dir():
        return [f"No existe la carpeta {carpeta}"]
    for nombre in ARCHIVOS_BASE:
        ruta = carpeta / nombre
        if not ruta.is_file() or ruta.stat().st_size == 0:
            errores.append(f"Falta o está vacío: {ruta}")
    tracking_dir = carpeta / "tracking"
    archivos_tr = sorted(tracking_dir.glob("tracking_*.csv")) if tracking_dir.is_dir() else []
    if len(archivos_tr) != TRACKING_ESPERADOS:
        errores.append(
            f"Se esperaban {TRACKING_ESPERADOS} archivos en {tracking_dir}, encontrados {len(archivos_tr)}"
        )
    return errores


def _descargar_con_git(destino: Path) -> bool:
    """Usa git sparse-checkout si git está disponible para traer únicamente ``data/``."""
    if shutil.which("git") is None:
        return False
    with tempfile.TemporaryDirectory(prefix="nfl-bdb-") as tmp:
        clon = Path(tmp) / "repo"
        cmd = ["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", REPO_URL, str(clon)]
        if subprocess.run(cmd, check=False).returncode != 0:
            return False
        if subprocess.run(["git", "-C", str(clon), "sparse-checkout", "set", "data"], check=False).returncode != 0:
            return False
        origen = clon / "data"
        if not origen.is_dir():
            return False
        shutil.copytree(origen, destino, dirs_exist_ok=True)
    return True


def _descargar_por_zip(destino: Path) -> None:
    """Respaldo sin git: descarga el ZIP de main y extrae únicamente ``data/``."""
    print(f"[datos] Descargando ZIP desde {ZIP_URL}...", flush=True)
    with urllib.request.urlopen(ZIP_URL, timeout=180) as resp:
        contenido = resp.read()
    with zipfile.ZipFile(io.BytesIO(contenido)) as zf:
        for miembro in zf.infolist():
            if miembro.is_dir():
                continue
            partes = Path(miembro.filename).parts
            if len(partes) < 3 or partes[1] != "data":
                continue
            rel = Path(*partes[2:])
            salida = destino / rel
            salida.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(miembro) as src, open(salida, "wb") as dst:
                shutil.copyfileobj(src, dst)


def descargar(forzar: bool = False) -> int:
    """Descarga el dataset en ``data/`` si falta algún archivo y valida integridad."""
    if not forzar and not validar_datos(DATA_DIR):
        print(f"[datos] Dataset ya completo en {DATA_DIR} ({TRACKING_ESPERADOS} archivos de tracking).")
        return 0

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("[datos] Obteniendo dataset desde ThompsonJamesBliss/nfl-big-data-bowl-regional-event-data...", flush=True)
    if not _descargar_con_git(DATA_DIR):
        _descargar_por_zip(DATA_DIR)

    errores = validar_datos(DATA_DIR)
    if errores:
        print("[datos] Validación con advertencias/errores:")
        for e in errores:
            print(f"  - {e}")
        return 1
    print(f"[datos] Todo listo en {DATA_DIR} ({TRACKING_ESPERADOS} archivos de tracking verificados).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Descarga y verifica el dataset NFL Big Data Bowl 2023.")
    parser.add_argument("--verify-only", action="store_true", help="Solo verifica data/ sin descargar.")
    parser.add_argument("--force", action="store_true", help="Vuelve a descargar incluso si data/ ya existe.")
    args = parser.parse_args()

    if args.verify_only:
        errores = validar_datos(DATA_DIR)
        if errores:
            for e in errores:
                print(f"ERROR: {e}")
            return 1
        print(f"OK: dataset válido en {DATA_DIR} ({TRACKING_ESPERADOS} archivos tracking_*.csv).")
        return 0
    return descargar(forzar=args.force)


if __name__ == "__main__":
    raise SystemExit(main())
