"""Grilla 3x3 de la cancha: lado (eje X) x profundidad (eje Y).

  - LADO (X):         a qué lado lanzó el mariscal de campo.
  - PROFUNDIDAD (Y):  qué tan profunda fue la jugada.

Para el heatmap, la profundidad se ordena con PROFUNDO arriba y CORTO abajo
(como se ve la cancha desde atrás del ataque).
"""

from __future__ import annotations

# Orden canónico para ejes y categóricos.
LADOS = ["Izquierda", "Medio", "Derecha"]            # eje X, de izq a der
PROFUNDIDADES = ["Corto", "Medio", "Profundo"]        # eje Y, de cerca a lejos
PROFUNDIDAD_HEATMAP = ["Profundo", "Medio", "Corto"]  # filas del heatmap (lejos arriba)

# Sinónimos aceptados al importar (tolerante a abreviaturas).
_ALIAS_LADO = {
    "izquierda": "Izquierda", "izq": "Izquierda", "i": "Izquierda",
    "medio": "Medio", "centro": "Medio", "centro/medio": "Medio", "c": "Medio", "m": "Medio",
    "derecha": "Derecha", "der": "Derecha", "d": "Derecha",
}
_ALIAS_PROF = {
    "corto": "Corto", "corta": "Corto", "short": "Corto",
    "medio": "Medio", "media": "Medio", "medium": "Medio",
    "profundo": "Profundo", "profunda": "Profundo", "deep": "Profundo", "largo": "Profundo",
}


def norm_lado(valor) -> str | None:
    return _ALIAS_LADO.get(str(valor).strip().lower()) if valor else None


def norm_profundidad(valor) -> str | None:
    return _ALIAS_PROF.get(str(valor).strip().lower()) if valor else None
