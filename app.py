import os
import sqlite3
import json
import base64
import struct
from datetime import datetime
from flask import Flask, render_template
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

# Forzar Plotly a no usar base64 en JSON
pio.json.config.default = 'json'

app = Flask(__name__)

# Railway monta el volumen en /data por convencion.
# En local usamos la carpeta del proyecto.
DB_PATH = os.environ.get('DATABASE_PATH', os.path.join(os.path.dirname(__file__), 'database.db'))
EXCEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'Indicadores 2026.xlsx')


def ensure_db():
    """Si no existe la base de datos, ejecuta el ETL."""
    if not os.path.exists(DB_PATH):
        print(f'Base de datos no encontrada en {DB_PATH}. Ejecutando ETL...')
        from etl import run_etl
        # Override la ruta de la DB para que ETL use la misma
        original_db = __import__('etl').DB_PATH
        __import__('etl').DB_PATH = DB_PATH
        run_etl()
        __import__('etl').DB_PATH = original_db
        print('ETL completado.')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def query_to_df(query, params=()):
    conn = get_db()
    df = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in df]


def decode_bdata(obj):
    """Decodifica objetos base64 de Plotly a listas de Python."""
    if isinstance(obj, dict) and 'bdata' in obj and 'dtype' in obj:
        bdata = obj['bdata']
        dtype = obj['dtype']
        padding = 4 - len(bdata) % 4
        if padding != 4:
            bdata += '=' * padding
        try:
            raw = base64.b64decode(bdata)
        except Exception:
            return []
        fmt_map = {
            'i1': 'b', 'u1': 'B',
            'i2': 'h', 'u2': 'H',
            'i4': 'i', 'u4': 'I',
            'f4': 'f', 'f8': 'd',
        }
        fmt = fmt_map.get(dtype, 'f')
        item_size = struct.calcsize('<' + fmt)
        count = len(raw) // item_size
        fmt_str = '<' + fmt * count
        try:
            return list(struct.unpack(fmt_str, raw[:item_size * count]))
        except Exception:
            return []
    elif isinstance(obj, dict):
        return {k: decode_bdata(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decode_bdata(v) for v in obj]
    return obj


def fig_to_html(fig):
    d = fig.to_dict()
    d = decode_bdata(d)
    fig_clean = go.Figure(d)
    return fig_clean.to_html(full_html=False, include_plotlyjs=False)


def apply_dark_theme(fig):
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e2e8f0', family='Inter, sans-serif'),
        title_font=dict(color='#e2e8f0'),
        legend_font=dict(color='#94a3b8'),
        xaxis=dict(gridcolor='rgba(255,255,255,0.06)', linecolor='rgba(255,255,255,0.1)', tickfont=dict(color='#94a3b8')),
        yaxis=dict(gridcolor='rgba(255,255,255,0.06)', linecolor='rgba(255,255,255,0.1)', tickfont=dict(color='#94a3b8')),
    )
    return fig


# Asegurar que la base de datos exista antes de atender peticiones
ensure_db()


@app.context_processor
def inject_now():
    return {'now': datetime.now().strftime('%d/%m/%Y')}


@app.route('/')
def index():
    conn = get_db()
    cur = conn.cursor()

    total_requis = cur.execute('SELECT COUNT(*) FROM hechos_requisicion').fetchone()[0]
    contratados = cur.execute(
        "SELECT COUNT(*) FROM hechos_requisicion WHERE estado_requisicion = 'Finalizado - Llego hasta contratacion'"
    ).fetchone()[0]
    tasa_cierre = round((contratados / total_requis * 100), 1) if total_requis else 0

    ttf = cur.execute('SELECT AVG(tiempo_total_proceso) FROM hechos_requisicion WHERE tiempo_total_proceso IS NOT NULL').fetchone()[0]
    ttf = round(ttf, 1) if ttf else 0

    efec = cur.execute('SELECT AVG(efectividad_reclutamiento) FROM hechos_requisicion WHERE efectividad_reclutamiento IS NOT NULL').fetchone()[0]
    efec = round(efec * 100, 1) if efec else 0

    embudo = cur.execute('''
        SELECT 
            AVG(hojas_vida_presentadas) as hv_presentadas,
            AVG(personas_evaluadas) as evaluadas,
            AVG(informes_entregados) as informes,
            AVG(CASE WHEN estado_requisicion = 'Finalizado - Llego hasta contratacion' THEN 1.0 ELSE 0.0 END) as contratados
        FROM hechos_requisicion
    ''').fetchone()
    base = embudo['hv_presentadas'] or 1
    vals = [
        round(embudo['hv_presentadas'] or 0, 1),
        round(embudo['evaluadas'] or 0, 1),
        round(embudo['informes'] or 0, 1),
        round(embudo['contratados'] or 0, 1)
    ]
    pcts = [100] + [round((v/base)*100, 1) for v in vals[1:]]
    embudo_data = {
        'etapas': ['HV Presentadas', 'Personas Evaluadas', 'Informes Entregados', 'Contratados'],
        'valores': vals,
        'porcentajes': pcts
    }

    estados = query_to_df('''
        SELECT estado_requisicion as estado, COUNT(*) as total
        FROM hechos_requisicion
        GROUP BY estado_requisicion
        ORDER BY total DESC
    ''')
    fig_estados = px.bar(
        estados, x='estado', y='total', text='total',
        color='estado', color_discrete_sequence=['#22c55e', '#ef4444'],
        labels={'estado': 'Estado', 'total': 'Cantidad'}
    )
    fig_estados.update_traces(textposition='outside')
    fig_estados = apply_dark_theme(fig_estados)
    fig_estados.update_layout(margin=dict(l=20, r=20, t=30, b=20), showlegend=False)

    ttf_empresa = query_to_df('''
        SELECT e.empresa, COUNT(*) as requis, AVG(h.tiempo_total_proceso) as ttf
        FROM hechos_requisicion h
        JOIN dim_empresa e ON h.fk_empresa = e.id
        WHERE h.tiempo_total_proceso IS NOT NULL
        GROUP BY e.empresa
        ORDER BY requis DESC
        LIMIT 15
    ''')
    fig_ttf = px.bar(
        ttf_empresa, x='empresa', y='ttf', text='ttf',
        labels={'empresa': 'Empresa', 'ttf': 'Días Promedio'},
        color='ttf', color_continuous_scale='Teal'
    )
    fig_ttf.update_traces(texttemplate='%{text:.1f}', textposition='outside')
    fig_ttf = apply_dark_theme(fig_ttf)
    fig_ttf.update_layout(margin=dict(l=20, r=20, t=30, b=20))

    meses = query_to_df('''
        SELECT c.anio, c.mes, c.nombre_mes, COUNT(*) as total
        FROM hechos_requisicion h
        JOIN dim_calendario c ON h.fk_calendario = c.id
        GROUP BY c.anio, c.mes, c.nombre_mes
        ORDER BY c.anio, c.mes
    ''')
    if meses:
        meses_labels = [f"{m['nombre_mes'][:3]} {m['anio']}" for m in meses]
        meses_vals = [m['total'] for m in meses]
        fig_mes = px.line(
            x=meses_labels, y=meses_vals, markers=True,
            labels={'x': 'Mes', 'y': 'Requisiciones'}
        )
        fig_mes.update_traces(line_color='#00b4d8', marker=dict(size=10, color='#0077b6'))
        fig_mes = apply_dark_theme(fig_mes)
        fig_mes.update_layout(margin=dict(l=20, r=20, t=30, b=20))
        graph_mes = fig_to_html(fig_mes)
    else:
        graph_mes = None

    emp_data = query_to_df('''
        SELECT e.empresa, COUNT(*) as total
        FROM hechos_requisicion h
        JOIN dim_empresa e ON h.fk_empresa = e.id
        GROUP BY e.empresa
        ORDER BY total DESC
        LIMIT 12
    ''')
    fig_emp = px.bar(
        emp_data, y='empresa', x='total', orientation='h',
        color='total', color_continuous_scale='Blues',
        labels={'empresa': '', 'total': 'Requisiciones'}
    )
    fig_emp = apply_dark_theme(fig_emp)
    fig_emp.update_layout(margin=dict(l=20, r=20, t=30, b=20), yaxis=dict(autorange="reversed"))

    reg_data = query_to_df('''
        SELECT e.regional, COUNT(*) as total
        FROM hechos_requisicion h
        JOIN dim_empresa e ON h.fk_empresa = e.id
        WHERE e.regional IS NOT NULL
        GROUP BY e.regional
        ORDER BY total DESC
    ''')
    fig_reg = px.pie(reg_data, names='regional', values='total', hole=0.5,
                     color_discrete_sequence=px.colors.sequential.Teal)
    fig_reg = apply_dark_theme(fig_reg)
    fig_reg.update_layout(margin=dict(l=20, r=20, t=30, b=20), showlegend=True, legend=dict(orientation='h', yanchor='bottom', y=-0.2))

    conn.close()

    return render_template('index.html',
                           total_requis=total_requis,
                           contratados=contratados,
                           tasa_cierre=tasa_cierre,
                           ttf=ttf,
                           efec=efec,
                           embudo=embudo_data,
                           graph_ttf=fig_to_html(fig_ttf),
                           graph_mes=graph_mes,
                           graph_emp=fig_to_html(fig_emp),
                           graph_reg=fig_to_html(fig_reg),
                           graph_estados=fig_to_html(fig_estados),
                           zip=zip, max=max)


@app.route('/tiempos')
def tiempos():
    conn = get_db()
    cur = conn.cursor()

    proms = cur.execute('''
        SELECT 
            AVG(oportunidad_reclutamiento) as rec,
            AVG(oportunidad_seleccion) as sel,
            AVG(oportunidad_contratacion) as cont,
            AVG(tiempo_total_proceso) as ttp
        FROM hechos_requisicion
    ''').fetchone()

    promedios = {
        'reclutamiento': round(proms['rec'] or 0, 1),
        'seleccion': round(proms['sel'] or 0, 1),
        'contratacion': round(proms['cont'] or 0, 1),
        'total': round(proms['ttp'] or 0, 1)
    }

    box_data = query_to_df('''
        SELECT e.empresa, h.tiempo_total_proceso as ttp
        FROM hechos_requisicion h
        JOIN dim_empresa e ON h.fk_empresa = e.id
        WHERE h.tiempo_total_proceso IS NOT NULL
    ''')
    df_box = {}
    for row in box_data:
        df_box.setdefault(row['empresa'], []).append(row['ttp'])
    top_emp = sorted(df_box.keys(), key=lambda x: len(df_box[x]), reverse=True)[:10]
    fig_box = go.Figure()
    for emp in top_emp:
        fig_box.add_trace(go.Box(y=df_box[emp], name=emp[:15], boxpoints='outliers'))
    fig_box = apply_dark_theme(fig_box)
    fig_box.update_layout(
        title='Distribución de Time to Fill por Empresa',
        margin=dict(l=20, r=20, t=50, b=20),
        yaxis_title='Días'
    )

    ind_mes = query_to_df('''
        SELECT c.anio, c.mes, c.nombre_mes,
            AVG(h.oportunidad_reclutamiento) as rec,
            AVG(h.oportunidad_seleccion) as sel,
            AVG(h.oportunidad_contratacion) as cont,
            AVG(h.tiempo_total_proceso) as ttp
        FROM hechos_requisicion h
        JOIN dim_calendario c ON h.fk_calendario = c.id
        GROUP BY c.anio, c.mes, c.nombre_mes
        ORDER BY c.anio, c.mes
    ''')
    if ind_mes:
        labels = [f"{m['nombre_mes'][:3]} {m['anio']}" for m in ind_mes]
        fig_ind = go.Figure()
        fig_ind.add_trace(go.Scatter(x=labels, y=[m['rec'] for m in ind_mes], mode='lines+markers', name='Reclutamiento', line=dict(color='#00b4d8')))
        fig_ind.add_trace(go.Scatter(x=labels, y=[m['sel'] for m in ind_mes], mode='lines+markers', name='Selección', line=dict(color='#f4a261')))
        fig_ind.add_trace(go.Scatter(x=labels, y=[m['cont'] for m in ind_mes], mode='lines+markers', name='Contratación', line=dict(color='#2a9d8f')))
        fig_ind.add_trace(go.Scatter(x=labels, y=[m['ttp'] for m in ind_mes], mode='lines+markers', name='Total Proceso', line=dict(color='#e76f51', width=3)))
        fig_ind = apply_dark_theme(fig_ind)
        fig_ind.update_layout(
            margin=dict(l=20, r=20, t=30, b=20),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
        )
        graph_ind = fig_to_html(fig_ind)
    else:
        graph_ind = None

    tabla = query_to_df('''
        SELECT 
            e.empresa,
            COUNT(*) as total,
            ROUND(AVG(h.oportunidad_reclutamiento),1) as rec,
            ROUND(AVG(h.oportunidad_seleccion),1) as sel,
            ROUND(AVG(h.oportunidad_contratacion),1) as cont,
            ROUND(AVG(h.tiempo_total_proceso),1) as ttp,
            ROUND(AVG(h.efectividad_reclutamiento)*100,1) as efec
        FROM hechos_requisicion h
        JOIN dim_empresa e ON h.fk_empresa = e.id
        GROUP BY e.empresa
        ORDER BY total DESC
        LIMIT 20
    ''')

    conn.close()
    return render_template('tiempos.html',
                           promedios=promedios,
                           graph_box=fig_to_html(fig_box),
                           graph_ind=graph_ind,
                           tabla=tabla)


@app.route('/psicologos')
def psicologos():
    conn = get_db()
    cur = conn.cursor()

    prod = query_to_df('''
        SELECT p.psicologo, COUNT(*) as total,
            ROUND(AVG(h.efectividad_reclutamiento)*100,1) as efec,
            ROUND(AVG(h.tiempo_total_proceso),1) as ttp
        FROM hechos_requisicion h
        JOIN dim_psicologo p ON h.fk_psicologo = p.id
        GROUP BY p.psicologo
        ORDER BY total DESC
    ''')

    fig_prod = px.bar(
        prod, y='psicologo', x='total', orientation='h',
        color='efec', color_continuous_scale='RdYlGn',
        text='total',
        labels={'psicologo': '', 'total': 'Requisiciones'}
    )
    fig_prod.update_traces(textposition='outside')
    fig_prod = apply_dark_theme(fig_prod)
    fig_prod.update_layout(margin=dict(l=20, r=20, t=30, b=20), yaxis=dict(autorange="reversed"))

    fig_scatter = px.scatter(
        prod, x='ttp', y='efec', size='total', text='psicologo',
        color='total', color_continuous_scale='Teal',
        labels={'ttp': 'Time to Fill (días)', 'efec': 'Efectividad (%)'}
    )
    fig_scatter.update_traces(textposition='top center')
    fig_scatter = apply_dark_theme(fig_scatter)
    fig_scatter.update_layout(margin=dict(l=20, r=20, t=30, b=20))

    conn.close()
    return render_template('psicologos.html',
                           prod=prod,
                           graph_prod=fig_to_html(fig_prod),
                           graph_scatter=fig_to_html(fig_scatter))


@app.route('/fuentes')
def fuentes():
    conn = get_db()
    cur = conn.cursor()

    fuentes_data = query_to_df('''
        SELECT f.fuente, COUNT(*) as total,
            ROUND(AVG(h.efectividad_reclutamiento)*100,1) as efec
        FROM hechos_requisicion h
        JOIN dim_fuente f ON h.fk_fuente = f.id
        GROUP BY f.fuente
        ORDER BY total DESC
    ''')

    fig_fuentes = px.bar(
        fuentes_data, x='fuente', y='total',
        color='efec', color_continuous_scale='Viridis',
        text='total',
        labels={'fuente': 'Fuente', 'total': 'Requisiciones'}
    )
    fig_fuentes.update_traces(textposition='outside')
    fig_fuentes = apply_dark_theme(fig_fuentes)
    fig_fuentes.update_layout(margin=dict(l=20, r=20, t=30, b=20))

    fig_tree = px.treemap(
        fuentes_data, path=['fuente'], values='total', color='efec',
        color_continuous_scale='RdYlGn',
        labels={'total': 'Requisiciones'}
    )
    fig_tree = apply_dark_theme(fig_tree)
    fig_tree.update_layout(margin=dict(l=20, r=20, t=30, b=20))

    conn.close()
    return render_template('fuentes.html',
                           fuentes=fuentes_data,
                           graph_fuentes=fig_to_html(fig_fuentes),
                           graph_tree=fig_to_html(fig_tree))


@app.route('/detalle')
def detalle():
    conn = get_db()
    cur = conn.cursor()

    data = query_to_df('''
        SELECT 
            h.numero_requisicion,
            e.empresa, e.regional, e.ciudad,
            c.cargo, c.tipo_cargo, c.tipo_servicio,
            p.psicologo,
            f.fuente,
            h.estado_requisicion,
            h.efectividad_reclutamiento,
            h.tiempo_total_proceso,
            h.fecha_firma_contrato
        FROM hechos_requisicion h
        JOIN dim_empresa e ON h.fk_empresa = e.id
        JOIN dim_cargo c ON h.fk_cargo = c.id
        LEFT JOIN dim_psicologo p ON h.fk_psicologo = p.id
        LEFT JOIN dim_fuente f ON h.fk_fuente = f.id
        ORDER BY h.numero_requisicion DESC
        LIMIT 200
    ''')

    heat = query_to_df('''
        SELECT e.empresa, c.nombre_mes, COUNT(*) as total
        FROM hechos_requisicion h
        JOIN dim_empresa e ON h.fk_empresa = e.id
        JOIN dim_calendario c ON h.fk_calendario = c.id
        GROUP BY e.empresa, c.nombre_mes
    ''')
    if heat:
        import pandas as pd
        dfh = pd.DataFrame(heat)
        pivot = dfh.pivot(index='empresa', columns='nombre_mes', values='total').fillna(0)
        meses_ord = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
        cols = [m for m in meses_ord if m in pivot.columns]
        pivot = pivot[cols]
        fig_heat = px.imshow(
            pivot, text_auto=True, aspect='auto',
            color_continuous_scale='YlGnBu',
            labels={'x': 'Mes', 'y': 'Empresa', 'color': 'Requisiciones'}
        )
        fig_heat = apply_dark_theme(fig_heat)
        fig_heat.update_layout(margin=dict(l=20, r=20, t=30, b=20))
        graph_heat = fig_to_html(fig_heat)
    else:
        graph_heat = None

    conn.close()
    return render_template('detalle.html', data=data, graph_heat=graph_heat)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
