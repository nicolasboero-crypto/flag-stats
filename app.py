"""Dashboard de análisis de flag football (Streamlit).

Ejecutar:  streamlit run app.py

Filtra por perspectiva (rival / propio), equipo y partido, y muestra:
  - Mix pase/corrida (torta)
  - Heatmap de tendencia down x distancia (% de pase)
  - Rankings de QB y receptores
  - Efectividad por tipo de defensa
"""

from __future__ import annotations
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src import analysis
from src.importer import importar_csv

st.set_page_config(page_title="Flag Stats — Osos Polares", layout="wide")
st.title("🏈 Análisis de Flag Football")


def _sembrar_demo() -> None:
    """Carga datos de ejemplo si la base está vacía.

    Útil en el deploy (Streamlit Cloud), donde la base SQLite es temporal: así
    quien entra siempre ve la app con datos para explorar.
    """
    muestra = Path(__file__).parent / "sample_data" / "rival_ejemplo.csv"
    if muestra.exists():
        importar_csv(
            muestra, tipo_registro="RIVAL", equipo="Tiburones (demo)",
            rival="Osos Polares", fecha="2026-06-20",
        )


df = analysis.cargar_jugadas()
if df.empty:
    _sembrar_demo()
    df = analysis.cargar_jugadas()

if df.empty:
    st.warning("No hay datos todavía. Importá un CSV con `python -m src.importer ...`")
    st.stop()

# ----- Filtros -----
with st.sidebar:
    st.header("Filtros")
    tipo = st.radio("Perspectiva", ["RIVAL", "PROPIO", "Todos"], index=0)
    if tipo != "Todos":
        df = df[df["tipo_registro"] == tipo]

    equipos = ["Todos"] + sorted(df["equipo"].dropna().unique().tolist())
    equipo = st.selectbox("Equipo", equipos)
    if equipo != "Todos":
        df = df[df["equipo"] == equipo]

    partidos = ["Todos"] + sorted(df["partido_id"].dropna().unique().tolist())
    partido = st.selectbox("Partido", partidos)
    if partido != "Todos":
        df = df[df["partido_id"] == partido]

st.caption(f"{len(df)} jugadas en el filtro actual")

# ----- KPIs -----
c1, c2, c3, c4 = st.columns(4)
pases = df[df["tipo_jugada"] == "PASE"]
c1.metric("Jugadas", len(df))
c2.metric("% Pase", f"{(len(pases) / len(df) * 100):.0f}%" if len(df) else "—")
comp = (pases["resultado"] == "COMPLETO").mean() * 100 if len(pases) else 0
c3.metric("% Completos", f"{comp:.0f}%")
c4.metric("Yardas totales", int(df["yardas_hechas"].fillna(0).sum()))

# ----- Fila 1: torta + heatmap -----
col1, col2 = st.columns(2)
with col1:
    st.subheader("Mix Pase / Corrida")
    mix = analysis.mix_pase_corrida(df)
    if not mix.empty:
        fig = px.pie(mix, names="tipo_jugada", values="porcentaje", hole=0.4)
        st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Tendencia: % de Pase por Down × Distancia")
    heat = analysis.tendencia_down_distancia(df)
    if not heat.empty:
        fig = px.imshow(
            heat,
            text_auto=True,
            color_continuous_scale="RdYlGn",
            labels=dict(x="Yardas para situación", y="Down", color="% Pase"),
            aspect="auto",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Faltan datos de down/distancia.")

# ----- Fila 2: rankings -----
col3, col4 = st.columns(2)
with col3:
    st.subheader("Ranking QB")
    qb = analysis.ranking_qb(df)
    if not qb.empty:
        st.dataframe(qb, use_container_width=True)
    else:
        st.info("Sin pases.")
with col4:
    st.subheader("Ranking Receptores")
    wr = analysis.ranking_wr(df)
    if not wr.empty:
        st.dataframe(wr, use_container_width=True)
    else:
        st.info("Sin pases.")

# ----- Fila 3: heatmap de cancha 3x3 -----
st.subheader("Mapa de calor de la cancha (3×3)")
st.caption(
    "Eje X = lado del lanzamiento · Eje Y = profundidad de la jugada — "
    "Corto: 0 a 7 yardas · Medio: 8 a 15 yardas · Profundo: +15 yardas"
)
metrica = st.radio(
    "Métrica", ["conteo", "yardas"], horizontal=True,
    format_func=lambda x: "Cantidad de jugadas" if x == "conteo" else "Yardas promedio",
)
zonas = analysis.heatmap_zonas(df, valor=metrica)
if not zonas.empty:
    fig = px.imshow(
        zonas,
        text_auto=True,
        color_continuous_scale="YlOrRd",
        labels=dict(x="Lado", y="Profundidad", color=metrica),
        aspect="auto",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Faltan datos de zona (lado/profundidad).")

# ----- Fila 4: defensa -----
st.subheader("🛡️ Defensa")
defensa = analysis.ranking_defensa(df)
intercepciones = analysis.detalle_intercepciones(df)

d1, d2, d3 = st.columns(3)
d1.metric("Deflexiones", int(defensa["deflexiones"].sum()) if not defensa.empty else 0)
d2.metric("Intercepciones", len(intercepciones))
d3.metric("Yardas devueltas", int(intercepciones["Yardas devueltas"].sum()) if not intercepciones.empty else 0)

col7, col8 = st.columns(2)
with col7:
    st.markdown("**Ranking defensivo**")
    if not defensa.empty:
        st.dataframe(defensa, use_container_width=True)
    else:
        st.info("Sin jugadas defensivas registradas.")
with col8:
    st.markdown("**Detalle de intercepciones**")
    if not intercepciones.empty:
        st.dataframe(intercepciones, use_container_width=True, hide_index=True)
    else:
        st.info("Sin intercepciones registradas.")
