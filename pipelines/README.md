Pipelines RetailMax - Fase 3
Arquitectura Medallion en Python + SQL

Estructura

bronze/
  - Extrae datos raw de Azure SQL
  - Escribe Parquet en ADLS Gen2
  - Agrega metadata: batch_id, ingest_timestamp, source_system
  - Particiona por year/month/day

silver/
  - Lee desde Bronze (Parquet)
  - Limpia: elimina duplicos, maneja nulos
  - Masking SHA-256 en PII (id_miembro)
  - Valida integridad referencial
  - Registra errores en tabla SQL
  - Genera reporte calidad datos
  - Escribe Parquet limpio en ADLS

gold/
  - Crea 7 vistas SQL con logica negocio
  - dim_productos, dim_tiendas, dim_clientes
  - fact_ventas (RFM score), fact_inventario (stock alerts)
  - fact_devoluciones, fact_rfm_clientes

Ejecucion

1. Bronze: python pipelines/bronze/ingestion.py
2. Silver: python pipelines/silver/cleaning.py
3. Gold: python scripts SQL views directamente en BD

Credenciales
- USD: SQL_SERVER, SQLSERVER_USER, SQLSERVER_PASSWORD
- Azure Storage: AZURE_STORAGE_ACCOUNT, AZURE_STORAGE_KEY
- Lago datos: ADLS path = /retailmax/data/{table}/{year}/{month}/{day}

Archivos de error
- sqldb-retailmax-brs-dev: tabla pipeline_errors
- Registra: timestamp, tabla_origen, row_id, motivo_error, datos

Metricas calidad (Silver)
- Duplicados: COUNT(*) WHERE rn > 1
- Nulos: COUNT(*) WHERE columna IS NULL (por columna)
- Integridad referencial: FOREIGN KEY violations registradas
- Registro en pipeline_quality_report

