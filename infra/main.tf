# ============================================================================
# MAIN.TF - Todos los recursos Azure para RetailMax
# ============================================================================

# ==============================================================================
# 1. RESOURCE GROUP
# ==============================================================================

resource "azurerm_resource_group" "main" {
  name     = local.resource_group_name
  location = var.location

  tags = local.common_tags
}

# ==============================================================================
# 2. STORAGE ACCOUNT (Data Lake Gen2)
# ==============================================================================

resource "azurerm_storage_account" "data_lake" {
  name                     = local.storage_account_name
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  access_tier              = var.storage_access_tier

  is_hns_enabled = true

  https_traffic_only_enabled = true

  tags = local.common_tags
}

# ==============================================================================
# 3. STORAGE CONTAINERS (Bronze, Silver, Gold, tfstate)
# ==============================================================================

resource "azurerm_storage_container" "bronze" {
  name                  = local.bronze_container_name
  storage_account_name  = azurerm_storage_account.data_lake.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "silver" {
  name                  = local.silver_container_name
  storage_account_name  = azurerm_storage_account.data_lake.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "gold" {
  name                  = local.gold_container_name
  storage_account_name  = azurerm_storage_account.data_lake.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "tfstate" {
  name                  = local.tfstate_container_name
  storage_account_name  = azurerm_storage_account.data_lake.name
  container_access_type = "private"
}

# ==============================================================================
# 4. AZURE SQL SERVER
# ==============================================================================

resource "azurerm_mssql_server" "sql_server" {
  name                         = local.sql_server_name
  resource_group_name          = azurerm_resource_group.main.name
  location                     = azurerm_resource_group.main.location
  version                      = "12.0"
  administrator_login          = var.sql_admin_login
  administrator_login_password = var.sql_admin_password

  public_network_access_enabled = true

  tags = local.common_tags
}

resource "azurerm_mssql_firewall_rule" "azure_services" {
  name             = "AllowAzureServices"
  server_id        = azurerm_mssql_server.sql_server.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# ==============================================================================
# 5. AZURE SQL DATABASE
# ==============================================================================

resource "azurerm_mssql_database" "retailmax" {
  name      = local.sql_database_name
  server_id = azurerm_mssql_server.sql_server.id
  sku_name  = var.sql_sku

  storage_account_type = "Local"

  tags = local.common_tags
}

# ==============================================================================
# 6. KEY VAULT
# ==============================================================================

data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "main" {
  name                       = local.key_vault_name
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 7
  purge_protection_enabled   = false

  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    key_permissions = [
      "Get",
      "List",
      "Create",
      "Delete"
    ]

    secret_permissions = [
      "Get",
      "List",
      "Set",
      "Delete"
    ]
  }

  tags = local.common_tags

  # Ignorar cambios en access_policy inline para no entrar en conflicto
  # con los azurerm_key_vault_access_policy separados (ej: ADF)
  lifecycle {
    ignore_changes = [access_policy]
  }
}

# ==============================================================================
# 7. SECRETOS EN KEY VAULT
# ==============================================================================

resource "azurerm_key_vault_secret" "sql_password" {
  name         = "sql-admin-password"
  value        = var.sql_admin_password
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "sql_connection_string" {
  name         = "sql-connection-string"
  value        = "Server=tcp:${azurerm_mssql_server.sql_server.fully_qualified_domain_name},1433;Initial Catalog=${azurerm_mssql_database.retailmax.name};Persist Security Info=False;User ID=${var.sql_admin_login};Password=${var.sql_admin_password};MultipleActiveResultSets=False;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;"
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "storage_connection_string" {
  name         = "storage-connection-string"
  value        = azurerm_storage_account.data_lake.primary_connection_string
  key_vault_id = azurerm_key_vault.main.id
}

# ==============================================================================
# 8. LOG ANALYTICS WORKSPACE
# ==============================================================================

resource "azurerm_log_analytics_workspace" "main" {
  name                = local.log_analytics_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = var.log_analytics_retention

  tags = local.common_tags
}

# ==============================================================================
# 9. APPLICATION INSIGHTS
# ==============================================================================

resource "azurerm_application_insights" "main" {
  name                = local.app_insights_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  application_type    = "web"

  workspace_id               = azurerm_log_analytics_workspace.main.id
  retention_in_days          = var.app_insights_retention
  disable_ip_masking         = false
  internet_ingestion_enabled = true
  internet_query_enabled     = true

  tags = local.common_tags
}

# ==============================================================================
# 10. AZURE DATA FACTORY
# ==============================================================================

resource "azurerm_data_factory" "main" {
  name                = local.data_factory_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  identity {
    type = "SystemAssigned"
  }

  tags = local.common_tags
}

resource "azurerm_key_vault_access_policy" "adf_policy" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_data_factory.main.identity[0].principal_id

  secret_permissions = [
    "Get",
    "List"
  ]
}

resource "azurerm_role_assignment" "adf_storage" {
  scope                = azurerm_storage_account.data_lake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_data_factory.main.identity[0].principal_id
}

# ==============================================================================
# 11. DIAGNOSTIC SETTINGS (SQL Server a Log Analytics)
# ==============================================================================

resource "azurerm_monitor_diagnostic_setting" "sql_diagnostics" {
  name               = "sqlserver-diagnostics"
  target_resource_id = azurerm_mssql_server.sql_server.id

  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}


