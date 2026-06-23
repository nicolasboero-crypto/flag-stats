"""Capa de datos: conexión a SQLite y esquema.

Modelo central: una fila = una JUGADA (play). De ahí derivamos todo el análisis
de tendencias. Dos perspectivas en la misma tabla:

  - tipo_registro = 'RIVAL'   -> scouting de un equipo rival
  - tipo_registro = 'PROPIO'  -> jugadas de Osos Polares

Cada jugada pertenece a un PARTIDO (rival + fecha), lo que falta en el form actual
y agregamos acá para poder separar y comparar partidos.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

# Ubicación por defecto de la base (un único archivo, fácil de mover/respaldar).
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "flag_stats.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS jugadas (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Contexto del partido (lo que falta en el form y agregamos)
    tipo_registro       TEXT    NOT NULL CHECK (tipo_registro IN ('RIVAL', 'PROPIO')),
    equipo              TEXT    NOT NULL,   -- equipo dueño de la jugada (rival scouteado u 'Osos Polares')
    rival               TEXT,               -- oponente en ese partido
    fecha               TEXT,               -- ISO YYYY-MM-DD
    partido_id          TEXT,               -- agrupador de partido (equipo+rival+fecha)

    -- Situación (del form)
    intento             INTEGER,            -- down 1-4
    situacion           TEXT,               -- RENOVACION / GOL
    yardas_situacion    INTEGER,            -- yardas para renovar/anotar
    jugada_nro          INTEGER,            -- n° de jugada en la secuencia

    -- La jugada
    tipo_jugada         TEXT,               -- PASE / CORRIDA
    qb                  TEXT,               -- dorsal del pasador
    wr                  TEXT,               -- dorsal del receptor objetivo
    resultado           TEXT,               -- COMPLETO / INCOMPLETO
    zona_lado           TEXT,               -- Izquierda / Medio / Derecha (eje X: lado del lanzamiento)
    zona_profundidad    TEXT,               -- Corto / Medio / Profundo (eje Y: profundidad de la jugada)
    yardas_hechas       INTEGER,            -- yardas ganadas

    -- Defensa
    defensor_defleccion     TEXT,           -- dorsal del defensor que deflectó el pase (vacío si no hubo)
    defensor_intercepcion   TEXT,           -- dorsal del defensor que interceptó (vacío si no hubo)
    int_zona_lado           TEXT,           -- lado donde se produjo la intercepción
    int_zona_profundidad    TEXT,           -- profundidad donde se produjo la intercepción
    int_yarda               INTEGER,        -- yarda donde se interceptó
    int_yarda_devolucion    INTEGER,        -- hasta qué yarda la devolvió

    comentario          TEXT,
    creado_en           TEXT    DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_jugadas_equipo  ON jugadas (equipo);
CREATE INDEX IF NOT EXISTS idx_jugadas_partido ON jugadas (partido_id);
CREATE INDEX IF NOT EXISTS idx_jugadas_tipo    ON jugadas (tipo_registro);
"""


def get_connection(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    """Devuelve una conexión a SQLite con row_factory tipo dict."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | str = DB_PATH) -> None:
    """Crea las tablas si no existen."""
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


if __name__ == "__main__":
    init_db()
    print(f"Base inicializada en: {DB_PATH}")
