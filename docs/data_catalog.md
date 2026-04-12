# Catalogo de Datos - RetailMax

**Proyecto:** Prueba Tecnica Data Engineer - Escenario B: Retail & E-commerce
**Arquitectura:** Medallion (Bronze / Silver / Gold)
**Fecha:** Abril 2026

---

## Capas del Data Lake

| Capa   | Contenedor Azure          | Descripcion                                         |
|--------|---------------------------|-----------------------------------------------------|
| Bronze | stgretailmaxbrsdev/bronze | Datos raw copiados desde Azure SQL en formato Parquet. Sin transformacion. |
| Silver | stgretailmaxbrsdev/silver | Datos deduplicados y con PII enmascarado. Calidad registrada. |
| Gold   | stgretailmaxbrsdev/gold   | Vistas analiticas con reglas de negocio aplicadas. Exportadas en Parquet. |

---

## Tablas Fuente (Bronze)

### MSTR_PROVEEDORES

| Campo               | Tipo    | Descripcion                                  | Sensible |
|---------------------|---------|----------------------------------------------|----------|
| id_proveedor        | int     | Identificador unico del proveedor (PK)       | No       |
| razon_social        | varchar | Nombre legal del proveedor                   | No       |
| pais_origen         | varchar | Pais de origen del proveedor                 | No       |
| tiempo_repo_dias    | int     | Dias de reposicion promedio                  | No       |
| calificacion_calidad| float   | Calificacion de calidad (0-5)                | No       |
| activo              | int     | 1 = activo, 0 = inactivo                     | No       |

### MSTR_TIENDAS

| Campo           | Tipo    | Descripcion                                          | Sensible |
|-----------------|---------|------------------------------------------------------|----------|
| id_tienda       | int     | Identificador unico de la tienda (PK)                | No       |
| nom_tienda      | varchar | Nombre comercial de la tienda                        | No       |
| tipo_tienda     | varchar | Hipermercado / Supermercado / Tienda Conveniencia    | No       |
| id_ciudad       | int     | Referencia a ciudad                                  | No       |
| id_pais         | int     | Referencia a pais                                    | No       |
| metros_cuadrados| int     | Area de la tienda en m²                              | No       |
| activo          | int     | 1 = activa                                           | No       |
| fec_apertura    | date    | Fecha de apertura de la tienda                       | No       |

### MSTR_ARTICULOS

| Campo        | Tipo    | Descripcion                                     | Sensible |
|--------------|---------|-------------------------------------------------|----------|
| art_id       | int     | Identificador unico del articulo (PK)           | No       |
| cod_barra    | varchar | Codigo de barras EAN/UPC                        | No       |
| desc_art     | varchar | Descripcion del articulo                        | No       |
| id_categ_n1  | int     | Categoria nivel 1 (division principal)          | No       |
| id_categ_n2  | int     | Categoria nivel 2 (departamento)                | No       |
| id_categ_n3  | int     | Categoria nivel 3 (subdepartamento)             | No       |
| id_proveedor | int     | FK a MSTR_PROVEEDORES                           | No       |
| precio_lista | float   | Precio de lista sin descuentos                  | No       |
| peso_kg      | float   | Peso del articulo en kilogramos                 | No       |
| unid_medida  | varchar | Unidad de medida (und, kg, lt...)               | No       |
| activo       | int     | 1 = activo en catalogo                          | No       |
| fec_alta     | datetime| Fecha de alta en el sistema                     | No       |

### CRM_MIEMBROS

| Campo            | Tipo    | Descripcion                                     | Sensible |
|------------------|---------|-------------------------------------------------|----------|
| id_miembro       | int     | Identificador unico del cliente (PK). **PII**   | **Si**   |
| fec_registro     | date    | Fecha de registro en el CRM                     | No       |
| id_ciudad        | int     | Ciudad de residencia                            | No       |
| genero           | varchar | Genero: M, F, O (en Gold: M, F, No_informado)   | **Si**   |
| rango_edad       | varchar | 18-25 / 26-35 / 36-50 / 50+                     | **Si**   |
| canal_pref       | varchar | Canal preferido de compra                       | No       |
| activo           | int     | 1 = cliente activo                              | No       |
| fec_ultima_compra| date    | Ultima compra registrada                        | No       |

> **Nota PII:** `id_miembro` es hasheado (SHA-256) en la capa Silver. `genero` y `rango_edad` se categorizan y agrupan en Gold por diseno (no se exponen valores individuales directamente).

### TRANS_VENTAS

| Campo                 | Tipo    | Descripcion                                    | Sensible |
|-----------------------|---------|------------------------------------------------|----------|
| id_trans              | int     | Identificador de transaccion (PK)              | No       |
| id_miembro            | int     | FK a CRM_MIEMBROS (puede ser nulo)             | **Si**   |
| id_tienda             | int     | FK a MSTR_TIENDAS                              | No       |
| art_id                | int     | FK a MSTR_ARTICULOS                            | No       |
| fec_trans             | date    | Fecha de la transaccion                        | No       |
| hra_trans             | varchar | Hora de la transaccion                         | No       |
| qty_vendida           | int     | Cantidad vendida                               | No       |
| precio_unitario_venta | float   | Precio unitario en la venta                    | No       |
| descuento_aplicado    | float   | Descuento total aplicado a la linea            | No       |
| tipo_pago             | varchar | Efectivo / Tarjeta / Digital / etc.            | No       |
| canal_venta           | varchar | Fisica / Online / App                          | No       |

### INV_STOCK_DIARIO

| Campo              | Tipo  | Descripcion                                   | Sensible |
|--------------------|-------|-----------------------------------------------|----------|
| id_snapshot        | int   | Identificador del snapshot (PK)               | No       |
| art_id             | int   | FK a MSTR_ARTICULOS                           | No       |
| id_tienda          | int   | FK a MSTR_TIENDAS                             | No       |
| fec_snapshot       | date  | Fecha del snapshot de inventario              | No       |
| stock_fisico       | int   | Unidades fisicas en tienda                    | No       |
| stock_transito     | int   | Unidades en transito al reaprovisionamiento   | No       |
| stock_reservado    | int   | Unidades reservadas por ordenes pendientes    | No       |
| stock_minimo_config| int   | Stock minimo configurado para alerta          | No       |
| stock_maximo_config| int   | Stock maximo configurado                      | No       |

### POST_DEVOLUCIONES

| Campo              | Tipo    | Descripcion                                  | Sensible |
|--------------------|---------|----------------------------------------------|----------|
| id_devolucion      | int     | Identificador de devolucion (PK)             | No       |
| id_trans_origen    | int     | FK a TRANS_VENTAS                            | No       |
| art_id             | int     | FK a MSTR_ARTICULOS                          | No       |
| id_tienda          | int     | FK a MSTR_TIENDAS                            | No       |
| fec_devolucion     | date    | Fecha de la devolucion                       | No       |
| qty_devuelta       | int     | Cantidad devuelta                            | No       |
| motivo_cod         | varchar | Motivo legible: Defecto producto, etc.       | No       |
| canal_devolucion   | varchar | Canal por el que se realizo la devolucion    | No       |
| estado_devolucion  | varchar | Estado: pendiente / aprobada / rechazada     | No       |
| vr_reembolso       | float   | Valor monetario del reembolso                | No       |

---

## Vistas Gold (Capa Analitica)

### dim_productos

Enriquece el catalogo de articulos con datos del proveedor y calcula margen estimado.

| Campo                  | Tipo           | Origen                            | Descripcion                              |
|------------------------|----------------|-----------------------------------|------------------------------------------|
| product_id             | int            | MSTR_ARTICULOS.art_id             | Clave unica del articulo                 |
| barcode                | varchar        | MSTR_ARTICULOS.cod_barra          | Codigo de barras                         |
| product_name           | varchar        | MSTR_ARTICULOS.desc_art           | Nombre del articulo                      |
| category_level1        | int            | MSTR_ARTICULOS.id_categ_n1        | Jerarquia categoria nivel 1              |
| category_level2        | int            | MSTR_ARTICULOS.id_categ_n2        | Jerarquia categoria nivel 2              |
| category_level3        | int            | MSTR_ARTICULOS.id_categ_n3        | Jerarquia categoria nivel 3              |
| supplier_id            | int            | MSTR_ARTICULOS.id_proveedor       | FK al proveedor                          |
| supplier_name          | varchar        | MSTR_PROVEEDORES.razon_social     | Nombre del proveedor (JOIN Gold)         |
| supplier_country       | varchar        | MSTR_PROVEEDORES.pais_origen      | Pais del proveedor (JOIN Gold)           |
| supplier_quality_score | float          | MSTR_PROVEEDORES.calificacion_calidad | Calificacion de calidad del proveedor |
| list_price             | numeric        | MSTR_ARTICULOS.precio_lista       | Precio de lista                          |
| weight_kg              | float          | MSTR_ARTICULOS.peso_kg            | Peso en kg                               |
| unit_of_measure        | varchar        | MSTR_ARTICULOS.unid_medida        | Unidad de medida                         |
| is_active              | int            | MSTR_ARTICULOS.activo             | Estado activo                            |
| creation_date          | datetime       | MSTR_ARTICULOS.fec_alta           | Fecha alta en catalogo                   |
| **estimated_margin**   | **numeric(10,2)** | **Calculado: list_price * 0.30** | **Margen estimado del 30%**             |

**Linaje de campos calculados:**
- `estimated_margin` = `MSTR_ARTICULOS.precio_lista` × 0.30 — margen bruto estimado sin costes variables.

---

### dim_tiendas

| Campo               | Tipo    | Origen                        | Descripcion                                  |
|---------------------|---------|-------------------------------|----------------------------------------------|
| store_id            | int     | MSTR_TIENDAS.id_tienda        | Clave unica de la tienda                     |
| store_name          | varchar | MSTR_TIENDAS.nom_tienda       | Nombre de la tienda                          |
| store_type          | varchar | MSTR_TIENDAS.tipo_tienda      | Tipo de tienda                               |
| city_id             | int     | MSTR_TIENDAS.id_ciudad        | Ciudad                                       |
| country_id          | int     | MSTR_TIENDAS.id_pais          | Pais                                         |
| square_meters       | int     | MSTR_TIENDAS.metros_cuadrados | Superficie de la tienda                      |
| is_active           | int     | MSTR_TIENDAS.activo           | Estado activo                                |
| opening_date        | date    | MSTR_TIENDAS.fec_apertura     | Fecha de apertura                            |
| **zona_distribucion** | **varchar** | **Calculado: id_pais % 5** | **Zona logistica de distribucion**        |

**Linaje de campos calculados:**
- `zona_distribucion` = derivado de `id_pais % 5` → mapea cada pais a una de 5 zonas geograficas (Norte, Sur, Este, Oeste, Centro).

---

### dim_clientes

| Campo            | Tipo    | Origen                           | Descripcion                                        |
|------------------|---------|----------------------------------|----------------------------------------------------|
| customer_id      | int     | CRM_MIEMBROS.id_miembro          | Clave del cliente (hasheada en Silver)             |
| registration_date| date    | CRM_MIEMBROS.fec_registro        | Fecha de alta en CRM                               |
| city_id          | int     | CRM_MIEMBROS.id_ciudad           | Ciudad del cliente                                 |
| **gender**       | varchar | CRM_MIEMBROS.genero (estandarizado) | M / F / No_informado. 'O' o nulo → 'No_informado' |
| **age_range**    | varchar | CRM_MIEMBROS.rango_edad (imputado) | Imputado con moda por canal cuando es nulo        |
| preferred_channel| varchar | CRM_MIEMBROS.canal_pref          | Canal preferido de compra                          |
| is_active        | int     | CRM_MIEMBROS.activo              | Estado activo del cliente                          |
| last_purchase_date| date   | CRM_MIEMBROS.fec_ultima_compra   | Ultima compra                                      |
| **antiguedad_dias** | int  | **Calculado: DATEDIFF(fec_registro, HOY)** | **Dias desde el registro**              |

**Linaje de campos calculados:**
- `gender`: estandarizacion de `CRM_MIEMBROS.genero`. Valores 'M' y 'F' se conservan; cualquier otro → 'No_informado'.
- `age_range`: imputacion de nulos con la moda del mismo `canal_pref` (subconsulta correlacionada).
- `antiguedad_dias`: `DATEDIFF(DAY, fec_registro, GETDATE())`.

---

### fact_ventas

| Campo            | Tipo           | Origen                              | Descripcion                                   |
|------------------|----------------|-------------------------------------|-----------------------------------------------|
| sale_id          | int            | TRANS_VENTAS.id_trans               | Clave de transaccion                          |
| **customer_id**  | varchar        | TRANS_VENTAS.id_miembro (COALESCE)  | 'ANONIMO' cuando id_miembro es nulo           |
| store_id         | int            | TRANS_VENTAS.id_tienda              | Tienda                                        |
| product_id       | int            | TRANS_VENTAS.art_id                 | Articulo                                      |
| sale_date        | date           | TRANS_VENTAS.fec_trans              | Fecha de venta                                |
| quantity_sold    | int            | TRANS_VENTAS.qty_vendida            | Unidades vendidas                             |
| unit_price       | float          | TRANS_VENTAS.precio_unitario_venta  | Precio unitario aplicado                      |
| discount_amount  | float          | TRANS_VENTAS.descuento_aplicado     | Descuento aplicado                            |
| payment_type     | varchar        | TRANS_VENTAS.tipo_pago              | Forma de pago                                 |
| sales_channel    | varchar        | TRANS_VENTAS.canal_venta            | Canal de venta                                |
| gross_amount     | numeric(12,2)  | qty * unit_price                    | Importe bruto                                 |
| discount_value   | numeric(12,2)  | descuento_aplicado                  | Importe del descuento                         |
| net_amount       | numeric(12,2)  | gross_amount - discount_value       | Importe neto de la venta                      |
| **ind_con_descuento** | int      | **Calculado: descuento > 0**        | **1 si la venta tiene descuento aplicado**    |
| year_sale        | int            | YEAR(fec_trans)                     | Ano de la venta                               |
| month_sale       | int            | MONTH(fec_trans)                    | Mes de la venta                               |
| day_sale         | int            | DAY(fec_trans)                      | Dia de la venta                               |

**Linaje de campos calculados:**
- `customer_id`: `COALESCE(CAST(id_miembro AS NVARCHAR), 'ANONIMO')` — ventas sin cliente identificado se agrupan bajo 'ANONIMO'.
- `ind_con_descuento`: `CASE WHEN descuento_aplicado > 0 THEN 1 ELSE 0 END`.

---

### fact_inventario

| Campo                 | Tipo           | Origen                           | Descripcion                                           |
|-----------------------|----------------|----------------------------------|-------------------------------------------------------|
| inventory_id          | int            | INV_STOCK_DIARIO.id_snapshot     | Clave del snapshot                                    |
| product_id            | int            | INV_STOCK_DIARIO.art_id          | Articulo                                              |
| store_id              | int            | INV_STOCK_DIARIO.id_tienda       | Tienda                                                |
| snapshot_date         | date           | INV_STOCK_DIARIO.fec_snapshot    | Fecha del snapshot                                    |
| physical_stock        | int            | INV_STOCK_DIARIO.stock_fisico    | Stock fisico                                          |
| in_transit_stock      | int            | INV_STOCK_DIARIO.stock_transito  | Stock en transito                                     |
| reserved_stock        | int            | INV_STOCK_DIARIO.stock_reservado | Stock reservado                                       |
| min_stock_config      | int            | INV_STOCK_DIARIO.stock_minimo_config | Minimo configurado                               |
| max_stock_config      | int            | INV_STOCK_DIARIO.stock_maximo_config | Maximo configurado                               |
| available_stock       | numeric(10,2)  | stock_fisico - stock_reservado   | Stock disponible real                                 |
| **avg_daily_sales_14d** | numeric(10,4)| **CTE ventas_14d por art+tienda** | **Promedio unidades vendidas por dia (14 dias)**    |
| **cobertura_dias**    | numeric(10,2)  | **stock_fisico / avg_daily_sales_14d** | **Dias estimados de cobertura de inventario**  |
| **alerta_quiebre**    | int            | **cobertura_dias < 7 AND demanda > 0** | **1 = riesgo de quiebre en menos de 7 dias**   |
| year_snapshot         | int            | YEAR(fec_snapshot)               | Ano del snapshot                                      |
| month_snapshot        | int            | MONTH(fec_snapshot)              | Mes del snapshot                                      |

**Linaje de campos calculados:**
- `avg_daily_sales_14d`: CTE `ventas_14d` sobre TRANS_VENTAS de los ultimos 14 dias → `SUM(qty_vendida) / 14.0` por (art_id, id_tienda).
- `cobertura_dias`: `stock_fisico / avg_daily_sales_14d`. NULL cuando no hay ventas en los ultimos 14 dias.
- `alerta_quiebre`: 1 cuando `avg_daily_sales_14d > 0 AND cobertura_dias < 7`.

---

### fact_devoluciones

| Campo                  | Tipo           | Origen                               | Descripcion                                          |
|------------------------|----------------|--------------------------------------|------------------------------------------------------|
| return_id              | int            | POST_DEVOLUCIONES.id_devolucion      | Clave de devolucion                                  |
| origin_sale_id         | int            | POST_DEVOLUCIONES.id_trans_origen    | Transaccion de venta original                        |
| product_id             | int            | POST_DEVOLUCIONES.art_id             | Articulo devuelto                                    |
| store_id               | int            | POST_DEVOLUCIONES.id_tienda          | Tienda donde se proceso la devolucion                |
| return_date            | date           | POST_DEVOLUCIONES.fec_devolucion     | Fecha de la devolucion                               |
| quantity_returned      | int            | POST_DEVOLUCIONES.qty_devuelta       | Cantidad devuelta                                    |
| reason_code            | varchar        | POST_DEVOLUCIONES.motivo_cod         | Motivo de la devolucion (descripcion legible)        |
| return_channel         | varchar        | POST_DEVOLUCIONES.canal_devolucion   | Canal de la devolucion                               |
| return_status          | varchar        | POST_DEVOLUCIONES.estado_devolucion  | Estado de la devolucion                              |
| refund_amount          | float          | POST_DEVOLUCIONES.vr_reembolso       | Valor del reembolso                                  |
| **original_unit_price**| float          | **TRANS_VENTAS.precio_unitario_venta** | **Precio unitario de la venta original (JOIN)**    |
| **return_rate_by_product** | numeric(10,4) | **CTE tasa_art**                | **Tasa de devolucion del articulo respecto a ventas**|
| year_return            | int            | YEAR(fec_devolucion)                 | Ano de la devolucion                                 |
| month_return           | int            | MONTH(fec_devolucion)                | Mes de la devolucion                                 |

**Linaje de campos calculados:**
- `original_unit_price`: JOIN LEFT con TRANS_VENTAS por `id_trans_origen = id_trans`.
- `return_rate_by_product`: CTE `tasa_art` → `SUM(qty_devuelta) / SUM(qty_vendida)` agrupado por `art_id`.

---

### fact_rfm_clientes

| Campo              | Tipo           | Origen / Calculo                              | Descripcion                        |
|--------------------|----------------|-----------------------------------------------|------------------------------------|
| customer_id        | int            | CRM_MIEMBROS.id_miembro                       | Cliente                            |
| recency_days       | int            | DATEDIFF(MAX(fec_trans), HOY)                 | Dias desde la ultima compra (90d)  |
| frequency_purchases| int            | COUNT(DISTINCT id_trans)                      | Numero de transacciones en 90 dias |
| monetary_value     | numeric(12,2)  | SUM(qty * precio - descuento)                 | Valor monetario en 90 dias         |
| r_score            | int            | NTILE(5) ORDER BY recency DESC                | Quintil de recencia (1-5)          |
| f_score            | int            | NTILE(5) ORDER BY frequency ASC               | Quintil de frecuencia (1-5)        |
| m_score            | int            | NTILE(5) ORDER BY monetary ASC                | Quintil de monetario (1-5)         |
| rfm_segment        | varchar        | CONCAT('R', r, '-F', f, '-M', m)              | Codigo de segmento RFM             |
| rfm_classification | varchar        | Regla Champions/Loyal/At_Risk/Other           | Clasificacion textual              |
| status_90d         | varchar        | frequency > 0 → active_90d                   | Actividad en los ultimos 90 dias   |
| calculation_date   | date           | GETDATE()                                     | Fecha de calculo                   |

---

### kpi_ejecutivo

Resumen diario de ventas por pais y canal. Vista para reportes ejecutivos y dashboards.

| Campo                | Tipo           | Origen / Calculo                   | Descripcion                              |
|----------------------|----------------|------------------------------------|------------------------------------------|
| fecha                | date           | TRANS_VENTAS.fec_trans             | Fecha del dia                            |
| country_id           | int            | MSTR_TIENDAS.id_pais (JOIN)        | Pais de la tienda                        |
| sales_channel        | varchar        | TRANS_VENTAS.canal_venta           | Canal de venta                           |
| total_transacciones  | int            | COUNT(DISTINCT id_trans)           | Total de transacciones del dia           |
| clientes_unicos      | int            | COUNT(DISTINCT id_miembro)         | Clientes unicos del dia                  |
| unidades_vendidas    | int            | SUM(qty_vendida)                   | Unidades vendidas                        |
| ventas_brutas        | numeric(14,2)  | SUM(qty * precio)                  | Importe bruto sin descuentos             |
| descuentos_totales   | numeric(14,2)  | SUM(descuento_aplicado)            | Total de descuentos aplicados            |
| ventas_netas         | numeric(14,2)  | ventas_brutas - descuentos_totales | Importe neto                             |
| anio                 | int            | YEAR(fec_trans)                    | Ano                                      |
| mes                  | int            | MONTH(fec_trans)                   | Mes                                      |

---

## Campos PII y Estrategia de Enmascaramiento

| Campo           | Tabla         | Estrategia en Silver               | Estrategia en Gold                   |
|-----------------|---------------|------------------------------------|--------------------------------------|
| id_miembro      | CRM_MIEMBROS  | Hash SHA-256 en cleaning.py        | Se muestra como integer (FK interna) |
| id_miembro      | TRANS_VENTAS  | Sin modificacion en tabla fuente   | COALESCE → 'ANONIMO' si es NULL      |
| genero          | CRM_MIEMBROS  | Sin modificacion                   | Categorizado: M / F / No_informado   |
| rango_edad      | CRM_MIEMBROS  | Sin modificacion                   | Imputado con moda por canal          |

> Los campos de identificacion directa de clientes no se exponen en vistas Gold excepto como claves internas.

---

## Acceso por Rol (Fase 5 RBAC)

| Recurso                         | Ingeniero de Datos      | Analista de Datos       | Administrador |
|---------------------------------|-------------------------|-------------------------|---------------|
| Contenedor Bronze               | Lectura y escritura     | **Denegado**            | Control total |
| Contenedor Silver               | Lectura y escritura     | **Denegado**            | Control total |
| Contenedor Gold                 | Lectura y escritura     | Solo lectura            | Control total |
| Azure SQL (sqldb-retailmax)     | Contributor             | db_datareader via portal| Control total |
| Azure Data Factory              | Sin asignacion directa  | Sin acceso              | Control total |
| Resource Group completo         | Sin asignacion directa  | Sin acceso              | Owner         |

Script de asignacion: `orchestration/deploy_rbac.py`
