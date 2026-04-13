"""
Gold Layer - Exportacion de vistas a Parquet y subida a Azure Storage
Lee cada vista Gold de Azure SQL, genera Parquet local y lo sube al container 'gold'
"""

import os
import sys
import pyodbc
import pandas as pd
from pathlib import Path
from datetime import datetime

from azure.storage.blob import BlobServiceClient

BASE_DIR = Path(__file__).resolve().parent
GOLD_DATA = BASE_DIR / "data"
CONTAINER = "gold"

DB_CONFIG = {
    "server": os.environ.get("SQLSERVER_HOST", "sqlsrv-retailmax-brs-dev.database.windows.net"),
    "database": "sqldb-retailmax-brs-dev",
    "user": os.environ.get("SQLSERVER_USER", "sqladmin"),
    "password": os.environ.get("SQLSERVER_PASSWORD"),
    "driver": "SQL Server",
}

STORAGE_CONN = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")

GOLD_VIEWS = [
    "dim_productos",
    "dim_tiendas",
    "dim_clientes",
    "fact_ventas",
    "fact_inventario",
    "fact_devoluciones",
    "fact_rfm_clientes",
]


def export_and_upload():
    if not DB_CONFIG["password"]:
        print("ERROR: variable SQLSERVER_PASSWORD no definida.")
        sys.exit(1)
    if not STORAGE_CONN:
        print("ERROR: variable AZURE_STORAGE_CONNECTION_STRING no definida.")
        sys.exit(1)

    print("=" * 60)
    print("GOLD LAYER - Exportacion a Parquet + Azure Storage")
    print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    conn_str = (
        f"DRIVER={{{DB_CONFIG['driver']}}};"
        f"SERVER={DB_CONFIG['server']};"
        f"DATABASE={DB_CONFIG['database']};"
        f"UID={DB_CONFIG['user']};"
        f"PWD={DB_CONFIG['password']}"
    )

    try:
        conn = pyodbc.connect(conn_str)
        print(f"\nConexion SQL establecida con {DB_CONFIG['database']}")
    except Exception as e:
        print(f"ERROR SQL: {e}")
        sys.exit(1)

    try:
        blob_client = BlobServiceClient.from_connection_string(STORAGE_CONN)
        container = blob_client.get_container_client(CONTAINER)
        print("Conexion Azure Storage establecida\n")
    except Exception as e:
        print(f"ERROR Storage: {e}")
        sys.exit(1)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    year = datetime.now().strftime("%Y")
    month = datetime.now().strftime("%m")
    day = datetime.now().strftime("%d")

    resultados = []

    for vista in GOLD_VIEWS:
        try:
            df = pd.read_sql(f"SELECT * FROM {vista}", conn)
            rows = len(df)

            # Guardar Parquet local
            local_dir = GOLD_DATA / vista / year / month / day
            local_dir.mkdir(parents=True, exist_ok=True)
            local_file = local_dir / f"{vista}_{timestamp}.parquet"
            df.to_parquet(local_file, index=False, engine="pyarrow")

            # Subir a Azure Storage
            blob_name = f"{vista}/{year}/{month}/{day}/{vista}_{timestamp}.parquet"
            with open(local_file, "rb") as f:
                container.upload_blob(name=blob_name, data=f, overwrite=True)

            print(f"  [OK] {vista}: {rows:,} filas -> gold/{blob_name}")
            resultados.append((vista, rows, "OK"))

        except Exception as e:
            print(f"  [ERROR] {vista}: {e}")
            resultados.append((vista, 0, f"ERROR: {e}"))

    conn.close()

    # Subir log de ejecucion
    log_content = f"Gold Export Log - {timestamp}\n{'=' * 50}\n"
    for vista, rows, status in resultados:
        log_content += f"{vista}: {rows} filas - {status}\n"
    log_content += f"\nTotal vistas: {len(resultados)}\n"
    log_content += f"Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

    container.upload_blob(
        name=f"logs/gold_export_{timestamp}.log",
        data=log_content,
        overwrite=True,
    )

    print("\n" + "=" * 60)
    print("Resumen")
    print("=" * 60)
    ok = sum(1 for _, _, s in resultados if s == "OK")
    total = sum(r for _, r, s in resultados if s == "OK")
    print(f"  Vistas exportadas : {ok}/{len(GOLD_VIEWS)}")
    print(f"  Filas totales     : {total:,}")
    print(f"  Log subido a      : gold/logs/gold_export_{timestamp}.log")

    if ok == len(GOLD_VIEWS):
        print("\nConfirma en Azure Portal:")
        print("  Storage accounts -> stgretailmaxbrsdev -> Containers -> gold")
    else:
        sys.exit(1)

    print(f"\nFin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    export_and_upload()
