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
"""

# Los índices van aparte: se crean DESPUÉS de migrar columnas, porque una base
# vieja podría no tener todavía la columna que el índice referencia.
INDICES = """
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


# Columnas que pueden faltar en una base creada con un esquema anterior.
# Se agregan automáticamente al iniciar (migración liviana).
COLUMNAS_MIGRABLES = {
    "tipo_registro": "TEXT",
    "equipo": "TEXT",
    "rival": "TEXT",
    "fecha": "TEXT",
    "partido_id": "TEXT",
    "intento": "INTEGER",
    "situacion": "TEXT",
    "yardas_situacion": "INTEGER",
    "jugada_nro": "INTEGER",
    "tipo_jugada": "TEXT",
    "qb": "TEXT",
    "wr": "TEXT",
    "resultado": "TEXT",
    "zona_lado": "TEXT",
    "zona_profundidad": "TEXT",
    "yardas_hechas": "INTEGER",
    "defensor_defleccion": "TEXT",
    "defensor_intercepcion": "TEXT",
    "int_zona_lado": "TEXT",
    "int_zona_profundidad": "TEXT",
    "int_yarda": "INTEGER",
    "int_yarda_devolucion": "INTEGER",
    "comentario": "TEXT",
}


def init_db(db_path: Path | str = DB_PATH) -> None:
    """Crea la tabla si no existe y agrega columnas faltantes (migración liviana).

    Esto evita que una base creada con un esquema viejo (ej: la persistida en el
    deploy antes de sumar la defensa) rompa al consultar columnas nuevas.
    """
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA)
        existentes = {fila[1] for fila in conn.execute("PRAGMA table_info(jugadas)")}
        for col, tipo in COLUMNAS_MIGRABLES.items():
            if col not in existentes:
                conn.execute(f"ALTER TABLE jugadas ADD COLUMN {col} {tipo}")
        conn.executescript(INDICES)  # ahora sí, con todas las columnas presentes
        conn.commit()


if __name__ == "__main__":
    init_db()
    print(f"Base inicializada en: {DB_PATH}")
