import pandas as pd
import sqlite3
import os
from datetime import datetime

DB_PATH = os.environ.get('DATABASE_PATH', os.path.join(os.path.dirname(__file__), 'database.db')).strip()
EXCEL_PATH = os.environ.get('EXCEL_PATH', os.path.join(os.path.dirname(__file__), 'data', 'Indicadores 2026.xlsx')).strip()

# Mapeo por índice de columna para evitar problemas de encoding
COLUMN_NAMES = [
    'Numero_Requisicion', 'Empresa', 'Unidad', 'Fecha_Recepcion',
    'Fecha_aprobacion_requisicion', 'Regional', 'Ciudad', 'Tipo_Servicio',
    'Cargo_Solicitado', 'Tipo_Cargo', 'Psicologo_Responsable', 'Personas_Solicitadas',
    'Estado_Requisicion', 'Fecha_Afinamiento_Perfil', 'hojas_vida_presentadas',
    'Pertenece_Primera_Terna', 'Fecha_entrega_hv_cliente', 'Fecha_aprobacion_hv_cliente',
    'hojas_vida_aprobadas', 'Fecha_envio_perfil', 'Fecha_publicacion_concurso',
    'Fecha_entrega_matriz', 'Fecha_notif_prueba_tecnica', 'Fecha_aplicacion_prueba_tecnica',
    'Fecha_envio_prueba_tecnica', 'Fecha_notif_proceso_seleccion', 'personas_evaluadas',
    'informes_entregados', 'referencias', 'Fecha_entrega_informe_cliente',
    'Fecha_notif_cliente_seleccionada', 'Fecha_solicitud_contratacion', 'Fecha_firma_contrato',
    'Fecha_Ingreso', 'Mes', 'Candidato_contratado', 'Observacion',
    'Efectividad_reclutamiento', 'Oportunidad_reclutamiento', 'Oportunidad_proceso_seleccion',
    'Dias_descontar_seleccion', 'Oportunidad_Seleccion', 'Oportunidad_proceso_contratacion',
    'Dias_descontar_contratacion', 'Oportunidad_Contratacion', 'Tiempo_Total_Proceso',
    'Oportunidad_SyC', 'Fuente_Reclutamiento', 'Ultima_empresa',
    'Candidato_1', 'Candidato_2', 'Candidato_3', 'Candidato_4', 'Candidato_5'
]

def parse_date(val):
    if pd.isna(val):
        return None
    if isinstance(val, str):
        v = val.strip()
        if v in ['', '0000-00-00', '00:00:00', 'NaT']:
            return None
        try:
            return pd.to_datetime(v).strftime('%Y-%m-%d')
        except:
            return None
    try:
        dt = pd.to_datetime(val)
        if pd.isna(dt):
            return None
        return dt.strftime('%Y-%m-%d')
    except:
        return None

def parse_float(val):
    if pd.isna(val):
        return None
    try:
        return float(val)
    except:
        return None

def parse_int(val):
    if pd.isna(val):
        return None
    try:
        return int(float(val))
    except:
        return None

def run_etl():
    if not os.path.exists(EXCEL_PATH):
        raise FileNotFoundError(f'No se encontró el archivo Excel: {EXCEL_PATH} (abs: {os.path.abspath(EXCEL_PATH)})')
    print('Leyendo Excel...')
    xl = pd.ExcelFile(EXCEL_PATH)
    df = pd.read_excel(xl, sheet_name='Requisiciones')
    # Renombrar por índice
    rename_map = {old: new for old, new in zip(df.columns, COLUMN_NAMES)}
    df = df.rename(columns=rename_map)
    
    print(f'Filas leidas: {len(df)}')
    print('Columnas renombradas:', df.columns.tolist()[:10], '...')
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.executescript('''
    DROP TABLE IF EXISTS hechos_requisicion;
    DROP TABLE IF EXISTS dim_empresa;
    DROP TABLE IF EXISTS dim_cargo;
    DROP TABLE IF EXISTS dim_psicologo;
    DROP TABLE IF EXISTS dim_fuente;
    DROP TABLE IF EXISTS dim_calendario;
    
    CREATE TABLE dim_empresa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa TEXT,
        regional TEXT,
        ciudad TEXT,
        unidad TEXT
    );
    
    CREATE TABLE dim_cargo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cargo TEXT,
        tipo_cargo TEXT,
        tipo_servicio TEXT
    );
    
    CREATE TABLE dim_psicologo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        psicologo TEXT
    );
    
    CREATE TABLE dim_fuente (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fuente TEXT
    );
    
    CREATE TABLE dim_calendario (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        anio INTEGER,
        mes INTEGER,
        nombre_mes TEXT,
        trimestre INTEGER
    );
    
    CREATE TABLE hechos_requisicion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_requisicion INTEGER,
        fk_empresa INTEGER,
        fk_cargo INTEGER,
        fk_psicologo INTEGER,
        fk_fuente INTEGER,
        fk_calendario INTEGER,
        fecha_recepcion TEXT,
        fecha_aprobacion_requisicion TEXT,
        fecha_afinamiento_perfil TEXT,
        fecha_entrega_hv_cliente TEXT,
        fecha_aprobacion_hv_cliente TEXT,
        fecha_envio_perfil TEXT,
        fecha_publicacion_concurso TEXT,
        fecha_entrega_matriz TEXT,
        fecha_notif_prueba_tecnica TEXT,
        fecha_aplicacion_prueba_tecnica TEXT,
        fecha_envio_prueba_tecnica TEXT,
        fecha_notif_proceso_seleccion TEXT,
        fecha_entrega_informe_cliente TEXT,
        fecha_notif_cliente_seleccionada TEXT,
        fecha_solicitud_contratacion TEXT,
        fecha_firma_contrato TEXT,
        fecha_ingreso TEXT,
        personas_solicitadas INTEGER,
        estado_requisicion TEXT,
        hojas_vida_presentadas INTEGER,
        pertenece_primera_terna TEXT,
        hojas_vida_aprobadas INTEGER,
        personas_evaluadas INTEGER,
        informes_entregados INTEGER,
        referencias INTEGER,
        candidato_contratado TEXT,
        observacion TEXT,
        efectividad_reclutamiento REAL,
        oportunidad_reclutamiento REAL,
        oportunidad_proceso_seleccion REAL,
        dias_descontar_seleccion REAL,
        oportunidad_seleccion REAL,
        oportunidad_proceso_contratacion REAL,
        dias_descontar_contratacion REAL,
        oportunidad_contratacion REAL,
        tiempo_total_proceso REAL,
        oportunidad_syc REAL,
        candidato_1 TEXT,
        candidato_2 TEXT,
        candidato_3 TEXT,
        candidato_4 TEXT,
        candidato_5 TEXT,
        mes INTEGER
    );
    ''')
    
    # Dimensiones
    empresas = df[['Empresa', 'Regional', 'Ciudad', 'Unidad']].drop_duplicates().dropna(subset=['Empresa'])
    for _, row in empresas.iterrows():
        cur.execute('INSERT INTO dim_empresa (empresa, regional, ciudad, unidad) VALUES (?,?,?,?)',
                    (row['Empresa'], row['Regional'], row['Ciudad'], row['Unidad']))
    
    cargos = df[['Cargo_Solicitado', 'Tipo_Cargo', 'Tipo_Servicio']].drop_duplicates().dropna(subset=['Cargo_Solicitado'])
    for _, row in cargos.iterrows():
        cur.execute('INSERT INTO dim_cargo (cargo, tipo_cargo, tipo_servicio) VALUES (?,?,?)',
                    (row['Cargo_Solicitado'], row['Tipo_Cargo'], row['Tipo_Servicio']))
    
    psicologos = df[['Psicologo_Responsable']].drop_duplicates().dropna()
    for _, row in psicologos.iterrows():
        cur.execute('INSERT INTO dim_psicologo (psicologo) VALUES (?)', (row['Psicologo_Responsable'],))
    
    fuentes = df[['Fuente_Reclutamiento']].drop_duplicates().dropna()
    for _, row in fuentes.iterrows():
        cur.execute('INSERT INTO dim_fuente (fuente) VALUES (?)', (row['Fuente_Reclutamiento'],))
    
    # Calendario basado en fechas de firma de contrato válidas
    fechas_raw = df['Fecha_firma_contrato'].apply(parse_date).dropna()
    fechas = sorted(set(fechas_raw))
    for f in fechas:
        d = datetime.strptime(f, '%Y-%m-%d')
        nombre_mes = d.strftime('%B').capitalize()
        trimestre = (d.month - 1) // 3 + 1
        cur.execute('INSERT INTO dim_calendario (fecha, anio, mes, nombre_mes, trimestre) VALUES (?,?,?,?,?)',
                    (f, d.year, d.month, nombre_mes, trimestre))
    
    conn.commit()
    
    # Lookups
    cur.execute('SELECT id, empresa FROM dim_empresa')
    emp_map = {r[1]: r[0] for r in cur.fetchall()}
    cur.execute('SELECT id, cargo FROM dim_cargo')
    cargo_map = {r[1]: r[0] for r in cur.fetchall()}
    cur.execute('SELECT id, psicologo FROM dim_psicologo')
    psic_map = {r[1]: r[0] for r in cur.fetchall()}
    cur.execute('SELECT id, fuente FROM dim_fuente')
    fuente_map = {r[1]: r[0] for r in cur.fetchall()}
    cur.execute('SELECT id, fecha FROM dim_calendario')
    cal_map = {r[1]: r[0] for r in cur.fetchall()}
    
    # Insertar hechos
    for _, row in df.iterrows():
        fk_emp = emp_map.get(row['Empresa'])
        fk_car = cargo_map.get(row['Cargo_Solicitado'])
        fk_psi = psic_map.get(row['Psicologo_Responsable'])
        fk_fue = fuente_map.get(row['Fuente_Reclutamiento'])
        fc = parse_date(row.get('Fecha_firma_contrato'))
        fk_cal = cal_map.get(fc) if fc else None
        
        cur.execute('''
        INSERT INTO hechos_requisicion (
            numero_requisicion, fk_empresa, fk_cargo, fk_psicologo, fk_fuente, fk_calendario,
            fecha_recepcion, fecha_aprobacion_requisicion, fecha_afinamiento_perfil,
            fecha_entrega_hv_cliente, fecha_aprobacion_hv_cliente, fecha_envio_perfil,
            fecha_publicacion_concurso, fecha_entrega_matriz, fecha_notif_prueba_tecnica,
            fecha_aplicacion_prueba_tecnica, fecha_envio_prueba_tecnica, fecha_notif_proceso_seleccion,
            fecha_entrega_informe_cliente, fecha_notif_cliente_seleccionada, fecha_solicitud_contratacion,
            fecha_firma_contrato, fecha_ingreso, personas_solicitadas, estado_requisicion,
            hojas_vida_presentadas, pertenece_primera_terna, hojas_vida_aprobadas,
            personas_evaluadas, informes_entregados, referencias, candidato_contratado,
            observacion, efectividad_reclutamiento, oportunidad_reclutamiento,
            oportunidad_proceso_seleccion, dias_descontar_seleccion, oportunidad_seleccion,
            oportunidad_proceso_contratacion, dias_descontar_contratacion, oportunidad_contratacion,
            tiempo_total_proceso, oportunidad_syc, candidato_1, candidato_2, candidato_3, candidato_4, candidato_5, mes
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            parse_int(row.get('Numero_Requisicion')),
            fk_emp, fk_car, fk_psi, fk_fue, fk_cal,
            parse_date(row.get('Fecha_Recepcion')),
            parse_date(row.get('Fecha_aprobacion_requisicion')),
            parse_date(row.get('Fecha_Afinamiento_Perfil')),
            parse_date(row.get('Fecha_entrega_hv_cliente')),
            parse_date(row.get('Fecha_aprobacion_hv_cliente')),
            parse_date(row.get('Fecha_envio_perfil')),
            parse_date(row.get('Fecha_publicacion_concurso')),
            parse_date(row.get('Fecha_entrega_matriz')),
            parse_date(row.get('Fecha_notif_prueba_tecnica')),
            parse_date(row.get('Fecha_aplicacion_prueba_tecnica')),
            parse_date(row.get('Fecha_envio_prueba_tecnica')),
            parse_date(row.get('Fecha_notif_proceso_seleccion')),
            parse_date(row.get('Fecha_entrega_informe_cliente')),
            parse_date(row.get('Fecha_notif_cliente_seleccionada')),
            parse_date(row.get('Fecha_solicitud_contratacion')),
            fc,
            parse_date(row.get('Fecha_Ingreso')),
            parse_int(row.get('Personas_Solicitadas')),
            row['Estado_Requisicion'] if pd.notna(row.get('Estado_Requisicion')) else None,
            parse_int(row.get('hojas_vida_presentadas')),
            row['Pertenece_Primera_Terna'] if pd.notna(row.get('Pertenece_Primera_Terna')) else None,
            parse_int(row.get('hojas_vida_aprobadas')),
            parse_int(row.get('personas_evaluadas')),
            parse_int(row.get('informes_entregados')),
            parse_int(row.get('referencias')),
            row['Candidato_contratado'] if pd.notna(row.get('Candidato_contratado')) else None,
            row['Observacion'] if pd.notna(row.get('Observacion')) else None,
            parse_float(row.get('Efectividad_reclutamiento')),
            parse_float(row.get('Oportunidad_reclutamiento')),
            parse_float(row.get('Oportunidad_proceso_seleccion')),
            parse_float(row.get('Dias_descontar_seleccion')),
            parse_float(row.get('Oportunidad_Seleccion')),
            parse_float(row.get('Oportunidad_proceso_contratacion')),
            parse_float(row.get('Dias_descontar_contratacion')),
            parse_float(row.get('Oportunidad_Contratacion')),
            parse_float(row.get('Tiempo_Total_Proceso')),
            parse_float(row.get('Oportunidad_SyC')),
            row['Candidato_1'] if pd.notna(row.get('Candidato_1')) else None,
            row['Candidato_2'] if pd.notna(row.get('Candidato_2')) else None,
            row['Candidato_3'] if pd.notna(row.get('Candidato_3')) else None,
            row['Candidato_4'] if pd.notna(row.get('Candidato_4')) else None,
            row['Candidato_5'] if pd.notna(row.get('Candidato_5')) else None,
            parse_int(row.get('Mes'))
        ))
    
    conn.commit()
    conn.close()
    print('ETL completado. Base de datos creada en', DB_PATH)

if __name__ == '__main__':
    run_etl()
