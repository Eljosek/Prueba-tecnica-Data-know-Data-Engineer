-- Gold Layer Views - RetailMax
-- Escenario B: Retail & E-commerce
-- Incluye todas las reglas de negocio requeridas por la prueba tecnica

-- ===========================================================================
-- DIMENSIONES
-- ===========================================================================

-- 1. dim_productos
-- JOIN con MSTR_PROVEEDORES para enriquecer el catalogo de articulos.
-- Incluye margen estimado del 30% sobre precio de lista como indicador de rentabilidad.
CREATE OR ALTER VIEW dim_productos AS
SELECT
    a.art_id           AS product_id,
    a.cod_barra        AS barcode,
    a.desc_art         AS product_name,
    a.id_categ_n1      AS category_level1,
    a.id_categ_n2      AS category_level2,
    a.id_categ_n3      AS category_level3,
    a.id_proveedor     AS supplier_id,
    p.razon_social     AS supplier_name,
    p.pais_origen      AS supplier_country,
    p.calificacion_calidad AS supplier_quality_score,
    a.precio_lista     AS list_price,
    a.peso_kg          AS weight_kg,
    a.unid_medida      AS unit_of_measure,
    a.activo           AS is_active,
    a.fec_alta         AS creation_date,
    CONVERT(NUMERIC(10,2), a.precio_lista * 0.30) AS estimated_margin
FROM MSTR_ARTICULOS a
LEFT JOIN MSTR_PROVEEDORES p ON a.id_proveedor = p.id_proveedor;

-- 2. dim_tiendas
-- zona_distribucion derivada del id_pais para segmentar la red de distribucion.
CREATE OR ALTER VIEW dim_tiendas AS
SELECT
    id_tienda       AS store_id,
    nom_tienda      AS store_name,
    tipo_tienda     AS store_type,
    id_ciudad       AS city_id,
    id_pais         AS country_id,
    metros_cuadrados AS square_meters,
    activo          AS is_active,
    fec_apertura    AS opening_date,
    CASE
        WHEN id_pais % 5 = 0 THEN 'Zona_Norte'
        WHEN id_pais % 5 = 1 THEN 'Zona_Sur'
        WHEN id_pais % 5 = 2 THEN 'Zona_Este'
        WHEN id_pais % 5 = 3 THEN 'Zona_Oeste'
        ELSE                      'Zona_Centro'
    END AS zona_distribucion
FROM MSTR_TIENDAS;

-- 3. dim_clientes
-- gender estandarizado: M, F o No_informado.
-- age_range imputado con el valor mas frecuente del mismo canal cuando es nulo.
-- antiguedad_dias calculado desde fec_registro hasta hoy.
CREATE OR ALTER VIEW dim_clientes AS
SELECT
    c.id_miembro    AS customer_id,
    c.fec_registro  AS registration_date,
    c.id_ciudad     AS city_id,
    CASE c.genero
        WHEN 'M' THEN 'M'
        WHEN 'F' THEN 'F'
        ELSE          'No_informado'
    END AS gender,
    COALESCE(
        c.rango_edad,
        (
            SELECT TOP 1 t.rango_edad
            FROM   CRM_MIEMBROS t
            WHERE  t.canal_pref    = c.canal_pref
              AND  t.rango_edad   IS NOT NULL
            GROUP  BY t.rango_edad
            ORDER  BY COUNT(*) DESC
        )
    ) AS age_range,
    c.canal_pref        AS preferred_channel,
    c.activo            AS is_active,
    c.fec_ultima_compra AS last_purchase_date,
    DATEDIFF(DAY, c.fec_registro, CAST(GETDATE() AS DATE)) AS antiguedad_dias
FROM CRM_MIEMBROS c;

-- ===========================================================================
-- HECHOS
-- ===========================================================================

-- 4. fact_ventas
-- customer_id muestra 'ANONIMO' cuando id_miembro es nulo.
-- ind_con_descuento = 1 cuando descuento_aplicado > 0.
CREATE OR ALTER VIEW fact_ventas AS
SELECT
    id_trans                                                           AS sale_id,
    COALESCE(CAST(id_miembro AS NVARCHAR(20)), 'ANONIMO')             AS customer_id,
    id_tienda                                                          AS store_id,
    art_id                                                             AS product_id,
    CAST(fec_trans AS DATE)                                            AS sale_date,
    qty_vendida                                                        AS quantity_sold,
    precio_unitario_venta                                              AS unit_price,
    descuento_aplicado                                                 AS discount_amount,
    tipo_pago                                                          AS payment_type,
    canal_venta                                                        AS sales_channel,
    CONVERT(NUMERIC(12,2), qty_vendida * precio_unitario_venta)       AS gross_amount,
    CONVERT(NUMERIC(12,2), descuento_aplicado)                        AS discount_value,
    CONVERT(NUMERIC(12,2),
        qty_vendida * precio_unitario_venta - descuento_aplicado)     AS net_amount,
    CASE WHEN descuento_aplicado > 0 THEN 1 ELSE 0 END                AS ind_con_descuento,
    YEAR(fec_trans)                                                    AS year_sale,
    MONTH(fec_trans)                                                   AS month_sale,
    DAY(fec_trans)                                                     AS day_sale
FROM TRANS_VENTAS;

-- 5. fact_inventario
-- cobertura_dias = stock_fisico / promedio de ventas diarias en los ultimos 14 dias.
-- alerta_quiebre = 1 cuando cobertura_dias < 7 y existe demanda en los ultimos 14 dias.
CREATE OR ALTER VIEW fact_inventario AS
WITH ventas_14d AS (
    SELECT
        art_id,
        id_tienda,
        CONVERT(NUMERIC(12,4), SUM(qty_vendida) * 1.0 / 14.0) AS avg_daily_sales_14d
    FROM  TRANS_VENTAS
    WHERE fec_trans >= DATEADD(DAY, -14, CAST(GETDATE() AS DATE))
    GROUP BY art_id, id_tienda
)
SELECT
    s.id_snapshot     AS inventory_id,
    s.art_id          AS product_id,
    s.id_tienda       AS store_id,
    CAST(s.fec_snapshot AS DATE)                                      AS snapshot_date,
    s.stock_fisico                                                     AS physical_stock,
    s.stock_transito                                                   AS in_transit_stock,
    s.stock_reservado                                                  AS reserved_stock,
    s.stock_minimo_config                                              AS min_stock_config,
    s.stock_maximo_config                                              AS max_stock_config,
    CONVERT(NUMERIC(10,2), s.stock_fisico - s.stock_reservado)        AS available_stock,
    CONVERT(NUMERIC(10,4), COALESCE(v.avg_daily_sales_14d, 0))        AS avg_daily_sales_14d,
    CASE
        WHEN COALESCE(v.avg_daily_sales_14d, 0) > 0
        THEN CONVERT(NUMERIC(10,2), s.stock_fisico * 1.0 / v.avg_daily_sales_14d)
        ELSE NULL
    END AS cobertura_dias,
    CASE
        WHEN COALESCE(v.avg_daily_sales_14d, 0) > 0
         AND (s.stock_fisico * 1.0 / v.avg_daily_sales_14d) < 7
        THEN 1
        ELSE 0
    END AS alerta_quiebre,
    YEAR(s.fec_snapshot)  AS year_snapshot,
    MONTH(s.fec_snapshot) AS month_snapshot
FROM INV_STOCK_DIARIO s
LEFT JOIN ventas_14d v ON s.art_id = v.art_id AND s.id_tienda = v.id_tienda;

-- 6. fact_devoluciones
-- JOIN con TRANS_VENTAS para recuperar el precio unitario de la venta original.
-- return_rate_by_product = tasa de devolucion agregada por articulo.
CREATE OR ALTER VIEW fact_devoluciones AS
WITH tasa_art AS (
    SELECT
        d.art_id,
        CONVERT(NUMERIC(10,4),
            SUM(d.qty_devuelta) * 1.0 / NULLIF(SUM(v.qty_vendida), 0)
        ) AS tasa_devolucion_articulo
    FROM  POST_DEVOLUCIONES d
    LEFT JOIN TRANS_VENTAS v ON d.art_id = v.art_id
    GROUP BY d.art_id
)
SELECT
    d.id_devolucion                AS return_id,
    d.id_trans_origen              AS origin_sale_id,
    d.art_id                       AS product_id,
    d.id_tienda                    AS store_id,
    CAST(d.fec_devolucion AS DATE) AS return_date,
    d.qty_devuelta                 AS quantity_returned,
    d.motivo_cod                   AS reason_code,
    d.canal_devolucion             AS return_channel,
    d.estado_devolucion            AS return_status,
    d.vr_reembolso                 AS refund_amount,
    v2.precio_unitario_venta       AS original_unit_price,
    COALESCE(t.tasa_devolucion_articulo, 0) AS return_rate_by_product,
    YEAR(d.fec_devolucion)         AS year_return,
    MONTH(d.fec_devolucion)        AS month_return
FROM  POST_DEVOLUCIONES d
LEFT JOIN TRANS_VENTAS v2    ON d.id_trans_origen = v2.id_trans
LEFT JOIN tasa_art t         ON d.art_id          = t.art_id;

-- 7. fact_rfm_clientes
CREATE OR ALTER VIEW fact_rfm_clientes AS
WITH rfm_calc AS (
    SELECT 
        cm.id_miembro AS customer_id,
        DATEDIFF(DAY, MAX(tv.fec_trans), CAST(GETDATE() AS DATE)) AS recency_days,
        COUNT(DISTINCT tv.id_trans) AS frequency_purchases,
        CONVERT(NUMERIC(12,2), SUM(tv.qty_vendida * tv.precio_unitario_venta - tv.descuento_aplicado)) AS monetary_value
    FROM CRM_MIEMBROS cm
    LEFT JOIN TRANS_VENTAS tv ON cm.id_miembro = tv.id_miembro
        AND tv.fec_trans >= DATEADD(DAY, -90, CAST(GETDATE() AS DATE))
    GROUP BY cm.id_miembro
),
rfm_scored AS (
    SELECT 
        customer_id,
        recency_days,
        frequency_purchases,
        monetary_value,
        NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
        NTILE(5) OVER (ORDER BY frequency_purchases ASC) AS f_score,
        NTILE(5) OVER (ORDER BY monetary_value ASC) AS m_score,
        CASE 
            WHEN frequency_purchases > 0 THEN 'active_90d'
            ELSE 'inactive'
        END AS status_90d
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
        WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal'
        WHEN r_score >= 2 AND frequency_purchases <= 1 THEN 'At_Risk'
        ELSE 'Other'
    END AS rfm_classification,
    status_90d,
    CAST(GETDATE() AS DATE) AS calculation_date
FROM rfm_scored;

-- ===========================================================================
-- KPIs EJECUTIVOS
-- ===========================================================================

-- 8. kpi_ejecutivo
-- Resumen diario de ventas por pais y canal para reportes ejecutivos.
-- Agrega transacciones, clientes unicos, unidades y montos brutos/netos.
CREATE OR ALTER VIEW kpi_ejecutivo AS
SELECT
    CAST(tv.fec_trans AS DATE)                                              AS fecha,
    ts.id_pais                                                              AS country_id,
    tv.canal_venta                                                          AS sales_channel,
    COUNT(DISTINCT tv.id_trans)                                             AS total_transacciones,
    COUNT(DISTINCT tv.id_miembro)                                           AS clientes_unicos,
    SUM(tv.qty_vendida)                                                     AS unidades_vendidas,
    CONVERT(NUMERIC(14,2), SUM(tv.qty_vendida * tv.precio_unitario_venta)) AS ventas_brutas,
    CONVERT(NUMERIC(14,2), SUM(tv.descuento_aplicado))                     AS descuentos_totales,
    CONVERT(NUMERIC(14,2),
        SUM(tv.qty_vendida * tv.precio_unitario_venta - tv.descuento_aplicado)) AS ventas_netas,
    YEAR(tv.fec_trans)                                                      AS anio,
    MONTH(tv.fec_trans)                                                     AS mes
FROM  TRANS_VENTAS tv
INNER JOIN MSTR_TIENDAS ts ON tv.id_tienda = ts.id_tienda
GROUP BY
    CAST(tv.fec_trans AS DATE),
    ts.id_pais,
    tv.canal_venta,
    YEAR(tv.fec_trans),
    MONTH(tv.fec_trans);
