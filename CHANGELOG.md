# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)  
and follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [1.0.0] — 2026-04-13

### Fixed
- `orchestration/deploy_adf_pipelines.py` — retry policy de todos los pipelines actualizada
  de 1–2 a 3 reintentos, alineada con la definicion IaC (`infra/adf_pipelines.tf`).
- RBAC: creados 6 role assignments en Azure (Ingeniero: Blob Contributor×3 + SQL Contributor,
  Analista: Blob Reader gold, Administrador: Owner RG). Verificados en cada scope.
- ADF Linked Services: corregido LS_DataLake_RetailMax a Managed Identity y
  LS_AzureSQL_RetailMax a connection string explicito (resuelve error 403 en pipelines).
- `PL_Orquestador_Maestro` ejecutado exitosamente end-to-end (Bronze → Silver → Gold → Calidad).

---

## [0.9.0] — 2026-04-12

### Added
- `dashboards/README.md` — guia de conexion Power BI Desktop a las 8 vistas Gold:
  modelo de datos, relaciones, paleta de colores y diseño de 5 paginas.
- `dashboards/dax_measures.md` — medidas DAX: ventas (7), inventario (4),
  devoluciones (3), clientes RFM (4), KPIs ejecutivos (4).
- `README.md` — seccion "Dashboard Power BI" con tabla de paginas y archivos de referencia.

---

## [0.8.0] — 2026-04-12

### Added
- `infra/main.tf` — Action Group (`ag-retailmax-*`) con receptor de correo para alertas.
- `infra/main.tf` — 3 reglas de alerta en Azure Monitor:
  - `alert-adf-pipeline-failed` (Sev 1): notifica cuando un pipeline de ADF falla.
  - `alert-adf-pipeline-succeeded` (Sev 3): reporte diario de ejecucion exitosa.
  - `alert-volume-anomaly` (Sev 2): scheduled query que detecta ausencia de ejecuciones Bronze en 24h.
- `infra/main.tf` — Diagnostic Settings de ADF a Log Analytics (PipelineRuns, ActivityRuns,
  TriggerRuns).
- `infra/variables.tf` — variable `alert_email_address` para configurar el correo de alertas.
- `.github/workflows/ci.yml` — pipeline CI/CD con GitHub Actions:
  - `python-lint`: valida estilo con flake8.
  - `quality-tests`: ejecuta quality_tests.py contra Azure SQL.
  - `terraform-validate`: valida sintaxis y formato de IaC.
- `docs/data_lineage.md` — documentacion de linaje de datos con diagramas Mermaid:
  - Flujo general Origen → Bronze → Silver → Gold (por tabla y vista).
  - Detalle por vista Gold: campos calculados, tablas origen, reglas de negocio.
  - Cadena de orquestacion: Trigger → Maestro → Bronze → Silver → Gold → Calidad.

### Changed
- `README.md` — actualizado con Fase 5 completa (3 alertas, 3 roles RBAC, catalogo de datos,
  linaje de datos, 5 pruebas de calidad), seccion Extras (CI/CD, Lineage, Monitoreo), tabla
  Gold actualizada a 8 vistas con descripcion de reglas de negocio por vista.
- `docs/` — screenshots renombrados con convencion profesional secuencial:
  - `03-sql-verification-azure.png` → `04-fase1-sql-verification-azure.png`
  - `04-fase2-resource-visualizer.png` → `05-fase2-resource-visualizer.png`
  - `8 vistas gold.png` → `06-fase3-gold-views.png`
  - `conjunto de datos.png` → `07-fase1-dataset-overview.png`
  - `Datos de kpi_ejecutivo.png` → `08-fase3-kpi-ejecutivo.png`
  - `dim_productos.png` → `09-fase3-dim-productos.png`
  - `Flujo_datos_16.png` → `10-fase4-dataflows-16.png`
  - `pipeline_medallion_etl.png` → `11-fase3-pipeline-medallion.png`
  - `Tablas_tracking_sql.png` → `12-fase4-tablas-tracking.png`

### Fixed
- Permiso ADF MSI: asignado `Storage Blob Data Contributor` via Azure CLI (resuelve error 403
  Forbidden al escribir en Storage Account desde ADF Managed Identity).

---

## [0.7.0] — 2026-04-13

### Added
- `docs/data_catalog.md` — catalogo de datos completo con una seccion por tabla (Bronze) y por
  vista (Gold). Documenta nombre de campo, tipo, origen, si es calculado, si contiene PII y la
  regla de negocio aplicada. Incluye tabla de acceso por rol RBAC.
- `pipelines/tests/quality_tests.py` — 5 pruebas automatizadas de calidad contra las vistas Gold
  en Azure SQL:
  - Test 1: PKs sin nulos (dim + fact + kpi).
  - Test 2: sin fechas futuras en fact_ventas, fact_inventario, fact_devoluciones.
  - Test 3: cobertura_dias y physical_stock no negativos en fact_inventario.
  - Test 4: rfm_segment con patron Rx-Fy-Mz y rfm_classification sin nulos.
  - Test 5: net_amount >= 0 en todas las ventas.
  - Incluye reporte de volumetria por vista al final de cada ejecucion.
- `orchestration/deploy_rbac.py` — asigna roles Azure RBAC a los tres perfiles del proyecto:
  - Ingeniero de Datos: `Storage Blob Data Contributor` en bronze/silver/gold + `Contributor` en SQL.
  - Analista de Datos: `Storage Blob Data Reader` unicamente en gold (bronze/silver denegado).
  - Administrador: `Owner` sobre el resource group completo.

---

## [0.6.0] — 2026-04-12

### Changed
- `pipelines/gold/views.sql` — reescritura completa con todas las reglas de negocio del
  Escenario B. Cambios por vista:
  - `dim_productos`: JOIN con MSTR_PROVEEDORES → campos `supplier_name`, `supplier_country`,
    `supplier_quality_score`. Campo calculado `estimated_margin` (30% del precio de lista).
  - `dim_tiendas`: campo calculado `zona_distribucion` derivado de `id_pais % 5`.
  - `dim_clientes`: estandarizacion de `gender` (O/NULL → No_informado), imputacion de
    `age_range` nulos con moda por canal (subconsulta correlacionada), campo `antiguedad_dias`.
  - `fact_ventas`: campo `customer_id` como COALESCE → 'ANONIMO' si nulo. Campo binario
    `ind_con_descuento`.
  - `fact_inventario`: CTE `ventas_14d` para calcular `avg_daily_sales_14d`, `cobertura_dias`
    y `alerta_quiebre` (1 si cobertura < 7 dias con demanda activa).
  - `fact_devoluciones`: JOIN con TRANS_VENTAS para `original_unit_price`. CTE `tasa_art` para
    `return_rate_by_product`.
  - `fact_rfm_clientes`: sin cambios (correcto desde v0.4.0).
- `pipelines/gold/views.sql` — nueva vista `kpi_ejecutivo`: agrega por fecha, pais y canal
  las metricas ejecutivas diarias (transacciones, clientes unicos, unidades, ventas brutas,
  descuentos, ventas netas).
- `orchestration/deploy_adf_pipelines.py`:
  - Actualizado `VISTAS_GOLD` con las 8 vistas (incluida `kpi_ejecutivo`).
  - Actualizados `SQL_VISTAS_DIM` y `SQL_VISTAS_FACT` con los nuevos SQL de todas las vistas.
  - Descripcion del pipeline `PL_Vistas_Gold` actualizada a "8 vistas".
  - Nuevo bloque al final: crea y activa `Trigger_Diario_0200` (ScheduleTrigger diario a las
    02:00 AM UTC) apuntando a `PL_Orquestador_Maestro`.

---

## [0.5.0] — 2026-04-11

### Added
- `orchestration/deploy_adf_pipelines.py` — despliega via SDK Python (`azure-mgmt-datafactory`)
  los 2 linked services, 2 datasets y 5 pipelines de ADF. Incluye autenticacion interactiva via
  `InteractiveBrowserCredential`.
- `orchestration/deploy_adf_dataflows.py` — crea los 16 Mapping Data Flows en ADF:
  - 7 Silver: filtro de nulos + columnas de auditoria `silver_ingest_ts` / `silver_source`
  - 7 Gold: lectura de vistas SQL + columna `gold_ingest_ts`
  - 2 Calidad: `DF_Silver_Quality_Report` (metricas agregadas) y `DF_Quality_Checks` (errores)
- `orchestration/PL_Orquestador_Maestro.json` — exportacion del pipeline maestro en formato
  ARM/ADF JSON.
- `infra/adf_pipelines.tf` — definicion IaC Terraform de linked services, datasets y 5 pipelines.

### Changed
- `README.md` — actualizado para documentar las 5 fases completas con arquitectura, recursos
  Azure, instrucciones de reproduccion y tabla de data flows.

### Fixed
- Corregido nombre de columna `error_timestamp` → `timestamp_error` en `PL_Calidad_Datos`,
  `orchestration/deploy_adf_pipelines.py` e `infra/adf_pipelines.tf`. La columna correcta en
  `pipeline_errors` es `timestamp_error`.

---

## [0.4.0] — 2026-04-10

### Added
- `pipelines/bronze/ingestion.py` — ingesta desde Azure SQL hacia el contenedor `bronze` en
  Parquet. Agrega columnas de auditoria: `batch_id`, `ingest_timestamp`, `source_system`.
- `pipelines/silver/cleaning.py` — limpieza y deduplicacion (`SELECT DISTINCT`) con registro
  de metricas en `pipeline_quality_report` y `pipeline_errors`.
- `pipelines/silver/export_quality_logs.py` — exporta logs de calidad a `silver/logs/` en
  Azure Blob Storage.
- `pipelines/gold/views.sql` — 7 vistas SQL (`CREATE OR ALTER VIEW`): dim_productos,
  dim_tiendas, dim_clientes, fact_ventas, fact_inventario, fact_devoluciones, fact_rfm_clientes.
- `pipelines/gold/create_views.py` — ejecuta las 7 vistas en Azure SQL Database.
- `pipelines/gold/export_to_storage.py` — exporta las 7 vistas como Parquet al contenedor `gold`.
- `orchestration/pipeline_orchestrator.py` — orquestador Python local que ejecuta
  Bronze → Silver → Gold con logging detallado.
- `migrations/01_crear_tablas_tracking.sql` — DDL de tablas `pipeline_quality_report` y
  `pipeline_errors` para trazabilidad de ejecuciones.

---

## [0.3.0] — 2026-04-09

---

## [0.3.0] — 2026-04-09

### Added
- Azure Data Factory (`adf-retailmax-brs-dev`) con Managed Identity en `infra/main.tf`.
- Política de acceso de ADF sobre Key Vault para leer secretos en tiempo de ejecución.
- Rol `Storage Blob Data Contributor` para la MSI de ADF sobre la cuenta de almacenamiento.
- Backend remoto de Terraform en Azure Storage Blob
  (`stgretailmaxbrsdev/tfstate/dev.terraform.tfstate`).
- Contenedor `tfstate` en la cuenta de almacenamiento para el estado remoto.
- `infra/outputs.tf` — salidas `data_factory_name`, `data_factory_id`, `data_factory_url`
  y resumen de deployment actualizado.
- `infra/backend.tf` — documentación del backend remoto (no ejecutable; guía para el equipo).

### Changed
- `infra/providers.tf` — configuración activa del backend `azurerm` apuntando al estado remoto.
- `infra/main.tf` — añadido `lifecycle { ignore_changes = [access_policy] }` en Key Vault
  para evitar drift permanente con la política separada de ADF.

### Fixed
- Error de migración de estado con `terraform init -migrate-state` resuelto usando el flag
  `-force-copy`.

---

## [0.2.0] — 2026-04-08

### Added
- Infraestructura Azure Fase 2 completa en `infra/main.tf`:
  - `azurerm_sql_server` + `azurerm_sql_database` (Azure SQL S2).
  - `azurerm_key_vault` con access policy para el usuario actual.
  - `azurerm_key_vault_secret` `sql-admin-password`.
  - `azurerm_log_analytics_workspace` y `azurerm_application_insights`.
  - Regla de firewall `AllowAzureServices` en el servidor SQL.
- `infra/variables.tf` — variables `sql_admin_username`, `sql_admin_password` y
  `alert_email_address`.
- `infra/outputs.tf` (versión inicial) — SQL server FQDN, Key Vault URI,
  Application Insights key.

### Changed
- `infra/main.tf` — reorganizado con `locals.tf` para convenciones de nombrado
  `{servicio}-{proyecto}-{region}-{entorno}`.

---

## [0.1.0] — 2026-04-07

### Added
- Infraestructura Azure Fase 1: Resource Group y Storage Account
  (`stgretailmaxbrsdev` con contenedores `raw`, `bronze`, `silver`, `gold`).
- `infra/providers.tf` — provider `azurerm ~> 3.80` con autenticación CLI.
- `infra/locals.tf` — base con `resource_base_name` y `common_tags`.
- `data-generation/generate_data.py` — generación de 7 datasets sintéticos con Faker:
  - 800 proveedores, 150 tiendas, 5 000 artículos, 50 000 miembros CRM.
  - 1 000 000 transacciones de venta, 750 000 registros de stock, 50 000 devoluciones.
  - Anomalías controladas en precio, stock y datos de contacto.
- `data-generation/config.yaml` — parámetros de generación (tamaños, seed, rutas).
- `data-generation/requirements.txt` — dependencias Python iniciales.
- `README.md` — descripción general del proyecto, arquitectura de capas y estructura.
- `CHANGELOG.md` — este archivo.

---

[Unreleased]: https://github.com/Eljosek/Prueba-tecnica-Data-know-Data-Engineer/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/Eljosek/Prueba-tecnica-Data-know-Data-Engineer/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/Eljosek/Prueba-tecnica-Data-know-Data-Engineer/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/Eljosek/Prueba-tecnica-Data-know-Data-Engineer/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Eljosek/Prueba-tecnica-Data-know-Data-Engineer/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Eljosek/Prueba-tecnica-Data-know-Data-Engineer/releases/tag/v0.1.0
