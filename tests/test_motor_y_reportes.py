"""Pruebas unitarias y de contrato HTTP para motor, reportes y FastAPI.

Se ejecutan con ``pytest -v`` sin requerir los ~850 MB del dataset real: construyen un mini-dataset
sintético reproducible en ``tmp_path`` y verifican definiciones, casos límite y códigos HTTP.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend import contrato, main, motor, reportes


def _escribir_dataset_sintetico(carpeta: Path) -> None:
    """Genera los 5 archivos mínimos del formato NFL Big Data Bowl en ``carpeta``."""
    (carpeta / "tracking").mkdir(parents=True, exist_ok=True)

    pd.DataFrame([
        {"gameId": 2021090900, "week": 1},
    ]).to_csv(carpeta / "games.csv", index=False)

    pd.DataFrame([
        {"nflId": 1, "displayName": "Tom Brady"},
        {"nflId": 2, "displayName": "Donovan Smith"},
        {"nflId": 3, "displayName": "Myles Garrett"},
        {"nflId": 4, "displayName": "Baker Mayfield"},
        {"nflId": 5, "displayName": "Jedrick Wills"},
        {"nflId": 6, "displayName": "Shaquil Barrett"},
    ]).to_csv(carpeta / "players.csv", index=False)

    # Jugada 101: TB ataca hacia la derecha contra CLE, con presión por izquierda (dy > 1).
    # Jugada 102: TB ataca hacia la izquierda contra CLE, con presión por izquierda (dy_raw < -1 -> -dy > 1).
    # Jugada 103: CLE ataca hacia la derecha contra TB, sin presión (rusher a 4 yd).
    pd.DataFrame([
        {
            "gameId": 2021090900, "playId": 101, "down": 3, "yardsToGo": 8,
            "possessionTeam": "TB", "defensiveTeam": "CLE", "passResult": "S",
            "prePenaltyPlayResult": -7, "dropBackType": "TRADITIONAL",
            "pff_playAction": 0, "pff_passCoverageType": "Man",
        },
        {
            "gameId": 2021090900, "playId": 102, "down": 1, "yardsToGo": 10,
            "possessionTeam": "TB", "defensiveTeam": "CLE", "passResult": "C",
            "prePenaltyPlayResult": 12, "dropBackType": "DESIGNED_ROLLOUT_RIGHT",
            "pff_playAction": 1, "pff_passCoverageType": "Zone",
        },
        {
            "gameId": 2021090900, "playId": 103, "down": 1, "yardsToGo": 10,
            "possessionTeam": "CLE", "defensiveTeam": "TB", "passResult": "C",
            "prePenaltyPlayResult": 6, "dropBackType": "TRADITIONAL",
            "pff_playAction": 0, "pff_passCoverageType": "Zone",
        },
    ]).to_csv(carpeta / "plays.csv", index=False)

    # El bloqueador 5 (Jedrick Wills, LT de CLE) tiene 0 duelos en PFF para validar pierde_pct=None.
    pd.DataFrame([
        {"gameId": 2021090900, "playId": 101, "nflId": 1, "pff_role": "Pass", "pff_positionLinedUp": "QB",
         "pff_hit": 0, "pff_hurry": 0, "pff_sack": 0, "pff_hitAllowed": 0, "pff_hurryAllowed": 0, "pff_sackAllowed": 0, "pff_nflIdBlockedPlayer": None},
        {"gameId": 2021090900, "playId": 101, "nflId": 2, "pff_role": "Pass Block", "pff_positionLinedUp": "LT",
         "pff_hit": 0, "pff_hurry": 0, "pff_sack": 0, "pff_hitAllowed": 0, "pff_hurryAllowed": 0, "pff_sackAllowed": 1, "pff_nflIdBlockedPlayer": 3},
        {"gameId": 2021090900, "playId": 101, "nflId": 3, "pff_role": "Pass Rush", "pff_positionLinedUp": "LE",
         "pff_hit": 0, "pff_hurry": 0, "pff_sack": 1, "pff_hitAllowed": 0, "pff_hurryAllowed": 0, "pff_sackAllowed": 0, "pff_nflIdBlockedPlayer": None},

        {"gameId": 2021090900, "playId": 102, "nflId": 1, "pff_role": "Pass", "pff_positionLinedUp": "QB",
         "pff_hit": 0, "pff_hurry": 0, "pff_sack": 0, "pff_hitAllowed": 0, "pff_hurryAllowed": 0, "pff_sackAllowed": 0, "pff_nflIdBlockedPlayer": None},
        {"gameId": 2021090900, "playId": 102, "nflId": 2, "pff_role": "Pass Block", "pff_positionLinedUp": "LT",
         "pff_hit": 0, "pff_hurry": 0, "pff_sack": 0, "pff_hitAllowed": 0, "pff_hurryAllowed": 1, "pff_sackAllowed": 0, "pff_nflIdBlockedPlayer": 3},
        {"gameId": 2021090900, "playId": 102, "nflId": 3, "pff_role": "Pass Rush", "pff_positionLinedUp": "LE",
         "pff_hit": 0, "pff_hurry": 1, "pff_sack": 0, "pff_hitAllowed": 0, "pff_hurryAllowed": 0, "pff_sackAllowed": 0, "pff_nflIdBlockedPlayer": None},

        {"gameId": 2021090900, "playId": 103, "nflId": 4, "pff_role": "Pass", "pff_positionLinedUp": "QB",
         "pff_hit": 0, "pff_hurry": 0, "pff_sack": 0, "pff_hitAllowed": 0, "pff_hurryAllowed": 0, "pff_sackAllowed": 0, "pff_nflIdBlockedPlayer": None},
        {"gameId": 2021090900, "playId": 103, "nflId": 5, "pff_role": "Pass Block", "pff_positionLinedUp": "LT",
         "pff_hit": 0, "pff_hurry": 0, "pff_sack": 0, "pff_hitAllowed": 0, "pff_hurryAllowed": 0, "pff_sackAllowed": 0, "pff_nflIdBlockedPlayer": None},
        {"gameId": 2021090900, "playId": 103, "nflId": 6, "pff_role": "Pass Rush", "pff_positionLinedUp": "LE",
         "pff_hit": 0, "pff_hurry": 0, "pff_sack": 0, "pff_hitAllowed": 0, "pff_hurryAllowed": 0, "pff_sackAllowed": 0, "pff_nflIdBlockedPlayer": None},
    ]).to_csv(carpeta / "pffScoutingData.csv", index=False)

    filas = []
    # Play 101 (right): snap=1, pressure at frame=8 (dt=0.7s, rusher at dy=+1.5 -> izquierda), fin=10 (qb_sack).
    for f in range(1, 12):
        ev = "ball_snap" if f == 1 else ("qb_sack" if f == 10 else "None")
        rusher_y = 29.0 if f >= 8 else 32.0
        rusher_x = 50.0 if f >= 8 else 54.0
        for nid, x, y in ((1, 50.0, 27.5), (2, 51.0, 29.0), (3, rusher_x, rusher_y)):
            filas.append({"gameId": 2021090900, "playId": 101, "nflId": nid, "frameId": f,
                          "x": x, "y": y, "event": ev, "playDirection": "right"})

    # Play 102 (left): snap=1, pressure at frame=6 (rusher at y=26.0 vs qb y=27.5 -> dy_raw=-1.5 -> -dy=+1.5 -> izquierda).
    for f in range(1, 10):
        ev = "ball_snap" if f == 1 else ("pass_forward" if f == 9 else "None")
        rusher_y = 26.0 if f >= 6 else 22.0
        rusher_x = 60.0 if f >= 6 else 55.0
        for nid, x, y in ((1, 60.0, 27.5), (2, 59.0, 26.0), (3, rusher_x, rusher_y)):
            filas.append({"gameId": 2021090900, "playId": 102, "nflId": nid, "frameId": f,
                          "x": x, "y": y, "event": ev, "playDirection": "left"})

    # Play 103 (right): CLE offense vs TB defense, no pressure.
    for f in range(1, 10):
        ev = "ball_snap" if f == 1 else ("pass_forward" if f == 9 else "None")
        for nid, x, y in ((4, 40.0, 26.5), (5, 42.0, 28.0), (6, 46.0, 32.0)):
            filas.append({"gameId": 2021090900, "playId": 103, "nflId": nid, "frameId": f,
                          "x": x, "y": y, "event": ev, "playDirection": "right"})

    pd.DataFrame(filas).to_csv(carpeta / "tracking" / "tracking_2021090900.csv", index=False)


@pytest.fixture()
def datos_sinteticos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    _escribir_dataset_sintetico(tmp_path)
    monkeypatch.setattr(motor, "DATA", tmp_path)
    reportes._cache.clear()
    yield tmp_path
    reportes._cache.clear()


def test_motor_ventana_presion_y_lado_izquierda_derecha(datos_sinteticos: Path) -> None:
    d = motor.cargar(datos_sinteticos)
    j = d.jugadas.sort_values("playId").reset_index(drop=True)

    assert len(j) == 3
    # Play 101 (right): snap=1, pressure=8 -> reloj=7; fin=10 -> lanzamiento=9
    assert bool(j.loc[0, "presion"]) is True
    assert int(j.loc[0, "reloj_f"]) == 7
    assert int(j.loc[0, "lanzamiento_f"]) == 9
    assert j.loc[0, "lado"] == "izquierda"

    # Play 102 (left): dy invertido mantiene lado == "izquierda"
    assert bool(j.loc[1, "presion"]) is True
    assert int(j.loc[1, "reloj_f"]) == 5
    assert j.loc[1, "lado"] == "izquierda"

    # Play 103: sin presión
    assert bool(j.loc[2, "presion"]) is False
    assert pd.isna(j.loc[2, "reloj_f"])


def test_utilidades_reportes_reparto_ts_y_repeticion_vacia() -> None:
    reparto = reportes._reparto(pd.Series({"izquierda": 1, "centro": 1, "derecha": 1}))
    assert sum(reparto.values()) == 100
    assert reportes._reparto(pd.Series(dtype="int64")) == {"izquierda": 0, "centro": 0, "derecha": 0}
    assert reportes._ts_frames([5, 10, None, None, None, None, None, None, None, None]) == 10
    assert reportes._ts_frames([None, None, None]) is None

    vacia = pd.DataFrame(columns=["presion", "x0", "presionador", "reloj_f", "sack", "gameId", "playId"])
    rep = reportes._repeticion(vacia, None, pd.DataFrame(), lambda _: "Jugador")
    assert rep["frames"] == []
    assert rep["reloj_s"] == 0.0


def test_api_contratos_errores_y_nulabilidad(datos_sinteticos: Path) -> None:
    with TestClient(main.app) as client:
        r_health = client.get("/health")
        assert r_health.status_code == 200
        assert r_health.json() == {"status": "ok"}

        r_opt = client.get("/api/opciones")
        assert r_opt.status_code == 200
        opt = contrato.Opciones(**r_opt.json())
        assert opt.equipos == ["CLE", "TB"]

        # TB vs CLE: bloqueador Donovan Smith con duelos registrados
        r_tb_cle = client.get("/api/partido", params={"ofensiva": "TB", "rival": "CLE"})
        assert r_tb_cle.status_code == 200
        p1 = contrato.Partido(**r_tb_cle.json())
        assert p1.bloqueador.pierde_pct == 100.0

        # CLE vs TB: TB no tiene presiones -> fallback seguro; CLE LT Jedrick Wills tiene pierde_pct=None
        r_cle_tb = client.get("/api/partido", params={"ofensiva": "CLE", "rival": "TB"})
        assert r_cle_tb.status_code == 200
        p2 = contrato.Partido(**r_cle_tb.json())
        assert p2.bloqueador.pierde_pct is None

        # Situación con < 20 jugadas -> fuente "liga"
        r_sit = client.get("/api/situacion", params={"rival": "CLE", "sit": "l"})
        assert r_sit.status_code == 200
        assert contrato.SituacionRespuesta(**r_sit.json()).fuente == "liga"

        assert client.get("/api/escenario", params={"rival": "CLE", "pa": 1, "rollout": 0, "bloqueadores": 6}).status_code == 200
        assert client.get("/api/estrella", params={"rival": "CLE"}).status_code == 200

        r_rep_tb = client.get("/api/repeticion", params={"rival": "TB"})
        assert r_rep_tb.status_code == 200
        assert contrato.Repeticion(**r_rep_tb.json()).frames == []

        # Errores del contrato: 404 y 400 (nunca 422)
        assert client.get("/api/partido", params={"ofensiva": "TB", "rival": "XXX"}).status_code == 404
        assert client.get("/api/partido", params={"ofensiva": "CLE", "rival": "CLE"}).status_code == 400
        assert client.get("/api/situacion", params={"rival": "CLE", "sit": "z"}).status_code == 400
        assert client.get("/api/escenario", params={"rival": "CLE", "pa": 2}).status_code == 400
        assert client.get("/api/partido", params={"ofensiva": "TB"}).status_code == 400
