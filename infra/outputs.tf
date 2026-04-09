# Outputs: Lo que Terraform exporta después de crear los recursos
# Estos valores se usan en las próximas fases

# ==============================================================================
# RESOURCE GROUP
# ==============================================================================

output "resource_group_name" {
  value       = azurerm_resource_group.main.name
  description = "Nombre del Resource Group"
}

output "resource_group_id" {
  value       = azurerm_resource_group.main.id
  description = "ID del Resource Group"
}

# ==============================================================================
# STORAGE ACCOUNT
# ==============================================================================

output "storage_account_id" {
  value       = azurerm_storage_account.data_lake.id
  description = "ID de la Storage Account"
}

output "storage_account_name" {
  value       = azurerm_storage_account.data_lake.name
  description = "Nombre de la Storage Account"
}

output "storage_primary_blob_endpoint" {
  value       = azurerm_storage_account.data_lake.primary_blob_endpoint
  description = "Endpoint del Blob Storage"
}

output "storage_connection_string" {
  value       = azurerm_storage_account.data_lake.primary_connection_string
  sensitive   = true
  description = "Connection string (SECRETO)"
}

# ==============================================================================
# DATA LAKE CONTAINERS
# ==============================================================================

output "bronze_container_name" {
  value       = azurerm_storage_container.bronze.name
  description = "Nombre del contenedor Bronze"
}

output "silver_container_name" {
  value       = azurerm_storage_container.silver.name
  description = "Nombre del contenedor Silver"
}

output "gold_container_name" {
  value       = azurerm_storage_container.gold.name
  description = "Nombre del contenedor Gold"
}

# ==============================================================================
# SQL SERVER & DATABASE
# ==============================================================================

output "sql_server_id" {
  value       = azurerm_mssql_server.sql_server.id
  description = "ID del SQL Server"
}

output "sql_server_name" {
  value       = azurerm_mssql_server.sql_server.name
  description = "Nombre del SQL Server"
}

output "sql_server_fqdn" {
  value       = azurerm_mssql_server.sql_server.fully_qualified_domain_name
  description = "FQDN del SQL Server (para conexiones)"
}

output "sql_database_id" {
  value       = azurerm_mssql_database.retailmax.id
  description = "ID de la SQL Database"
}

output "sql_database_name" {
  value       = azurerm_mssql_database.retailmax.name
  description = "Nombre de la SQL Database"
}

output "sql_admin_login" {
  value       = var.sql_admin_login
  sensitive   = true
  description = "Login del admin SQL"
}

output "sql_connection_string" {
  value       = "Server=tcp:${azurerm_mssql_server.sql_server.fully_qualified_domain_name},1433;Initial Catalog=${azurerm_mssql_database.retailmax.name};User ID=${var.sql_admin_login};Password=<PASSWORD>;Encrypt=True;Connection Timeout=30;"
  sensitive   = true
  description = "Connection string plantilla (reemplazar <PASSWORD>)"
}

# ==============================================================================
# KEY VAULT
# ==============================================================================

output "key_vault_id" {
  value       = azurerm_key_vault.main.id
  description = "ID del Key Vault"
}

output "key_vault_name" {
  value       = azurerm_key_vault.main.name
  description = "Nombre del Key Vault"
}

output "key_vault_uri" {
  value       = azurerm_key_vault.main.vault_uri
  description = "URI del Key Vault"
}

# ==============================================================================
# LOG ANALYTICS
# ==============================================================================

output "log_analytics_workspace_id" {
  value       = azurerm_log_analytics_workspace.main.id
  description = "ID del Log Analytics Workspace"
}

output "log_analytics_workspace_name" {
  value       = azurerm_log_analytics_workspace.main.name
  description = "Nombre del Log Analytics"
}

# ==============================================================================
# APPLICATION INSIGHTS
# ==============================================================================

output "app_insights_id" {
  value       = azurerm_application_insights.main.id
  description = "ID de Application Insights"
}

output "app_insights_instrumentation_key" {
  value       = azurerm_application_insights.main.instrumentation_key
  sensitive   = true
  description = "Instrumentation key de App Insights"
}

output "app_insights_connection_string" {
  value       = azurerm_application_insights.main.connection_string
  sensitive   = true
  description = "Connection string de App Insights"
}

# ==============================================================================
# SUMMARY (Útil en terminal)
# ==============================================================================

output "deployment_summary" {
  value = {
    environment            = var.environment
    region                 = var.location
    resource_group         = azurerm_resource_group.main.name
    storage_account        = azurerm_storage_account.data_lake.name
    sql_server             = azurerm_mssql_server.sql_server.fully_qualified_domain_name
    sql_database           = azurerm_mssql_database.retailmax.name
    key_vault              = azurerm_key_vault.main.name
    log_analytics_workspace = azurerm_log_analytics_workspace.main.name
  }
  description = "Resumen de recursos desplegados"
}
