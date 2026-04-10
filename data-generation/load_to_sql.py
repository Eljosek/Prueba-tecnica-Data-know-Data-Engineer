#!/usr/bin/env python3
"""
load_to_sql.py - Carga de datos CSV a Azure SQL Database
Proyecto: RetailMax - Data Platform
Usa pyodbc directo (sin SQLAlchemy) para compatibilidad con driver legacy ODBC.
"""

import os
import sys
import logging
import pyodbc
import pandas as pd
from pathlib import Path
from datetime import datetime

# --- Logging -----------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# --- Conexion ----------------------------------------------------------------
SERVER   = "sqlsrv-retailmax-brs-dev.database.windows.net"
DATABASE = "sqldb-retailmax-brs-dev"

# --- Tablas a cargar (orden respeta dependencias implicitas) -----------------
TABLAS = [
    {"nombre": "MSTR_PROVEEDORES",  "archivo": "MSTR_PROVEEDORES.csv",  "chunksize": 5_000},
    {"nombre": "MSTR_TIENDAS",      "archivo": "MSTR_TIENDAS.csv",      "chunksize": 5_000},
    {"nombre": "MSTR_ARTICULOS",    "archivo": "MSTR_ARTICULOS.csv",    "chunksize": 5_000},
    {"nombre": "CRM_MIEMBROS",      "archivo": "CRM_MIEMBROS.csv",      "chunksize": 5_000},
    {"nombre": "TRANS_VENTAS",      "archivo": "TRANS_VENTAS.csv",      "chunksize": 10_000},
    {"nombre": "INV_STOCK_DIARIO",  "archivo": "INV_STOCK_DIARIO.csv",  "chunksize": 10_000},
    {"nombre": "POST_DEVOLUCIONES", "archivo": "POST_DEVOLUCIONES.csv", "chunksize": 5_000},
]

CONTEOS_ESPERADOS = {
    "MSTR_PROVEEDORES":    800,
    "MSTR_TIENDAS":        150,
    "MSTR_ARTICULOS":    5_000,
    "CRM_MIEMBROS":     50_000,
    "TRANS_VENTAS":  1_000_000,
    "INV_STOCK_DIARIO": 750_000,
    "POST_DEVOLUCIONES":  50_000,
}


def validar_env():
    usuario  = os.environ.get("SQLSERVER_USER")
    password = os.environ.get("SQLSERVER_PASSWORD")
    if not usuario:
        raise EnvironmentError("Variable de entorno SQLSERVER_USER no definida.")
    if not password:
        raise EnvironmentError("Variable de entorno SQLSERVER_PASSWORD no definida.")
    return usuario, password


def crear_conexion(usuario: str, password: str) -> pyodbc.Connection:
    drivers_pref = [
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server",
        "SQL Server",
    ]
    disponibles = set(pyodbc.drivers())
    driver = next((d for d in drivers_pref if d in disponibles), None)
    if not driver:
        raise RuntimeError(f"No se encontro driver ODBC compatible. Disponibles: {list(disponibles)}")

    logger.info(f"Driver ODBC      : {driver}")
    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        f"UID={usuario};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )
    conn = pyodbc.connect(conn_str, timeout=30)
    conn.autocommit = False
    return conn


def inferir_tipo_sql(serie: pd.Series) -> str:
    dtype = serie.dtype
    if pd.api.types.is_integer_dtype(dtype):
        return "BIGINT"
    if pd.api.types.is_float_dtype(dtype):
        return "FLOAT"
    if pd.api.types.is_bool_dtype(dtype):
        return "BIT"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "DATETIME2(0)"
    sample = serie.dropna()
    if len(sample) == 0:
        return "NVARCHAR(255)"
    max_len = int(sample.astype(str).str.len().max())
    if max_len > 4000:
        return "NVARCHAR(MAX)"
    return f"NVARCHAR({min(max(max_len * 2, 50), 4000)})"


def preparar_tabla(conn: pyodbc.Connection, nombre: str, df: pd.DataFrame):
    cursor = conn.cursor()
    cursor.execute(
        f"IF OBJECT_ID(N'dbo.[{nombre}]', N'U') IS NOT NULL DROP TABLE dbo.[{nombre}]"
    )
    cols_ddl = ", ".join(f"[{col}] {inferir_tipo_sql(df[col])} NULL" for col in df.columns)
    cursor.execute(f"CREATE TABLE dbo.[{nombre}] ({cols_ddl})")
    conn.commit()
    logger.info(f"  Tabla dbo.[{nombre}] creada ({len(df.columns)} columnas)")


def normalizar_df(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].astype(object).where(df[col].notnull(), None)
        elif pd.api.types.is_float_dtype(df[col]):
            df[col] = df[col].astype(object).where(df[col].notnull(), None)
        elif pd.api.types.is_integer_dtype(df[col]):
            # convierte enteros a Python int para evitar np.int64 que pyodbc puede rechazar
            df[col] = df[col].astype(object)
        else:
            df[col] = df[col].astype(object).where(df[col].notnull(), None)
    return df


def cargar_tabla(
    conn: pyodbc.Connection, nombre: str, ruta_csv: Path, chunksize: int
) -> int:
    logger.info(f"Iniciando carga de {nombre} ...")
    df = pd.read_csv(ruta_csv, low_memory=False)
    logger.info(f"  Filas leidas del CSV : {len(df):,}")

    preparar_tabla(conn, nombre, df)
    df = normalizar_df(df)

    cols_sql   = ", ".join(f"[{c}]" for c in df.columns)
    marks      = ", ".join("?" for _ in df.columns)
    insert_sql = f"INSERT INTO dbo.[{nombre}] ({cols_sql}) VALUES ({marks})"

    cursor = conn.cursor()
    cursor.fast_executemany = True

    total    = len(df)
    cargados = 0

    for inicio in range(0, total, chunksize):
        chunk  = df.iloc[inicio : inicio + chunksize]
        params = [list(row) for row in chunk.itertuples(index=False, name=None)]
        cursor.executemany(insert_sql, params)
        conn.commit()
        cargados += len(chunk)
        pct = cargados / total * 100
        logger.info(f"  {nombre} : {cargados:,}/{total:,} filas ({pct:.1f}%)")

    logger.info(f"  OK - {nombre} completada ({cargados:,} filas)")
    return cargados


def verificar_conteos(conn: pyodbc.Connection):
    logger.info("=" * 60)
    logger.info("Verificacion de conteos finales")
    logger.info("=" * 60)
    cursor = conn.cursor()
    ok = True
    for tabla, esperado in CONTEOS_ESPERADOS.items():
        cursor.execute(f"SELECT COUNT(*) FROM dbo.[{tabla}]")
        real  = cursor.fetchone()[0]
        diff  = abs(real - esperado)
        estado = "OK" if diff <= esperado * 0.01 else "DIFERENCIA"
        logger.info(
            f"  {tabla:<25} esperado={esperado:>9,}  real={real:>9,}  {estado}"
        )
        if estado != "OK":
            ok = False
    return ok


def main():
    logger.info("=" * 60)
    logger.info("RetailMax - Carga de datos a Azure SQL Database")
    logger.info("=" * 60)

    usuario, password = validar_env()

    logger.info(f"Servidor destino : {SERVER}")
    logger.info(f"Base de datos    : {DATABASE}")

    conn = crear_conexion(usuario, password)

    cur = conn.cursor()
    cur.execute("SELECT @@VERSION")
    version = cur.fetchone()[0].split("\n")[0].strip()
    logger.info(f"Conexion exitosa. SQL Server: {version}")

    directorio = Path(__file__).parent / "output"
    logger.info(f"Directorio de datos: {directorio}")

    inicio_total = datetime.now()
    resultados   = {}
    errores      = []

    for cfg in TABLAS:
        nombre = cfg["nombre"]
        ruta   = directorio / cfg["archivo"]
        chunk  = cfg["chunksize"]

        if not ruta.exists():
            logger.warning(f"  OMITIDA - Archivo no encontrado: {ruta}")
            continue

        t0 = datetime.now()
        try:
            filas   = cargar_tabla(conn, nombre, ruta, chunk)
            elapsed = (datetime.now() - t0).total_seconds()
            logger.info(f"  Tiempo: {elapsed:.1f}s  ({filas/max(elapsed,0.1):,.0f} filas/s)")
            resultados[nombre] = filas
        except Exception as exc:
            logger.error(f"Error al cargar {nombre}: {exc}", exc_info=True)
            errores.append(nombre)

    elapsed_total = (datetime.now() - inicio_total).total_seconds()
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"Carga completada en {elapsed_total:.1f}s")
    logger.info(f"Tablas cargadas : {len(resultados)}")
    logger.info(f"Tablas con error: {len(errores)}")
    if errores:
        logger.error(f"Tablas fallidas : {', '.join(errores)}")

    if resultados:
        verificar_conteos(conn)

    conn.close()
    if errores:
        sys.exit(1)


if __name__ == "__main__":
    main()
