# PASOS PARA EJECUTAR FASE 2 - Terraform

**Fecha:** Miércoles 8 de Abril  
**Duración estimada:** 1-2 horas  
**Resultado:** Todos los recursos Azure provisioned

---

## ✅ PRE-REQUISITOS:

Verifica que tengas:
- [ ] Azure CLI instalado (`az --version`)
- [ ] Terraform instalado (`terraform --version`)
- [ ] Autenticado en Azure (`az login`)
- [ ] Conexión a internet estable

---

## 📋 PASO A PASO:

### PASO 1: Verificar Azure Login
```bash
az account show
```
Deberías ver tu suscripción de Azure. Si no funciona:
```bash
az login
```

---

### PASO 2: Crear estructura Terraform

En tu repo real (`Prueba-tecnica-Data-know-Data-Engineer`):

```bash
cd infra/
```

Verifica que tienes estos 7 archivos:
```
infra/
├── providers.tf          ✅
├── variables.tf          ✅
├── main.tf               ✅
├── outputs.tf            ✅
├── locals.tf             ✅
├── terraform.tfvars      ✅
└── backend.tf            ✅
```

---

### PASO 3: Inicializar Terraform

```bash
terraform init
```

**¿Qué hace?**
- Descarga el provider de Azure (~200MB)
- Crea carpeta `.terraform/`
- Prepara el environment

**Tiempo:** 2-3 minutos

---

### PASO 4: Validar configuración

```bash
terraform validate
```

**¿Qué hace?**
- Revisa que la sintaxis sea correcta
- Verifica que variables existan

**Esperado:** Verde (sin errores)

---

### PASO 5: Ver qué se va a crear

```bash
terraform plan
```

**¿Qué hace?**
- Muestra TODOS los recursos que se crearán
- **NO los crea aún**
- Útil para revisar antes de ejecutar

**Esperado:** Ver ~15-20 recursos a crear

```
Terraform will perform the following actions:

# azurerm_application_insights.main will be created
+ resource "azurerm_application_insights" "main" {
    ...
  }

# azurerm_key_vault.main will be created
...

Plan: 15 to add, 0 to change, 0 to destroy.
```

**Tiempo:** 1-2 minutos

---

### PASO 6: Aplicar los cambios (CREAR TODO)

```bash
terraform apply
```

**¿Qué hace?**
- Crea TODO en Azure
- Muestra primero el plan
- Pide confirmación ("yes/no")

**Acción:** Escribe `yes` y presiona Enter

**Esperado:** Ver "Apply complete! Resources: X added."

**Tiempo:** 5-10 minutos (depende de Azure)

---

### PASO 7: Verificar que se creó

```bash
terraform output
```

**¿Qué hace?**
- Muestra todos los IDs y conexiones de recursos

**Esperado:** Ver algo así:

```
app_insights_connection_string = <sensitive>
app_insights_id = /subscriptions/XXX/resourceGroups/rg-retailmax-use-dev/...
deployment_summary = {
  "environment" = "dev"
  "key_vault" = "kv-retailmax-use-dev"
  "log_analytics_workspace" = "la-retailmax-use-dev"
  "region" = "eastus"
  "resource_group" = "rg-retailmax-use-dev"
  "sql_database" = "sqldb-retailmax-use-dev"
  "sql_server" = "sqlsrv-retailmax-use-dev.database.windows.net"
  "storage_account" = "stgretailmaxusedev"
}
...
```

---

### PASO 8: Verificar en Azure Portal (Optional)

Ve a https://portal.azure.com

Verifica que ves:
- Resource Group: `rg-retailmax-use-dev`
- Storage Account: `stgretailmaxusedev`
- SQL Server: `sqlsrv-retailmax-use-dev`
- Key Vault: `kv-retailmax-use-dev`
- Log Analytics: `la-retailmax-use-dev`

---

### PASO 9: Guardar outputs para Fase 3

Los outputs importantes:

```bash
# SQL Connection string
terraform output sql_server_fqdn
terraform output sql_database_name
terraform output sql_admin_login

# Storage
terraform output storage_account_name
terraform output bronze_container_name
terraform output silver_container_name
terraform output gold_container_name

# Key Vault
terraform output key_vault_uri
```

Guarda estos valores. Los usarás en Fase 3 (pipeline).

---

### PASO 10: Hacer commit

```bash
git add infra/
git commit -m "feat: provisionar infraestructura Azure con Terraform

- Crear Resource Group
- Data Lake Storage Gen2 con containers (Bronze, Silver, Gold)
- Azure SQL Server + Database
- Key Vault para secretos
- Log Analytics + Application Insights
- Configurar firewall y diagnósticos"
```

---

## 🚨 Si algo falla:

### Error: "Azure subscription not found"
```bash
az login
az account set --subscription "YOUR-SUBSCRIPTION-ID"
```

### Error: "Resource already exists"
```bash
# Hay con este nombre en Azure. Opciones:
# 1. Cambiar el nombre en terraform.tfvars
# 2. Destruir y recrear: terraform destroy
```

### Error: "Access denied"
```bash
# No tienes permisos en Azure. Contacta a tu admin.
# O verifica: az account show
```

### Error: "Terraform lock file"
```bash
rm .terraform.lock.hcl
terraform init
```

---

## 📊 Checklist Final:

- [ ] `az login` funciona
- [ ] `terraform init` completado
- [ ] `terraform validate` sin errores
- [ ] `terraform plan` muestra recursos
- [ ] `terraform apply` completado
- [ ] `terraform output` muestra IDs
- [ ] Recursos visible en Azure Portal
- [ ] Commit en Git
- [ ] Outputs guardados (para Fase 3)

---

## 🎉 FASE 2: COMPLETADA!

Cuando termines, tienes:
- ✅ Resource Group en Azure
- ✅ Storage Account (Data Lake)
- ✅ Azure SQL Database
- ✅ Key Vault
- ✅ Log Analytics + App Insights

**Próximo:**
- Fase 3: Cargar datos a Azure SQL
- Fase 3: Crear transformaciones (Bronze/Silver/Gold)

---

*Guía de ejecución: 8 de Abril de 2026*
