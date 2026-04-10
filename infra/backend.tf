# backend.tf - Documentacion del estado remoto de Terraform
#
# El estado de Terraform se almacena remotamente en Azure Storage Account.
# Configuracion en providers.tf dentro del bloque terraform { backend "azurerm" {} }
#
# Recursos:
#   Resource Group:   rg-retailmax-brs-dev
#   Storage Account:  stgretailmaxbrsdev
#   Contenedor:       tfstate
#   Clave:            dev.terraform.tfstate
#
# Para inicializar por primera vez en una maquina nueva:
#   az login
#   terraform init
#
# Para migrar de backend local a remoto:
#   terraform init -migrate-state -force-copy
