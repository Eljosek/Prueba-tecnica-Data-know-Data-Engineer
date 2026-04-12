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
`pipelines/gold/views.sql`: 7 vistas SQL (DDL con `CREATE OR ALTER VIEW`):

| Vista | Tipo | Descripcion |
|---|---|---|
| `dim_productos` | Dimension | Catalogo de 5 000 productos con categoria |
| `dim_tiendas` | Dimension | 200 tiendas con tipo y ubicacion |
| `dim_clientes` | Dimension | 50 000 clientes CRM |
| `fact_ventas` | Hecho | 1.5M transacciones con net_amount calculado |
| `fact_inventario` | Hecho | Snapshots diarios con available_stock |
| `fact_devoluciones` | Hecho | Devoluciones con refund_amount |
| `fact_rfm_clientes` | Hecho | RFM (Recencia / Frecuencia / Monetario) ventana 90 dias |

`pipelines/gold/export_to_storage.py`: exporta las 7 vistas como Parquet al contenedor `gold`.

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

Implementado en `infra/main.tf`:

- **Key Vault** (`kv-retailmax-brs-dev`): toda credencial (SQL password, connection strings) se almacena como secreto. Ningun script contiene credenciales en texto plano; se leen de variables de entorno en ejecucion local y de Key Vault en ADF.
- **Managed Identity**: Azure Data Factory usa identidad administrada asignada por el sistema (`SystemAssigned`) con acceso `Get`/`List` a secretos de Key Vault y rol `Storage Blob Data Contributor` sobre el Storage Account.
- **RBAC minimo**: cada recurso solo tiene los permisos necesarios para operar.
- **Diagnostics**: SQL Server envia logs a Log Analytics Workspace para auditoria.
- **Sin secretos en git**: `.gitignore` excluye `*.tfstate`, `*.tfvars`, `.env` y archivos de credenciales. El estado de Terraform se almacena en el Storage Account, no en el repositorio.

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

*Ultima actualizacion: 11 de abril de 2026*

---

## Cierre

Gracias nuevamente por revisar este proyecto. Quedo atento a cualquier pregunta, sugerencia o feedback.

**Jose Miguel Herrera Gutierrez**