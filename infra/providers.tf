terraform {
  required_version = ">= 1.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
  }

  # Backend comentado: descomenta después de crear Storage Account manualmente
  # backend "azurerm" {
  #   resource_group_name  = "rg-retailmax-usoeast-dev"
  #   storage_account_name = "stgterraformusoeastdev"
  #   container_name       = "tfstate"
  #   key                  = "retailmax.tfstate"
  # }
}

provider "azurerm" {
  skip_provider_registration = true
  features {
    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = true
    }
  }
}

