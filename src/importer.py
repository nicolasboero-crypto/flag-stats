"""Importador de respuestas del Google Form hacia SQLite.

Dos fuentes posibles:
  - Un CSV descargado de la planilla  -> importar_csv()
  - Directo desde el Google Sheet      -> importar_sheet()  (sin descargar a mano)

Mapea los títulos de las preguntas del form a las columnas de la tabla `jugadas`.
Es tolerante a tildes/mayúsculas en los encabezados. Las columnas que el form
todavía NO captura (RIVAL, FECHA) se pasan como parámetros al importar, o se leen
del CSV/Sheet si ya las agregaste como columnas.
"""

from __future__ import annotations

import csv
import io
import re
import unicodedata
import urllib.request
from pathlib import Path

from .db import get_connection, init_db
from .zonas import norm_lado, norm_profundidad

# Mapa: encabezado normalizado del CSV -> columna de la tabla.
COLUMNAS = {
    "intento": "intento",
    "yardas para situacion": "yardas_situacion",
    "situacion": "situacion",
    "jugada": "jugada_nro",
    "tipo de jugada": "tipo_jugada",
    "qb": "qb",
    "wr": "wr",
    "resultado": "resultado",
    "lado": "zona_lado",
    "profundidad": "zona_profundidad",
    "yardas hechas": "yardas_hechas",
    # Defensa
    "defensor defleccion": "defensor_defleccion",
    "defleccion": "defensor_defleccion",
    "defensor deflexion": "defensor_defleccion",  # tolera la grafía vieja
    "deflexion": "defensor_defleccion",
    "defensor intercepcion": "defensor_intercepcion",
    "intercepcion": "defensor_intercepcion",
    "lado intercepcion": "int_zona_lado",
    "profundidad intercepcion": "int_zona_profundidad",
    "yarda intercepcion": "int_yarda",
    "yarda devolucion": "int_yarda_devolucion",
    "comentario": "comentario",
    # Por si ya las agregaste a la planilla:
    "rival": "rival",
    "fecha": "fecha",
    "equipo": "equipo",
}

INT_COLS = {
    "intento", "yardas_situacion", "jugada_nro", "yardas_hechas",
    "int_yarda", "int_yarda_devolucion",
}


def _norm(texto: str) -> str:
    """Minúsculas, sin tildes, sin espacios sobrantes."""
    s = unicodedata.normalize("NFKD", texto or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.strip().lower()


def _a_int(valor: str):
    try:
        return int(str(valor).strip())
    except (ValueError, TypeError):
        return None


def _importar_filas(
    reader: csv.DictReader,
    *,
    tipo_registro: str,
    equipo: str,
    rival: str | None,
    fecha: str | None,
    db_path: Path | str | None,
) -> int:
    """Núcleo compartido: recorre un DictReader e inserta en `jugadas`."""
    if tipo_registro not in ("RIVAL", "PROPIO"):
        raise ValueError("tipo_registro debe ser 'RIVAL' o 'PROPIO'")

    conn = get_connection(db_path) if db_path else get_connection()
    init_db(db_path) if db_path else init_db()

    mapa = {col: COLUMNAS[_norm(col)] for col in reader.fieldnames or [] if _norm(col) in COLUMNAS}

    insertadas = 0
    for fila in reader:
        registro: dict = {}
        for origen, destino in mapa.items():
            valor = fila.get(origen)
            if destino in INT_COLS:
                registro[destino] = _a_int(valor)
            elif destino in ("zona_lado", "int_zona_lado"):
                registro[destino] = norm_lado(valor)
            elif destino in ("zona_profundidad", "int_zona_profundidad"):
                registro[destino] = norm_profundidad(valor)
            else:
                registro[destino] = valor

        registro["tipo_registro"] = tipo_registro
        registro["equipo"] = registro.get("equipo") or equipo
        registro["rival"] = registro.get("rival") or rival
        registro["fecha"] = registro.get("fecha") or fecha
        registro["partido_id"] = "|".join(
            str(x) for x in (registro["equipo"], registro.get("rival"), registro.get("fecha"))
        )

        cols = ", ".join(registro.keys())
        placeholders = ", ".join("?" for _ in registro)
        conn.execute(
            f"INSERT INTO jugadas ({cols}) VALUES ({placeholders})",
            list(registro.values()),
        )
        insertadas += 1

    conn.commit()
    conn.close()
    return insertadas


def importar_csv(
    csv_path: Path | str,
    *,
    tipo_registro: str,
    equipo: str,
    rival: str | None = None,
    fecha: str | None = None,
    db_path: Path | str | None = None,
) -> int:
    """Importa un CSV local. Devuelve la cantidad de filas insertadas."""
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return _importar_filas(
            reader, tipo_registro=tipo_registro, equipo=equipo,
            rival=rival, fecha=fecha, db_path=db_path,
        )


def url_csv_de_sheet(url_o_id: str, gid: str | int = 0) -> str:
    """Arma la URL de exportación CSV de un Google Sheet.

    Acepta: la URL completa del Sheet, una URL de export ya armada, o solo el ID.
    El Sheet debe estar compartido como 'cualquiera con el enlace'.
    """
    if "/export?" in url_o_id or "output=csv" in url_o_id:
        return url_o_id  # ya es una URL de export válida

    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url_o_id)
    sheet_id = m.group(1) if m else url_o_id.strip()

    m_gid = re.search(r"[#&?]gid=([0-9]+)", url_o_id)
    gid = m_gid.group(1) if m_gid else gid

    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def importar_sheet(
    url_o_id: str,
    *,
    tipo_registro: str,
    equipo: str,
    gid: str | int = 0,
    rival: str | None = None,
    fecha: str | None = None,
    db_path: Path | str | None = None,
) -> int:
    """Importa directo desde un Google Sheet publicado, sin descargar a mano."""
    url = url_csv_de_sheet(url_o_id, gid)
    req = urllib.request.Request(url, headers={"User-Agent": "flag-stats/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        texto = resp.read().decode("utf-8-sig")

    if texto.lstrip().lower().startswith("<!doctype html") or "<html" in texto[:200].lower():
        raise RuntimeError(
            "El Sheet no devolvió CSV (probablemente no es público). "
            "Compartilo como 'Cualquiera con el enlace' o publicalo a la web."
        )

    reader = csv.DictReader(io.StringIO(texto))
    return _importar_filas(
        reader, tipo_registro=tipo_registro, equipo=equipo,
        rival=rival, fecha=fecha, db_path=db_path,
    )


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Importa respuestas del form a SQLite (CSV local o Google Sheet).")
    p.add_argument("origen", help="Ruta a un CSV local, o URL/ID de un Google Sheet")
    p.add_argument("--tipo", required=True, choices=["RIVAL", "PROPIO"])
    p.add_argument("--equipo", required=True, help="Equipo dueño de las jugadas")
    p.add_argument("--gid", default="0", help="gid de la hoja dentro del Sheet (default 0)")
    p.add_argument("--rival", help="Oponente en ese partido")
    p.add_argument("--fecha", help="Fecha del partido (YYYY-MM-DD)")
    args = p.parse_args()

    es_url = args.origen.startswith("http") or "/spreadsheets/" in args.origen
    if es_url:
        n = importar_sheet(
            args.origen, tipo_registro=args.tipo, equipo=args.equipo,
            gid=args.gid, rival=args.rival, fecha=args.fecha,
        )
    else:
        n = importar_csv(
            args.origen, tipo_registro=args.tipo, equipo=args.equipo,
            rival=args.rival, fecha=args.fecha,
        )
    print(f"{n} jugadas importadas.")
