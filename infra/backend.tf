# backend.tf - Configuración del estado remoto de Terraform
# 
# DESARROLLO: Estado LOCAL (.tfstate en tu máquina)
# PRODUCCIÓN: Estado REMOTO (Azure Storage Account)
#
# Por ahora usamos LOCAL para simplificar

# El archivo .tfstate será creado en la raíz del proyecto
# Cuando git pull ocurra, todos tendrán el mismo state

# Para usar backend remoto después (producción):
# 1. Crear manualmente un Storage Account en Azure
# 2. Descomenta la sección en providers.tf
# 3. Ejecutar: terraform init
# 4. Elegir "yes" para migrar state a remoto
