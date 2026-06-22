# Flag Stats — Osos Polares 🏈

Carga y análisis de estadísticas de flag football, jugada por jugada, para
scoutear rivales (tendencias, mejores jugadores, cómo prefieren jugar) y analizar
al propio equipo (**Osos Polares**).

## Cómo funciona

```
Google Form  ->  Google Sheet  ->  CSV  ->  [importer]  ->  SQLite  ->  [análisis]  ->  Dashboard
```

- **Una fila = una jugada (play).** De ahí derivamos todo.
- Dos perspectivas en la misma tabla: `RIVAL` (scouting) y `PROPIO` (Osos Polares).

## Instalación

```bash
cd flag-stats
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

1. **Inicializar la base** (opcional, el importador ya lo hace):
   ```bash
   python -m src.db
   ```

2. **Importar respuestas** del form. Dos opciones:

   **a) Desde un CSV descargado:**
   ```bash
   python -m src.importer sample_data/rival_ejemplo.csv \
       --tipo RIVAL --equipo "Tiburones" --rival "Osos Polares" --fecha 2026-06-20
   ```

   **b) Directo desde el Google Sheet** (sin descargar a mano). El Sheet de
   respuestas debe estar compartido como *"Cualquiera con el enlace"*:
   ```bash
   python -m src.importer "https://docs.google.com/spreadsheets/d/TU_ID/edit#gid=0" \
       --tipo RIVAL --equipo "Tiburones"
   ```
   Acepta la URL completa del Sheet o solo el ID. Si la hoja no es la primera,
   pasá su `gid` con `--gid`.

3. **Abrir el dashboard**:
   ```bash
   streamlit run app.py
   ```

## Modelo de datos (tabla `jugadas`)

| Campo | Origen | Nota |
|-------|--------|------|
| tipo_registro | nuevo | RIVAL / PROPIO |
| equipo | nuevo | dueño de la jugada |
| rival, fecha, partido_id | nuevo | **falta en el form actual** |
| intento | INTENTO | down 1–4 |
| situacion | SITUACIÓN | RENOVACIÓN / GOL |
| yardas_situacion | YARDAS PARA SITUACIÓN | |
| jugada_nro | JUGADA | |
| tipo_jugada | TIPO DE JUGADA | PASE / CORRIDA |
| qb | QB | dorsal |
| wr | WR | dorsal |
| resultado | RESULTADO | COMPLETO / INCOMPLETO |
| zona_lado | LADO | Izquierda / Medio / Derecha (eje X, lado del lanzamiento) |
| zona_profundidad | PROFUNDIDAD | Corto / Medio / Profundo (eje Y, profundidad de la jugada) |
| yardas_hechas | YARDAS HECHAS | |
| comentario | COMENTARIO | |

## Pendiente / próximos pasos

- [x] Grilla de cancha 3×3 (LADO × PROFUNDIDAD) con heatmap real.
- [ ] Agregar **RIVAL**, **FECHA**, **LADO** y **PROFUNDIDAD** al Google Form.
- [ ] Formulario propio para **Osos Polares** (mismo esquema, `--tipo PROPIO`).
- [ ] (Opcional) Lectura directa del CSV publicado de Google Sheets, sin descarga manual.
