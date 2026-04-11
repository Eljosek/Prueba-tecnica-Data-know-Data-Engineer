"""
Gold Layer - Creacion de vistas analiticas en Azure SQL
Ejecuta cada vista de forma individual para evitar problemas de batch en SQL Server
"""

import os
import sys
import pyodbc
from datetime import datetime

SERVER   = "sqlsrv-retailmax-brs-dev.database.windows.net"
DATABASE = "sqldb-retailmax-brs-dev"
USER     = os.environ.get("SQLSERVER_USER", "sqladmin")
PASSWORD = os.environ.get("SQLSERVER_PASSWORD", "RetailMax@2026Data")

CONN_STR = (
    f"DRIVER={{SQL Server}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    f"UID={USER};"
    f"PWD={PASSWORD};"
)

VIEWS = {
    "dim_productos": """
CREATE OR ALTER VIEW dim_productos AS
SELECT
    art_id              AS product_id,
    cod_barra           AS barcode,
    desc_art            AS product_name,
    id_categ_n1         AS category_level1,
    id_categ_n2         AS category_level2,
    id_categ_n3         AS category_level3,
    id_proveedor        AS supplier_id,
    precio_lista        AS list_price,
    peso_kg             AS weight_kg,
    unid_medida         AS unit_of_measure,
    activo              AS is_active,
    fec_alta            AS creation_date
FROM MSTR_ARTICULOS
""",

    "dim_tiendas": """
CREATE OR ALTER VIEW dim_tiendas AS
SELECT
    id_tienda           AS store_id,
    nom_tienda          AS store_name,
    tipo_tienda         AS store_type,
    id_ciudad           AS city_id,
    id_pais             AS country_id,
    metros_cuadrados    AS square_meters,
    activo              AS is_active,
    fec_apertura        AS opening_date
FROM MSTR_TIENDAS
""",

    "dim_clientes": """
CREATE OR ALTER VIEW dim_clientes AS
SELECT
    id_miembro          AS customer_id,
    fec_registro        AS registration_date,
    id_ciudad           AS city_id,
    genero              AS gender,
    rango_edad          AS age_range,
    canal_pref          AS preferred_channel,
    activo              AS is_active,
    fec_ultima_compra   AS last_purchase_date
FROM CRM_MIEMBROS
""",

    "fact_ventas": """
CREATE OR ALTER VIEW fact_ventas AS
SELECT
    id_trans                    AS sale_id,
    id_miembro                  AS customer_id,
    id_tienda                   AS store_id,
    art_id                      AS product_id,
    CAST(fec_trans AS DATE)     AS sale_date,
    qty_vendida                 AS quantity_sold,
    precio_unitario_venta       AS unit_price,
    descuento_aplicado          AS discount_amount,
    tipo_pago                   AS payment_type,
    canal_venta                 AS sales_channel,
    CONVERT(NUMERIC(12,2), qty_vendida * precio_unitario_venta)                     AS gross_amount,
    CONVERT(NUMERIC(12,2), qty_vendida * precio_unitario_venta - descuento_aplicado) AS net_amount,
    YEAR(fec_trans)             AS year_sale,
    MONTH(fec_trans)            AS month_sale,
    DAY(fec_trans)              AS day_sale
FROM TRANS_VENTAS
""",

    "fact_inventario": """
CREATE OR ALTER VIEW fact_inventario AS
SELECT
    id_snapshot                 AS inventory_id,
    art_id                      AS product_id,
    id_tienda                   AS store_id,
    CAST(fec_snapshot AS DATE)  AS snapshot_date,
    stock_fisico                AS physical_stock,
    stock_transito              AS in_transit_stock,
    stock_reservado             AS reserved_stock,
    stock_minimo_config         AS min_stock_config,
    stock_maximo_config         AS max_stock_config,
    CONVERT(NUMERIC(10,2), stock_fisico - stock_reservado) AS available_stock,
    YEAR(fec_snapshot)          AS year_snapshot,
    MONTH(fec_snapshot)         AS month_snapshot
FROM INV_STOCK_DIARIO
""",

    "fact_devoluciones": """
CREATE OR ALTER VIEW fact_devoluciones AS
SELECT
    id_devolucion               AS return_id,
    id_trans_origen             AS origin_sale_id,
    art_id                      AS product_id,
    id_tienda                   AS store_id,
    CAST(fec_devolucion AS DATE) AS return_date,
    qty_devuelta                AS quantity_returned,
    motivo_cod                  AS reason_code,
    canal_devolucion            AS return_channel,
    estado_devolucion           AS return_status,
    vr_reembolso                AS refund_amount,
    YEAR(fec_devolucion)        AS year_return,
    MONTH(fec_devolucion)       AS month_return
FROM POST_DEVOLUCIONES
""",

    "fact_rfm_clientes": """
CREATE OR ALTER VIEW fact_rfm_clientes AS
WITH rfm_calc AS (
    SELECT
        cm.id_miembro AS customer_id,
        DATEDIFF(DAY, MAX(tv.fec_trans), CAST(GETDATE() AS DATE))   AS recency_days,
        COUNT(DISTINCT tv.id_trans)                                  AS frequency_purchases,
        CONVERT(NUMERIC(12,2),
            SUM(tv.qty_vendida * tv.precio_unitario_venta - tv.descuento_aplicado)
        )                                                            AS monetary_value
    FROM CRM_MIEMBROS cm
    LEFT JOIN TRANS_VENTAS tv
        ON cm.id_miembro = tv.id_miembro
       AND tv.fec_trans >= DATEADD(DAY, -90, CAST(GETDATE() AS DATE))
    GROUP BY cm.id_miembro
),
rfm_scored AS (
    SELECT
        customer_id,
        recency_days,
        frequency_purchases,
        monetary_value,
        NTILE(5) OVER (ORDER BY recency_days      DESC) AS r_score,
        NTILE(5) OVER (ORDER BY frequency_purchases ASC) AS f_score,
        NTILE(5) OVER (ORDER BY monetary_value      ASC) AS m_score,
        CASE WHEN frequency_purchases > 0 THEN 'active_90d' ELSE 'inactive' END AS status_90d
    FROM rfm_calc
)
SELECT
    customer_id,
    recency_days,
    frequency_purchases,
    monetary_value,
    r_score,
    f_score,
    m_score,
    CONVERT(NVARCHAR(20), CONCAT('R', r_score, '-F', f_score, '-M', m_score)) AS rfm_segment,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3                  THEN 'Loyal'
        WHEN r_score >= 2 AND frequency_purchases <= 1      THEN 'At_Risk'
        ELSE 'Other'
    END AS rfm_classification,
    status_90d,
    CAST(GETDATE() AS DATE) AS calculation_date
FROM rfm_scored
""",
}


def main():
    print("=" * 60)
    print("GOLD LAYER - Creacion de vistas analiticas")
    print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    try:
        conn = pyodbc.connect(CONN_STR)
        conn.autocommit = True
        cursor = conn.cursor()
        print(f"\nConexion establecida con {DATABASE}\n")
    except Exception as e:
        print(f"ERROR de conexion: {e}")
        sys.exit(1)

    resultados = []
    for nombre, ddl in VIEWS.items():
        try:
            cursor.execute(ddl.strip())
            print(f"  [OK] {nombre}")
            resultados.append((nombre, "OK"))
        except Exception as e:
            print(f"  [ERROR] {nombre}: {e}")
            resultados.append((nombre, f"ERROR: {e}"))

    cursor.close()
    conn.close()

    print("\n" + "=" * 60)
    print("Resumen")
    print("=" * 60)
    ok    = sum(1 for _, r in resultados if r == "OK")
    error = len(resultados) - ok
    print(f"  Vistas creadas : {ok}")
    print(f"  Errores        : {error}")

    if ok == len(VIEWS):
        print("\nTodas las vistas del Gold layer fueron creadas exitosamente.")
        print("\nPuedes confirmar en Azure Portal:")
        print("  Query Editor -> SELECT * FROM sys.views ORDER BY name")
        print("  O ejecutar  -> SELECT TOP 5 * FROM fact_rfm_clientes")
    else:
        print("\nRevisa los errores anteriores.")
        sys.exit(1)

    print(f"\nFin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
