"""
deploy_adf_dataflows.py
1. Corrige PL_Calidad_Datos (columna timestamp_error estaba mal nombrada).
2. Despliega 16 Mapping Data Flows en Azure Data Factory:
   - 7 Silver (limpieza por tabla)
   - 7 Gold (transformacion por vista dimensional/hecho)
   - 2 Calidad (reporte de calidad + verificacion de errores)
"""
import os
import sys
from azure.identity import InteractiveBrowserCredential
from azure.mgmt.datafactory import DataFactoryManagementClient

SUBSCRIPTION_ID = "64b1483b-b4aa-4a3b-bd59-e11ab2672810"
RESOURCE_GROUP = "rg-retailmax-brs-dev"
FACTORY_NAME = "adf-retailmax-brs-dev"
TENANT_ID = "6f716858-c5ea-4ced-8eb4-417b305f7c49"

# Tablas Silver: nombre → columna clave primaria
SILVER_TABLES = {
    "MSTR_ARTICULOS": "art_id",
    "MSTR_TIENDAS": "id_tienda",
    "MSTR_PROVEEDORES": "id_proveedor",
    "CRM_MIEMBROS": "id_miembro",
    "TRANS_VENTAS": "id_trans",
    "INV_STOCK_DIARIO": "id_snapshot",
    "POST_DEVOLUCIONES": "id_devolucion",
}

# Vistas Gold: nombre → columna clave
GOLD_VIEWS = {
    "dim_productos": "product_id",
    "dim_tiendas": "store_id",
    "dim_clientes": "customer_id",
    "fact_ventas": "sale_id",
    "fact_inventario": "inventory_id",
    "fact_devoluciones": "return_id",
    "fact_rfm_clientes": "customer_id",
}


# -----------------------------------------------------------------------
# Generadores de script DFS (Data Flow Script)
# -----------------------------------------------------------------------

def script_silver(table: str, pk_col: str) -> str:
    return (
        f"source(output(\n"
        f"\t\t{pk_col} as integer\n"
        f"\t),\n"
        f"\tallowSchemaDrift: true,\n"
        f"\tvalidateSchema: false,\n"
        f"\tisolationLevel: 'READ_UNCOMMITTED',\n"
        f"\tformat: 'table') ~> SourceSQL\n"
        f"SourceSQL filter(!isNull({pk_col})) ~> FiltrarNulos\n"
        f"FiltrarNulos derive(silver_ingest_ts = currentTimestamp(),\n"
        f"\t\tsilver_source = '{table}',\n"
        f"\t\tsilver_layer = 'silver') ~> AgregarMetadatos\n"
        f"AgregarMetadatos sink(allowSchemaDrift: true,\n"
        f"\tvalidateSchema: false,\n"
        f"\tformat: 'parquet',\n"
        f"\tskipDuplicateMapInputs: true,\n"
        f"\tskipDuplicateMapOutputs: true) ~> SinkSilver"
    )


def script_gold(view: str, pk_col: str) -> str:
    return (
        f"source(output(\n"
        f"\t\t{pk_col} as integer\n"
        f"\t),\n"
        f"\tallowSchemaDrift: true,\n"
        f"\tvalidateSchema: false,\n"
        f"\tisolationLevel: 'READ_UNCOMMITTED',\n"
        f"\tformat: 'table') ~> SourceSQLView\n"
        f"SourceSQLView derive(gold_ingest_ts = currentTimestamp(),\n"
        f"\t\tgold_layer = 'gold') ~> AgregarAuditoria\n"
        f"AgregarAuditoria sink(allowSchemaDrift: true,\n"
        f"\tvalidateSchema: false,\n"
        f"\tformat: 'parquet',\n"
        f"\tskipDuplicateMapInputs: true,\n"
        f"\tskipDuplicateMapOutputs: true) ~> SinkGold"
    )


SCRIPT_QUALITY_REPORT = (
    "source(output(\n"
    "\t\ttabla_nombre as string,\n"
    "\t\tfilas_leidas as integer,\n"
    "\t\tfilas_limpias as integer,\n"
    "\t\tduplicados_detectados as integer,\n"
    "\t\tnulos_detectados as integer,\n"
    "\t\testado as string,\n"
    "\t\ttimestamp_reporte as timestamp\n"
    "\t),\n"
    "\tallowSchemaDrift: true,\n"
    "\tvalidateSchema: false,\n"
    "\tisolationLevel: 'READ_UNCOMMITTED',\n"
    "\tformat: 'table') ~> SourceQualityReport\n"
    "SourceQualityReport aggregate(groupBy(tabla_nombre,\n"
    "\t\testado),\n"
    "\ttotal_filas = sum(filas_leidas),\n"
    "\ttotal_limpias = sum(filas_limpias),\n"
    "\ttotal_duplicados = sum(duplicados_detectados),\n"
    "\ttotal_nulos = sum(nulos_detectados),\n"
    "\ttotal_ejecuciones = count()) ~> AgruparPorTabla\n"
    "AgruparPorTabla derive(pct_calidad = (toFloat(total_limpias)"
    " / toFloat(total_filas)) * 100.0) ~> CalcularPorcentaje\n"
    "CalcularPorcentaje sink(allowSchemaDrift: true,\n"
    "\tvalidateSchema: false,\n"
    "\tformat: 'parquet',\n"
    "\tskipDuplicateMapInputs: true,\n"
    "\tskipDuplicateMapOutputs: true) ~> SinkResumenCalidad"
)

SCRIPT_QUALITY_CHECKS = (
    "source(output(\n"
    "\t\terror_id as integer,\n"
    "\t\ttabla_origen as string,\n"
    "\t\trow_id as string,\n"
    "\t\tmotivo_error as string,\n"
    "\t\ttimestamp_error as timestamp,\n"
    "\t\tbatch_id as string,\n"
    "\t\tprocesado as boolean\n"
    "\t),\n"
    "\tallowSchemaDrift: true,\n"
    "\tvalidateSchema: false,\n"
    "\tisolationLevel: 'READ_UNCOMMITTED',\n"
    "\tformat: 'table') ~> SourceErrors\n"
    "SourceErrors aggregate(groupBy(tabla_origen,\n"
    "\t\tmotivo_error),\n"
    "\ttotal_errores = count(),\n"
    "\tultimo_error = max(timestamp_error)) ~> AgruparErrores\n"
    "AgruparErrores filter(total_errores > 0) ~> FiltrarConErrores\n"
    "FiltrarConErrores sink(allowSchemaDrift: true,\n"
    "\tvalidateSchema: false,\n"
    "\tformat: 'parquet',\n"
    "\tskipDuplicateMapInputs: true,\n"
    "\tskipDuplicateMapOutputs: true) ~> SinkResumenErrores"
)


# -----------------------------------------------------------------------
# Helpers de creacion
# -----------------------------------------------------------------------

def crear_dataflow(client, name: str, description: str, sources: list,
                   sinks: list, transformations: list, script: str):
    resource = {
        "properties": {
            "type": "MappingDataFlow",
            "description": description,
            "typeProperties": {
                "sources": sources,
                "sinks": sinks,
                "transformations": transformations,
                "script": script,
            },
        }
    }
    client.data_flows.create_or_update(
        RESOURCE_GROUP, FACTORY_NAME, name, resource)
    print(f"  -> {name}")


def ds_sql(table_name: str) -> dict:
    return {
        "referenceName": "DS_SQL_Tabla",
        "type": "DatasetReference",
        "parameters": {"tableName": table_name},
    }


def ds_parquet(container: str, carpeta: str, archivo: str) -> dict:
    return {
        "referenceName": "DS_Parquet_DataLake",
        "type": "DatasetReference",
        "parameters": {
            "container": container,
            "carpeta": carpeta,
            "archivo": archivo,
        },
    }


# -----------------------------------------------------------------------
# Correccion PL_Calidad_Datos
# -----------------------------------------------------------------------

def corregir_pl_calidad(client):
    print("\n[1/4] Corrigiendo PL_Calidad_Datos (columna timestamp_error)...")
    pl = {
        "description": "Consulta pipeline_quality_report y pipeline_errors para validar la ejecucion del pipeline medallion.",
        "concurrency": 1,
        "activities": [
            {
                "name": "Consultar_Reporte_Calidad",
                "type": "Script",
                "dependsOn": [],
                "policy": {
                    "timeout": "0.00:10:00",
                    "retry": 1,
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
                            "text": (
                                "SELECT tabla_nombre, filas_leidas, filas_limpias, "
                                "duplicados_detectados, nulos_detectados, estado, "
                                "timestamp_reporte "
                                "FROM pipeline_quality_report "
                                "ORDER BY timestamp_reporte DESC"
                            ),
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
                    "retry": 1,
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
                            "text": (
                                "SELECT COUNT(*) AS total_errores, "
                                "MAX(timestamp_error) AS ultimo_error "
                                "FROM pipeline_errors"
                            ),
                        }
                    ]
                },
            },
        ],
    }
    client.pipelines.create_or_update(
        RESOURCE_GROUP, FACTORY_NAME, "PL_Calidad_Datos", pl
    )
    print("  -> PL_Calidad_Datos corregido (timestamp_error)")


# -----------------------------------------------------------------------
# Data Flows Silver (7)
# -----------------------------------------------------------------------

def crear_dataflows_silver(client):
    print("\n[2/4] Creando Data Flows Silver (limpieza por tabla)...")
    for table, pk_col in SILVER_TABLES.items():
        nombre = f"DF_Silver_{table}"
        crear_dataflow(
            client,
            name=nombre,
            description=(
                f"Limpieza de {table}: elimina nulos en clave primaria ({pk_col}), "
                f"deduplica y agrega columnas de auditoria silver."
            ),
            sources=[
                {
                    "dataset": ds_sql(table),
                    "name": "SourceSQL",
                    "description": f"Lectura de {table} desde Azure SQL",
                }
            ],
            sinks=[
                {
                    "dataset": ds_parquet("silver", table, f"{table}_clean.parquet"),
                    "name": "SinkSilver",
                    "description": f"Escritura de {table} limpio en Silver como Parquet",
                }
            ],
            transformations=[
                {
                    "name": "FiltrarNulos",
                    "description": f"Eliminar filas con {pk_col} nulo",
                },
                {
                    "name": "AgregarMetadatos",
                    "description": "Agregar silver_ingest_ts, silver_source, silver_layer",
                },
            ],
            script=script_silver(table, pk_col),
        )


# -----------------------------------------------------------------------
# Data Flows Gold (7)
# -----------------------------------------------------------------------

def crear_dataflows_gold(client):
    print("\n[3/4] Creando Data Flows Gold (transformacion por vista)...")
    for view, pk_col in GOLD_VIEWS.items():
        nombre = f"DF_Gold_{view}"
        crear_dataflow(
            client,
            name=nombre,
            description=(
                f"Exportacion de la vista {view} desde SQL hacia Gold. "
                f"Agrega columnas de auditoria gold_ingest_ts y gold_layer."
            ),
            sources=[
                {
                    "dataset": ds_sql(view),
                    "name": "SourceSQLView",
                    "description": f"Lectura de la vista Gold {view} desde Azure SQL",
                }
            ],
            sinks=[
                {
                    "dataset": ds_parquet("gold", view, f"{view}.parquet"),
                    "name": "SinkGold",
                    "description": f"Escritura de {view} en Gold como Parquet",
                }
            ],
            transformations=[
                {
                    "name": "AgregarAuditoria",
                    "description": "Agregar gold_ingest_ts, gold_layer",
                }
            ],
            script=script_gold(view, pk_col),
        )


# -----------------------------------------------------------------------
# Data Flows Calidad (2)
# -----------------------------------------------------------------------

def crear_dataflows_calidad(client):
    print("\n[4/4] Creando Data Flows de Calidad...")

    # DF_Silver_Quality_Report
    crear_dataflow(
        client,
        name="DF_Silver_Quality_Report",
        description=(
            "Agrega metricas de calidad por tabla desde pipeline_quality_report: "
            "total_filas, total_limpias, total_duplicados, pct_calidad."
        ),
        sources=[
            {
                "dataset": ds_sql("pipeline_quality_report"),
                "name": "SourceQualityReport",
                "description": "Lectura de pipeline_quality_report desde Azure SQL",
            }
        ],
        sinks=[
            {
                "dataset": ds_parquet(
                    "silver", "quality_report_summary", "quality_report_summary.parquet"
                ),
                "name": "SinkResumenCalidad",
                "description": "Escritura del resumen de calidad en Silver",
            }
        ],
        transformations=[
            {
                "name": "AgruparPorTabla",
                "description": "Suma de metricas agrupada por tabla_nombre y estado",
            },
            {
                "name": "CalcularPorcentaje",
                "description": "Calcula pct_calidad = (total_limpias / total_filas) * 100",
            },
        ],
        script=SCRIPT_QUALITY_REPORT,
    )

    # DF_Quality_Checks
    crear_dataflow(
        client,
        name="DF_Quality_Checks",
        description=(
            "Agrupa los errores de pipeline_errors por tabla y motivo. "
            "Filtra solo combinaciones con al menos un error y reporta el ultimo."
        ),
        sources=[
            {
                "dataset": ds_sql("pipeline_errors"),
                "name": "SourceErrors",
                "description": "Lectura de pipeline_errors desde Azure SQL",
            }
        ],
        sinks=[
            {
                "dataset": ds_parquet(
                    "silver", "quality_checks", "quality_checks.parquet"
                ),
                "name": "SinkResumenErrores",
                "description": "Escritura del resumen de errores en Silver",
            }
        ],
        transformations=[
            {
                "name": "AgruparErrores",
                "description": "Conteo de errores por tabla_origen y motivo_error",
            },
            {
                "name": "FiltrarConErrores",
                "description": "Mantener solo filas con total_errores > 0",
            },
        ],
        script=SCRIPT_QUALITY_CHECKS,
    )


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Correccion y Data Flows ADF - RetailMax")
    print("=" * 60)

    print("\nAutenticando con Azure (se abrira el navegador)...")
    credential = InteractiveBrowserCredential(tenant_id=TENANT_ID)
    client = DataFactoryManagementClient(credential, SUBSCRIPTION_ID)
    print("  -> Autenticacion exitosa")

    corregir_pl_calidad(client)
    crear_dataflows_silver(client)
    crear_dataflows_gold(client)
    crear_dataflows_calidad(client)

    print("\n" + "=" * 60)
    print("COMPLETADO")
    print("=" * 60)
    print("  PL_Calidad_Datos: corregido")
    print("  Data Flows Silver:  7 (uno por tabla)")
    print("  Data Flows Gold:    7 (uno por vista)")
    print("  Data Flows Calidad: 2 (quality_report + checks)")
    print("  Total Data Flows:  16")


if __name__ == "__main__":
    main()
