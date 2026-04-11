import pyodbc
import pandas as pd
import os
from datetime import datetime
import logging

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

TABLAS = [
    'MSTR_PROVEEDORES',
    'MSTR_TIENDAS',
    'MSTR_ARTICULOS',
    'CRM_MIEMBROS',
    'TRANS_VENTAS',
    'INV_STOCK_DIARIO',
    'POST_DEVOLUCIONES'
]

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(OUTPUT_DIR, exist_ok=True)

def conectar_sql():
    conn_str = f'DRIVER={DB_CONFIG["driver"]};SERVER={DB_CONFIG["server"]};DATABASE={DB_CONFIG["database"]};UID={DB_CONFIG["user"]};PWD={DB_CONFIG["password"]}'
    try:
        conn = pyodbc.connect(conn_str)
        logger.info(f"Conexion exitosa a {DB_CONFIG['database']}")
        return conn
    except Exception as e:
        logger.error(f"Error conectando a SQL: {e}")
        raise

def leer_tabla(conn, nombre_tabla):
    query = f"SELECT * FROM {nombre_tabla}"
    try:
        df = pd.read_sql(query, conn)
        logger.info(f"Leiдо {nombre_tabla}: {len(df)} filas")
        return df
    except Exception as e:
        logger.error(f"Error leyendo {nombre_tabla}: {e}")
        raise

def agregar_metadatos(df, nombre_tabla):
    batch_id = datetime.now().strftime('%Y%m%d%H%M%S')
    ingest_timestamp = datetime.now().isoformat()
    source_system = 'sqldb-retailmax-brs-dev'
    
    df['batch_id'] = batch_id
    df['ingest_timestamp'] = ingest_timestamp
    df['source_system'] = source_system
    
    return df, batch_id

def escribir_parquet(df, nombre_tabla, batch_id):
    fecha_hoy = datetime.now()
    year = fecha_hoy.strftime('%Y')
    month = fecha_hoy.strftime('%m')
    day = fecha_hoy.strftime('%d')
    
    directorio_tabla = os.path.join(OUTPUT_DIR, nombre_tabla, year, month, day)
    os.makedirs(directorio_tabla, exist_ok=True)
    
    archivo = os.path.join(directorio_tabla, f'{nombre_tabla}_{batch_id}.parquet')
    df.to_parquet(archivo, index=False, compression='snappy')
    
    logger.info(f"Escrito: {archivo}")
    return len(df)

def ejecutar_bronze():
    logger.info("===== BRONZE PIPELINE INICIADO =====")
    
    conn = conectar_sql()
    inicio = datetime.now()
    filas_totales = 0
    
    try:
        for tabla in TABLAS:
            logger.info(f"Procesando: {tabla}")
            df = leer_tabla(conn, tabla)
            df_con_meta, batch_id = agregar_metadatos(df, tabla)
            filas_ingeridas = escribir_parquet(df_con_meta, tabla, batch_id)
            filas_totales += filas_ingeridas
    
    finally:
        conn.close()
    
    duracion = (datetime.now() - inicio).total_seconds()
    logger.info(f"===== BRONZE COMPLETADO =====")
    logger.info(f"Total filas procesadas: {filas_totales}")
    logger.info(f"Duracion: {duracion:.2f} segundos")
    logger.info(f"Archivos en: {OUTPUT_DIR}")

if __name__ == '__main__':
    ejecutar_bronze()
