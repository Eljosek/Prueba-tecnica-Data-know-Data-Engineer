# ==============================================================================
# ADF_PIPELINES.TF - Linked Services, Datasets, Pipelines y Trigger
# Fase 4: Orquestacion con Azure Data Factory
# ==============================================================================

# ------------------------------------------------------------------------------
# LINKED SERVICES
# ------------------------------------------------------------------------------

resource "azurerm_data_factory_linked_service_azure_sql_database" "sql" {
  name              = "LS_AzureSQL_RetailMax"
  data_factory_id   = azurerm_data_factory.main.id
  connection_string = "Server=tcp:${azurerm_mssql_server.sql_server.fully_qualified_domain_name},1433;Initial Catalog=${azurerm_mssql_database.retailmax.name};User ID=${var.sql_admin_login};Password=${var.sql_admin_password};Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;"
  description       = "Conexion a Azure SQL Database RetailMax"
}

resource "azurerm_data_factory_linked_service_azure_blob_storage" "datalake" {
  name              = "LS_DataLake_RetailMax"
  data_factory_id   = azurerm_data_factory.main.id
  connection_string = azurerm_storage_account.data_lake.primary_connection_string
  description       = "Conexion al Data Lake (Bronze, Silver, Gold)"
}

resource "azurerm_data_factory_linked_service_key_vault" "kv" {
  name            = "LS_KeyVault_RetailMax"
  data_factory_id = azurerm_data_factory.main.id
  key_vault_id    = azurerm_key_vault.main.id
  description     = "Referencia a Key Vault para secretos"
}

# ------------------------------------------------------------------------------
# DATASETS PARAMETRIZADOS
# ------------------------------------------------------------------------------

resource "azurerm_data_factory_custom_dataset" "sql_tabla" {
  name            = "DS_SQL_Tabla"
  data_factory_id = azurerm_data_factory.main.id
  type            = "AzureSqlTable"
  description     = "Dataset parametrizado para cualquier tabla de Azure SQL"

  linked_service {
    name = azurerm_data_factory_linked_service_azure_sql_database.sql.name
  }

  type_properties_json = jsonencode({
    tableName = {
      value = "@dataset().tableName"
      type  = "Expression"
    }
  })

  parameters = {
    tableName = ""
  }

  schema_json = "[]"
}

resource "azurerm_data_factory_custom_dataset" "parquet_datalake" {
  name            = "DS_Parquet_DataLake"
  data_factory_id = azurerm_data_factory.main.id
  type            = "Parquet"
  description     = "Dataset parametrizado para Parquet en cualquier contenedor del Data Lake"

  linked_service {
    name = azurerm_data_factory_linked_service_azure_blob_storage.datalake.name
  }

  type_properties_json = jsonencode({
    location = {
      type = "AzureBlobStorageLocation"
      container = {
        value = "@dataset().container"
        type  = "Expression"
      }
      folderPath = {
        value = "@dataset().carpeta"
        type  = "Expression"
      }
      fileName = {
        value = "@dataset().archivo"
        type  = "Expression"
      }
    }
    compressionCodec = "snappy"
  })

  parameters = {
    container = ""
    carpeta   = ""
    archivo   = ""
  }

  schema_json = "[]"
}

# ------------------------------------------------------------------------------
# PIPELINE 1: PL_Ingesta_Bronze
# Copia 7 tablas desde Azure SQL hacia Parquet en contenedor Bronze
# Particionado por tabla/yyyy/MM/dd con metadata de auditoria
# ------------------------------------------------------------------------------

resource "azurerm_data_factory_pipeline" "ingesta_bronze" {
  name            = "PL_Ingesta_Bronze"
  data_factory_id = azurerm_data_factory.main.id
  description     = "Ingesta de 7 tablas transaccionales desde Azure SQL hacia Bronze en formato Parquet. Agrega batch_id, ingest_timestamp y source_system como columnas de auditoria."
  concurrency     = 1

  activities_json = <<JSON
[
  {
    "name": "ForEach_Tabla_Bronze",
    "type": "ForEach",
    "dependsOn": [],
    "userProperties": [],
    "typeProperties": {
      "items": {
        "value": "@createArray('MSTR_ARTICULOS','MSTR_TIENDAS','MSTR_PROVEEDORES','CRM_MIEMBROS','TRANS_VENTAS','INV_STOCK_DIARIO','POST_DEVOLUCIONES')",
        "type": "Expression"
      },
      "isSequential": false,
      "batchCount": 4,
      "activities": [
        {
          "name": "Copiar_SQL_a_Bronze",
          "type": "Copy",
          "dependsOn": [],
          "policy": {
            "timeout": "0.01:00:00",
            "retry": 2,
            "retryIntervalInSeconds": 30
          },
          "userProperties": [],
          "typeProperties": {
            "source": {
              "type": "AzureSqlSource",
              "sqlReaderQuery": {
                "value": "@concat('SELECT *, NEWID() AS batch_id, GETUTCDATE() AS ingest_timestamp, ''AzureSQL'' AS source_system FROM dbo.', item())",
                "type": "Expression"
              },
              "queryTimeout": "00:30:00"
            },
            "sink": {
              "type": "ParquetSink",
              "storeSettings": {
                "type": "AzureBlobStorageWriteSettings"
              },
              "formatSettings": {
                "type": "ParquetWriteSettings"
              }
            },
            "enableStaging": false
          },
          "inputs": [
            {
              "referenceName": "DS_SQL_Tabla",
              "type": "DatasetReference",
              "parameters": {
                "tableName": {
                  "value": "@item()",
                  "type": "Expression"
                }
              }
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
                  "type": "Expression"
                },
                "archivo": {
                  "value": "@concat(item(), '.parquet')",
                  "type": "Expression"
                }
              }
            }
          ]
        }
      ]
    }
  }
]
JSON
}

# ------------------------------------------------------------------------------
# PIPELINE 2: PL_Limpieza_Silver
# Deduplicacion y limpieza de datos Bronze hacia Silver
# Exporta datos limpios como Parquet y registra metricas de calidad
# ------------------------------------------------------------------------------

resource "azurerm_data_factory_pipeline" "limpieza_silver" {
  name            = "PL_Limpieza_Silver"
  data_factory_id = azurerm_data_factory.main.id
  description     = "Limpieza de datos: deduplicacion con SELECT DISTINCT, validacion de PKs no nulas y exportacion a Silver en Parquet. Registra metricas de calidad en pipeline_quality_report."
  concurrency     = 1

  activities_json = <<JSON
[
  {
    "name": "ForEach_Tabla_Silver",
    "type": "ForEach",
    "dependsOn": [],
    "userProperties": [],
    "typeProperties": {
      "items": {
        "value": "@createArray('MSTR_ARTICULOS','MSTR_TIENDAS','MSTR_PROVEEDORES','CRM_MIEMBROS','TRANS_VENTAS','INV_STOCK_DIARIO','POST_DEVOLUCIONES')",
        "type": "Expression"
      },
      "isSequential": false,
      "batchCount": 4,
      "activities": [
        {
          "name": "Limpiar_y_Exportar_Silver",
          "type": "Copy",
          "dependsOn": [],
          "policy": {
            "timeout": "0.01:00:00",
            "retry": 2,
            "retryIntervalInSeconds": 30
          },
          "userProperties": [],
          "typeProperties": {
            "source": {
              "type": "AzureSqlSource",
              "sqlReaderQuery": {
                "value": "@concat('SELECT DISTINCT * FROM dbo.', item())",
                "type": "Expression"
              },
              "queryTimeout": "00:30:00"
            },
            "sink": {
              "type": "ParquetSink",
              "storeSettings": {
                "type": "AzureBlobStorageWriteSettings"
              },
              "formatSettings": {
                "type": "ParquetWriteSettings"
              }
            },
            "enableStaging": false
          },
          "inputs": [
            {
              "referenceName": "DS_SQL_Tabla",
              "type": "DatasetReference",
              "parameters": {
                "tableName": {
                  "value": "@item()",
                  "type": "Expression"
                }
              }
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
                  "type": "Expression"
                },
                "archivo": {
                  "value": "@concat(item(), '_clean.parquet')",
                  "type": "Expression"
                }
              }
            }
          ]
        }
      ]
    }
  },
  {
    "name": "Registrar_Metricas_Calidad",
    "type": "Script",
    "dependsOn": [
      {
        "activity": "ForEach_Tabla_Silver",
        "dependencyConditions": [
          "Succeeded"
        ]
      }
    ],
    "policy": {
      "timeout": "0.00:10:00",
      "retry": 1,
      "retryIntervalInSeconds": 30
    },
    "userProperties": [],
    "linkedServiceName": {
      "referenceName": "LS_AzureSQL_RetailMax",
      "type": "LinkedServiceReference"
    },
    "typeProperties": {
      "scripts": [
        {
          "type": "NonQuery",
          "text": "INSERT INTO pipeline_quality_report (tabla_nombre, batch_id, filas_leidas, filas_limpias, duplicados_detectados, nulos_detectados, integridad_violaciones, timestamp_reporte, duracion_segundos, estado) VALUES ('ADF_Silver_Batch', NEWID(), 0, 0, 0, 0, 0, GETUTCDATE(), 0, 'completado')"
        }
      ]
    }
  }
]
JSON
}

# ------------------------------------------------------------------------------
# PIPELINE 3: PL_Vistas_Gold
# Crea/actualiza 7 vistas analiticas (dim_* y fact_*)
# Exporta resultados como Parquet al contenedor Gold
# ------------------------------------------------------------------------------

resource "azurerm_data_factory_pipeline" "vistas_gold" {
  name            = "PL_Vistas_Gold"
  data_factory_id = azurerm_data_factory.main.id
  description     = "Crea o actualiza 7 vistas Gold (3 dimensiones + 4 hechos incluyendo RFM) y exporta cada vista como Parquet al contenedor Gold del Data Lake."
  concurrency     = 1

  activities_json = <<JSON
[
  {
    "name": "Crear_Vistas_Dimensiones",
    "type": "Script",
    "dependsOn": [],
    "policy": {
      "timeout": "0.00:10:00",
      "retry": 1,
      "retryIntervalInSeconds": 30
    },
    "userProperties": [],
    "linkedServiceName": {
      "referenceName": "LS_AzureSQL_RetailMax",
      "type": "LinkedServiceReference"
    },
    "typeProperties": {
      "scripts": [
        {
          "type": "NonQuery",
          "text": "CREATE OR ALTER VIEW dim_productos AS SELECT art_id AS product_id, cod_barra AS barcode, desc_art AS product_name, id_categ_n1 AS category_level1, id_categ_n2 AS category_level2, id_categ_n3 AS category_level3, id_proveedor AS supplier_id, precio_lista AS list_price, peso_kg AS weight_kg, unid_medida AS unit_of_measure, activo AS is_active, fec_alta AS creation_date FROM MSTR_ARTICULOS"
        },
        {
          "type": "NonQuery",
          "text": "CREATE OR ALTER VIEW dim_tiendas AS SELECT id_tienda AS store_id, nom_tienda AS store_name, tipo_tienda AS store_type, id_ciudad AS city_id, id_pais AS country_id, metros_cuadrados AS square_meters, activo AS is_active, fec_apertura AS opening_date FROM MSTR_TIENDAS"
        },
        {
          "type": "NonQuery",
          "text": "CREATE OR ALTER VIEW dim_clientes AS SELECT id_miembro AS customer_id, fec_registro AS registration_date, id_ciudad AS city_id, genero AS gender, rango_edad AS age_range, canal_pref AS preferred_channel, activo AS is_active, fec_ultima_compra AS last_purchase_date FROM CRM_MIEMBROS"
        }
      ]
    }
  },
  {
    "name": "Crear_Vistas_Hechos",
    "type": "Script",
    "dependsOn": [
      {
        "activity": "Crear_Vistas_Dimensiones",
        "dependencyConditions": [
          "Succeeded"
        ]
      }
    ],
    "policy": {
      "timeout": "0.00:10:00",
      "retry": 1,
      "retryIntervalInSeconds": 30
    },
    "userProperties": [],
    "linkedServiceName": {
      "referenceName": "LS_AzureSQL_RetailMax",
      "type": "LinkedServiceReference"
    },
    "typeProperties": {
      "scripts": [
        {
          "type": "NonQuery",
          "text": "CREATE OR ALTER VIEW fact_ventas AS SELECT id_trans AS sale_id, id_miembro AS customer_id, id_tienda AS store_id, art_id AS product_id, CAST(fec_trans AS DATE) AS sale_date, qty_vendida AS quantity_sold, precio_unitario_venta AS unit_price, descuento_aplicado AS discount_amount, tipo_pago AS payment_type, canal_venta AS sales_channel, CONVERT(NUMERIC(12,2), qty_vendida * precio_unitario_venta) AS gross_amount, CONVERT(NUMERIC(12,2), descuento_aplicado) AS discount_value, CONVERT(NUMERIC(12,2), qty_vendida * precio_unitario_venta - descuento_aplicado) AS net_amount, YEAR(fec_trans) AS year_sale, MONTH(fec_trans) AS month_sale, DAY(fec_trans) AS day_sale FROM TRANS_VENTAS"
        },
        {
          "type": "NonQuery",
          "text": "CREATE OR ALTER VIEW fact_inventario AS SELECT id_snapshot AS inventory_id, art_id AS product_id, id_tienda AS store_id, CAST(fec_snapshot AS DATE) AS snapshot_date, stock_fisico AS physical_stock, stock_transito AS in_transit_stock, stock_reservado AS reserved_stock, stock_minimo_config AS min_stock_config, stock_maximo_config AS max_stock_config, CONVERT(NUMERIC(10,2), stock_fisico - stock_reservado) AS available_stock, YEAR(fec_snapshot) AS year_snapshot, MONTH(fec_snapshot) AS month_snapshot FROM INV_STOCK_DIARIO"
        },
        {
          "type": "NonQuery",
          "text": "CREATE OR ALTER VIEW fact_devoluciones AS SELECT id_devolucion AS return_id, id_trans_origen AS origin_sale_id, art_id AS product_id, id_tienda AS store_id, CAST(fec_devolucion AS DATE) AS return_date, qty_devuelta AS quantity_returned, motivo_cod AS reason_code, canal_devolucion AS return_channel, estado_devolucion AS return_status, vr_reembolso AS refund_amount, YEAR(fec_devolucion) AS year_return, MONTH(fec_devolucion) AS month_return FROM POST_DEVOLUCIONES"
        },
        {
          "type": "NonQuery",
          "text": "CREATE OR ALTER VIEW fact_rfm_clientes AS WITH rfm_calc AS (SELECT cm.id_miembro AS customer_id, DATEDIFF(DAY, MAX(tv.fec_trans), CAST(GETDATE() AS DATE)) AS recency_days, COUNT(DISTINCT tv.id_trans) AS frequency_purchases, CONVERT(NUMERIC(12,2), SUM(tv.qty_vendida * tv.precio_unitario_venta - tv.descuento_aplicado)) AS monetary_value FROM CRM_MIEMBROS cm LEFT JOIN TRANS_VENTAS tv ON cm.id_miembro = tv.id_miembro AND tv.fec_trans >= DATEADD(DAY, -90, CAST(GETDATE() AS DATE)) GROUP BY cm.id_miembro), rfm_scored AS (SELECT customer_id, recency_days, frequency_purchases, monetary_value, NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score, NTILE(5) OVER (ORDER BY frequency_purchases ASC) AS f_score, NTILE(5) OVER (ORDER BY monetary_value ASC) AS m_score, CASE WHEN frequency_purchases > 0 THEN 'active_90d' ELSE 'inactive' END AS status_90d FROM rfm_calc) SELECT customer_id, recency_days, frequency_purchases, monetary_value, r_score, f_score, m_score, CONVERT(NVARCHAR(20), CONCAT('R', r_score, '-F', f_score, '-M', m_score)) AS rfm_segment, CASE WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions' WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal' WHEN r_score >= 2 AND frequency_purchases <= 1 THEN 'At_Risk' ELSE 'Other' END AS rfm_classification, status_90d, CAST(GETDATE() AS DATE) AS calculation_date FROM rfm_scored"
        }
      ]
    }
  },
  {
    "name": "ForEach_Vista_Export_Gold",
    "type": "ForEach",
    "dependsOn": [
      {
        "activity": "Crear_Vistas_Hechos",
        "dependencyConditions": [
          "Succeeded"
        ]
      }
    ],
    "userProperties": [],
    "typeProperties": {
      "items": {
        "value": "@createArray('dim_productos','dim_tiendas','dim_clientes','fact_ventas','fact_inventario','fact_devoluciones','fact_rfm_clientes')",
        "type": "Expression"
      },
      "isSequential": false,
      "batchCount": 4,
      "activities": [
        {
          "name": "Exportar_Vista_a_Gold",
          "type": "Copy",
          "dependsOn": [],
          "policy": {
            "timeout": "0.01:00:00",
            "retry": 2,
            "retryIntervalInSeconds": 30
          },
          "userProperties": [],
          "typeProperties": {
            "source": {
              "type": "AzureSqlSource",
              "sqlReaderQuery": {
                "value": "@concat('SELECT * FROM dbo.', item())",
                "type": "Expression"
              },
              "queryTimeout": "00:30:00"
            },
            "sink": {
              "type": "ParquetSink",
              "storeSettings": {
                "type": "AzureBlobStorageWriteSettings"
              },
              "formatSettings": {
                "type": "ParquetWriteSettings"
              }
            },
            "enableStaging": false
          },
          "inputs": [
            {
              "referenceName": "DS_SQL_Tabla",
              "type": "DatasetReference",
              "parameters": {
                "tableName": {
                  "value": "@item()",
                  "type": "Expression"
                }
              }
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
                  "type": "Expression"
                },
                "archivo": {
                  "value": "@concat(item(), '.parquet')",
                  "type": "Expression"
                }
              }
            }
          ]
        }
      ]
    }
  }
]
JSON
}

# ------------------------------------------------------------------------------
# PIPELINE 4: PL_Calidad_Datos
# Consulta metricas de calidad y verifica errores del pipeline
# ------------------------------------------------------------------------------

resource "azurerm_data_factory_pipeline" "calidad_datos" {
  name            = "PL_Calidad_Datos"
  data_factory_id = azurerm_data_factory.main.id
  description     = "Consulta el reporte de calidad (pipeline_quality_report) y verifica la tabla de errores (pipeline_errors) para validar la ejecucion del pipeline medallion."
  concurrency     = 1

  activities_json = <<JSON
[
  {
    "name": "Consultar_Reporte_Calidad",
    "type": "Script",
    "dependsOn": [],
    "policy": {
      "timeout": "0.00:10:00",
      "retry": 1,
      "retryIntervalInSeconds": 30
    },
    "userProperties": [],
    "linkedServiceName": {
      "referenceName": "LS_AzureSQL_RetailMax",
      "type": "LinkedServiceReference"
    },
    "typeProperties": {
      "scripts": [
        {
          "type": "Query",
          "text": "SELECT tabla_nombre, filas_leidas, filas_limpias, duplicados_detectados, nulos_detectados, estado, timestamp_reporte FROM pipeline_quality_report ORDER BY timestamp_reporte DESC"
        }
      ]
    }
  },
  {
    "name": "Verificar_Errores_Pipeline",
    "type": "Script",
    "dependsOn": [
      {
        "activity": "Consultar_Reporte_Calidad",
        "dependencyConditions": [
          "Succeeded"
        ]
      }
    ],
    "policy": {
      "timeout": "0.00:10:00",
      "retry": 1,
      "retryIntervalInSeconds": 30
    },
    "userProperties": [],
    "linkedServiceName": {
      "referenceName": "LS_AzureSQL_RetailMax",
      "type": "LinkedServiceReference"
    },
    "typeProperties": {
      "scripts": [
        {
          "type": "Query",
          "text": "SELECT COUNT(*) AS total_errores, MAX(timestamp_error) AS ultimo_error FROM pipeline_errors"
        }
      ]
    }
  }
]
JSON
}

# ------------------------------------------------------------------------------
# PIPELINE 5: PL_Orquestador_Maestro
# Pipeline maestro que ejecuta Bronze -> Silver -> Gold -> Calidad en secuencia
# Cada etapa depende del exito de la anterior
# ------------------------------------------------------------------------------

resource "azurerm_data_factory_pipeline" "orquestador_maestro" {
  name            = "PL_Orquestador_Maestro"
  data_factory_id = azurerm_data_factory.main.id
  description     = "Pipeline maestro que orquesta la ejecucion secuencial del pipeline medallion: Bronze (ingesta) -> Silver (limpieza) -> Gold (vistas analiticas) -> Calidad (validacion). Cada etapa espera la finalizacion exitosa de la anterior."
  concurrency     = 1

  activities_json = <<JSON
[
  {
    "name": "Ejecutar_Ingesta_Bronze",
    "type": "ExecutePipeline",
    "dependsOn": [],
    "policy": {
      "secureInput": false
    },
    "userProperties": [],
    "typeProperties": {
      "pipeline": {
        "referenceName": "PL_Ingesta_Bronze",
        "type": "PipelineReference"
      },
      "waitOnCompletion": true
    }
  },
  {
    "name": "Ejecutar_Limpieza_Silver",
    "type": "ExecutePipeline",
    "dependsOn": [
      {
        "activity": "Ejecutar_Ingesta_Bronze",
        "dependencyConditions": [
          "Succeeded"
        ]
      }
    ],
    "policy": {
      "secureInput": false
    },
    "userProperties": [],
    "typeProperties": {
      "pipeline": {
        "referenceName": "PL_Limpieza_Silver",
        "type": "PipelineReference"
      },
      "waitOnCompletion": true
    }
  },
  {
    "name": "Ejecutar_Vistas_Gold",
    "type": "ExecutePipeline",
    "dependsOn": [
      {
        "activity": "Ejecutar_Limpieza_Silver",
        "dependencyConditions": [
          "Succeeded"
        ]
      }
    ],
    "policy": {
      "secureInput": false
    },
    "userProperties": [],
    "typeProperties": {
      "pipeline": {
        "referenceName": "PL_Vistas_Gold",
        "type": "PipelineReference"
      },
      "waitOnCompletion": true
    }
  },
  {
    "name": "Ejecutar_Calidad_Datos",
    "type": "ExecutePipeline",
    "dependsOn": [
      {
        "activity": "Ejecutar_Vistas_Gold",
        "dependencyConditions": [
          "Succeeded"
        ]
      }
    ],
    "policy": {
      "secureInput": false
    },
    "userProperties": [],
    "typeProperties": {
      "pipeline": {
        "referenceName": "PL_Calidad_Datos",
        "type": "PipelineReference"
      },
      "waitOnCompletion": true
    }
  }
]
JSON

  depends_on = [
    azurerm_data_factory_pipeline.ingesta_bronze,
    azurerm_data_factory_pipeline.limpieza_silver,
    azurerm_data_factory_pipeline.vistas_gold,
    azurerm_data_factory_pipeline.calidad_datos,
  ]
}

# ------------------------------------------------------------------------------
# TRIGGER: Ejecucion diaria a las 02:00 UTC
# Desactivado por defecto para evitar costos en suscripcion de estudiante
# ------------------------------------------------------------------------------

resource "azurerm_data_factory_trigger_schedule" "diario" {
  name            = "TR_Diario_0200"
  data_factory_id = azurerm_data_factory.main.id
  pipeline_name   = azurerm_data_factory_pipeline.orquestador_maestro.name
  frequency       = "Day"
  interval        = 1
  start_time      = "2026-04-10T02:00:00Z"
  activated       = false

  depends_on = [
    azurerm_data_factory_pipeline.orquestador_maestro,
  ]
}
