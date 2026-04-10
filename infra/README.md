# Infraestructura - RetailMax Data Platform

Infraestructura como código (IaC) para la plataforma de datos RetailMax, desplegada en **Microsoft Azure** usando **Terraform**.

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│  Azure   rg-retailmax-brs-dev  (Brazil South)                   │
│                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────────────┐   │
│  │ ADLS Gen2    │   │ Azure SQL    │   │ Azure Data Factory │   │
│  │ stgretailmax │   │ sqldb-retail │   │ adf-retailmax      │   │
│  │ bronze/      │   │ max-brs-dev  │   │ (System Identity)  │   │
│  │ silver/      │   └──────────────┘   └────────────────────┘   │
│  │ gold/        │                                                │
│  │ tfstate/     │   ┌──────────────┐   ┌────────────────────┐   │
│  └──────────────┘   │ Key Vault    │   │ Log Analytics +    │   │
│                     │ kv-retailmax │   │ App Insights       │   │
│                     └──────────────┘   └────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Recursos desplegados

| Recurso | Nombre | Propósito |
|---|---|---|
| Resource Group | rg-retailmax-brs-dev | Contenedor lógico de todos los recursos |
| Storage Account (ADLS Gen2) | stgretailmaxbrsdev | Data Lake con capas bronze/silver/gold |
| Contenedores | bronze, silver, gold, tfstate | Zonas del Data Lake + estado de Terraform |
| SQL Server | sqlsrv-retailmax-brs-dev | Servidor de base de datos relacional |
| SQL Database | sqldb-retailmax-brs-dev | Base de datos (SKU S0) |
| Key Vault | kv-retailmax-brs-dev | Secretos y credenciales (sql-admin-password) |
| Log Analytics | la-retailmax-brs-dev | Centralización de logs y métricas |
| Application Insights | ai-retailmax-brs-dev | Monitoreo de aplicaciones |
| Azure Data Factory | adf-retailmax-brs-dev | Orquestación de pipelines ETL |

## Prerrequisitos

- [Terraform](https://developer.hashicorp.com/terraform/downloads) >= 1.5
- [Azure CLI](https://docs.microsoft.com/es-es/cli/azure/install-azure-cli) >= 2.50
- Suscripción de Azure con permisos de `Contributor` en el Resource Group
- Los siguientes providers de Terraform: `hashicorp/azurerm ~> 3.80`

## Variables

| Variable | Descripción | Valor por defecto |
|---|---|---|
| `project_name` | Nombre del proyecto | `retailmax` |
| `environment` | Entorno (dev / stg / prod) | `dev` |
| `location` | Región de Azure | `brazilsouth` |
| `location_short` | Abreviatura de región | `brs` |
| `sql_admin_login` | Usuario administrador SQL | `sqladmin` |
| `sql_admin_password` | Contraseña admin SQL | *(requerida, no tiene default)* |

## Cómo desplegar

### 1. Autenticación

```bash
az login
az account set --subscription "<ID_DE_SUBSCRIPCION>"
```

### 2. Configurar variables

Copiar el archivo de ejemplo y ajustar los valores:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Editar `terraform.tfvars` con la contraseña SQL real:

```hcl
sql_admin_password = "<contraseña-segura>"
```

> **Nota:** `terraform.tfvars` está en `.gitignore` para evitar exponer credenciales.

### 3. Inicializar Terraform

En el **primer despliegue** (sin backend remoto previo):

```bash
terraform init
```

En despliegues subsecuentes (backend remoto ya configurado en Azure Storage):

```bash
terraform init -backend-config=providers.tf
```

### 4. Revisar el plan

```bash
terraform plan
```

### 5. Aplicar los cambios

```bash
terraform apply
```

## Backend remoto

El estado de Terraform se almacena en Azure Storage para trabajo en equipo y mayor seguridad:

```
Storage Account : stgretailmaxbrsdev
Contenedor      : tfstate
Clave           : dev.terraform.tfstate
```

La configuración del backend está en `providers.tf`:

```hcl
backend "azurerm" {
  resource_group_name  = "rg-retailmax-brs-dev"
  storage_account_name = "stgretailmaxbrsdev"
  container_name       = "tfstate"
  key                  = "dev.terraform.tfstate"
}
```

## Estructura de archivos

```
infra/
├── main.tf               # Definición de todos los recursos Azure
├── providers.tf          # Configuración del provider + backend remoto
├── variables.tf          # Declaración de variables de entrada
├── locals.tf             # Valores calculados y nombres de recursos
├── outputs.tf            # Valores exportados tras el despliegue
├── terraform.tfvars      # Variables con valores reales (excluido de git)
└── terraform.tfvars.example  # Plantilla de variables para el equipo
```

## Convención de nombres

Los recursos siguen el patrón: `<tipo>-<proyecto>-<región>-<entorno>`

Ejemplo: `sqlsrv-retailmax-brs-dev`

## Seguridad

- Credenciales SQL almacenadas en Key Vault (secreto `sql-admin-password`)
- Azure Data Factory accede al Storage via Managed Identity (rol `Storage Blob Data Contributor`)
- `terraform.tfvars` está en `.gitignore`
- Firewall del SQL Server permite solo servicios Azure y las IPs autorizadas explícitamente
