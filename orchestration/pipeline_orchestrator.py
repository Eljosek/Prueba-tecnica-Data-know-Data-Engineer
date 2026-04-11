"""
Phase 4 - Orquestador del pipeline medallion RetailMax
Ejecuta las capas en secuencia: Bronze -> Silver -> Gold
Registra la duracion de cada fase y el estado final
"""

import os
import sys
import time
import subprocess
import logging
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(BASE_DIR / "orchestration" / "pipeline_run.log", mode="a", encoding="utf-8"),
    ],
)
logger = logging.getLogger("orchestrator")

PYTHON = sys.executable

FASES = [
    {
        "nombre": "Bronze - Ingestion",
        "script":  BASE_DIR / "pipelines" / "bronze" / "ingestion.py",
        "cwd":     BASE_DIR / "pipelines" / "bronze",
    },
    {
        "nombre": "Silver - Cleaning",
        "script":  BASE_DIR / "pipelines" / "silver" / "cleaning.py",
        "cwd":     BASE_DIR / "pipelines" / "silver",
    },
    {
        "nombre": "Gold - Create Views",
        "script":  BASE_DIR / "pipelines" / "gold" / "create_views.py",
        "cwd":     BASE_DIR / "pipelines" / "gold",
    },
]


def ejecutar_fase(fase: dict, env: dict) -> tuple[bool, float]:
    """Ejecuta un script como subproceso y retorna (exito, segundos)."""
    nombre = fase["nombre"]
    script = fase["script"]
    cwd    = fase["cwd"]

    if not script.exists():
        logger.error(f"Script no encontrado: {script}")
        return False, 0.0

    logger.info(f"Iniciando: {nombre}")
    inicio = time.time()

    result = subprocess.run(
        [PYTHON, str(script)],
        cwd=str(cwd),
        env=env,
        capture_output=False,
    )

    duracion = round(time.time() - inicio, 2)
    exito    = result.returncode == 0

    if exito:
        logger.info(f"Completado: {nombre} ({duracion}s)")
    else:
        logger.error(f"Fallido: {nombre} (codigo {result.returncode}, {duracion}s)")

    return exito, duracion


def main():
    run_id  = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.info("=" * 60)
    logger.info(f"Pipeline RetailMax - Run ID: {run_id}")
    logger.info(f"Base dir: {BASE_DIR}")
    logger.info("=" * 60)

    # Hereda el entorno actual (variables SQLSERVER_USER / PASSWORD deben estar definidas)
    env = os.environ.copy()

    if not env.get("SQLSERVER_PASSWORD"):
        logger.error("La variable SQLSERVER_PASSWORD no esta definida.")
        logger.error("Ejecuta:  $env:SQLSERVER_PASSWORD='RetailMax@2026Data'")
        sys.exit(1)

    resultados = []
    fallo_en   = None

    for fase in FASES:
        exito, duracion = ejecutar_fase(fase, env)
        resultados.append({
            "fase":       fase["nombre"],
            "exito":      exito,
            "duracion_s": duracion,
        })
        if not exito:
            fallo_en = fase["nombre"]
            break

    logger.info("")
    logger.info("=" * 60)
    logger.info("RESUMEN DEL RUN")
    logger.info("=" * 60)
    for r in resultados:
        estado = "OK" if r["exito"] else "FALLIDO"
        logger.info(f"  {r['fase']:<30} {estado:<8} {r['duracion_s']}s")

    total = sum(r["duracion_s"] for r in resultados)
    logger.info(f"\n  Duracion total: {total}s")

    if fallo_en:
        logger.error(f"\nPipeline detenido en '{fallo_en}'.")
        logger.error("Corrige el error y vuelve a ejecutar.")
        sys.exit(1)
    else:
        logger.info("\nPipeline completado exitosamente.")
        logger.info("Las tres capas (Bronze, Silver, Gold) estan sincronizadas.")

    logger.info("=" * 60)


if __name__ == "__main__":
    main()
