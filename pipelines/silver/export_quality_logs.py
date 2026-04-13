"""
Silver Quality Report - Exporta el reporte de calidad a Azure Storage
Lee pipeline_quality_report de SQL y lo sube como CSV al container silver/logs/
"""

import os
import sys
import pyodbc
import pandas as pd
from datetime import datetime

from azure.storage.blob import BlobServiceClient

DB_CONFIG = {
    "server": os.environ.get("SQLSERVER_HOST", "sqlsrv-retailmax-brs-dev.database.windows.net"),
    "database": "sqldb-retailmax-brs-dev",
    "user": os.environ.get("SQLSERVER_USER", "sqladmin"),
    "password": os.environ.get("SQLSERVER_PASSWORD"),
    "driver": "SQL Server",
}

STORAGE_CONN = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")


def main():
    if not DB_CONFIG["password"] or not STORAGE_CONN:
        print("ERROR: variables SQLSERVER_PASSWORD y AZURE_STORAGE_CONNECTION_STRING requeridas.")
        sys.exit(1)

    conn_str = (
        f"DRIVER={{{DB_CONFIG['driver']}}};"
        f"SERVER={DB_CONFIG['server']};"
        f"DATABASE={DB_CONFIG['database']};"
        f"UID={DB_CONFIG['user']};"
        f"PWD={DB_CONFIG['password']}"
    )

    conn = pyodbc.connect(conn_str)

    # Reporte de calidad
    df_quality = pd.read_sql(
        "SELECT * FROM pipeline_quality_report ORDER BY timestamp_reporte DESC", conn)

    # Errores del pipeline
    df_errors = pd.read_sql("SELECT TOP 100 * FROM pipeline_errors", conn)

    conn.close()

    blob_client = BlobServiceClient.from_connection_string(STORAGE_CONN)
    container = blob_client.get_container_client("silver")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Subir quality report
    quality_csv = df_quality.to_csv(index=False)
    container.upload_blob(
        name=f"logs/quality_report_{timestamp}.csv",
        data=quality_csv,
        overwrite=True,
    )
    print(
        f"  [OK] silver/logs/quality_report_{timestamp}.csv ({len(df_quality)} registros)")

    # Subir errors log
    errors_csv = df_errors.to_csv(index=False)
    container.upload_blob(
        name=f"logs/pipeline_errors_{timestamp}.csv",
        data=errors_csv,
        overwrite=True,
    )
    print(
        f"  [OK] silver/logs/pipeline_errors_{timestamp}.csv ({len(df_errors)} registros)")

    # Subir tambien al bronze
    container_bronze = blob_client.get_container_client("bronze")
    container_bronze.upload_blob(
        name=f"logs/ingestion_log_{timestamp}.csv",
        data=quality_csv,
        overwrite=True,
    )
    print(f"  [OK] bronze/logs/ingestion_log_{timestamp}.csv")

    print("\nLogs de calidad subidos a Azure Storage.")


if __name__ == "__main__":
    main()
