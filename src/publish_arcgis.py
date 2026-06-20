"""Publicação ou atualização de Feature Layer no ArcGIS Online/Enterprise."""
import argparse
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
LOG_DIR = BASE_DIR / "logs"
OUT_DIR = BASE_DIR / "data" / "processed"

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s — %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "arcgis.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("arcgis_publish")


def _get_gis():
    try:
        from arcgis.gis import GIS
    except ImportError:
        logger.error("Pacote 'arcgis' não instalado. Execute: pip install arcgis")
        sys.exit(1)

    portal = os.environ.get("ARCGIS_PORTAL_URL", "https://www.arcgis.com")
    token = os.environ.get("ARCGIS_TOKEN")
    username = os.environ.get("ARCGIS_USERNAME")
    password = os.environ.get("ARCGIS_PASSWORD")

    if token:
        gis = GIS(portal, token=token)
    elif username and password:
        gis = GIS(portal, username=username, password=password)
    else:
        logger.error("Configure ARCGIS_TOKEN ou ARCGIS_USERNAME + ARCGIS_PASSWORD no .env")
        sys.exit(1)

    logger.info("Conectado como: %s", gis.properties.user.username)
    return gis


def publish(dry_run: bool = False):
    import pandas as pd
    from arcgis.features import FeatureLayerCollection, FeatureSet
    from arcgis.geometry import Point

    csv_path = OUT_DIR / "processos_hidreletricas.csv"
    if not csv_path.exists():
        logger.error("Execute o pipeline primeiro: python src/run_pipeline.py")
        sys.exit(1)

    df = pd.read_csv(csv_path, dtype=str, encoding="utf-8-sig")
    logger.info("Registros lidos: %d", len(df))

    layer_id = os.environ.get("ARCGIS_FEATURE_LAYER_ID", "")
    folder = os.environ.get("ARCGIS_FOLDER", "Hidreletricas_IAT")

    if dry_run:
        logger.info("[DRY-RUN] Publicação simulada. %d registros prontos para envio.", len(df))
        return

    gis = _get_gis()

    if layer_id:
        # Atualizar camada existente via overwrite
        item = gis.content.get(layer_id)
        if item is None:
            logger.error("Item não encontrado: %s", layer_id)
            sys.exit(1)
        flc = FeatureLayerCollection.fromitem(item)
        result = flc.manager.overwrite(str(csv_path))
        logger.info("Camada atualizada: %s", result)
    else:
        # Criar nova camada a partir do CSV
        item_props = {
            "title": "Processos Hidrelétricos IAT",
            "tags": "hidreletricas,IAT,licenciamento,Paraná",
            "type": "CSV",
        }
        csv_item = gis.content.add(item_props, data=str(csv_path), folder=folder)
        published = csv_item.publish({"type": "csv", "locationType": "coordinates",
                                       "latitudeFieldName": "latitude", "longitudeFieldName": "longitude"})
        logger.info("Nova camada publicada: %s | ID: %s", published.title, published.id)
        logger.info("Adicione ao .env: ARCGIS_FEATURE_LAYER_ID=%s", published.id)

    logger.info("Publicação concluída.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Publica Feature Layer no ArcGIS")
    parser.add_argument("--dry-run", action="store_true", help="Simula sem publicar")
    args = parser.parse_args()
    publish(dry_run=args.dry_run)
