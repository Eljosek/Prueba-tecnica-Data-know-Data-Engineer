"""
deploy_rbac.py
Fase 5 - Gobierno y Seguridad
Configura los tres roles RBAC requeridos sobre los recursos de RetailMax
asignando los permisos a **grupos de Azure Active Directory** (no a usuarios
individuales), lo que permite administrar el acceso mediante membresia de grupo.

Grupos AAD creados (object IDs fijos para rg-retailmax-brs-dev):
  RetailMax - Ingeniero de Datos  : 1f99d6a6-3a64-4048-8a75-2db0c2195794
  RetailMax - Analista de Datos   : b02b1fe4-b973-4f9d-8d98-38375734b0a7
  RetailMax - Administrador       : 1e3eff3d-e0ec-4788-a49a-ad6815bc8bdd

  Rol 1 - RetailMax - Ingeniero de Datos:
    Storage Blob Data Contributor sobre contenedores bronze, silver y gold.
    Contributor sobre el Azure SQL Database.

  Rol 2 - RetailMax - Analista de Datos:
    Storage Blob Data Reader unicamente sobre el contenedor gold.
    Acceso denegado por diseno a bronze y silver.

  Rol 3 - RetailMax - Administrador:
    Owner sobre el resource group completo.

Requisito: los IDs de objeto (object_id) de los GRUPOS AAD deben
pasarse como variables de entorno antes de ejecutar el script.
Por defecto se usan los IDs de los grupos pre-creados arriba.

Variables de entorno requeridas:
  SQLSERVER_PASSWORD          - contrasena del servidor SQL
  RG_INGENIERO_OBJECT_ID      - object_id del grupo Ingeniero de Datos
  RG_ANALISTA_OBJECT_ID       - object_id del grupo Analista de Datos
  RG_ADMINISTRADOR_OBJECT_ID  - object_id del grupo Administrador

Uso:
  $env:SQLSERVER_PASSWORD="..."
  $env:RG_INGENIERO_OBJECT_ID="1f99d6a6-3a64-4048-8a75-2db0c2195794"
  $env:RG_ANALISTA_OBJECT_ID="b02b1fe4-b973-4f9d-8d98-38375734b0a7"
  $env:RG_ADMINISTRADOR_OBJECT_ID="1e3eff3d-e0ec-4788-a49a-ad6815bc8bdd"
  python orchestration/deploy_rbac.py
"""
import os
import sys
import uuid

from azure.identity import InteractiveBrowserCredential
from azure.mgmt.authorization import AuthorizationManagementClient
from azure.mgmt.storage import StorageManagementClient

# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------
SUBSCRIPTION_ID = "64b1483b-b4aa-4a3b-bd59-e11ab2672810"
RESOURCE_GROUP = "rg-retailmax-brs-dev"
STORAGE_ACCOUNT = "stgretailmaxbrsdev"
TENANT_ID = "6f716858-c5ea-4ced-8eb4-417b305f7c49"

# IDs de grupos AAD pre-creados (valores por defecto)
_DEFAULT_INGENIERO_OID = "1f99d6a6-3a64-4048-8a75-2db0c2195794"
_DEFAULT_ANALISTA_OID = "b02b1fe4-b973-4f9d-8d98-38375734b0a7"
_DEFAULT_ADMINISTRADOR_OID = "1e3eff3d-e0ec-4788-a49a-ad6815bc8bdd"

# IDs de roles integrados de Azure RBAC
ROLE_STORAGE_BLOB_DATA_CONTRIBUTOR = "ba92f5b4-2d11-453d-a403-e96b0029c9fe"
ROLE_STORAGE_BLOB_DATA_READER = "2a2b9908-6ea1-4ae2-8e65-a410df84e7d1"
ROLE_CONTRIBUTOR = "b24988ac-6180-42a0-ab88-20f7382dd24c"
ROLE_OWNER = "8e3af657-a8ff-443c-a75c-2fe8c4bcb635"

# ---------------------------------------------------------------------------
# Carga de object_ids desde variables de entorno
# ---------------------------------------------------------------------------
INGENIERO_OID = os.environ.get(
    "RG_INGENIERO_OBJECT_ID",
    _DEFAULT_INGENIERO_OID)
ANALISTA_OID = os.environ.get("RG_ANALISTA_OBJECT_ID", _DEFAULT_ANALISTA_OID)
ADMIN_OID = os.environ.get(
    "RG_ADMINISTRADOR_OBJECT_ID",
    _DEFAULT_ADMINISTRADOR_OID)

if not all([INGENIERO_OID, ANALISTA_OID, ADMIN_OID]):
    print(
        "ERROR: Define las variables de entorno:\n"
        "  RG_INGENIERO_OBJECT_ID\n"
        "  RG_ANALISTA_OBJECT_ID\n"
        "  RG_ADMINISTRADOR_OBJECT_ID"
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def scope_rg() -> str:
    return f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}"


def scope_container(container: str) -> str:
    return (
        f"/subscriptions/{SUBSCRIPTION_ID}"
        f"/resourceGroups/{RESOURCE_GROUP}"
        f"/providers/Microsoft.Storage/storageAccounts/{STORAGE_ACCOUNT}"
        f"/blobServices/default/containers/{container}"
    )


def scope_sql_server() -> str:
    return (
        f"/subscriptions/{SUBSCRIPTION_ID}"
        f"/resourceGroups/{RESOURCE_GROUP}"
        f"/providers/Microsoft.Sql/servers/sqlsrv-retailmax-brs-dev"
        f"/databases/sqldb-retailmax-brs-dev"
    )


def asignar_rol(
    auth_client: AuthorizationManagementClient,
    scope: str,
    role_definition_id: str,
    principal_id: str,
    descripcion: str,
) -> None:
    role_def_scope = f"/subscriptions/{SUBSCRIPTION_ID}"
    assignment_name = str(uuid.uuid4())
    auth_client.role_assignments.create(
        scope=scope,
        role_assignment_name=assignment_name,
        parameters={
            "roleDefinitionId": f"{role_def_scope}/providers/Microsoft.Authorization/roleDefinitions/{role_definition_id}",
            "principalId": principal_id,
            "principalType": "Group",
        },
    )
    print(f"    [OK] {descripcion}")


def main() -> None:
    print("=" * 60)
    print("Configuracion RBAC - RetailMax (Fase 5)")
    print("=" * 60)

    print("\n[1/2] Autenticando con Azure...")
    credential = InteractiveBrowserCredential(tenant_id=TENANT_ID)
    auth_client = AuthorizationManagementClient(credential, SUBSCRIPTION_ID)
    print("  -> Autenticacion exitosa")

    # -----------------------------------------------------------------------
    # ROL 1 - Ingeniero de Datos
    # Acceso de lectura y escritura sobre las tres capas del Data Lake
    # mas acceso Contributor al SQL Database.
    # -----------------------------------------------------------------------
    print(f"\n[2/2] Asignando roles...")
    print(
        f"\n  --- Rol: Ingeniero de Datos (object_id: {INGENIERO_OID[:8]}...) ---")
    for container in ["bronze", "silver", "gold"]:
        asignar_rol(
            auth_client,
            scope_container(container),
            ROLE_STORAGE_BLOB_DATA_CONTRIBUTOR,
            INGENIERO_OID,
            f"Storage Blob Data Contributor -> {container}",
        )
    asignar_rol(
        auth_client,
        scope_sql_server(),
        ROLE_CONTRIBUTOR,
        INGENIERO_OID,
        "Contributor -> sqldb-retailmax-brs-dev",
    )

    # -----------------------------------------------------------------------
    # ROL 2 - Analista de Datos
    # Solo lectura sobre capa Gold. Sin acceso a bronze ni silver.
    # -----------------------------------------------------------------------
    print(
        f"\n  --- Rol: Analista de Datos (object_id: {ANALISTA_OID[:8]}...) ---")
    asignar_rol(
        auth_client,
        scope_container("gold"),
        ROLE_STORAGE_BLOB_DATA_READER,
        ANALISTA_OID,
        "Storage Blob Data Reader -> gold (unico contenedor permitido)",
    )
    # Sin asignacion sobre bronze o silver: el acceso queda denegado por
    # defecto.
    print("    [INFO] bronze: acceso denegado (sin asignacion)")
    print("    [INFO] silver: acceso denegado (sin asignacion)")

    # -----------------------------------------------------------------------
    # ROL 3 - Administrador
    # Control total sobre el resource group.
    # -----------------------------------------------------------------------
    print(f"\n  --- Rol: Administrador (object_id: {ADMIN_OID[:8]}...) ---")
    asignar_rol(
        auth_client,
        scope_rg(),
        ROLE_OWNER,
        ADMIN_OID,
        "Owner -> rg-retailmax-brs-dev (control total)",
    )

    # -----------------------------------------------------------------------
    # Resumen
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("CONFIGURACION RBAC COMPLETADA")
    print("=" * 60)
    print("  Ingeniero de Datos:")
    print("    - Storage Blob Data Contributor: bronze, silver, gold")
    print("    - Contributor: sqldb-retailmax-brs-dev")
    print("  Analista de Datos:")
    print("    - Storage Blob Data Reader: gold UNICAMENTE")
    print("    - Acceso denegado a bronze y silver por diseno")
    print("  Administrador:")
    print("    - Owner: rg-retailmax-brs-dev")
    print("\nVerificacion en Azure Portal:")
    print(
        f"  https://portal.azure.com/#@{TENANT_ID}/resource/subscriptions/"
        f"{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}/access"
    )


if __name__ == "__main__":
    main()
