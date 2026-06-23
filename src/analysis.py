"""Funciones de análisis sobre las jugadas (pandas).

Todas reciben un DataFrame ya filtrado (por equipo, partido, etc.) y devuelven
tablas listas para graficar. La idea: estas funciones no saben de Streamlit ni de
Plotly, así se pueden testear y reutilizar.
"""

from __future__ import annotations

import pandas as pd

from .db import get_connection, init_db
from .zonas import LADOS, PROFUNDIDAD_HEATMAP


def cargar_jugadas(db_path=None) -> pd.DataFrame:
    """Lee toda la tabla `jugadas` a un DataFrame.

    Garantiza el esquema primero, así funciona también en una base nueva/vacía
    (ej: primer arranque en el deploy) sin reventar.
    """
    init_db(db_path) if db_path else init_db()
    conn = get_connection(db_path) if db_path else get_connection()
    df = pd.read_sql_query("SELECT * FROM jugadas", conn)
    conn.close()
    return df


def mix_pase_corrida(df: pd.DataFrame) -> pd.DataFrame:
    """% de PASE vs CORRIDA (para torta)."""
    return (
        df["tipo_jugada"].value_counts(normalize=True).mul(100).round(1).rename("porcentaje").reset_index()
    )


def _etiqueta_down(i) -> str:
    """Down como evento discreto: 1°, 2°, 3°, 4° (nunca un decimal)."""
    return f"{int(i)}°"


def tendencia_por_down(df: pd.DataFrame) -> pd.DataFrame:
    """Conteo de tipo de jugada por down (para heatmap/barras apiladas)."""
    tabla = (
        df.dropna(subset=["intento"])
        .pivot_table(index="intento", columns="tipo_jugada", values="id", aggfunc="count", fill_value=0)
        .sort_index()
    )
    tabla.index = [_etiqueta_down(i) for i in tabla.index]  # eje categórico, sin decimales
    tabla.index.name = "Down"
    return tabla


def tendencia_down_distancia(df: pd.DataFrame, bins=(0, 5, 10, 15, 50)) -> pd.DataFrame:
    """% de PASE por down x rango de yardas para situación (heatmap de scouting)."""
    d = df.dropna(subset=["intento", "yardas_situacion"]).copy()
    if d.empty:
        return pd.DataFrame()
    etiquetas = [f"{int(a)}-{int(b)}" for a, b in zip(bins[:-1], bins[1:])]
    d["rango"] = pd.cut(d["yardas_situacion"], bins=bins, labels=etiquetas, include_lowest=True)
    d["es_pase"] = (d["tipo_jugada"] == "PASE").astype(int)
    tabla = (
        d.pivot_table(index="intento", columns="rango", values="es_pase", aggfunc="mean", observed=False)
        .mul(100)
        .round(0)
        .sort_index()
    )
    tabla.columns = tabla.columns.astype(str)  # Plotly no serializa Intervals
    tabla.index = [_etiqueta_down(i) for i in tabla.index]  # down discreto: 1°, 2°, 3°, 4°
    tabla.index.name = "Down"
    return tabla


def ranking_qb(df: pd.DataFrame) -> pd.DataFrame:
    """Ranking de QB: intentos de pase, % completos, yardas, yardas/intento."""
    pases = df[df["tipo_jugada"] == "PASE"].copy()
    if pases.empty:
        return pd.DataFrame()
    pases["completo"] = (pases["resultado"] == "COMPLETO").astype(int)
    g = pases.groupby("qb").agg(
        intentos=("id", "count"),
        completos=("completo", "sum"),
        yardas=("yardas_hechas", "sum"),
    )
    g["pct_completos"] = (g["completos"] / g["intentos"] * 100).round(1)
    g["yardas_x_intento"] = (g["yardas"] / g["intentos"]).round(1)
    return g.sort_values("yardas", ascending=False)


def ranking_wr(df: pd.DataFrame) -> pd.DataFrame:
    """Ranking de receptores: veces buscado, recepciones, % atrapadas, yardas."""
    pases = df[df["tipo_jugada"] == "PASE"].copy()
    if pases.empty:
        return pd.DataFrame()
    pases["completo"] = (pases["resultado"] == "COMPLETO").astype(int)
    g = pases.groupby("wr").agg(
        buscado=("id", "count"),
        recepciones=("completo", "sum"),
        yardas=("yardas_hechas", "sum"),
    )
    g["pct_atrapadas"] = (g["recepciones"] / g["buscado"] * 100).round(1)
    return g.sort_values("yardas", ascending=False)


def heatmap_zonas(df: pd.DataFrame, valor: str = "conteo") -> pd.DataFrame:
    """Grilla 3x3 de la cancha (profundidad x lado) para el heatmap.

    valor: 'conteo'  -> cantidad de jugadas por zona
           'yardas'  -> yardas promedio por zona
    Filas: Profundo/Medio/Corto (lejos arriba). Columnas: Izquierda/Medio/Derecha.
    """
    if df.empty:
        return pd.DataFrame()
    d = df.dropna(subset=["zona_lado", "zona_profundidad"]).copy()
    if d.empty:
        return pd.DataFrame()

    if valor == "yardas":
        tabla = d.pivot_table(
            index="zona_profundidad", columns="zona_lado",
            values="yardas_hechas", aggfunc="mean",
        ).round(1)
    else:
        tabla = d.pivot_table(
            index="zona_profundidad", columns="zona_lado",
            values="id", aggfunc="count",
        )

    # Reindexar a la grilla completa 3x3 y ordenar ejes.
    return tabla.reindex(index=PROFUNDIDAD_HEATMAP, columns=LADOS)


def _no_vacio(df: pd.DataFrame, col: str) -> pd.Series:
    """Filas donde `col` existe y tiene un valor real (no NaN ni texto vacío)."""
    if col not in df:
        return pd.Series(False, index=df.index)
    s = df[col]
    return s.notna() & (s.astype(str).str.strip() != "")


def _yardas_devueltas(d: pd.DataFrame) -> pd.Series:
    """Yardas devueltas en cada intercepción (0 si faltan las columnas de yarda)."""
    if {"int_yarda", "int_yarda_devolucion"} <= set(d.columns):
        return (d["int_yarda_devolucion"] - d["int_yarda"]).abs()
    return pd.Series(0, index=d.index)


def ranking_defensa(df: pd.DataFrame) -> pd.DataFrame:
    """Ranking defensivo por jugador: deflecciones, intercepciones, yardas devueltas.

    Robusto ante columnas defensivas ausentes (bases con esquema viejo): solo
    agrupa por una columna si realmente hay datos en ella.
    """
    if df.empty:
        return pd.DataFrame()

    partes = []

    if _no_vacio(df, "defensor_defleccion").any():
        partes.append(
            df[_no_vacio(df, "defensor_defleccion")]
            .groupby("defensor_defleccion").size().rename("deflecciones")
        )

    if _no_vacio(df, "defensor_intercepcion").any():
        inter_df = df[_no_vacio(df, "defensor_intercepcion")].copy()
        inter_df["yds_dev"] = _yardas_devueltas(inter_df)
        partes.append(
            inter_df.groupby("defensor_intercepcion").agg(
                intercepciones=("id", "count"),
                yardas_devueltas=("yds_dev", "sum"),
            )
        )

    if not partes:
        return pd.DataFrame()

    tabla = pd.concat(partes, axis=1).fillna(0)
    for col in ("deflecciones", "intercepciones", "yardas_devueltas"):
        if col not in tabla.columns:
            tabla[col] = 0
    tabla = tabla[["deflecciones", "intercepciones", "yardas_devueltas"]]
    tabla = tabla.astype({"deflecciones": int, "intercepciones": int})
    tabla.index.name = "defensor"
    return tabla.sort_values(["intercepciones", "deflecciones"], ascending=False)


def detalle_intercepciones(df: pd.DataFrame) -> pd.DataFrame:
    """Una fila por intercepción: quién, zona, yarda y hasta dónde la devolvió."""
    if not _no_vacio(df, "defensor_intercepcion").any():
        return pd.DataFrame()
    inter = df[_no_vacio(df, "defensor_intercepcion")].copy()
    inter["yardas_devueltas"] = _yardas_devueltas(inter)
    cols = {
        "defensor_intercepcion": "Defensor",
        "int_zona_lado": "Lado",
        "int_zona_profundidad": "Profundidad",
        "int_yarda": "Yarda INT",
        "int_yarda_devolucion": "Devuelta hasta",
        "yardas_devueltas": "Yardas devueltas",
    }
    presentes = [c for c in cols if c in inter.columns]
    return inter[presentes].rename(columns=cols).reset_index(drop=True)
