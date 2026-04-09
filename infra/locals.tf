# Valores calculados/reutilizables
# Esto evita hardcodear nombres en múltiples lugares

locals {
  # Nombre base para recursos
  resource_base_name = "${var.project_name}-${var.location_short}-${var.environment}"

  # Nombres de recursos (siguen convención Azure)
  resource_group_name = "rg-${local.resource_base_name}"
  
  storage_account_name = replace(
    "stg${var.project_name}${var.location_short}${var.environment}",
    "-",
    ""
  )
  
  sql_server_name   = "sqlsrv-${local.resource_base_name}"
  sql_database_name = "sqldb-${local.resource_base_name}"
  
  key_vault_name      = "kv-${local.resource_base_name}"
  log_analytics_name  = "la-${local.resource_base_name}"
  app_insights_name   = "ai-${local.resource_base_name}"
  
  # Contenedores Data Lake
  bronze_container_name = "bronze"
  silver_container_name = "silver"
  gold_container_name   = "gold"
  
  # Tags comunes
  common_tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
    CreatedDate = "2026-04-08"
    Location    = var.location
  }
}
