"""Monitoramento do arquivo Excel e disparo automático do pipeline."""
import hashlib
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s — %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(BASE_DIR / "logs" / "watch.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("watch")


def _md5(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _run_pipeline():
    script = str(BASE_DIR / "src" / "run_pipeline.py")
    logger.info("Disparando pipeline...")
    result = subprocess.run([sys.executable, script], capture_output=True, text=True)
    if result.returncode == 0:
        logger.info("Pipeline concluído com sucesso.")
    else:
        logger.error("Pipeline com erro:\n%s", result.stderr[-2000:])


def watch():
    with open(BASE_DIR / "config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    excel_path = os.environ.get("EXCEL_LOCAL_PATH") or cfg["excel"]["local_path"]
    intervalo = cfg.get("watch", {}).get("intervalo_segundos", 60)

    if not Path(excel_path).exists():
        logger.error("Arquivo não encontrado: %s", excel_path)
        sys.exit(1)

    logger.info("Monitorando: %s", excel_path)
    logger.info("Intervalo: %ds", intervalo)

    last_hash = _md5(excel_path)
    logger.info("Hash inicial: %s", last_hash)

    # Executa uma vez ao iniciar
    _run_pipeline()

    while True:
        time.sleep(intervalo)
        try:
            current_hash = _md5(excel_path)
            if current_hash != last_hash:
                logger.info("Alteração detectada! Hash: %s → %s", last_hash[:8], current_hash[:8])
                last_hash = current_hash
                _run_pipeline()
            else:
                logger.debug("Sem alteração.")
        except FileNotFoundError:
            logger.warning("Arquivo não encontrado (pode estar sendo sincronizado). Aguardando...")
        except Exception as e:
            logger.error("Erro no monitoramento: %s", e)


if __name__ == "__main__":
    watch()
