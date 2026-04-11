import os
import pandas as pd
import pyodbc
from datetime import datetime
import logging
import hashlib
import json
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'server': os.getenv('SQLSERVER_HOST', 'sqlsrv-retailmax-brs-dev.database.windows.net'),
    'database': 'sqldb-retailmax-brs-dev',
    'user': os.getenv('SQLSERVER_USER', 'sqladmin'),
    'password': os.getenv('SQLSERVER_PASSWORD'),
    'driver': 'SQL Server'
}

BRONZE_DIR = os.path.join(os.path.dirname(__file__), '..', 'bronze', 'data')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(OUTPUT_DIR, exist_ok=True)

COLUMNAS_PII = ['id_miembro']

def conectar_sql():
    conn_str = f'DRIVER={DB_CONFIG["driver"]};SERVER={DB_CONFIG["server"]};DATABASE={DB_CONFIG["database"]};UID={DB_CONFIG["user"]};PWD={DB_CONFIG["password"]}'
    try:
        conn = pyodbc.connect(conn_str)
        logger.info("Conexion SQL establecida")
        return conn
    except Exception as e:
        logger.error(f"Error conectando a SQL: {e}")
        raise

def crear_tablas_tracking(conn):
    cursor = conn.cursor()
    try:
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='pipeline_errors')
            CREATE TABLE pipeline_errors (
                error_id INT IDENTITY(1,1) PRIMARY KEY,
                tabla_origen NVARCHAR(100),
                row_id NVARCHAR(500),
                motivo_error NVARCHAR(1000),
                datos_json NVARCHAR(MAX),
                timestamp_error DATETIME DEFAULT GETDATE(),
                batch_id NVARCHAR(50),
                procesado BIT DEFAULT 0
            )
        """)
        
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='pipeline_quality_report')
            CREATE TABLE pipeline_quality_report (
                report_id INT IDENTITY(1,1) PRIMARY KEY,
                tabla_nombre NVARCHAR(100),
                batch_id NVARCHAR(50),
                filas_leidas INT,
                filas_limpias INT,
                duplicados_detectados INT,
                nulos_detectados INT,
                integridad_violaciones INT,
                timestamp_reporte DATETIME DEFAULT GETDATE(),
                duracion_segundos FLOAT,
                estado NVARCHAR(20)
            )
        """)
        conn.commit()
        logger.info("Tablas de tracking verificadas/creadas")
    except Exception as e:
        logger.error(f"Error creando tablas: {e}")
        raise

def registrar_error(conn, tabla, row_id, motivo, datos_dict, batch_id):
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO pipeline_errors (tabla_origen, row_id, motivo_error, datos_json, batch_id)
            VALUES (?, ?, ?, ?, ?)
        """, (tabla, str(row_id), motivo, json.dumps(datos_dict), batch_id))
        conn.commit()
    except Exception as e:
        logger.error(f"Error registrando error en BD: {e}")

def registrar_calidad(conn, tabla, batch_id, filas_leidas, filas_limpias, duplicados, nulos, fk_violaciones, duracion, estado):
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO pipeline_quality_report 
            (tabla_nombre, batch_id, filas_leidas, filas_limpias, duplicados_detectados, nulos_detectados, integridad_violaciones, duracion_segundos, estado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (tabla, batch_id, int(filas_leidas), int(filas_limpias), int(duplicados), int(nulos), int(fk_violaciones), float(duracion), estado))
        conn.commit()
        logger.info(f"Calidad registrada: {tabla} -> {estado}")
    except Exception as e:
        logger.error(f"Error registrando calidad: {e}")

def leer_datos_bronze(nombre_tabla):
    path = Path(BRONZE_DIR) / nombre_tabla
    if not path.exists():
        logger.warning(f"No existe directorio Bronze para {nombre_tabla}")
        return None
    
    archivos_parquet = list(path.rglob('*.parquet'))
    if not archivos_parquet:
        logger.warning(f"No hay archivos Parquet en {path}")
        return None
    
    logger.info(f"Leyendo {len(archivos_parquet)} archivo(s) Parquet de {nombre_tabla}")
    dfs = [pd.read_parquet(f) for f in archivos_parquet]
    return pd.concat(dfs, ignore_index=True)

def hash_sha256(valor):
    if pd.isna(valor):
        return None
    return hashlib.sha256(str(valor).encode()).hexdigest()

def masking_pii(df):
    for col in COLUMNAS_PII:
        if col in df.columns:
            df[col] = df[col].apply(hash_sha256)
    return df

def detectar_duplicados(df, tabla):
    tabla_dedup_cols = {
        'MSTR_ARTICULOS': ['art_id'],
        'MSTR_PROVEEDORES': ['id_proveedor'],
        'MSTR_TIENDAS': ['id_tienda'],
        'CRM_MIEMBROS': ['id_miembro'],
        'TRANS_VENTAS': ['id_trans'],
        'INV_STOCK_DIARIO': ['id_snapshot'],
        'POST_DEVOLUCIONES': ['id_devolucion']
    }
    
    dedup_cols = tabla_dedup_cols.get(tabla, [])
    if not dedup_cols:
        return df, 0
    
    df_before = len(df)
    df['_rn'] = df.groupby(dedup_cols, dropna=False).cumcount() + 1
    duplicados = (df['_rn'] > 1).sum()
    df = df[df['_rn'] == 1].drop('_rn', axis=1)
    
    logger.info(f"{tabla}: detectados {duplicados} duplicados (leyeron {df_before}, limpios {len(df)})")
    return df, duplicados

def validar_nulos(df, tabla):
    cols_problema = {}
    for col in df.columns:
        nulos = df[col].isna().sum()
        if nulos > 0:
            cols_problema[col] = nulos
    
    if cols_problema:
        logger.warning(f"{tabla}: nulos detectados - {cols_problema}")
    
    total_nulos = sum(cols_problema.values())
    return total_nulos

def escribir_parquet_silver(df, nombre_tabla, batch_id):
    fecha_hoy = datetime.now()
    year = fecha_hoy.strftime('%Y')
    month = fecha_hoy.strftime('%m')
    day = fecha_hoy.strftime('%d')
    
    directorio_tabla = os.path.join(OUTPUT_DIR, nombre_tabla, year, month, day)
    os.makedirs(directorio_tabla, exist_ok=True)
    
    archivo = os.path.join(directorio_tabla, f'{nombre_tabla}_clean_{batch_id}.parquet')
    df.to_parquet(archivo, index=False, compression='snappy')
    
    logger.info(f"Silver escrito: {archivo}")
    return archivo

def ejecutar_silver():
    logger.info("===== SILVER PIPELINE INICIADO =====")
    
    conn = conectar_sql()
    crear_tablas_tracking(conn)
    
    inicio = datetime.now()
    
    TABLAS = [
        'MSTR_PROVEEDORES',
        'MSTR_TIENDAS',
        'MSTR_ARTICULOS',
        'CRM_MIEMBROS',
        'TRANS_VENTAS',
        'INV_STOCK_DIARIO',
        'POST_DEVOLUCIONES'
    ]
    
    try:
        for tabla in TABLAS:
            inicio_tabla = datetime.now()
            logger.info(f"\nProcesando: {tabla}")
            
            df = leer_datos_bronze(tabla)
            if df is None or len(df) == 0:
                logger.warning(f"Saltando {tabla}: sin datos")
                continue
            
            filas_leidas = len(df)
            
            df, duplicados = detectar_duplicados(df, tabla)
            
            nulos = validar_nulos(df, tabla)
            
            df = masking_pii(df)
            
            filas_limpias = len(df)
            
            escribir_parquet_silver(df, tabla, datetime.now().strftime('%Y%m%d%H%M%S'))
            
            duracion_tabla = (datetime.now() - inicio_tabla).total_seconds()
            
            estado = 'EXITOSO' if duplicados == 0 and nulos == 0 else 'CON_ERRORES'
            
            registrar_calidad(
                conn,
                tabla,
                datetime.now().strftime('%Y%m%d%H%M%S'),
                filas_leidas,
                filas_limpias,
                duplicados,
                nulos,
                0,
                duracion_tabla,
                estado
            )
    
    finally:
        conn.close()
    
    duracion_total = (datetime.now() - inicio).total_seconds()
    logger.info(f"\n===== SILVER COMPLETADO =====")
    logger.info(f"Duracion total: {duracion_total:.2f} segundos")
    logger.info(f"Archivos en: {OUTPUT_DIR}")

if __name__ == '__main__':
    ejecutar_silver()
