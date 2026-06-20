"""
Passo 1 — Exportação geoespacial dos pontos da planilha.

Saídas:
  data/processed/pontos_originais.geojson
  data/processed/pontos_revisao_google_earth.kml
  data/processed/pontos_revisao_google_earth.kmz

Uso:
  cd C:/Users/rafae/Downloads/IAT/Dashboard
  python src/geo_review/01_exportar_kml.py
"""
import json
import logging
import os
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, indent, tostring

import pandas as pd
import yaml

# Permite importar do diretório pai
sys.path.insert(0, str(Path(__file__).parent.parent))
from extract_excel import extract, load_config
from geo_review.geo_utils import coords_validas, link_google_earth, safe_float

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_DIR = Path("data/processed")

# Ícones do Google Earth Pro por tipo de ponto
ESTILO_KML = {
    "barragem":      {"cor": "ffff0000", "icone": "http://maps.google.com/mapfiles/kml/paddle/B.png"},
    "casa_forca":    {"cor": "ff00ff00", "icone": "http://maps.google.com/mapfiles/kml/paddle/C.png"},
    "kmz_original":  {"cor": "ffff8800", "icone": "http://maps.google.com/mapfiles/kml/paddle/wht-blank.png"},
    "sem_coords":    {"cor": "ff888888", "icone": "http://maps.google.com/mapfiles/kml/paddle/grn-blank.png"},
}


# ---------------------------------------------------------------------------
# Helpers KML
# ---------------------------------------------------------------------------

def _add_estilo(doc: Element, estilo_id: str, cfg: dict) -> None:
    style = SubElement(doc, "Style", id=estilo_id)
    icon_style = SubElement(style, "IconStyle")
    color_el = SubElement(icon_style, "color")
    color_el.text = cfg["cor"]
    scale_el = SubElement(icon_style, "scale")
    scale_el.text = "1.2"
    icon = SubElement(icon_style, "Icon")
    href = SubElement(icon, "href")
    href.text = cfg["icone"]
    label = SubElement(style, "LabelStyle")
    label_scale = SubElement(label, "scale")
    label_scale.text = "0.8"


def _add_placemark(folder: Element, name: str, desc: str, lat: float, lon: float, estilo_id: str) -> None:
    pm = SubElement(folder, "Placemark")
    nm = SubElement(pm, "name")
    nm.text = name
    description = SubElement(pm, "description")
    description.text = f"<![CDATA[{desc}]]>"
    style_url = SubElement(pm, "styleUrl")
    style_url.text = f"#{estilo_id}"
    point = SubElement(pm, "Point")
    coords = SubElement(point, "coordinates")
    coords.text = f"{lon:.6f},{lat:.6f},0"


def _descricao_html(row: dict) -> str:
    campos = [
        ("Protocolo", row.get("protocolo", "")),
        ("Empreendimento", row.get("empreendimento", "")),
        ("Tipologia", row.get("tipologia", "")),
        ("Município", row.get("municipio", "")),
        ("Rio", row.get("rio", "")),
        ("Situação", row.get("situacao", "")),
        ("Técnico", row.get("tecnico_responsavel", "")),
        ("Status Coord Barragem", row.get("status_coord_barragem", "")),
        ("Status Coord Casa Força", row.get("status_coord_casa_forca", "")),
        ("Fonte Coord", row.get("fonte_coord", "")),
        ("Obs Auditoria", row.get("obs_auditoria", "")),
    ]
    linhas = "".join(f"<b>{k}:</b> {v}<br/>" for k, v in campos if v)
    return linhas


# ---------------------------------------------------------------------------
# GeoJSON
# ---------------------------------------------------------------------------

def _feature(row: dict, lat: float, lon: float, tipo_ponto: str) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {
            "protocolo": row.get("protocolo"),
            "empreendimento": row.get("empreendimento"),
            "tipologia": row.get("tipologia"),
            "municipio": row.get("municipio"),
            "rio": row.get("rio"),
            "situacao": row.get("situacao"),
            "tecnico_responsavel": row.get("tecnico_responsavel"),
            "tipo_ponto": tipo_ponto,
            "latitude_original": row.get("latitude"),
            "longitude_original": row.get("longitude"),
            "lat_kmz": row.get("lat_kmz"),
            "lon_kmz": row.get("lon_kmz"),
            "lat_casa_forca": row.get("lat_casa_forca"),
            "lon_casa_forca": row.get("lon_casa_forca"),
            "status_coord_barragem": row.get("status_coord_barragem"),
            "status_coord_casa_forca": row.get("status_coord_casa_forca"),
            "fonte_coord": row.get("fonte_coord"),
            "obs_auditoria": row.get("obs_auditoria"),
            "status_georreferenciamento": "Pendente de validação",
            "grau_confianca": "Pendente",
        },
    }


# ---------------------------------------------------------------------------
# Principal
# ---------------------------------------------------------------------------

def main():
    config = load_config("config.yaml")
    df_raw, md5, fname = extract(config)

    col_map = config.get("column_mapping", {})
    rename = {k: v for k, v in col_map.items() if k in df_raw.columns}
    df = df_raw.rename(columns=rename)

    logger.info("Registros lidos: %d", len(df))

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    features_geojson = []

    # ------------------------------------------------------------------
    # KML
    # ------------------------------------------------------------------
    kml = Element("kml", xmlns="http://www.opengis.net/kml/2.2")
    doc = SubElement(kml, "Document")
    doc_name = SubElement(doc, "name")
    doc_name.text = f"Revisão Geoespacial — Hidrelétricas IAT ({datetime.now():%Y-%m-%d})"
    doc_desc = SubElement(doc, "description")
    doc_desc.text = (
        "Pontos exportados para revisão técnica.\n"
        "INSTRUÇÕES:\n"
        "1. Confira cada ponto visualmente no Google Earth Pro ou QGIS.\n"
        "2. Reposicione os marcadores quando necessário.\n"
        "3. Não apague placmarks — apenas reposicione ou mova para a pasta correta.\n"
        "4. Exporte o KML corrigido e execute 02_importar_corrigido.py."
    )

    for estilo_id, cfg in ESTILO_KML.items():
        _add_estilo(doc, estilo_id, cfg)

    # Legenda de pastas
    pasta_barragem = SubElement(doc, "Folder")
    SubElement(pasta_barragem, "name").text = "Barragem (coordenada original)"
    pasta_barragem_kmz = SubElement(doc, "Folder")
    SubElement(pasta_barragem_kmz, "name").text = "Barragem KMZ (referência secundária)"
    pasta_casa = SubElement(doc, "Folder")
    SubElement(pasta_casa, "name").text = "Casa de Força (quando disponível)"
    pasta_sem = SubElement(doc, "Folder")
    SubElement(pasta_sem, "name").text = "Sem coordenadas válidas"

    sem_coords = 0
    com_barragem = 0
    com_casa = 0

    for _, row in df.iterrows():
        r = row.to_dict()
        protocolo = str(r.get("protocolo", "")).strip() or "S/N"
        empreend = str(r.get("empreendimento", "")).strip() or "Sem nome"
        label_base = f"{protocolo} — {empreend}"
        desc = _descricao_html(r)

        lat_barr = safe_float(r.get("latitude"))
        lon_barr = safe_float(r.get("longitude"))
        lat_kmz = safe_float(r.get("lat_kmz"))
        lon_kmz = safe_float(r.get("lon_kmz"))
        lat_cf = safe_float(r.get("lat_casa_forca"))
        lon_cf = safe_float(r.get("lon_casa_forca"))

        adicionou_algum = False

        # Ponto barragem coordenada direta
        if coords_validas(lat_barr, lon_barr):
            _add_placemark(pasta_barragem, f"[BARR] {label_base}", desc, lat_barr, lon_barr, "barragem")
            features_geojson.append(_feature(r, lat_barr, lon_barr, "barragem_original"))
            com_barragem += 1
            adicionou_algum = True

        # Ponto barragem KMZ (referência alternativa)
        if coords_validas(lat_kmz, lon_kmz):
            _add_placemark(pasta_barragem_kmz, f"[KMZ] {label_base}", desc, lat_kmz, lon_kmz, "kmz_original")
            features_geojson.append(_feature(r, lat_kmz, lon_kmz, "barragem_kmz"))
            adicionou_algum = True

        # Casa de força
        if coords_validas(lat_cf, lon_cf):
            _add_placemark(pasta_casa, f"[CF] {label_base}", desc, lat_cf, lon_cf, "casa_forca")
            features_geojson.append(_feature(r, lat_cf, lon_cf, "casa_forca_original"))
            com_casa += 1
            adicionou_algum = True

        if not adicionou_algum:
            # Placeholder sem coordenadas — usa centroide do Paraná
            _add_placemark(pasta_sem, f"[SEM COORD] {label_base}", desc + "<b>ATENÇÃO: Sem coordenadas válidas</b>", -24.5, -51.5, "sem_coords")
            sem_coords += 1

    # Serializa KML
    indent(kml, space="  ")
    kml_bytes = b'<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(kml, encoding="unicode").encode("utf-8")

    kml_path = PROCESSED_DIR / "pontos_revisao_google_earth.kml"
    kml_path.write_bytes(kml_bytes)
    logger.info("KML gerado: %s", kml_path)

    # KMZ (KML zipado)
    kmz_path = PROCESSED_DIR / "pontos_revisao_google_earth.kmz"
    with zipfile.ZipFile(kmz_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("doc.kml", kml_bytes)
    logger.info("KMZ gerado: %s", kmz_path)

    # GeoJSON
    geojson = {"type": "FeatureCollection", "features": features_geojson}
    geojson_path = PROCESSED_DIR / "pontos_originais.geojson"
    geojson_path.write_text(json.dumps(geojson, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("GeoJSON gerado: %s (%d features)", geojson_path, len(features_geojson))

    # Resumo
    logger.info("=" * 60)
    logger.info("Total de registros    : %d", len(df))
    logger.info("Com ponto barragem    : %d", com_barragem)
    logger.info("Com ponto casa força  : %d", com_casa)
    logger.info("Sem coordenadas       : %d", sem_coords)
    logger.info("=" * 60)
    logger.info("Próximo passo:")
    logger.info("  1. Abra '%s' no Google Earth Pro ou QGIS.", kmz_path.name)
    logger.info("  2. Confira e reposicione os marcadores.")
    logger.info("  3. Exporte o KML corrigido para data/processed/pontos_corrigido_tecnico.kml")
    logger.info("  4. Execute: python src/geo_review/02_importar_corrigido.py")


if __name__ == "__main__":
    main()
