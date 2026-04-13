"""
Subida de archivos Parquet a Azure Blob Storage
Containers: bronze, silver, gold
Requiere variable de entorno AZURE_STORAGE_CONNECTION_STRING
"""

import os
import sys
from pathlib import Path
from datetime import datetime

from azure.storage.blob import BlobServiceClient

BASE_DIR = Path(__file__).resolve().parent

# Mapeo local -> container
LAYERS = {
    "bronze": BASE_DIR / "bronze" / "data",
    "silver": BASE_DIR / "silver" / "data",
}

CONN_STR = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")


def upload_layer(client: BlobServiceClient, layer: str,
                 local_root: Path) -> dict:
    container = client.get_container_client(layer)
    parquet_files = list(local_root.rglob("*.parquet"))

    if not parquet_files:
        print(f"  Sin archivos Parquet en {local_root}")
        return {"layer": layer, "uploaded": 0, "errors": 0}

    uploaded = 0
    errors = 0

    for local_path in parquet_files:
        # Blob path relativa: ej. TRANS_VENTAS/2026/04/11/part0.parquet
        blob_name = local_path.relative_to(local_root).as_posix()
        try:
            with open(local_path, "rb") as f:
                container.upload_blob(
                    name=blob_name,
                    data=f,
                    overwrite=True,
                )
            print(f"    [OK] {layer}/{blob_name}")
            uploaded += 1
        except Exception as e:
            print(f"    [ERROR] {layer}/{blob_name}: {e}")
            errors += 1

    return {"layer": layer, "uploaded": uploaded, "errors": errors}


def main():
    if not CONN_STR:
        print("ERROR: la variable AZURE_STORAGE_CONNECTION_STRING no esta definida.")
        print("Obtenla desde Azure Portal:")
        print(
            "  Storage accounts -> stgretailmaxbrsdev -> Access keys -> Connection string")
        print('\nEjemplo de uso:')
        print('  $env:AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;..."')
        print('  python upload_to_storage.py')
        sys.exit(1)

    print("=" * 60)
    print("AZURE STORAGE - Subida de Parquets")
    print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    try:
        client = BlobServiceClient.from_connection_string(CONN_STR)
        # Verificar conectividad
        list(client.list_containers())
        print("\nConexion a Azure Storage establecida\n")
    except Exception as e:
        print(f"ERROR de conexion: {e}")
        sys.exit(1)

    resumen = []
    for layer, local_path in LAYERS.items():
        print(f"\n[{layer.upper()}] {local_path}")
        if not local_path.exists():
            print(f"  Directorio no encontrado: {local_path}")
            resumen.append({"layer": layer, "uploaded": 0, "errors": 1})
            continue
        resultado = upload_layer(client, layer, local_path)
        resumen.append(resultado)

    print("\n" + "=" * 60)
    print("Resumen")
    print("=" * 60)
    total_up = sum(r["uploaded"] for r in resumen)
    total_err = sum(r["errors"] for r in resumen)
    for r in resumen:
        print(
            f"  {
                r['layer']:<8} subidos={
                r['uploaded']}  errores={
                r['errors']}")
    print(f"\n  Total archivos subidos: {total_up}")
    print(f"  Total errores         : {total_err}")

    if total_err == 0:
        print("\nTodos los archivos fueron subidos. Confirma en Azure Portal:")
        print("  Storage accounts -> stgretailmaxbrsdev -> Containers")
    else:
        print("\nRevisa los errores anteriores.")
        sys.exit(1)

    print(f"\nFin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
