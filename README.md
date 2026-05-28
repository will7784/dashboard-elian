# Dashboard KPI Reclutamiento

Dashboard interactivo de indicadores de selección y contratación para COE Talento Humano.

## Tecnologías
- **Backend**: Python + Flask
- **Base de datos**: SQLite (modelo estrella)
- **Visualización**: Plotly (gráficos interactivos)
- **Frontend**: HTML5 + CSS3 (tema oscuro)
- **Deploy**: Railway

## Páginas
1. **Resumen Ejecutivo** — KPIs, embudo de conversión, evolución mensual, distribución regional
2. **Tiempos por Etapa** — Análisis SyC (Reclutamiento, Selección, Contratación)
3. **Productividad Psicólogos** — Rendimiento por profesional
4. **Fuentes de Reclutamiento** — Volumen y efectividad por canal
5. **Detalle & Mapa de Calor** — Explorador de datos + heatmap

## Variables de entorno (Railway)

| Variable | Descripción | Ejemplo |
|---|---|---|
| `DATABASE_PATH` | Ruta persistente de SQLite | `/data/database.db` |
| `PORT` | Puerto del servidor (Railway lo asigna automáticamente) | `5000` |

## Deploy en Railway

### 1. Volumen persistente (IMPORTANTE)
Railway reinicia los contenedores y borra el filesystem. Para persistir SQLite:
1. Ve a tu servicio en Railway → **Volumes**
2. Crea un volumen y montalo en `/data`
3. Agrega la variable de entorno: `DATABASE_PATH=/data/database.db`

### 2. Despliegue
1. Sube este repo a GitHub
2. En Railway → **New Project** → **Deploy from GitHub repo**
3. Selecciona tu repo
4. Railway detectará automáticamente el `Procfile` y `requirements.txt`
5. La primera vez que arranque, ejecutará el ETL automáticamente y creará la base de datos en el volumen

### 3. Recargar datos
Si actualizas el Excel, sube la nueva versión al repo y reinicia el servicio. El ETL se ejecutará automáticamente y regenerará la base de datos.

## Ejecución local

```bash
pip install -r requirements.txt
python etl.py      # Carga datos del Excel a SQLite
python app.py      # Inicia servidor en http://localhost:5000
```
