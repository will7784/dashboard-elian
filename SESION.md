# Resumen de Sesion - Dashboard KPI Reclutamiento

**Fecha:** 27-28 Mayo 2026  
**Estado:** ✅ Deployado en Railway y funcionando  
**URL:** (ver en dashboard de Railway)

---

## ✅ Lo que se logro en esta sesion

1. **Pipeline ETL completo** (`etl.py`)
   - Lee `data/Indicadores 2026.xlsx` (640 filas)
   - Mapeo por indice de columna para evitar problemas de encoding
   - Carga a SQLite con esquema estrella (5 dimensiones + hechos)

2. **Flask app con 5 vistas** (`app.py`)
   - `/` - Resumen Ejecutivo (KPIs, embudo, tendencias)
   - `/tiempos` - Time to Fill, box plots, evolucion mensual
   - `/psicologos` - Productividad por psicologo
   - `/fuentes` - Fuentes de reclutamiento (bar + treemap)
   - `/detalle` - Tabla detalle + mapa de calor

3. **Tema oscuro** con CSS custom (`style.css`)
   - Sidebar, cards con glassmorphism, gradientes, animaciones
   - Plotly charts con fondo transparente para modo oscuro

4. **Deploy en Railway**
   - Repo: https://github.com/will7784/dashboard-elian
   - Procfile + runtime.txt (Python 3.11) + requirements.txt
   - Volumen persistente en `/data` para SQLite
   - Variables de entorno configuradas

5. **Fecha de corte dinamica** (ultima funcionalidad agregada)
   - Selector de fecha en el header (input type="date")
   - POST a `/set_corte` guarda en session de Flask
   - **Todas las queries SQL filtran por `fecha_recepcion <= fecha_corte`**
   - Por defecto usa la fecha maxima de la base de datos

---

## ⚙️ Configuracion en Railway (recordatorio)

| Variable | Valor actual | Notas |
|----------|-------------|-------|
| `DATABASE_PATH` | `/data/database.db` | Volumen persistente |
| `SECRET_KEY` | (tu string) | Necesaria para sesiones Flask |
| `EXCEL_PATH` | (eliminada) | Ya no se usa, etl.py calcula la ruta |

**Volumen:** Mount path `/data`

---

## 📁 Estructura del repo

```
dashboard/
  app.py              # Flask app principal
  etl.py              # Pipeline ETL
  database.db         # SQLite (se regenera si no existe)
  data/
    Indicadores 2026.xlsx   # Fuente de datos
  templates/
    base.html           # Layout con sidebar + selector de fecha
    index.html          # Resumen
    tiempos.html
    psicologos.html
    fuentes.html
    detalle.html
  static/css/
    style.css           # Tema oscuro
  Procfile
  runtime.txt         # python-3.11.11
  requirements.txt
  README.md
  SESION.md           # Este archivo
```

---

## 🔄 Como actualizar datos en el futuro

1. Reemplazar `data/Indicadores 2026.xlsx` con el nuevo archivo
2. `git add data/Indicadores\ 2026.xlsx && git commit -m "nuevos datos" && git push`
3. Railway redeploya automaticamente
4. Como el volumen persiste, el ETL **NO** se reejecuta solo

**Para forzar re-ETL:** Borrar `/data/database.db` desde la consola de Railway y reiniciar el servicio.

---

## 📝 Pendientes / Ideas para manana

- [ ] Validar que el filtro de fecha funcione correctamente en todos los graficos
- [ ] Agregar un boton "Limpiar filtro" para volver a la fecha maxima
- [ ] Exportar tablas a Excel/PDF
- [ ] Paginacion en la tabla de detalle (ahora limitada a 200 filas)
- [ ] Filtros adicionales (empresa, regional, psicologo)
- [ ] Autenticacion basica si se requiere acceso restringido
- [ ] Optimizar queries con indices si el dataset crece
- [ ] Agregar tests unitarios

---

## 🔧 Comandos utiles

```bash
# Correr local
cd dashboard
python app.py

# Verificar queries
python -c "from app import app; print('OK')"

# Forzar ETL
python -c "from etl import run_etl; run_etl()"
```
