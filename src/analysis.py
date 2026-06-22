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


def tendencia_por_down(df: pd.DataFrame) -> pd.DataFrame:
    """Conteo de tipo de jugada por down (para heatmap/barras apiladas)."""
    return (
        df.pivot_table(index="intento", columns="tipo_jugada", values="id", aggfunc="count", fill_value=0)
        .sort_index()
    )


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
    )
    tabla.columns = tabla.columns.astype(str)  # Plotly no serializa Intervals
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
