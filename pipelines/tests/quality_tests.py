"""
quality_tests.py
Pruebas automatizadas de calidad de datos sobre las vistas Gold en Azure SQL.
Verifica integridad, validez y consistencia de los datos procesados.

Uso:
    python pipelines/tests/quality_tests.py

Variables de entorno requeridas:
    SQLSERVER_HOST      (default: sqlsrv-retailmax-brs-dev.database.windows.net)
    SQLSERVER_DB        (default: sqldb-retailmax-brs-dev)
    SQLSERVER_USER      (default: sqladmin)
    SQLSERVER_PASSWORD  (obligatorio)
"""
import os
import sys
import pyodbc

# -----------------------------------------------------------------------
# Configuracion de conexion
# -----------------------------------------------------------------------
SQL_SERVER = os.environ.get("SQLSERVER_HOST",
                            "sqlsrv-retailmax-brs-dev.database.windows.net")
SQL_DATABASE = os.environ.get("SQLSERVER_DB", "sqldb-retailmax-brs-dev")
SQL_USER = os.environ.get("SQLSERVER_USER", "sqladmin")
SQL_PASSWORD = os.environ.get("SQLSERVER_PASSWORD", "")

if not SQL_PASSWORD:
    print("ERROR: Variable de entorno SQLSERVER_PASSWORD no definida.")
    sys.exit(1)

CONN_STR = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER={SQL_SERVER};"
    f"DATABASE={SQL_DATABASE};"
    f"UID={SQL_USER};"
    f"PWD={SQL_PASSWORD};"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
    "Connection Timeout=30;"
)


def conectar():
    """Abre una conexion ODBC a Azure SQL y la devuelve."""
    return pyodbc.connect(CONN_STR)


def ejecutar_query(cursor, sql):
    """Ejecuta una consulta y devuelve el primer valor de la primera fila."""
    cursor.execute(sql)
    fila = cursor.fetchone()
    return fila[0] if fila else None


# -----------------------------------------------------------------------
# Pruebas
# -----------------------------------------------------------------------

def test_no_nulls_pks(cursor):
    """
    Test 1: Claves primarias sin nulos en todas las vistas Gold.
    Las PKs definidas en el diseno no deben contener nulos.
    """
    nombre = "test_no_nulls_pks"
    checks = {
        "dim_productos.product_id": "SELECT COUNT(*) FROM dim_productos WHERE product_id IS NULL",
        "dim_tiendas.store_id": "SELECT COUNT(*) FROM dim_tiendas WHERE store_id IS NULL",
        "dim_clientes.customer_id": "SELECT COUNT(*) FROM dim_clientes WHERE customer_id IS NULL",
        "fact_ventas.sale_id": "SELECT COUNT(*) FROM fact_ventas WHERE sale_id IS NULL",
        "fact_inventario.inventory_id": "SELECT COUNT(*) FROM fact_inventario WHERE inventory_id IS NULL",
        "fact_devoluciones.return_id": "SELECT COUNT(*) FROM fact_devoluciones WHERE return_id IS NULL",
        "fact_rfm_clientes.customer_id": "SELECT COUNT(*) FROM fact_rfm_clientes WHERE customer_id IS NULL",
        "kpi_ejecutivo.fecha": "SELECT COUNT(*) FROM kpi_ejecutivo WHERE fecha IS NULL",
    }
    errores = []
    for campo, sql in checks.items():
        nulos = ejecutar_query(cursor, sql)
        if nulos and nulos > 0:
            errores.append(f"  {campo}: {nulos} nulos encontrados")
    if errores:
        return False, "\n".join(errores)
    return True, "Todas las PKs sin nulos"


def test_fechas_validas(cursor):
    """
    Test 2: No existen fechas futuras en tablas de hechos.
    Las fechas de ventas e inventario no pueden ser posteriores a la fecha actual.
    """
    nombre = "test_fechas_validas"
    checks = {
        "fact_ventas.sale_date": "SELECT COUNT(*) FROM fact_ventas WHERE sale_date > CAST(GETDATE() AS DATE)",
        "fact_inventario.snapshot_date": "SELECT COUNT(*) FROM fact_inventario WHERE snapshot_date > CAST(GETDATE() AS DATE)",
        "fact_devoluciones.return_date": "SELECT COUNT(*) FROM fact_devoluciones WHERE return_date > CAST(GETDATE() AS DATE)",
    }
    errores = []
    for campo, sql in checks.items():
        futuros = ejecutar_query(cursor, sql)
        if futuros and futuros > 0:
            errores.append(f"  {campo}: {futuros} registros con fecha futura")
    if errores:
        return False, "\n".join(errores)
    return True, "Ninguna fecha futura encontrada"


def test_stock_no_negativo(cursor):
    """
    Test 3: cobertura_dias no es negativa en fact_inventario.
    Cuando existe demanda, la cobertura de dias debe ser >= 0.
    Un stock fisico negativo indicaria un error de carga de datos.
    """
    sql = """
        SELECT COUNT(*)
        FROM fact_inventario
        WHERE cobertura_dias IS NOT NULL
          AND cobertura_dias < 0
    """
    negativos = ejecutar_query(cursor, sql)
    if negativos and negativos > 0:
        return False, f"{negativos} registros con cobertura_dias negativa"
    sql_stock_fisico = "SELECT COUNT(*) FROM fact_inventario WHERE physical_stock < 0"
    stock_neg = ejecutar_query(cursor, sql_stock_fisico)
    if stock_neg and stock_neg > 0:
        return False, f"{stock_neg} registros con physical_stock negativo"
    return True, "Cobertura y stock fisico dentro de rango valido"


def test_rfm_segmentos(cursor):
    """
    Test 4: Segmentos RFM con formato correcto y sin nulos.
    rfm_segment debe seguir el patron Rx-Fy-Mz con x, y, z entre 1 y 5.
    rfm_classification no debe ser nulo.
    """
    sql_nulos = """
        SELECT COUNT(*)
        FROM fact_rfm_clientes
        WHERE rfm_segment IS NULL OR rfm_classification IS NULL
    """
    nulos = ejecutar_query(cursor, sql_nulos)
    if nulos and nulos > 0:
        return False, f"{nulos} registros con rfm_segment o rfm_classification nulo"

    sql_patron = """
        SELECT COUNT(*)
        FROM fact_rfm_clientes
        WHERE rfm_segment NOT LIKE 'R[1-5]-F[1-5]-M[1-5]'
    """
    patron_invalido = ejecutar_query(cursor, sql_patron)
    if patron_invalido and patron_invalido > 0:
        return False, f"{patron_invalido} registros con formato rfm_segment invalido"

    return True, "Todos los segmentos RFM con formato valido"


def test_ventas_netas_positivas(cursor):
    """
    Test 5: net_amount >= 0 en fact_ventas.
    No debe haber ventas con importe neto negativo (el descuento no puede superar el bruto).
    """
    sql = "SELECT COUNT(*) FROM fact_ventas WHERE net_amount < 0"
    negativas = ejecutar_query(cursor, sql)
    if negativas and negativas > 0:
        return False, f"{negativas} registros con net_amount negativo"
    return True, "Todas las ventas netas son >= 0"


# -----------------------------------------------------------------------
# Registro de volumetria (informativo, no falla el test)
# -----------------------------------------------------------------------

def registrar_volumetria(cursor):
    """Muestra un resumen de filas por tabla Gold para control de volumetria."""
    tablas = [
        ("dim_productos", "SELECT COUNT(*) FROM dim_productos"),
        ("dim_tiendas", "SELECT COUNT(*) FROM dim_tiendas"),
        ("dim_clientes", "SELECT COUNT(*) FROM dim_clientes"),
        ("fact_ventas", "SELECT COUNT(*) FROM fact_ventas"),
        ("fact_inventario", "SELECT COUNT(*) FROM fact_inventario"),
        ("fact_devoluciones", "SELECT COUNT(*) FROM fact_devoluciones"),
        ("fact_rfm_clientes", "SELECT COUNT(*) FROM fact_rfm_clientes"),
        ("kpi_ejecutivo", "SELECT COUNT(*) FROM kpi_ejecutivo"),
    ]
    print("\nVolometria de vistas Gold:")
    print(f"  {'Vista':<25} {'Registros':>12}")
    print(f"  {'-' * 25} {'-' * 12}")
    for nombre, sql in tablas:
        try:
            filas = ejecutar_query(cursor, sql)
            print(f"  {nombre:<25} {filas:>12,}")
        except pyodbc.Error as exc:
            print(f"  {nombre:<25} {'ERROR':>12}  ({exc.args[1][:60]})")


# -----------------------------------------------------------------------
# Ejecucion principal
# -----------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Pruebas de Calidad - RetailMax Gold Layer")
    print("=" * 60)

    print(f"\nConectando a {SQL_DATABASE} en {SQL_SERVER}...")
    try:
        conn = conectar()
    except pyodbc.Error as exc:
        print(f"ERROR al conectar: {exc}")
        sys.exit(1)
    print("  -> Conexion establecida")

    cursor = conn.cursor()

    pruebas = [
        ("Test 1: PKs sin nulos", test_no_nulls_pks),
        ("Test 2: Fechas validas", test_fechas_validas),
        ("Test 3: Stock no negativo", test_stock_no_negativo),
        ("Test 4: Formato segmentos RFM", test_rfm_segmentos),
        ("Test 5: Ventas netas positivas", test_ventas_netas_positivas),
    ]

    resultados = []
    print()
    for nombre, funcion in pruebas:
        try:
            ok, detalle = funcion(cursor)
        except pyodbc.Error as exc:
            ok = False
            detalle = f"Error SQL: {exc.args[1][:120]}"
        estado = "PASS" if ok else "FAIL"
        print(f"  [{estado}] {nombre}")
        if not ok:
            print(f"         {detalle}")
        resultados.append((nombre, ok))

    registrar_volumetria(cursor)

    pasadas = sum(1 for _, ok in resultados if ok)
    falladas = len(resultados) - pasadas

    print("\n" + "=" * 60)
    print(f"Resultado: {pasadas}/{len(resultados)} pruebas pasadas")
    if falladas:
        print(
            f"ADVERTENCIA: {falladas} prueba(s) fallaron. Revisar datos en capa Gold.")
    else:
        print("Todas las pruebas de calidad pasaron correctamente.")
    print("=" * 60)

    cursor.close()
    conn.close()

    if falladas:
        sys.exit(1)


if __name__ == "__main__":
    main()
