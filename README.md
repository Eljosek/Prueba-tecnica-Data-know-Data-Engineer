# Prueba Tecnica - Ingeniero de Datos
### RetailMax · Escenario B – Retail y Comercio Electrónico

> **Candidato:** Jose Miguel Herrera Gutierrez 
> **Correo:** Josemiguelherreragutierrez7@gmail.com
> **Fecha:** Abril 8, 2026  
> **GitHub:** https://github.com/Eljosek/Prueba-tecnica-Data-know-Data-Engineer
> **LinkedIn:** https://www.linkedin.com/in/joseherreradev/

---

## Saludo Cordial

Agradezco sinceramente la oportunidad de participar en esta prueba técnica de **DataKnow**. Ha sido un verdadero honor trabajar en este desafío y demostrar mis habilidades como Ingeniero de Datos. Espero que este proyecto refleje mi dedicación, conocimiento técnico y pasión por la ingeniería de datos moderna. Saludos cordiales a quienes revisen este trabajo.

## Escenario Elegido: B - Retail y Comercio Electrónico

RetailMax es una cadena de retail que necesita optimizar su cadena de suministro mediante análisis de datos. Este escenario fue elegido porque:
- Lógica de negocio clara y relatable
- Datos reales de ventas, inventario y devoluciones
- Aplicación práctica de RFM y análisis de quiebres de stock

## Plataforma Elegida: Microsoft Azure

Se seleccionó Azure porque:
- **Data Lake Storage Gen2** para almacenamiento escalable
- **Azure Data Factory** para orquestación nativa
- **Azure SQL Database** para datos origen
- **Terraform** para infraestructura como código (IaC)
- Integración nativa con servicios Microsoft

## Tabla de Contenido

- [Arquitectura](#arquitectura)
- [Recursos Azure](#recursos-azure)
- [Fase 1 – Generacion de datos sinteticos](#fase-1--generacion-de-datos-sinteticos)
- [Fase 2 – Infraestructura como Codigo](#fase-2--infraestructura-como-codigo)
- [Fase 3 – Pipeline Medallion](#fase-3--pipeline-medallion)
- [Fase 4 – Orquestacion ADF](#fase-4--orquestacion-adf)
- [Fase 5 – Gobierno y Seguridad](#fase-5--gobierno-y-seguridad)
- [Extras – CI/CD, Lineage y Monitoreo](#extras--cicd-lineage-y-monitoreo)
- [Dashboard Power BI](#dashboard-power-bi)
- [Reproduccion local](#reproduccion-local)

---

## Arquitectura

```
Azure SQL Database (origen)
        |
        v
[PL_Ingesta_Bronze]  -->  Storage: bronze/{tabla}/yyyy/MM/dd/{tabla}.parquet
        |
        v
[PL_Limpieza_Silver] -->  Storage: silver/{tabla}/yyyy/MM/dd/{tabla}_clean.parquet
        |
        v
[PL_Vistas_Gold]     -->  Storage: gold/{vista}/yyyy/MM/dd/{vista}.parquet
        |
        v
[PL_Calidad_Datos]   -->  pipeline_quality_report + pipeline_errors (SQL)
        ^
        |
[PL_Orquestador_Maestro]  <-- punto de entrada unico
```

**Mapping Data Flows (16)**
| Capa | Data Flows |
|---|---|
| Silver | DF_Silver_MSTR_ARTICULOS, DF_Silver_MSTR_TIENDAS, DF_Silver_MSTR_PROVEEDORES, DF_Silver_CRM_MIEMBROS, DF_Silver_TRANS_VENTAS, DF_Silver_INV_STOCK_DIARIO, DF_Silver_POST_DEVOLUCIONES |
| Gold | DF_Gold_dim_productos, DF_Gold_dim_tiendas, DF_Gold_dim_clientes, DF_Gold_fact_ventas, DF_Gold_fact_inventario, DF_Gold_fact_devoluciones, DF_Gold_fact_rfm_clientes |
| Calidad | DF_Silver_Quality_Report, DF_Quality_Checks |

---

## Recursos Azure

| Recurso | Nombre | Descripcion |
|---|---|---|
| Resource Group | `rg-retailmax-brs-dev` | Contenedor de todos los recursos |
| Storage Account | `stgretailmaxbrsdev` | Data Lake con capas bronze, silver, gold |
| Azure SQL Server | `sqlsrv-retailmax-brs-dev` | Motor de base de datos |
| Azure SQL Database | `sqldb-retailmax-brs-dev` | 7 tablas fuente + tablas de tracking |
| Key Vault | `kv-retailmax-brs-dev` | Gestion de secretos (SQL password, connection strings) |
| Data Factory | `adf-retailmax-brs-dev` | 5 pipelines + 16 data flows |
| Log Analytics | `log-retailmax-brs-dev` | Telemetria y diagnosticos |
| Application Insights | `ai-retailmax-brs-dev` | Monitoreo de la aplicacion |

---

## Fase 1 – Generacion de datos sinteticos

**Archivos:** `data-generation/`

Se generaron datos sinteticos realistas para 7 tablas del dominio retail:

| Tabla | Filas | Descripcion |
|---|---|---|
| `MSTR_ARTICULOS` | 5 000 | Catalogo de productos con categoria y proveedor |
| `MSTR_TIENDAS` | 200 | Tiendas con tipo, ciudad y metros cuadrados |
| `MSTR_PROVEEDORES` | 500 | Proveedores con pais y tipo |
| `CRM_MIEMBROS` | 50 000 | Clientes con canal preferido y fecha de alta |
| `TRANS_VENTAS` | 1 500 000 | Transacciones con descuento, precio y canal de venta |
| `INV_STOCK_DIARIO` | 365 000 | Snapshots de stock fisico, transito y reservado |
| `POST_DEVOLUCIONES` | 75 000 | Devoluciones con motivo, estado y canal |

**Total: 1 795 700 filas cargadas a Azure SQL Database.**

Herramientas usadas: `Faker`, `numpy`, `pyodbc`, `pandas`.

```bash
python data-generation/generate_data.py
python data-generation/load_to_sql.py
```

---

## Fase 2 – Infraestructura como Codigo

**Archivos:** `infra/`

Todos los recursos Azure se definen en Terraform (`hashicorp/azurerm ~> 3.80`):

| Archivo | Contenido |
|---|---|
| `main.tf` | SQL Server, Storage, Key Vault, ADF, Log Analytics, App Insights, roles RBAC |
| `adf_pipelines.tf` | Linked services, datasets y 5 pipelines definidos como IaC |
| `variables.tf` | Variables configurables (entorno, region, SKU) |
| `locals.tf` | Nombres de recursos calculados con convencion Azure |
| `outputs.tf` | Outputs de todos los recursos desplegados |
| `providers.tf` | Proveedor azurerm con backend de estado remoto |

La infraestructura fue aplicada con `terraform apply`. El estado se almacena en `stgretailmaxbrsdev/tfstate/`.

---

## Fase 3 – Pipeline Medallion

**Archivos:** `pipelines/`

### Bronze
`pipelines/bronze/ingestion.py`

Ingesta desde Azure SQL hacia el contenedor `bronze` en formato Parquet. Agrega columnas de auditoria:
- `batch_id`: UUID unico por ejecucion
- `ingest_timestamp`: marca de tiempo UTC
- `source_system`: nombre del servidor SQL origen

### Silver
`pipelines/silver/cleaning.py`

Limpieza y deduplicacion con `SELECT DISTINCT`. Por cada tabla se registra en `pipeline_quality_report`:
- filas leidas, filas limpias, duplicados detectados, nulos detectados
- duracion en segundos y estado (`EXITOSO` / `CON_ERRORES`)

Los errores de registro individual se almacenan en `pipeline_errors`.

`pipelines/silver/export_quality_logs.py`: exporta los logs a `silver/logs/` en Storage.

### Gold
`pipelines/gold/views.sql`: 8 vistas SQL (DDL con `CREATE OR ALTER VIEW`):

| Vista | Tipo | Descripcion |
|---|---|---|
| `dim_productos` | Dimension | JOIN con proveedores, `estimated_margin` (30%) |
| `dim_tiendas` | Dimension | `zona_distribucion` calculada por `id_pais % 5` |
| `dim_clientes` | Dimension | Género estandarizado, `age_range` imputado con moda, `antiguedad_dias` |
| `fact_ventas` | Hecho | `COALESCE` para anónimos, `gross/net_amount`, `ind_con_descuento` |
| `fact_inventario` | Hecho | CTE ventas 14d, `avg_daily_sales_14d`, `cobertura_dias`, `alerta_quiebre` |
| `fact_devoluciones` | Hecho | `original_unit_price` por JOIN, `return_rate_by_product` por CTE |
| `fact_rfm_clientes` | Hecho | RFM ventana 90 días, `NTILE(5)`, segmento R#-F#-M#, clasificación |
| `kpi_ejecutivo` | KPI | Agregación diaria por fecha/país/canal: transacciones, clientes, ventas brutas/netas |

`pipelines/gold/export_to_storage.py`: exporta las 8 vistas como Parquet al contenedor `gold`.

---

## Fase 4 – Orquestacion ADF

**Archivos:** `orchestration/`

### Pipelines (5)

| Pipeline | Descripcion |
|---|---|
| `PL_Ingesta_Bronze` | ForEach con 4 actividades paralelas: copia 7 tablas SQL a Parquet bronze |
| `PL_Limpieza_Silver` | ForEach: `SELECT DISTINCT` por tabla + registro de metricas de calidad |
| `PL_Vistas_Gold` | `CREATE OR ALTER VIEW` x7 + ForEach export a Parquet gold |
| `PL_Calidad_Datos` | Consulta `pipeline_quality_report` y `pipeline_errors` |
| `PL_Orquestador_Maestro` | Ejecuta Bronze → Silver → Gold → Calidad en cadena |

### Mapping Data Flows (16)

Cada Data Flow define la logica de transformacion visual en ADF:
- **Silver (7):** filtro de nulos en clave primaria + columnas de auditoria `silver_ingest_ts`, `silver_source`
- **Gold (7):** lectura desde vistas SQL + columna de auditoria `gold_ingest_ts`
- **Calidad (2):** `DF_Silver_Quality_Report` (agregacion de metricas) y `DF_Quality_Checks` (resumen de errores)

### Despliegue

Los pipelines y data flows se desplegaron via SDK de Python (`azure-mgmt-datafactory`) dado que Terraform CLI no estaba disponible en el entorno de desarrollo:

```bash
# Variables de entorno requeridas
$env:SQLSERVER_PASSWORD="..."
$env:AZURE_STORAGE_CONNECTION_STRING="..."

# Desplegar pipelines, linked services y datasets
python orchestration/deploy_adf_pipelines.py

# Desplegar data flows y corregir queries
python orchestration/deploy_adf_dataflows.py
```

### Orquestador Python local

`orchestration/pipeline_orchestrator.py`: alternativa local que ejecuta Bronze → Silver → Gold secuencialmente con logging detallado, sin dependencia de ADF.

---

## Fase 5 – Gobierno y Seguridad

### Gestion de Secretos
- **Key Vault** (`kv-retailmax-brs-dev`): toda credencial (SQL password, connection strings) se almacena como secreto. Ningun script contiene credenciales en texto plano; se leen de variables de entorno en ejecucion local y de Key Vault en ADF.
- **Sin secretos en git**: `.gitignore` excluye `*.tfstate`, `*.tfvars`, `.env` y archivos de credenciales. El estado de Terraform se almacena en Storage Account remoto.

### Managed Identity y RBAC
- **Managed Identity**: ADF usa identidad `SystemAssigned` con acceso `Get`/`List` a Key Vault y rol `Storage Blob Data Contributor` en Storage.
- **3 roles RBAC** definidos en `orchestration/deploy_rbac.py`:

| Rol | Permisos Storage | Permisos SQL | Scope |
|---|---|---|---|
| Ingeniero de Datos | `Blob Data Contributor` (bronze/silver/gold) | `Contributor` | Por contenedor |
| Analista de Datos | `Blob Data Reader` (solo gold) | `Reader` | Solo gold |
| Administrador | `Owner` | `Owner` | Resource Group completo |

### Alertas (Azure Monitor)
Definidas en `infra/main.tf` con Action Group para notificacion por correo:

| Alerta | Severidad | Descripcion |
|---|---|---|
| `alert-adf-pipeline-failed` | 1 (Critica) | Notifica cuando un pipeline de ADF falla |
| `alert-adf-pipeline-succeeded` | 3 (Info) | Reporte diario: confirma ejecucion exitosa |
| `alert-volume-anomaly` | 2 (Warning) | Detecta cuando no hay ejecuciones de Bronze en 24h |

### Diagnosticos
- SQL Server y ADF envian logs a Log Analytics Workspace con categorias `PipelineRuns`, `ActivityRuns`, `TriggerRuns`.
- Application Insights disponible para monitoreo de la aplicacion.

### Catalogo de Datos
`docs/data_catalog.md`: catalogo completo con una seccion por tabla (Bronze) y por vista (Gold). Documenta nombre de campo, tipo, origen, si es calculado, PII y regla de negocio.

### Linaje de Datos
`docs/data_lineage.md`: diagrama Mermaid con el flujo completo de datos desde origen SQL hasta las 8 vistas Gold, incluyendo detalle de campos calculados y reglas de negocio por vista.

### Pruebas de Calidad
`pipelines/tests/quality_tests.py`: 5 pruebas automatizadas contra las vistas Gold:
1. PKs sin nulos en todas las vistas
2. Sin fechas futuras en tablas de hechos
3. `cobertura_dias` y `physical_stock` no negativos
4. `rfm_segment` con patron R#-F#-M# y clasificacion sin nulos
5. `net_amount >= 0` en todas las ventas

---

## Extras – CI/CD, Lineage y Monitoreo

### CI/CD con GitHub Actions
`.github/workflows/ci.yml`: pipeline de integracion continua que se ejecuta en cada push/PR a `main`:
- **Python Lint**: valida estilo de codigo con `flake8` (max 120 caracteres)
- **Quality Tests**: ejecuta las 5 pruebas de calidad contra Azure SQL
- **Terraform Validate**: valida sintaxis y formato de la infraestructura IaC

### Linaje de Datos
`docs/data_lineage.md`: documentacion completa del flujo de datos con diagramas Mermaid:
- Flujo general: Origen → Bronze → Silver → Gold (por tabla y vista)
- Detalle por vista Gold: campos calculados, tablas origen, reglas de negocio
- Cadena de orquestacion: Trigger → Maestro → Bronze → Silver → Gold → Calidad

### Monitoreo y Alertas
- **Action Group**: notificacion por correo configurada en Terraform
- **3 alertas**: fallo de pipeline (Sev 1), exito diario (Sev 3), anomalia de volumen (Sev 2)
- **Diagnosticos ADF**: logs de PipelineRuns, ActivityRuns y TriggerRuns a Log Analytics

---

## Dashboard Power BI

Se incluye un dashboard de visualizacion con **Power BI Desktop** (gratuito) conectado
directamente a las 8 vistas Gold de Azure SQL.

### Paginas del dashboard

| Pagina | Contenido |
|---|---|
| **Resumen Ejecutivo** | KPIs diarios: ventas netas, transacciones, clientes unicos, ticket promedio (desde `kpi_ejecutivo`) |
| **Analisis de Ventas** | Ventas por canal, pais y categoria. Top 10 productos. Segmentacion con/sin descuento |
| **Inventario** | Productos con alerta de quiebre, cobertura promedio, stock disponible vs reservado |
| **Devoluciones** | Tasa de devolucion por producto, motivos principales, tendencia mensual |
| **Clientes RFM** | Segmentos Champions / Loyal / At\_Risk, clientes activos vs inactivos 90d |

### Archivos de referencia

- `dashboards/README.md`: guia completa de conexion, modelo de datos y relaciones
- `dashboards/dax_measures.md`: medidas DAX (ventas, inventario, devoluciones, RFM, KPIs)

---

## Reproduccion local

### Requisitos
- Python 3.x con paquetes: `pyodbc`, `pandas`, `azure-storage-blob`, `pyarrow`, `faker`, `numpy`, `azure-identity`, `azure-mgmt-datafactory`
- Acceso a suscripcion Azure con los recursos desplegados
- ODBC Driver para SQL Server

### Variables de entorno

```powershell
$env:SQLSERVER_HOST   = "sqlsrv-retailmax-brs-dev.database.windows.net"
$env:SQLSERVER_DB     = "sqldb-retailmax-brs-dev"
$env:SQLSERVER_USER   = "sqladmin"
$env:SQLSERVER_PASSWORD = "<password>"
$env:AZURE_STORAGE_CONNECTION_STRING = "<connection_string>"
```

### Orden de ejecucion

```bash
# Fase 1: generar y cargar datos
python data-generation/generate_data.py
python data-generation/load_to_sql.py

# Fase 3: ejecutar pipeline medallion local
python pipelines/bronze/ingestion.py
python pipelines/silver/cleaning.py
python pipelines/silver/export_quality_logs.py
python pipelines/gold/create_views.py
python pipelines/gold/export_to_storage.py
python pipelines/upload_to_storage.py

# Fase 4 opcion A: desplegar ADF (requiere credenciales Azure)
python orchestration/deploy_adf_pipelines.py
python orchestration/deploy_adf_dataflows.py

# Fase 4 opcion B: orquestador Python local
python orchestration/pipeline_orchestrator.py
```

---

*Ultima actualizacion: 13 de abril de 2026*

---

## Capturas de Pantalla

Todas las evidencias del proyecto se encuentran en `docs/`:

| # | Archivo | Descripcion |
|---|---|---|
| 01 | `01-fase1-generacion-datos.png` | Generacion de datos sinteticos |
| 02 | `02-fase1-output-files.png` | Archivos de salida generados |
| 03 | `03-fase1-sql-verification.png` | Verificacion SQL local |
| 04 | `04-fase1-sql-verification-azure.png` | Verificacion SQL en Azure |
| 05 | `05-fase2-resource-visualizer.png` | Visualizador de recursos Azure |
| 06 | `06-fase3-gold-views.png` | 8 vistas Gold en SQL |
| 07 | `07-fase1-dataset-overview.png` | Overview del dataset completo |
| 08 | `08-fase3-kpi-ejecutivo.png` | Vista kpi_ejecutivo |
| 09 | `09-fase3-dim-productos.png` | Vista dim_productos |
| 10 | `10-fase4-dataflows-16.png` | 16 Mapping Data Flows en ADF |
| 11 | `11-fase3-pipeline-medallion.png` | Pipeline Medallion ETL |
| 12 | `12-fase4-tablas-tracking.png` | Tablas de tracking SQL |
| 13 | `13-fase4-pipeline-runs.png` | Ejecuciones de pipeline (todas Correcto) |
| 14 | `14-fase5-alert-failed-email.png` | Email de alerta: pipeline failed |
| 15 | `15-fase5-alert-succeeded-email.png` | Email de alerta: pipeline succeeded |
| 16 | `16-fase5-alertas-monitor.png` | 3 reglas de alerta en Azure Monitor |
| 17 | `17-fase5-rbac-roles-gold.png` | Roles RBAC en contenedor gold (3 grupos) |
| 18 | `18-fase4-quality-report-sql.png` | Quality report en SQL |
| 19 | `19-fase5-quality-tests-5de5.png` | 5/5 pruebas de calidad pasadas |

---

## Cierre

Gracias nuevamente por revisar este proyecto. Quedo atento a cualquier pregunta, sugerencia o feedback.

**Jose Miguel Herrera Gutierrez**