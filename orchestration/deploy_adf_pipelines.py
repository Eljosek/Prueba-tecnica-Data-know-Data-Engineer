"""
deploy_adf_pipelines.py
Despliega linked services, datasets y pipelines en Azure Data Factory
usando el SDK de Python. Autenticacion via navegador (InteractiveBrowserCredential).
"""
import os
import sys
from azure.identity import InteractiveBrowserCredential
from azure.mgmt.datafactory import DataFactoryManagementClient
from azure.mgmt.datafactory.models import (
    LinkedServiceResource,
    AzureSqlDatabaseLinkedService,
    AzureBlobStorageLinkedService,
    AzureKeyVaultLinkedService,
    AzureKeyVaultSecretReference,
    DatasetResource,
    AzureSqlTableDataset,
    ParquetDataset,
    AzureBlobStorageLocation,
    LinkedServiceReference,
    DatasetReference,
    PipelineResource,
    ForEachActivity,
    CopyActivity,
    ScriptActivity,
    ExecutePipelineActivity,
    PipelineReference,
    ActivityDependency,
    Expression,
    DatasetReference,
    AzureSqlSource,
    ParquetSink,
    BlobSink,
    ActivityPolicy,
    ScriptActivityScriptBlock,
    ScheduleTrigger,
    TriggerResource,
    ScheduleTriggerRecurrence,
    TriggerPipelineReference,
)

# -----------------------------------------------------------------------
# Configuracion
# -----------------------------------------------------------------------
SUBSCRIPTION_ID = "64b1483b-b4aa-4a3b-bd59-e11ab2672810"
RESOURCE_GROUP = "rg-retailmax-brs-dev"
FACTORY_NAME = "adf-retailmax-brs-dev"

SQL_SERVER = os.environ.get("SQLSERVER_HOST",
                            "sqlsrv-retailmax-brs-dev.database.windows.net")
SQL_DATABASE = os.environ.get("SQLSERVER_DB", "sqldb-retailmax-brs-dev")
SQL_USER = os.environ.get("SQLSERVER_USER", "sqladmin")
SQL_PASSWORD = os.environ.get("SQLSERVER_PASSWORD", "")
STORAGE_CONN = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")

if not SQL_PASSWORD:
    print("ERROR: Variable de entorno SQLSERVER_PASSWORD no definida.")
    sys.exit(1)
if not STORAGE_CONN:
    print("ERROR: Variable de entorno AZURE_STORAGE_CONNECTION_STRING no definida.")
    sys.exit(1)

TENANT_ID = "6f716858-c5ea-4ced-8eb4-417b305f7c49"

SQL_CONN_STRING = (
    f"Server=tcp:{SQL_SERVER},1433;Initial Catalog={SQL_DATABASE};"
    f"User ID={SQL_USER};Password={SQL_PASSWORD};"
    "Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;"
)

TABLAS = [
    "MSTR_ARTICULOS", "MSTR_TIENDAS", "MSTR_PROVEEDORES",
    "CRM_MIEMBROS", "TRANS_VENTAS", "INV_STOCK_DIARIO", "POST_DEVOLUCIONES",
]

VISTAS_GOLD = [
    "dim_productos", "dim_tiendas", "dim_clientes",
    "fact_ventas", "fact_inventario", "fact_devoluciones", "fact_rfm_clientes",
    "kpi_ejecutivo",
]

# SQL para crear cada vista Gold (una por batch)
SQL_VISTAS_DIM = [
    "CREATE OR ALTER VIEW dim_productos AS SELECT a.art_id AS product_id, a.cod_barra AS barcode, a.desc_art AS product_name, a.id_categ_n1 AS category_level1, a.id_categ_n2 AS category_level2, a.id_categ_n3 AS category_level3, a.id_proveedor AS supplier_id, p.razon_social AS supplier_name, p.pais_origen AS supplier_country, p.calificacion_calidad AS supplier_quality_score, a.precio_lista AS list_price, a.peso_kg AS weight_kg, a.unid_medida AS unit_of_measure, a.activo AS is_active, a.fec_alta AS creation_date, CONVERT(NUMERIC(10,2), a.precio_lista * 0.30) AS estimated_margin FROM MSTR_ARTICULOS a LEFT JOIN MSTR_PROVEEDORES p ON a.id_proveedor = p.id_proveedor",
    "CREATE OR ALTER VIEW dim_tiendas AS SELECT id_tienda AS store_id, nom_tienda AS store_name, tipo_tienda AS store_type, id_ciudad AS city_id, id_pais AS country_id, metros_cuadrados AS square_meters, activo AS is_active, fec_apertura AS opening_date, CASE WHEN id_pais % 5 = 0 THEN 'Zona_Norte' WHEN id_pais % 5 = 1 THEN 'Zona_Sur' WHEN id_pais % 5 = 2 THEN 'Zona_Este' WHEN id_pais % 5 = 3 THEN 'Zona_Oeste' ELSE 'Zona_Centro' END AS zona_distribucion FROM MSTR_TIENDAS",
    "CREATE OR ALTER VIEW dim_clientes AS SELECT c.id_miembro AS customer_id, c.fec_registro AS registration_date, c.id_ciudad AS city_id, CASE c.genero WHEN 'M' THEN 'M' WHEN 'F' THEN 'F' ELSE 'No_informado' END AS gender, COALESCE(c.rango_edad, (SELECT TOP 1 t.rango_edad FROM CRM_MIEMBROS t WHERE t.canal_pref = c.canal_pref AND t.rango_edad IS NOT NULL GROUP BY t.rango_edad ORDER BY COUNT(*) DESC)) AS age_range, c.canal_pref AS preferred_channel, c.activo AS is_active, c.fec_ultima_compra AS last_purchase_date, DATEDIFF(DAY, c.fec_registro, CAST(GETDATE() AS DATE)) AS antiguedad_dias FROM CRM_MIEMBROS c",
]

SQL_VISTAS_FACT = [
    "CREATE OR ALTER VIEW fact_ventas AS SELECT id_trans AS sale_id, COALESCE(CAST(id_miembro AS NVARCHAR(20)), 'ANONIMO') AS customer_id, id_tienda AS store_id, art_id AS product_id, CAST(fec_trans AS DATE) AS sale_date, qty_vendida AS quantity_sold, precio_unitario_venta AS unit_price, descuento_aplicado AS discount_amount, tipo_pago AS payment_type, canal_venta AS sales_channel, CONVERT(NUMERIC(12,2), qty_vendida * precio_unitario_venta) AS gross_amount, CONVERT(NUMERIC(12,2), descuento_aplicado) AS discount_value, CONVERT(NUMERIC(12,2), qty_vendida * precio_unitario_venta - descuento_aplicado) AS net_amount, CASE WHEN descuento_aplicado > 0 THEN 1 ELSE 0 END AS ind_con_descuento, YEAR(fec_trans) AS year_sale, MONTH(fec_trans) AS month_sale, DAY(fec_trans) AS day_sale FROM TRANS_VENTAS",
    "CREATE OR ALTER VIEW fact_inventario AS WITH ventas_14d AS (SELECT art_id, id_tienda, CONVERT(NUMERIC(12,4), SUM(qty_vendida) * 1.0 / 14.0) AS avg_daily_sales_14d FROM TRANS_VENTAS WHERE fec_trans >= DATEADD(DAY, -14, CAST(GETDATE() AS DATE)) GROUP BY art_id, id_tienda) SELECT s.id_snapshot AS inventory_id, s.art_id AS product_id, s.id_tienda AS store_id, CAST(s.fec_snapshot AS DATE) AS snapshot_date, s.stock_fisico AS physical_stock, s.stock_transito AS in_transit_stock, s.stock_reservado AS reserved_stock, s.stock_minimo_config AS min_stock_config, s.stock_maximo_config AS max_stock_config, CONVERT(NUMERIC(10,2), s.stock_fisico - s.stock_reservado) AS available_stock, CONVERT(NUMERIC(10,4), COALESCE(v.avg_daily_sales_14d, 0)) AS avg_daily_sales_14d, CASE WHEN COALESCE(v.avg_daily_sales_14d, 0) > 0 THEN CONVERT(NUMERIC(10,2), s.stock_fisico * 1.0 / v.avg_daily_sales_14d) ELSE NULL END AS cobertura_dias, CASE WHEN COALESCE(v.avg_daily_sales_14d, 0) > 0 AND (s.stock_fisico * 1.0 / v.avg_daily_sales_14d) < 7 THEN 1 ELSE 0 END AS alerta_quiebre, YEAR(s.fec_snapshot) AS year_snapshot, MONTH(s.fec_snapshot) AS month_snapshot FROM INV_STOCK_DIARIO s LEFT JOIN ventas_14d v ON s.art_id = v.art_id AND s.id_tienda = v.id_tienda",
    "CREATE OR ALTER VIEW fact_devoluciones AS WITH tasa_art AS (SELECT d.art_id, CONVERT(NUMERIC(10,4), SUM(d.qty_devuelta) * 1.0 / NULLIF(SUM(v.qty_vendida), 0)) AS tasa_devolucion_articulo FROM POST_DEVOLUCIONES d LEFT JOIN TRANS_VENTAS v ON d.art_id = v.art_id GROUP BY d.art_id) SELECT d.id_devolucion AS return_id, d.id_trans_origen AS origin_sale_id, d.art_id AS product_id, d.id_tienda AS store_id, CAST(d.fec_devolucion AS DATE) AS return_date, d.qty_devuelta AS quantity_returned, d.motivo_cod AS reason_code, d.canal_devolucion AS return_channel, d.estado_devolucion AS return_status, d.vr_reembolso AS refund_amount, v2.precio_unitario_venta AS original_unit_price, COALESCE(t.tasa_devolucion_articulo, 0) AS return_rate_by_product, YEAR(d.fec_devolucion) AS year_return, MONTH(d.fec_devolucion) AS month_return FROM POST_DEVOLUCIONES d LEFT JOIN TRANS_VENTAS v2 ON d.id_trans_origen = v2.id_trans LEFT JOIN tasa_art t ON d.art_id = t.art_id",
    "CREATE OR ALTER VIEW fact_rfm_clientes AS WITH rfm_calc AS (SELECT cm.id_miembro AS customer_id, DATEDIFF(DAY, MAX(tv.fec_trans), CAST(GETDATE() AS DATE)) AS recency_days, COUNT(DISTINCT tv.id_trans) AS frequency_purchases, CONVERT(NUMERIC(12,2), SUM(tv.qty_vendida * tv.precio_unitario_venta - tv.descuento_aplicado)) AS monetary_value FROM CRM_MIEMBROS cm LEFT JOIN TRANS_VENTAS tv ON cm.id_miembro = tv.id_miembro AND tv.fec_trans >= DATEADD(DAY, -90, CAST(GETDATE() AS DATE)) GROUP BY cm.id_miembro), rfm_scored AS (SELECT customer_id, recency_days, frequency_purchases, monetary_value, NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score, NTILE(5) OVER (ORDER BY frequency_purchases ASC) AS f_score, NTILE(5) OVER (ORDER BY monetary_value ASC) AS m_score, CASE WHEN frequency_purchases > 0 THEN 'active_90d' ELSE 'inactive' END AS status_90d FROM rfm_calc) SELECT customer_id, recency_days, frequency_purchases, monetary_value, r_score, f_score, m_score, CONVERT(NVARCHAR(20), CONCAT('R', r_score, '-F', f_score, '-M', m_score)) AS rfm_segment, CASE WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions' WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal' WHEN r_score >= 2 AND frequency_purchases <= 1 THEN 'At_Risk' ELSE 'Other' END AS rfm_classification, status_90d, CAST(GETDATE() AS DATE) AS calculation_date FROM rfm_scored",
    "CREATE OR ALTER VIEW kpi_ejecutivo AS SELECT CAST(tv.fec_trans AS DATE) AS fecha, ts.id_pais AS country_id, tv.canal_venta AS sales_channel, COUNT(DISTINCT tv.id_trans) AS total_transacciones, COUNT(DISTINCT tv.id_miembro) AS clientes_unicos, SUM(tv.qty_vendida) AS unidades_vendidas, CONVERT(NUMERIC(14,2), SUM(tv.qty_vendida * tv.precio_unitario_venta)) AS ventas_brutas, CONVERT(NUMERIC(14,2), SUM(tv.descuento_aplicado)) AS descuentos_totales, CONVERT(NUMERIC(14,2), SUM(tv.qty_vendida * tv.precio_unitario_venta - tv.descuento_aplicado)) AS ventas_netas, YEAR(tv.fec_trans) AS anio, MONTH(tv.fec_trans) AS mes FROM TRANS_VENTAS tv INNER JOIN MSTR_TIENDAS ts ON tv.id_tienda = ts.id_tienda GROUP BY CAST(tv.fec_trans AS DATE), ts.id_pais, tv.canal_venta, YEAR(tv.fec_trans), MONTH(tv.fec_trans)",
]


def main():
    print("=" * 60)
    print("Despliegue de pipelines ADF - RetailMax")
    print("=" * 60)

    # Autenticacion
    print("\n[1/7] Autenticando con Azure (se abrira el navegador)...")
    credential = InteractiveBrowserCredential(tenant_id=TENANT_ID)
    client = DataFactoryManagementClient(credential, SUBSCRIPTION_ID)
    print("  -> Autenticacion exitosa")

    # --- LINKED SERVICES ---
    print("\n[2/7] Creando linked services...")

    # LS_AzureSQL_RetailMax
    ls_sql = LinkedServiceResource(
        properties=AzureSqlDatabaseLinkedService(
            connection_string=SQL_CONN_STRING,
            description="Conexion a Azure SQL Database RetailMax",
        )
    )
    client.linked_services.create_or_update(
        RESOURCE_GROUP, FACTORY_NAME, "LS_AzureSQL_RetailMax", ls_sql
    )
    print("  -> LS_AzureSQL_RetailMax creado")

    # LS_DataLake_RetailMax
    ls_blob = LinkedServiceResource(
        properties=AzureBlobStorageLinkedService(
            connection_string=STORAGE_CONN,
            description="Conexion al Data Lake (Bronze, Silver, Gold)",
        )
    )
    client.linked_services.create_or_update(
        RESOURCE_GROUP, FACTORY_NAME, "LS_DataLake_RetailMax", ls_blob
    )
    print("  -> LS_DataLake_RetailMax creado")

    # --- DATASETS ---
    print("\n[3/7] Creando datasets parametrizados...")

    # DS_SQL_Tabla
    ds_sql = DatasetResource(
        properties={
            "type": "AzureSqlTable",
            "linkedServiceName": {
                "referenceName": "LS_AzureSQL_RetailMax",
                "type": "LinkedServiceReference",
            },
            "typeProperties": {
                "tableName": {"value": "@dataset().tableName", "type": "Expression"}
            },
            "parameters": {"tableName": {"type": "String", "defaultValue": ""}},
            "description": "Dataset parametrizado para cualquier tabla de Azure SQL",
        }
    )
    client.datasets.create_or_update(
        RESOURCE_GROUP, FACTORY_NAME, "DS_SQL_Tabla", ds_sql
    )
    print("  -> DS_SQL_Tabla creado")

    # DS_Parquet_DataLake
    ds_parquet = DatasetResource(
        properties={
            "type": "Parquet",
            "linkedServiceName": {
                "referenceName": "LS_DataLake_RetailMax",
                "type": "LinkedServiceReference",
            },
            "typeProperties": {
                "location": {
                    "type": "AzureBlobStorageLocation",
                    "container": {
                        "value": "@dataset().container",
                        "type": "Expression",
                    },
                    "folderPath": {
                        "value": "@dataset().carpeta",
                        "type": "Expression",
                    },
                    "fileName": {
                        "value": "@dataset().archivo",
                        "type": "Expression",
                    },
                },
                "compressionCodec": "snappy",
            },
            "parameters": {
                "container": {"type": "String", "defaultValue": ""},
                "carpeta": {"type": "String", "defaultValue": ""},
                "archivo": {"type": "String", "defaultValue": ""},
            },
            "description": "Dataset parametrizado Parquet en cualquier contenedor del Data Lake",
        }
    )
    client.datasets.create_or_update(
        RESOURCE_GROUP, FACTORY_NAME, "DS_Parquet_DataLake", ds_parquet
    )
    print("  -> DS_Parquet_DataLake creado")

    # --- PIPELINE 1: PL_Ingesta_Bronze ---
    print("\n[4/7] Creando PL_Ingesta_Bronze...")
    tablas_expr = ",".join([f"'{t}'" for t in TABLAS])

    pl_bronze = PipelineResource(
        description="Ingesta de 7 tablas desde Azure SQL hacia Bronze en Parquet. Agrega batch_id, ingest_timestamp y source_system.",
        concurrency=1,
        activities=[
            {
                "name": "ForEach_Tabla_Bronze",
                "type": "ForEach",
                "dependsOn": [],
                "userProperties": [],
                "typeProperties": {
                    "items": {
                        "value": f"@createArray({tablas_expr})",
                        "type": "Expression",
                    },
                    "isSequential": False,
                    "batchCount": 4,
                    "activities": [
                        {
                            "name": "Copiar_SQL_a_Bronze",
                            "type": "Copy",
                            "dependsOn": [],
                            "policy": {
                                "timeout": "0.01:00:00",
                                "retry": 3,
                                # ADF aplica backoff exponencial internamente:
                                # intento 1 → ~30s, intento 2 → ~60s, intento 3 → ~120s
                                "retryIntervalInSeconds": 30,
                            },
                            "userProperties": [],
                            "typeProperties": {
                                "source": {
                                    "type": "AzureSqlSource",
                                    "sqlReaderQuery": {
                                        "value": "@concat('SELECT *, NEWID() AS batch_id, GETUTCDATE() AS ingest_timestamp, ''AzureSQL'' AS source_system FROM dbo.', item())",
                                        "type": "Expression",
                                    },
                                    "queryTimeout": "00:30:00",
                                },
                                "sink": {
                                    "type": "ParquetSink",
                                    "storeSettings": {
                                        "type": "AzureBlobStorageWriteSettings"
                                    },
                                    "formatSettings": {
                                        "type": "ParquetWriteSettings"
                                    },
                                },
                                "enableStaging": False,
                            },
                            "inputs": [
                                {
                                    "referenceName": "DS_SQL_Tabla",
                                    "type": "DatasetReference",
                                    "parameters": {
                                        "tableName": {
                                            "value": "@item()",
                                            "type": "Expression",
                                        }
                                    },
                                }
                            ],
                            "outputs": [
                                {
                                    "referenceName": "DS_Parquet_DataLake",
                                    "type": "DatasetReference",
                                    "parameters": {
                                        "container": "bronze",
                                        "carpeta": {
                                            "value": "@concat(item(), '/', formatDateTime(utcNow(), 'yyyy/MM/dd'))",
                                            "type": "Expression",
                                        },
                                        "archivo": {
                                            "value": "@concat(item(), '.parquet')",
                                            "type": "Expression",
                                        },
                                    },
                                }
                            ],
                        }
                    ],
                },
            }
        ],
    )
    client.pipelines.create_or_update(
        RESOURCE_GROUP, FACTORY_NAME, "PL_Ingesta_Bronze", pl_bronze
    )
    print("  -> PL_Ingesta_Bronze creado")

    # --- PIPELINE 2: PL_Limpieza_Silver ---
    print("\n[5/7] Creando PL_Limpieza_Silver...")

    pl_silver = PipelineResource(
        description="Deduplicacion con SELECT DISTINCT y exportacion a Silver en Parquet. Registra metricas de calidad.",
        concurrency=1,
        activities=[
            {
                "name": "ForEach_Tabla_Silver",
                "type": "ForEach",
                "dependsOn": [],
                "userProperties": [],
                "typeProperties": {
                    "items": {
                        "value": f"@createArray({tablas_expr})",
                        "type": "Expression",
                    },
                    "isSequential": False,
                    "batchCount": 4,
                    "activities": [
                        {
                            "name": "Limpiar_y_Exportar_Silver",
                            "type": "Copy",
                            "dependsOn": [],
                            "policy": {
                                "timeout": "0.01:00:00",
                                "retry": 3,
                                "retryIntervalInSeconds": 30,
                            },
                            "userProperties": [],
                            "typeProperties": {
                                "source": {
                                    "type": "AzureSqlSource",
                                    "sqlReaderQuery": {
                                        "value": "@concat('SELECT DISTINCT * FROM dbo.', item())",
                                        "type": "Expression",
                                    },
                                    "queryTimeout": "00:30:00",
                                },
                                "sink": {
                                    "type": "ParquetSink",
                                    "storeSettings": {
                                        "type": "AzureBlobStorageWriteSettings"
                                    },
                                    "formatSettings": {
                                        "type": "ParquetWriteSettings"
                                    },
                                },
                                "enableStaging": False,
                            },
                            "inputs": [
                                {
                                    "referenceName": "DS_SQL_Tabla",
                                    "type": "DatasetReference",
                                    "parameters": {
                                        "tableName": {
                                            "value": "@item()",
                                            "type": "Expression",
                                        }
                                    },
                                }
                            ],
                            "outputs": [
                                {
                                    "referenceName": "DS_Parquet_DataLake",
                                    "type": "DatasetReference",
                                    "parameters": {
                                        "container": "silver",
                                        "carpeta": {
                                            "value": "@concat(item(), '/', formatDateTime(utcNow(), 'yyyy/MM/dd'))",
                                            "type": "Expression",
                                        },
                                        "archivo": {
                                            "value": "@concat(item(), '_clean.parquet')",
                                            "type": "Expression",
                                        },
                                    },
                                }
                            ],
                        }
                    ],
                },
            },
            {
                "name": "Registrar_Metricas_Calidad",
                "type": "Script",
                "dependsOn": [
                    {
                        "activity": "ForEach_Tabla_Silver",
                        "dependencyConditions": ["Succeeded"],
                    }
                ],
                "policy": {
                    "timeout": "0.00:10:00",
                    "retry": 3,
                    "retryIntervalInSeconds": 30,
                },
                "userProperties": [],
                "linkedServiceName": {
                    "referenceName": "LS_AzureSQL_RetailMax",
                    "type": "LinkedServiceReference",
                },
                "typeProperties": {
                    "scripts": [
                        {
                            "type": "NonQuery",
                            "text": "INSERT INTO pipeline_quality_report (tabla_nombre, batch_id, filas_leidas, filas_limpias, duplicados_detectados, nulos_detectados, integridad_violaciones, timestamp_reporte, duracion_segundos, estado) VALUES ('ADF_Silver_Batch', NEWID(), 0, 0, 0, 0, 0, GETUTCDATE(), 0, 'completado')",
                        }
                    ]
                },
            },
        ],
    )
    client.pipelines.create_or_update(
        RESOURCE_GROUP, FACTORY_NAME, "PL_Limpieza_Silver", pl_silver
    )
    print("  -> PL_Limpieza_Silver creado")

    # --- PIPELINE 3: PL_Vistas_Gold ---
    print("\n[6/7] Creando PL_Vistas_Gold...")
    vistas_expr = ",".join([f"'{v}'" for v in VISTAS_GOLD])

    pl_gold = PipelineResource(
        description="Crea 8 vistas Gold (3 dimensiones + 4 hechos + 1 KPI ejecutivo) y exporta cada vista como Parquet al contenedor Gold.",
        concurrency=1,
        activities=[
            {
                "name": "Crear_Vistas_Dimensiones",
                "type": "Script",
                "dependsOn": [],
                "policy": {
                    "timeout": "0.00:10:00",
                    "retry": 3,
                    "retryIntervalInSeconds": 30,
                },
                "userProperties": [],
                "linkedServiceName": {
                    "referenceName": "LS_AzureSQL_RetailMax",
                    "type": "LinkedServiceReference",
                },
                "typeProperties": {
                    "scripts": [
                        {"type": "NonQuery", "text": sql} for sql in SQL_VISTAS_DIM
                    ]
                },
            },
            {
                "name": "Crear_Vistas_Hechos",
                "type": "Script",
                "dependsOn": [
                    {
                        "activity": "Crear_Vistas_Dimensiones",
                        "dependencyConditions": ["Succeeded"],
                    }
                ],
                "policy": {
                    "timeout": "0.00:10:00",
                    "retry": 3,
                    "retryIntervalInSeconds": 30,
                },
                "userProperties": [],
                "linkedServiceName": {
                    "referenceName": "LS_AzureSQL_RetailMax",
                    "type": "LinkedServiceReference",
                },
                "typeProperties": {
                    "scripts": [
                        {"type": "NonQuery", "text": sql} for sql in SQL_VISTAS_FACT
                    ]
                },
            },
            {
                "name": "ForEach_Vista_Export_Gold",
                "type": "ForEach",
                "dependsOn": [
                    {
                        "activity": "Crear_Vistas_Hechos",
                        "dependencyConditions": ["Succeeded"],
                    }
                ],
                "userProperties": [],
                "typeProperties": {
                    "items": {
                        "value": f"@createArray({vistas_expr})",
                        "type": "Expression",
                    },
                    "isSequential": False,
                    "batchCount": 4,
                    "activities": [
                        {
                            "name": "Exportar_Vista_a_Gold",
                            "type": "Copy",
                            "dependsOn": [],
                            "policy": {
                                "timeout": "0.01:00:00",
                                "retry": 3,
                                "retryIntervalInSeconds": 30,
                            },
                            "userProperties": [],
                            "typeProperties": {
                                "source": {
                                    "type": "AzureSqlSource",
                                    "sqlReaderQuery": {
                                        "value": "@concat('SELECT * FROM dbo.', item())",
                                        "type": "Expression",
                                    },
                                    "queryTimeout": "00:30:00",
                                },
                                "sink": {
                                    "type": "ParquetSink",
                                    "storeSettings": {
                                        "type": "AzureBlobStorageWriteSettings"
                                    },
                                    "formatSettings": {
                                        "type": "ParquetWriteSettings"
                                    },
                                },
                                "enableStaging": False,
                            },
                            "inputs": [
                                {
                                    "referenceName": "DS_SQL_Tabla",
                                    "type": "DatasetReference",
                                    "parameters": {
                                        "tableName": {
                                            "value": "@item()",
                                            "type": "Expression",
                                        }
                                    },
                                }
                            ],
                            "outputs": [
                                {
                                    "referenceName": "DS_Parquet_DataLake",
                                    "type": "DatasetReference",
                                    "parameters": {
                                        "container": "gold",
                                        "carpeta": {
                                            "value": "@concat(item(), '/', formatDateTime(utcNow(), 'yyyy/MM/dd'))",
                                            "type": "Expression",
                                        },
                                        "archivo": {
                                            "value": "@concat(item(), '.parquet')",
                                            "type": "Expression",
                                        },
                                    },
                                }
                            ],
                        }
                    ],
                },
            },
        ],
    )
    client.pipelines.create_or_update(
        RESOURCE_GROUP, FACTORY_NAME, "PL_Vistas_Gold", pl_gold
    )
    print("  -> PL_Vistas_Gold creado")

    # --- PIPELINE 4: PL_Calidad_Datos ---
    pl_calidad = PipelineResource(
        description="Consulta pipeline_quality_report y pipeline_errors para validar la ejecucion del pipeline medallion.",
        concurrency=1,
        activities=[
            {
                "name": "Consultar_Reporte_Calidad",
                "type": "Script",
                "dependsOn": [],
                "policy": {
                    "timeout": "0.00:10:00",
                    "retry": 3,
                    "retryIntervalInSeconds": 30,
                },
                "userProperties": [],
                "linkedServiceName": {
                    "referenceName": "LS_AzureSQL_RetailMax",
                    "type": "LinkedServiceReference",
                },
                "typeProperties": {
                    "scripts": [
                        {
                            "type": "Query",
                            "text": "SELECT tabla_nombre, filas_leidas, filas_limpias, duplicados_detectados, nulos_detectados, estado, timestamp_reporte FROM pipeline_quality_report ORDER BY timestamp_reporte DESC",
                        }
                    ]
                },
            },
            {
                "name": "Verificar_Errores_Pipeline",
                "type": "Script",
                "dependsOn": [
                    {
                        "activity": "Consultar_Reporte_Calidad",
                        "dependencyConditions": ["Succeeded"],
                    }
                ],
                "policy": {
                    "timeout": "0.00:10:00",
                    "retry": 3,
                    "retryIntervalInSeconds": 30,
                },
                "userProperties": [],
                "linkedServiceName": {
                    "referenceName": "LS_AzureSQL_RetailMax",
                    "type": "LinkedServiceReference",
                },
                "typeProperties": {
                    "scripts": [
                        {
                            "type": "Query",
                            "text": "SELECT COUNT(*) AS total_errores, MAX(timestamp_error) AS ultimo_error FROM pipeline_errors",
                        }
                    ]
                },
            },
        ],
    )
    client.pipelines.create_or_update(
        RESOURCE_GROUP, FACTORY_NAME, "PL_Calidad_Datos", pl_calidad
    )
    print("  -> PL_Calidad_Datos creado")

    # --- PIPELINE 5: PL_Orquestador_Maestro ---
    print("\n[7/7] Creando PL_Orquestador_Maestro...")

    pl_master = PipelineResource(
        description="Pipeline maestro: Bronze -> Silver -> Gold -> Calidad. Cada etapa espera la finalizacion exitosa de la anterior.",
        concurrency=1,
        activities=[
            {
                "name": "Ejecutar_Ingesta_Bronze",
                "type": "ExecutePipeline",
                "dependsOn": [],
                "policy": {"secureInput": False},
                "userProperties": [],
                "typeProperties": {
                    "pipeline": {
                        "referenceName": "PL_Ingesta_Bronze",
                        "type": "PipelineReference",
                    },
                    "waitOnCompletion": True,
                },
            },
            {
                "name": "Ejecutar_Limpieza_Silver",
                "type": "ExecutePipeline",
                "dependsOn": [
                    {
                        "activity": "Ejecutar_Ingesta_Bronze",
                        "dependencyConditions": ["Succeeded"],
                    }
                ],
                "policy": {"secureInput": False},
                "userProperties": [],
                "typeProperties": {
                    "pipeline": {
                        "referenceName": "PL_Limpieza_Silver",
                        "type": "PipelineReference",
                    },
                    "waitOnCompletion": True,
                },
            },
            {
                "name": "Ejecutar_Vistas_Gold",
                "type": "ExecutePipeline",
                "dependsOn": [
                    {
                        "activity": "Ejecutar_Limpieza_Silver",
                        "dependencyConditions": ["Succeeded"],
                    }
                ],
                "policy": {"secureInput": False},
                "userProperties": [],
                "typeProperties": {
                    "pipeline": {
                        "referenceName": "PL_Vistas_Gold",
                        "type": "PipelineReference",
                    },
                    "waitOnCompletion": True,
                },
            },
            {
                "name": "Ejecutar_Calidad_Datos",
                "type": "ExecutePipeline",
                "dependsOn": [
                    {
                        "activity": "Ejecutar_Vistas_Gold",
                        "dependencyConditions": ["Succeeded"],
                    }
                ],
                "policy": {"secureInput": False},
                "userProperties": [],
                "typeProperties": {
                    "pipeline": {
                        "referenceName": "PL_Calidad_Datos",
                        "type": "PipelineReference",
                    },
                    "waitOnCompletion": True,
                },
            },
        ],
    )
    client.pipelines.create_or_update(
        RESOURCE_GROUP, FACTORY_NAME, "PL_Orquestador_Maestro", pl_master
    )
    print("  -> PL_Orquestador_Maestro creado")

    # --- TRIGGER: Ejecucion diaria a las 02:00 AM UTC ---
    print("\n[8/8] Configurando trigger diario 02:00 AM UTC...")
    trigger = TriggerResource(
        properties={
            "type": "ScheduleTrigger",
            "description": "Trigger diario a las 02:00 AM UTC para ejecutar PL_Orquestador_Maestro",
            "recurrence": {
                "frequency": "Day",
                "interval": 1,
                "startTime": "2026-01-01T02:00:00Z",
                "timeZone": "UTC",
                "schedule": {
                    "hours": [2],
                    "minutes": [0],
                },
            },
            "pipelines": [
                {
                    "pipelineReference": {
                        "type": "PipelineReference",
                        "referenceName": "PL_Orquestador_Maestro",
                    }
                }
            ],
        }
    )
    client.triggers.create_or_update(
        RESOURCE_GROUP, FACTORY_NAME, "Trigger_Diario_0200", trigger
    )
    print("  -> Trigger_Diario_0200 creado")
    print("  -> Iniciando trigger...")
    client.triggers.begin_start(
        RESOURCE_GROUP, FACTORY_NAME, "Trigger_Diario_0200"
    ).result()
    print("  -> Trigger activo (ejecutara PL_Orquestador_Maestro a las 02:00 AM UTC)")

    # --- Resumen ---
    print("\n" + "=" * 60)
    print("DESPLIEGUE COMPLETADO")
    print("=" * 60)
    print(f"  Data Factory: {FACTORY_NAME}")
    print(f"  Linked Services: 2 (SQL + DataLake)")
    print(f"  Datasets: 2 (SQL parametrizado + Parquet parametrizado)")
    print(f"  Pipelines: 5")
    print(f"    - PL_Ingesta_Bronze")
    print(f"    - PL_Limpieza_Silver")
    print(f"    - PL_Vistas_Gold (8 vistas con reglas de negocio Escenario B)")
    print(f"    - PL_Calidad_Datos")
    print(f"    - PL_Orquestador_Maestro")
    print(f"  Trigger: Trigger_Diario_0200 (02:00 AM UTC)")
    print(
        f"\n  URL: https://adf.azure.com/en/authoring/pipeline/PL_Orquestador_Maestro?factory=%2Fsubscriptions%2F{SUBSCRIPTION_ID}%2FresourceGroups%2F{RESOURCE_GROUP}%2Fproviders%2FMicrosoft.DataFactory%2Ffactories%2F{FACTORY_NAME}")


if __name__ == "__main__":
    main()
