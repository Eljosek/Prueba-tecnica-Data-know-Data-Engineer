#!/usr/bin/env python3
"""Consulta los conteos de las tablas cargadas en Azure SQL Database."""
import os
import sys
import pyodbc
from datetime import datetime

def get_credentials():
    usuario = os.environ.get("SQLSERVER_USER")
    password = os.environ.get("SQLSERVER_PASSWORD")
    if not usuario or not password:
        raise EnvironmentError(
            "Debe definir las variables de entorno SQLSERVER_USER y SQLSERVER_PASSWORD."
        )
    return usuario, password

SERVER = "sqlsrv-retailmax-brs-dev.database.windows.net"
DATABASE = "sqldb-retailmax-brs-dev"
TABLES = [
    "MSTR_PROVEEDORES",
    "MSTR_TIENDAS",
    "MSTR_ARTICULOS",
    "CRM_MIEMBROS",
    "TRANS_VENTAS",
    "INV_STOCK_DIARIO",
    "POST_DEVOLUCIONES",
]
EXPECTED_COUNTS = {
    "MSTR_PROVEEDORES": 800,
    "MSTR_TIENDAS": 150,
    "MSTR_ARTICULOS": 5005,
    "CRM_MIEMBROS": 50000,
    "TRANS_VENTAS": 1001000,
    "INV_STOCK_DIARIO": 750000,
    "POST_DEVOLUCIONES": 50000,
}


def get_driver():
    preferred = [
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server",
        "SQL Server",
    ]
    available = set(pyodbc.drivers())
    for driver in preferred:
        if driver in available:
            return driver
    raise RuntimeError(f"No se encontro driver ODBC compatible. Drivers disponibles: {available}")


def create_connection(user, password):
    driver = get_driver()
    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        f"UID={user};"
        f"PWD={password};"
        "Encrypt=yes;TrustServerCertificate=yes;"
    )
    conn = pyodbc.connect(conn_str, timeout=30)
    conn.autocommit = True
    return conn


def query_counts(conn):
    cursor = conn.cursor()
    results = []
    for table in TABLES:
        cursor.execute(f"SELECT COUNT(*) FROM dbo.[{table}]")
        count = cursor.fetchone()[0]
        expected = EXPECTED_COUNTS.get(table)
        status = "OK" if expected == count else "ERROR"
        results.append((table, count, expected, status))
    return results


def print_report(results):
    print("\nSQL Counts Verification")
    print("=" * 50)
    for table, count, expected, status in results:
        print(f"{table:<20} {count:>10,}  esperado: {expected:>10,}  {status}")
    discrepancies = [r for r in results if r[3] != "OK"]
    print("=" * 50)
    if discrepancies:
        print(f"ERROR: {len(discrepancies)} tabla(s) con conteos diferentes.")
        sys.exit(1)
    print("Todos los conteos coinciden con lo esperado.")


def main():
    try:
        user, password = get_credentials()
    except EnvironmentError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    conn = create_connection(user, password)
    results = query_counts(conn)
    print_report(results)
    conn.close()


if __name__ == "__main__":
    main()
