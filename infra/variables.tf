# Variables globales para Terraform

variable "environment" {
  type        = string
  description = "Entorno: dev, test, prod"
  default     = "dev"
}

variable "project_name" {
  type        = string
  description = "Nombre del proyecto"
  default     = "retailmax"
}

variable "location" {
  type        = string
  description = "Región Azure: eastus, westus, etc"
  default     = "eastus"
}

variable "location_short" {
  type        = string
  description = "Código corto de región (para nombres)"
  default     = "use"
}

variable "sql_admin_login" {
  type        = string
  description = "Login del admin SQL"
  default     = "sqladmin"
  sensitive   = true
}

variable "sql_admin_password" {
  type        = string
  description = "Password del admin SQL (generar fuerte)"
  sensitive   = true
}

variable "sql_sku" {
  type        = string
  description = "SKU de Azure SQL Database"
  default     = "S0"  # Standard tier (suficiente para dev)
}

variable "storage_access_tier" {
  type        = string
  description = "Access tier para storage: Hot, Cool, Archive"
  default     = "Hot"
}

variable "app_insights_retention" {
  type        = number
  description = "Retención de logs en días"
  default     = 30
}

variable "log_analytics_retention" {
  type        = number
  description = "Retención de Analytics logs"
  default     = 30
}

variable "tags" {
  type = object({
    Environment = string
    Project     = string
    ManagedBy   = string
    CreatedDate = string
  })
  description = "Tags comunes para todos los recursos"
  default = {
    Environment = "dev"
    Project     = "RetailMax"
    ManagedBy   = "Terraform"
    CreatedDate = "2026-04-08"
  }
}
