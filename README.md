<p align="center">
  <img src="docs/logo2020_DataKnow-compressor.png" alt="DataKnow Logo" width="320"/>
</p>

# Prueba Técnica — Ingeniero de Datos

**Escenario B: RetailMax · Retail y Comercio Electrónico**

| | |
|---|---|
| **Candidato** | Jose Miguel Herrera Gutierrez |
| **Correo** | Josemiguelherreragutierrez7@gmail.com |
| **GitHub** | [Eljosek](https://github.com/Eljosek/Prueba-tecnica-Data-know-Data-Engineer) |
| **LinkedIn** | [joseherreradev](https://www.linkedin.com/in/joseherreradev/) |
| **Fecha de entrega** | 13 de abril de 2026 |

---

## Hola, equipo de DataKnow

Quiero empezar agradeciendo la oportunidad. Soy Estudiante de Ingeniería de Sistemas y esta prueba fue, sin exagerar, el proyecto más completo que he armado hasta ahora. Me obligó a salir de la zona cómoda, conectar muchas piezas que solo había visto en teoría y resolver problemas reales contra la nube.

Elegí el **Escenario B (RetailMax)** porque me pareció el más tangible: ventas, inventarios, devoluciones... son datos que puedes visualizar mentalmente y eso me ayudaba a validar si los resultados tenían sentido o no. La lógica de negocio tipo RFM, quiebres de stock y tasas de devolución le daba peso analítico real.

La plataforma es **Microsoft Azure** porque es la que mejor conozco como estudiante (tengo la suscripción Azure for Students) y porque Data Factory + SQL Database + Storage Gen2 cubren todo el flujo de datos sin necesidad de recursos más complejos como Databricks o Synapse.

---

## Tabla de Contenido

- [Arquitectura general](#arquitectura-general)
- [Recursos desplegados en Azure](#recursos-desplegados-en-azure)
- [Fase 1 — Generación de datos sintéticos](#fase-1--generación-de-datos-sintéticos)
- [Fase 2 — Infraestructura como Código (Terraform)](#fase-2--infraestructura-como-código-terraform)
- [Fase 3 — pipeline Medallion (Bronze → Silver → Gold)](#fase-3--pipeline-medallion-bronze--silver--gold)
- [Fase 4 — Orquestación con Azure Data Factory](#fase-4--orquestación-con-azure-data-factory)
- [Fase 5 — Gobierno, seguridad y calidad](#fase-5--gobierno-seguridad-y-calidad)
- [Dashboard Power BI (extra — no solicitado)](#dashboard-power-bi-extra--no-solicitado)
- [Cómo reproducir este proyecto](#cómo-reproducir-este-proyecto)
- [Reflexión personal y metodología](#reflexión-personal-y-metodología)

---

## Arquitectura general

El flujo va desde Azure SQL Database (origen) hasta las vistas Gold en Storage, pasando por tres capas y un pipeline orquestador:

```
Azure SQL Database (7 tablas origen)
        │
        ▼
 PL_Ingesta_Bronze  ──►  bronze/{tabla}/yyyy/MM/dd/{tabla}.parquet
        │
        ▼
 PL_Limpieza_Silver ──►  silver/{tabla}/yyyy/MM/dd/{tabla}_clean.parquet
        │
        ▼
 PL_Vistas_Gold     ──►  gold/{vista}/yyyy/MM/dd/{vista}.parquet
        │
        ▼
 PL_Calidad_Datos   ──►  pipeline_quality_report + pipeline_errors (SQL)
        ▲
        │
 PL_Orquestador_Maestro   ← punto de entrada único (trigger diario 02:00 UTC)
```

En ADF además se definieron **16 Mapping Data Flows** que implementan la lógica de cada capa de forma visual:

| Capa | Data Flows |
|---|---|
| Silver (7) | `DF_Silver_MSTR_ARTICULOS`, `DF_Silver_MSTR_TIENDAS`, `DF_Silver_MSTR_PROVEEDORES`, `DF_Silver_CRM_MIEMBROS`, `DF_Silver_TRANS_VENTAS`, `DF_Silver_INV_STOCK_DIARIO`, `DF_Silver_POST_DEVOLUCIONES` |
| Gold (7) | `DF_Gold_dim_productos`, `DF_Gold_dim_tiendas`, `DF_Gold_dim_clientes`, `DF_Gold_fact_ventas`, `DF_Gold_fact_inventario`, `DF_Gold_fact_devoluciones`, `DF_Gold_fact_rfm_clientes` |
| Calidad (2) | `DF_Silver_Quality_Report`, `DF_Quality_Checks` |

<p align="center">
  <img src="docs/10-fase4-dataflows-16.png" alt="16 Data Flows en ADF" width="700"/>
  <br><em>Los 16 Data Flows desplegados en Azure Data Factory</em>
</p>

---

## Recursos desplegados en Azure

Todo vive en la región **Brazil South** dentro de un solo Resource Group:

| Recurso | Nombre | Para qué sirve |
|---|---|---|
| Resource Group | `rg-retailmax-brs-dev` | Agrupa todos los recursos del proyecto |
| Storage Account (ADLS Gen2) | `stgretailmaxbrsdev` | Data Lake con contenedores bronze, silver, gold y tfstate |
| Azure SQL Server | `sqlsrv-retailmax-brs-dev` | Motor de base de datos |
| Azure SQL Database | `sqldb-retailmax-brs-dev` | 7 tablas fuente + tablas de tracking/errores |
| Key Vault | `kv-retailmax-brs-dev` | Secretos: password SQL, connection strings |
| Data Factory | `adf-retailmax-brs-dev` | 5 pipelines, 16 data flows, trigger diario |
| Log Analytics | `log-retailmax-brs-dev` | Telemetría y logs de diagnóstico |
| Application Insights | `ai-retailmax-brs-dev` | Monitoreo de la aplicación |

<p align="center">
  <img src="docs/05-fase2-resource-visualizer.png" alt="Recursos Azure desplegados" width="700"/>
  <br><em>Vista del Resource Visualizer en Azure Portal</em>
</p>

---

## Fase 1 — Generación de datos sintéticos

**Carpeta:** `data-generation/`

Generé datos sintéticos con `Faker` y `numpy` para 7 tablas del dominio retail. Los datos buscan ser realistas: precios coherentes, fechas dentro de rangos lógicos, relaciones entre proveedores y artículos, etc.

| Tabla | Filas | Qué contiene |
|---|---|---|
| `MSTR_ARTICULOS` | 5 000 | Catálogo de productos con categoría y proveedor |
| `MSTR_TIENDAS` | 200 | Tiendas con tipo, ciudad y metros cuadrados |
| `MSTR_PROVEEDORES` | 500 | Proveedores con país y calificación |
| `CRM_MIEMBROS` | 50 000 | Clientes con canal preferido y fecha de alta |
| `TRANS_VENTAS` | 1 500 000 | Transacciones: precio, descuento, canal |
| `INV_STOCK_DIARIO` | 365 000 | Snapshots de stock físico, tránsito y reservado |
| `POST_DEVOLUCIONES` | 75 000 | Devoluciones con motivo, estado y canal |

**Total: ~1.8 millones de filas** cargadas a Azure SQL Database.

```bash
python data-generation/generate_data.py   # genera CSVs locales
python data-generation/load_to_sql.py     # carga a Azure SQL
```

<p align="center">
  <img src="docs/01-fase1-generacion-datos.png" alt="Generación de datos" width="700"/>
  <br><em>Ejecución de generate_data.py — 7 tablas generadas</em>
</p>

<p align="center">
  <img src="docs/04-fase1-sql-verification-azure.png" alt="Verificación SQL Azure" width="700"/>
  <br><em>Conteo de filas directamente en Azure SQL</em>
</p>

El diagrama ER del modelo está documentado en [`docs/er_diagram.md`](docs/er_diagram.md) con diagrama Mermaid.

---

## Fase 2 — Infraestructura como Código (Terraform)

**Carpeta:** `infra/`

Toda la infraestructura se define con Terraform (`azurerm ~> 3.80`). Nada se creó a mano en el portal salvo los grupos AAD para RBAC.

| Archivo | Qué define |
|---|---|
| `main.tf` | SQL Server, Storage, Key Vault, ADF, Log Analytics, App Insights, alertas, diagnósticos, RBAC de ADF |
| `adf_pipelines.tf` | Linked services, datasets y los 5 pipelines como IaC |
| `variables.tf` | Variables configurables (entorno, región, SKU). Las sensibles marcadas con `sensitive = true` |
| `locals.tf` | Nombres de recursos calculados con convención `{recurso}-{proyecto}-{región}-{env}` |
| `outputs.tf` | IDs y nombres de todos los recursos creados |
| `providers.tf` | Proveedor azurerm + backend remoto en Storage Account |

**Estado de Terraform:** almacenado remotamente en `stgretailmaxbrsdev/tfstate/terraform.tfstate` — no está en git (`.gitignore` lo excluye).

**Despliegue:**
```bash
cd infra
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
```

> Las instrucciones completas de despliegue están en `infra/` junto con los archivos de configuración.

---

## Fase 3 — pipeline Medallion (Bronze → Silver → Gold)

**Carpeta:** `pipelines/`

### Bronze — Ingesta cruda

`pipelines/bronze/ingestion.py` copia las 7 tablas de SQL a Parquet en el contenedor `bronze`. Agrega columnas de auditoría: `batch_id` (UUID), `ingest_timestamp` (UTC) y `source_system`.

### Silver — Limpieza y calidad

`pipelines/silver/cleaning.py` aplica `SELECT DISTINCT` y registra métricas por tabla en `pipeline_quality_report`: filas leídas, filas limpias, duplicados detectados, nulos y duración. Los errores individuales se guardan en `pipeline_errors`.

`pipelines/silver/export_quality_logs.py` exporta esos logs a `silver/logs/` en Storage.

<p align="center">
  <img src="docs/18-fase4-quality-report-sql.png" alt="Quality report en SQL" width="700"/>
  <br><em>Reporte de calidad en pipeline_quality_report — todas las tablas con estado EXITOSO</em>
</p>

### Gold — Vistas de negocio

`pipelines/gold/views.sql` define 8 vistas SQL con reglas de negocio reales:

| Vista | Tipo | lógica principal |
|---|---|---|
| `dim_productos` | Dimension | JOIN con proveedores, margen estimado al 30% |
| `dim_tiendas` | Dimension | Zona de distribución calculada |
| `dim_clientes` | Dimension | Género estandarizado, rango de edad imputado con moda, antigüedad en días |
| `fact_ventas` | Hecho | COALESCE para anónimos, monto bruto/neto, indicador de descuento |
| `fact_inventario` | Hecho | Promedio ventas 14d, cobertura en días, alerta de quiebre de stock |
| `fact_devoluciones` | Hecho | Precio original por JOIN, tasa de devolución por producto |
| `fact_rfm_clientes` | Hecho | Modelo RFM a 90 días con NTILE(5), segmento y clasificación |
| `kpi_ejecutivo` | KPI | métricas agregadas por fecha/país/canal |

`pipelines/gold/export_to_storage.py` exporta las 8 vistas como Parquet al contenedor `gold`.

<p align="center">
  <img src="docs/06-fase3-gold-views.png" alt="Vistas Gold" width="700"/>
  <br><em>Las 8 vistas Gold creadas en Azure SQL</em>
</p>

<p align="center">
  <img src="docs/11-fase3-pipeline-medallion.png" alt="pipeline Medallion" width="700"/>
  <br><em>pipeline Medallion: Bronze → Silver → Gold → Calidad</em>
</p>

---

## Fase 4 — Orquestación con Azure Data Factory

**Carpeta:** `orchestration/`

### 5 Pipelines en ADF

| pipeline | Qué hace |
|---|---|
| `PL_Ingesta_Bronze` | ForEach paralelo: copia las 7 tablas SQL a Parquet en bronze |
| `PL_Limpieza_Silver` | ForEach: SELECT DISTINCT + métricas de calidad por tabla |
| `PL_Vistas_Gold` | Crea las 8 vistas + exporta a Parquet en gold |
| `PL_Calidad_Datos` | Consulta quality report y errores |
| `PL_Orquestador_Maestro` | Ejecuta Bronze → Silver → Gold → Calidad en secuencia |

**Configuración:**
- **Trigger diario** a las 02:00 AM UTC (`Trigger_Diario_0200`)
- **3 reintentos** con backoff exponencial en caso de fallo
- **Dependencias explícitas** entre etapas (cada pipeline espera al anterior)

Los pipelines se desplegaron vía Python SDK (`azure-mgmt-datafactory`) porque en mi entorno de desarrollo no tenía Terraform CLI completo. El script `orchestration/deploy_adf_pipelines.py` crea linked services, datasets, los 5 pipelines y el trigger.

```bash
python orchestration/deploy_adf_pipelines.py    # pipelines + trigger
python orchestration/deploy_adf_dataflows.py     # 16 data flows
```

También existe `orchestration/pipeline_orchestrator.py` como alternativa local que ejecuta Bronze → Silver → Gold sin depender de ADF.

<p align="center">
  <img src="docs/13-fase4-pipeline-runs.png" alt="pipeline runs exitosos" width="700"/>
  <br><em>Todas las ejecuciones del orquestador con estado "Correcto"</em>
</p>

---

## Fase 5 — Gobierno, seguridad y calidad

### Gestión de secretos

**Key Vault** (`kv-retailmax-brs-dev`) almacena toda credencial sensible: password de SQL y connection strings. Ningún script tiene credenciales en texto plano — se leen de variables de entorno localmente y de Key Vault en ADF.

`.gitignore` excluye `*.tfstate`, `*.tfvars`, `.env` y archivos de credenciales. El estado de Terraform está en Storage remoto, no en el repositorio.

### RBAC — 3 roles implementados

Se crearon 3 grupos en Azure Active Directory y se asignaron roles con `orchestration/deploy_rbac.py`:

| Rol | Storage | SQL | Scope |
|---|---|---|---|
| Ingeniero de Datos | `Blob Data Contributor` en bronze/silver/gold | `Contributor` | Por contenedor |
| Analista de Datos | `Blob Data Reader` solo en gold | `Reader` | Solo lectura gold |
| Administrador | `Owner` | `Owner` | Resource Group completo |

El Analista no tiene acceso a bronze ni silver — solo puede leer gold. Esto asegura que los datos crudos y en proceso queden protegidos.

<p align="center">
  <img src="docs/17-fase5-rbac-roles-gold.png" alt="RBAC roles" width="700"/>
  <br><em>Roles RBAC asignados a los 3 grupos AAD en el contenedor gold</em>
</p>

### Alertas — Azure Monitor

Tres reglas de alerta definidas en Terraform (`infra/main.tf`) con Action Group para Notificación por correo:

| Alerta | Severidad | Qué detecta |
|---|---|---|
| `alert-adf-pipeline-failed` | 1 (Crítica) | Un pipeline de ADF falló |
| `alert-adf-pipeline-succeeded` | 3 (Info) | Reporte diario de ejecución exitosa |
| `alert-volume-anomaly` | 2 (Warning) | No hubo ejecuciones de Bronze en 24h |

<p align="center">
  <img src="docs/16-fase5-alertas-monitor.png" alt="Alertas Monitor" width="500"/>
  <br><em>Las 3 reglas de alerta activas en Azure Monitor</em>
</p>

<p align="center">
  <img src="docs/14-fase5-alert-failed-email.png" alt="Email alerta fallo" width="500"/>
  <img src="docs/15-fase5-alert-succeeded-email.png" alt="Email alerta éxito" width="500"/>
  <br><em>Emails recibidos: alerta de fallo (izq.) y confirmación de éxito (der.)</em>
</p>

### Diagnósticos y monitoreo

- ADF envía logs de `PipelineRuns`, `ActivityRuns` y `TriggerRuns` a Log Analytics
- Application Insights disponible para monitoreo adicional
- Las tablas `pipeline_quality_report` y `pipeline_errors` en SQL sirven como log de auditoría de cada ejecución

### Catálogo de datos

[`docs/data_catalog.md`](docs/data_catalog.md) documenta cada tabla Bronze y cada vista Gold con: nombre de campo, tipo, origen, si es calculado, si contiene PII y la regla de negocio aplicada.

### Linaje de datos

[`docs/data_lineage.md`](docs/data_lineage.md) tiene diagramas Mermaid con el flujo completo: desde las 7 tablas SQL de origen hasta las 8 vistas Gold, incluyendo campos calculados y reglas de transformación por vista.

### Pruebas de calidad — 5/5 pasadas

`pipelines/tests/quality_tests.py` ejecuta 5 pruebas automatizadas contra las vistas Gold:

1. PKs sin nulos en todas las vistas (dim + fact + kpi)
2. Sin fechas futuras en fact_ventas, fact_inventario, fact_devoluciones
3. `cobertura_dias` y `physical_stock` no negativos en fact_inventario
4. `rfm_segment` con patrón `Rx-Fy-Mz` y `rfm_classification` sin nulos
5. `net_amount >= 0` en todas las ventas

<p align="center">
  <img src="docs/19-fase5-quality-tests-5de5.png" alt="5 de 5 tests pasados" width="700"/>
  <br><em>Las 5 pruebas de calidad ejecutadas — todas pasaron</em>
</p>

---

## Dashboard Power BI (extra — no solicitado)

Quiero ser transparente: la prueba técnica no pide un dashboard. Lo sé. Pero después de construir las 8 vistas Gold con sus reglas de negocio, quería validar visualmente que los datos realmente tuvieran sentido antes de entregar. No me bastaba con ver filas en SQL — necesitaba graficarlo para confirmar que las transformaciones producían resultados coherentes.

Mi experiencia con Power BI es muy limitada. Nunca había armado un dashboard completo, y este fue mi primer intento real conectando datos desde Azure SQL. El resultado no es un tablero de producción ni pretende serlo, pero cumple su propósito: demuestra que la capa Gold funciona y que los datos son consumibles para análisis.

Usé **Power BI Desktop** (versión gratuita) conectado directamente a las vistas Gold de `sqldb-retailmax-brs-dev`.

### Página 1 — Ventas por año

Muestra el monto neto de ventas (`net_amount`) agrupado por año (2023 y 2024). Sirve para validar que `fact_ventas` tiene cobertura temporal completa y que los cálculos de `qty_vendida * precio_unitario - descuento` producen valores razonables.

<p align="center">
  <img src="docs/20-dashboard-ventas-por-año.png" alt="Dashboard - Ventas por año" width="700"/>
  <br><em>Ventas netas por año — datos de fact_ventas</em>
</p>

### Página 2 — Top productos

Grafica los productos con mayor volumen de transacciones usando `product_name` de `dim_productos`. Confirma que el JOIN entre `fact_ventas` y `dim_productos` funciona correctamente y que la jerarquía de categorías tiene sentido.

<p align="center">
  <img src="docs/21-dashboard-top-productos.png" alt="Dashboard - Top productos" width="700"/>
  <br><em>Productos con más transacciones — JOIN fact_ventas + dim_productos</em>
</p>

### Página 3 — Segmentos RFM

Muestra la distribución de clientes por `rfm_classification` desde `fact_rfm_clientes`. Los segmentos (Champions, Loyal, At_Risk, otros) se generan con el modelo RFM a 90 días usando NTILE(5). El gráfico confirma que la segmentación produce una distribución realista.

<p align="center">
  <img src="docs/22-dashboard-segmentos-rfm.png" alt="Dashboard - Segmentos RFM" width="700"/>
  <br><em>Distribución de clientes por segmento RFM — fact_rfm_clientes</em>
</p>

### Archivos del dashboard

| Archivo | Contenido |
|---|---|
| `dashboards/RetailMax_Dashboard.pbix` | Archivo Power BI con las 3 páginas |
| `dashboards/README.md` | Guía de Conexión a Azure SQL, modelo de datos y relaciones |
| `dashboards/dax_measures.md` | Medidas DAX definidas para el modelo |

---

## Cómo reproducir este proyecto

### Requisitos previos

- Python 3.10+ con: `pyodbc`, `pandas`, `azure-storage-blob`, `pyarrow`, `faker`, `numpy`, `azure-identity`, `azure-mgmt-datafactory`
- Terraform >= 1.5
- Suscripción Azure con los recursos desplegados (o desplegar con `terraform apply`)
- ODBC Driver 17 o 18 para SQL Server

### Variables de entorno

```powershell
$env:SQLSERVER_HOST            = "sqlsrv-retailmax-brs-dev.database.windows.net"
$env:SQLSERVER_DB              = "sqldb-retailmax-brs-dev"
$env:SQLSERVER_USER            = "sqladmin"
$env:SQLSERVER_PASSWORD        = "<tu-password>"
$env:AZURE_STORAGE_CONNECTION_STRING = "<tu-connection-string>"
```

### Paso a paso

```bash
# 1. Infraestructura
cd infra
terraform init
terraform apply -var-file="terraform.tfvars"

# 2. Generar y cargar datos
python data-generation/generate_data.py
python data-generation/load_to_sql.py

# 3. pipeline Medallion (local)
python pipelines/bronze/ingestion.py
python pipelines/silver/cleaning.py
python pipelines/silver/export_quality_logs.py
python pipelines/gold/create_views.py
python pipelines/gold/export_to_storage.py
python pipelines/upload_to_storage.py

# 4. Desplegar ADF (opcional — requiere credenciales Azure)
python orchestration/deploy_adf_pipelines.py
python orchestration/deploy_adf_dataflows.py

# 5. Pruebas de calidad
python pipelines/tests/quality_tests.py
```

---

## Reflexión personal y metodología

### Lo difícil (siendo honesto)

Este proyecto me tomó varios días y hubo momentos en los que me sentí bastante perdido. Quiero ser transparente sobre las partes que más me costaron porque creo que eso también dice algo sobre el proceso de aprendizaje:

- **La arquitectura Medallion:** Entender bien la separación Bronze/Silver/Gold no fue trivial. Al principio quería meter toda la lógica en una sola etapa y me di cuenta de que así se pierde la trazabilidad. Separar responsabilidades (ingesta cruda, limpieza, vistas de negocio) fue un antes y después.

- **Azure Data Factory:** La conexión entre ADF y los demás servicios me dio muchos dolores de cabeza. El error 403 del MSI contra Storage me tuvo horas dándole vueltas hasta que entendí que necesitaba asignar `Storage Blob Data Contributor` a la identidad administrada. Tampoco fue fácil crear los pipelines y data flows por SDK — la documentación de `azure-mgmt-datafactory` es bastante escasa.

- **Los Data Flows visuales:** Definir 16 data flows programáticamente (no desde el portal) fue un reto. Cada uno tiene su propio DSL y cualquier error de sintaxis hace que ADF lo rechace sin un mensaje claro. Fue mucho prueba y error.

- **Terraform y el estado remoto:** Configurar el backend remoto en Storage fue sencillo en teoría, pero en la práctica tuve que crear el contenedor `tfstate` antes de poder iniciar. Ese tipo de dependencias circulares (necesitas el recurso que aún no existe para guardarlo) me confundió al inicio.

- **Las pruebas de calidad:** Diseñar tests que fueran significativos y no solo "la tabla tiene filas" requirió pensar bien que podía salir mal: fechas futuras, nulos en PKs, valores negativos donde no debería haberlos.

### Metodología Agile Analytics

Algo que noté al investigar sobre DataKnow es su enfoque de **Agile Analytics**: ciclos cortos de Entender → Arquitectura → Adopción → Soporte, con iteraciones tipo Scrum (Planning → Daily → Review → Retrospectiva). Aunque trabajé solo en este proyecto, intenté seguir un patrón similar:

1. **Entender** — Primero leí todo el documento de la prueba, entendí cada fase y armé un plan mental de qué necesitaba.
2. **Arquitectura** — Definí la infraestructura con Terraform antes de escribir los scripts de datos. Primero el esqueleto, luego la carne.
3. **Adopción** — Fui implementando fase por fase, verificando cada una antes de pasar a la siguiente. No intenté hacer todo de golpe.
4. **Soporte** — Al final agregué alertas, monitoreo y pruebas de calidad para que el pipeline se pueda mantener en el tiempo.

Cada commit en el `CHANGELOG.md` refleja una iteración real del proyecto. No es un commit gigante al final — fui construyendo incrementalmente, y cuando algo se rompía, lo arreglaba y seguía.

### Lo que me llevo

Más allá de la prueba técnica, este proyecto me dejó claro que la ingeniería de datos no es solo hacer queries o mover archivos. Es diseñar sistemas que sean reproducibles, auditables y que alguien más pueda entender. Ese cambio de mentalidad fue lo más valioso.

---

**Jose Miguel Herrera Gutierrez**  
Estudiante de Ingeniería de Sistemas  
Abril 2026