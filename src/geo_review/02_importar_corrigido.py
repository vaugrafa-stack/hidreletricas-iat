"""
Passo 2 — Importação do KML corrigido pelo técnico e geração das saídas derivadas.

Entrada esperada:
  data/processed/pontos_corrigido_tecnico.kml   (exportado do Google Earth Pro / QGIS)

Saídas:
  data/processed/pontos_corrigidos.csv
  data/processed/pontos_corrigidos.geojson
  data/processed/relatorio_validacao_geoespacial.csv
  data/processed/planilha_atualizacao_coordenadas.xlsx

Uso:
  cd C:/Users/rafae/Downloads/IAT/Dashboard
  python src/geo_review/02_importar_corrigido.py [--kml caminho/para/arquivo.kml]
"""
import argparse
import json
import logging
import re
import sys
from datetime import date
from pathlib import Path
from xml.etree import ElementTree as ET

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))
from extract_excel import extract, load_config
from geo_review.geo_utils import (
    GRAU_VALIDOS,
    STATUS_VALIDOS,
    coords_validas,
    distancia_metros,
    link_google_earth,
    safe_float,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_DIR = Path("data/processed")
KML_CORRIGIDO_PADRAO = PROCESSED_DIR / "pontos_corrigido_tecnico.kml"

# Namespace KML
NS = {"kml": "http://www.opengis.net/kml/2.2"}

# Distância mínima (m) entre barragem e casa de força para aceitar como pontos distintos
DIST_MIN_CF_BARR = 20


# ---------------------------------------------------------------------------
# Parsing KML
# ---------------------------------------------------------------------------

def _texto(el, tag: str) -> str:
    child = el.find(tag)
    return (child.text or "").strip() if child is not None else ""


def _coords_kml(placemark: ET.Element) -> tuple[float | None, float | None]:
    """Extrai lon, lat do elemento Point/coordinates de um Placemark."""
    coords_text = None
    for el in placemark.iter():
        if el.tag.endswith("coordinates"):
            coords_text = (el.text or "").strip()
            break
    if not coords_text:
        return None, None
    parts = coords_text.split(",")
    if len(parts) < 2:
        return None, None
    try:
        lon = float(parts[0])
        lat = float(parts[1])
        return lat, lon
    except ValueError:
        return None, None


def _prefixo_nome(name: str) -> str:
    """Extrai prefixo entre colchetes: '[BARR]', '[CF]', '[KMZ]', '[SEM COORD]'."""
    m = re.match(r"\[([^\]]+)\]", name.strip())
    return m.group(1).upper() if m else ""


def _protocolo_do_nome(name: str) -> str:
    """Extrai protocolo do padrão '[PREF] PROTOCOLO — NOME'.
    Suporta em-dash (—), en-dash (–) e hífen como separador."""
    sem_prefixo = re.sub(r"^\[[^\]]+\]\s*", "", name.strip())
    partes = re.split(r"\s*[—–\-]\s*", sem_prefixo, maxsplit=1)
    return partes[0].strip() if partes else sem_prefixo.strip()


def parse_kml(kml_path: Path) -> dict[str, dict]:
    """
    Lê o KML corrigido e retorna dicionário keyed por protocolo.
    Cada entrada pode ter: barragem, casa_forca, kmz.
    """
    tree = ET.parse(kml_path)
    root = tree.getroot()

    result: dict[str, dict] = {}

    for pm in root.iter():
        if not pm.tag.endswith("Placemark"):
            continue
        name_el = pm.find(".//{http://www.opengis.net/kml/2.2}name")
        if name_el is None:
            name_el = pm.find(".//name")
        name = (name_el.text or "").strip() if name_el is not None else ""

        lat, lon = _coords_kml(pm)
        if lat is None:
            continue

        prefixo = _prefixo_nome(name)
        protocolo = _protocolo_do_nome(name)

        if not protocolo:
            continue

        if protocolo not in result:
            result[protocolo] = {}

        if prefixo in ("BARR", ""):
            result[protocolo]["barragem"] = (lat, lon)
        elif prefixo == "CF":
            result[protocolo]["casa_forca"] = (lat, lon)
        elif prefixo == "KMZ":
            result[protocolo]["kmz"] = (lat, lon)
        # [SEM COORD] ignorado se ainda no centroide do PR

    return result


# ---------------------------------------------------------------------------
# Construção da base derivada
# ---------------------------------------------------------------------------

CAMPOS_NOVOS = [
    "latitude_barragem_original",
    "longitude_barragem_original",
    "latitude_barragem_corrigida",
    "longitude_barragem_corrigida",
    "latitude_casa_forca",
    "longitude_casa_forca",
    "latitude_restituicao",
    "longitude_restituicao",
    "latitude_tomada_dagua",
    "longitude_tomada_dagua",
    "status_georreferenciamento",
    "metodo_validacao",
    "data_validacao",
    "responsavel_validacao",
    "grau_confianca",
    "observacao_geoespacial",
    "link_google_earth",
]


def _classificar(
    lat_orig: float | None,
    lon_orig: float | None,
    lat_corr: float | None,
    lon_corr: float | None,
    lat_cf: float | None,
    lon_cf: float | None,
) -> tuple[str, str, str]:
    """Retorna (status, grau_confianca, observacao)."""
    tem_orig = coords_validas(lat_orig, lon_orig)
    tem_corr = coords_validas(lat_corr, lon_corr)
    tem_cf = coords_validas(lat_cf, lon_cf)

    if not tem_orig and not tem_corr:
        return "Não identificado", "Pendente", "Sem coordenadas disponíveis."

    if tem_corr:
        if tem_orig:
            dist = distancia_metros(lat_orig, lon_orig, lat_corr, lon_corr)
            if dist < 1:
                obs = "Coordenada validada sem alteração."
                return "Validado", "Alto", obs
            else:
                obs = f"Coordenada corrigida; deslocamento de {dist:.0f} m em relação ao original."
                grau = "Alto" if dist < 500 else "Médio"
                return "Corrigido", grau, obs
        return "Corrigido", "Médio", "Coordenada inserida pelo técnico (sem referência original)."

    if tem_orig:
        if not tem_cf:
            return "Pendente de validação", "Pendente", "Apenas coordenada original — revisar no Google Earth."
        return "Pendente de validação", "Pendente", "Coordenada original não revisada; casa de força disponível."

    return "Pendente de validação", "Pendente", "Nenhuma coordenada validada."


def main(kml_path: Path):
    if not kml_path.exists():
        logger.error("Arquivo KML corrigido não encontrado: %s", kml_path)
        logger.error("Execute primeiro o passo 1 (01_exportar_kml.py) e faça a revisão no Google Earth Pro.")
        sys.exit(1)

    config = load_config("config.yaml")
    df_raw, _, _ = extract(config)

    col_map = config.get("column_mapping", {})
    rename = {k: v for k, v in col_map.items() if k in df_raw.columns}
    df = df_raw.rename(columns=rename)

    logger.info("Lendo KML corrigido: %s", kml_path)
    pontos_corrigidos = parse_kml(kml_path)
    logger.info("Placemarks parseados: %d protocolos", len(pontos_corrigidos))

    # Inicializa colunas novas
    for campo in CAMPOS_NOVOS:
        df[campo] = None

    hoje = date.today().isoformat()

    for idx, row in df.iterrows():
        protocolo = str(row.get("protocolo", "")).strip()

        lat_orig = safe_float(row.get("latitude"))
        lon_orig = safe_float(row.get("longitude"))

        df.at[idx, "latitude_barragem_original"] = lat_orig
        df.at[idx, "longitude_barragem_original"] = lon_orig

        ponto = pontos_corrigidos.get(protocolo, {})

        lat_corr, lon_corr = ponto.get("barragem", (None, None))
        lat_cf, lon_cf = ponto.get("casa_forca", (None, None))

        df.at[idx, "latitude_barragem_corrigida"] = lat_corr
        df.at[idx, "longitude_barragem_corrigida"] = lon_corr
        df.at[idx, "latitude_casa_forca"] = lat_cf
        df.at[idx, "longitude_casa_forca"] = lon_cf

        # Campos de restituição e tomada d'água permanecem None — preenchimento manual futuro
        df.at[idx, "latitude_restituicao"] = None
        df.at[idx, "longitude_restituicao"] = None
        df.at[idx, "latitude_tomada_dagua"] = None
        df.at[idx, "longitude_tomada_dagua"] = None

        status, grau, obs = _classificar(lat_orig, lon_orig, lat_corr, lon_corr, lat_cf, lon_cf)
        df.at[idx, "status_georreferenciamento"] = status
        df.at[idx, "grau_confianca"] = grau
        df.at[idx, "observacao_geoespacial"] = obs
        df.at[idx, "metodo_validacao"] = "Revisão visual Google Earth Pro / QGIS"
        df.at[idx, "data_validacao"] = hoje
        df.at[idx, "responsavel_validacao"] = ""  # preencher manualmente

        ref_lat = lat_corr or lat_orig
        ref_lon = lon_corr or lon_orig
        if coords_validas(ref_lat, ref_lon):
            df.at[idx, "link_google_earth"] = link_google_earth(ref_lat, ref_lon)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # CSV corrigido
    # ------------------------------------------------------------------
    csv_path = PROCESSED_DIR / "pontos_corrigidos.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    logger.info("CSV gerado: %s", csv_path)

    # ------------------------------------------------------------------
    # GeoJSON corrigido
    # ------------------------------------------------------------------
    features = []
    for _, row in df.iterrows():
        lat = safe_float(row.get("latitude_barragem_corrigida")) or safe_float(row.get("latitude_barragem_original"))
        lon = safe_float(row.get("longitude_barragem_corrigida")) or safe_float(row.get("longitude_barragem_original"))
        if not coords_validas(lat, lon):
            continue
        props = {c: (None if pd.isna(v) else v) for c, v in row.items()}
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": props,
        })
    geojson = {"type": "FeatureCollection", "features": features}
    gj_path = PROCESSED_DIR / "pontos_corrigidos.geojson"
    gj_path.write_text(json.dumps(geojson, ensure_ascii=False, default=str), encoding="utf-8")
    logger.info("GeoJSON gerado: %s (%d features)", gj_path, len(features))

    # ------------------------------------------------------------------
    # Relatório de validação
    # ------------------------------------------------------------------
    cols_relatorio = [
        "protocolo", "empreendimento", "tipologia", "municipio", "rio",
        "latitude_barragem_original", "longitude_barragem_original",
        "latitude_barragem_corrigida", "longitude_barragem_corrigida",
        "latitude_casa_forca", "longitude_casa_forca",
        "status_georreferenciamento", "grau_confianca",
        "observacao_geoespacial",
    ]
    cols_existentes = [c for c in cols_relatorio if c in df.columns]
    df_rel = df[cols_existentes].copy()
    df_rel["problema_identificado"] = df_rel["status_georreferenciamento"].apply(
        lambda s: "Sem coordenada barragem" if s == "Não identificado"
        else "Coordenada não revisada" if s == "Pendente de validação"
        else ""
    )
    df_rel["recomendacao"] = df_rel["status_georreferenciamento"].apply(
        lambda s: "Inserir coordenadas manualmente após consulta documental" if s == "Não identificado"
        else "Revisão obrigatória no Google Earth Pro antes de usar em análise" if s == "Pendente de validação"
        else "Nenhuma ação necessária"
    )

    rel_path = PROCESSED_DIR / "relatorio_validacao_geoespacial.csv"
    df_rel.to_csv(rel_path, index=False, encoding="utf-8-sig")
    logger.info("Relatório gerado: %s", rel_path)

    # ------------------------------------------------------------------
    # Planilha XLSX de atualização
    # ------------------------------------------------------------------
    xlsx_path = PROCESSED_DIR / "planilha_atualizacao_coordenadas.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        # Aba 1 — todos os registros
        df.to_excel(writer, sheet_name="Coordenadas Completas", index=False)

        # Aba 2 — apenas pendentes
        df_pend = df[df["status_georreferenciamento"].isin(["Pendente de validação", "Não identificado"])].copy()
        df_pend.to_excel(writer, sheet_name="Pendentes", index=False)

        # Aba 3 — relatório resumido
        df_rel.to_excel(writer, sheet_name="Relatório Validação", index=False)

        # Aba 4 — estatísticas
        stats = df["status_georreferenciamento"].value_counts().reset_index()
        stats.columns = ["status", "quantidade"]
        stats.to_excel(writer, sheet_name="Estatísticas", index=False)

    logger.info("Planilha XLSX gerada: %s", xlsx_path)

    # Resumo final
    contagem = df["status_georreferenciamento"].value_counts()
    logger.info("=" * 60)
    logger.info("RESUMO DA VALIDAÇÃO GEOESPACIAL")
    logger.info("=" * 60)
    for status, qtd in contagem.items():
        logger.info("  %-35s: %d", status, qtd)
    logger.info("=" * 60)
    pendentes = contagem.get("Pendente de validação", 0) + contagem.get("Não identificado", 0)
    logger.info("Total pendentes de ação técnica: %d", pendentes)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Importar KML corrigido e gerar base derivada.")
    parser.add_argument("--kml", type=Path, default=KML_CORRIGIDO_PADRAO, help="Caminho do KML corrigido")
    args = parser.parse_args()
    main(args.kml)
