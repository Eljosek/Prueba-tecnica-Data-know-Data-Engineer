# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)  
and follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- `data-generation/load_to_sql.py` — script de carga de 7 archivos CSV a Azure SQL Database
  usando `pyodbc` directo con `fast_executemany`, detección automática de driver ODBC,
  inferencia de tipos SQL, normalización de nulos y verificación de conteos finales.
- `docs/er_diagram.md` — diagrama Entidad-Relación en formato Mermaid con las 7 tablas del
  modelo de datos: MSTR_PROVEEDORES, MSTR_TIENDAS, MSTR_ARTICULOS, CRM_MIEMBROS,
  TRANS_VENTAS, INV_STOCK_DIARIO y POST_DEVOLUCIONES.
- `infra/README.md` — guía de despliegue de la infraestructura Terraform: arquitectura,
  recursos provisionados, variables, pasos de deploy, backend remoto y convenciones de nombrado.

### Changed
- `data-generation/requirements.txt` — añadidos `pyodbc>=4.0.39` y `python-dotenv>=1.0.0`.
- `data-generation/config.yaml` — corregido nombre del servidor SQL
  (`sqlsrv-retailmax-brs-dev.database.windows.net`) y base de datos (`sqldb-retailmax-brs-dev`).

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

[Unreleased]: https://github.com/JoseMariaDiazContador/Prueba-tecnica-Data-know-Data-Engineer/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/JoseMariaDiazContador/Prueba-tecnica-Data-know-Data-Engineer/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/JoseMariaDiazContador/Prueba-tecnica-Data-know-Data-Engineer/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/JoseMariaDiazContador/Prueba-tecnica-Data-know-Data-Engineer/releases/tag/v0.1.0
