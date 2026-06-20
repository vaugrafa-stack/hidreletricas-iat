"""Pipeline principal: extrai, transforma, valida e salva arquivos de saída."""
import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from extract_excel import load_config, extract
from transform_data import transform
from validate_data import validate

OUT_DIR = BASE_DIR / "data" / "processed"
LOG_DIR = BASE_DIR / "logs"

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "pipeline.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("pipeline")


def _save_geojson(df: pd.DataFrame, path: Path):
    features = []
    geo_cols = {"latitude", "longitude", "tem_coordenada", "linha_original"}
    prop_cols = [c for c in df.columns if c not in {"latitude", "longitude"}]

    for _, row in df[df["tem_coordenada"] == True].iterrows():
        props = {}
        for c in prop_cols:
            v = row[c]
            if pd.isna(v) if not isinstance(v, str) else v is None:
                props[c] = None
            elif hasattr(v, "isoformat"):
                props[c] = v.isoformat()
            else:
                props[c] = v
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(row["longitude"]), float(row["latitude"])]},
            "properties": props,
        })

    geojson = {"type": "FeatureCollection", "features": features}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, default=str)
    logger.info("GeoJSON salvo: %d pontos → %s", len(features), path.name)


def _calc_indicadores(df: pd.DataFrame, resumo: dict) -> dict:
    ind = dict(resumo)

    if "tipologia" in df.columns:
        ind["por_tipologia"] = df["tipologia"].value_counts().to_dict()
    if "situacao" in df.columns:
        ind["por_situacao"] = df["situacao"].value_counts().to_dict()
    if "tipo_licenca" in df.columns:
        ind["por_tipo_licenca"] = df["tipo_licenca"].value_counts().to_dict()
    if "bacia_hidrografica" in df.columns:
        ind["por_bacia"] = df["bacia_hidrografica"].value_counts().to_dict()
    if "tecnico_responsavel" in df.columns:
        ind["por_tecnico"] = df["tecnico_responsavel"].value_counts().to_dict()
    if "municipio" in df.columns:
        ind["por_municipio"] = df["municipio"].value_counts().head(20).to_dict()
    if "potencia" in df.columns:
        ind["potencia_total_mw"] = round(float(df["potencia"].sum()), 2)
        if "tipologia" in df.columns:
            ind["potencia_por_tipologia"] = df.groupby("tipologia")["potencia"].sum().round(2).to_dict()
    if "data_protocolo" in df.columns:
        anos = df["data_protocolo"].dropna().apply(lambda d: d.year if hasattr(d, "year") else None).dropna()
        ind["por_ano_protocolo"] = anos.astype(int).value_counts().sort_index().to_dict()

    return ind


def run(dry_run: bool = False):
    inicio = datetime.now()
    status = "sucesso"
    erros_exec = []

    config = load_config(str(BASE_DIR / "config.yaml"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        df_raw, md5, nome_arquivo = extract(config)
    except Exception as e:
        logger.error("Falha na extração: %s", e)
        raise

    try:
        df = transform(df_raw, config)
    except Exception as e:
        logger.error("Falha na transformação: %s", e)
        raise

    df_errors, resumo = validate(df, config)
    indicadores = _calc_indicadores(df, resumo)

    if dry_run:
        logger.info("[DRY-RUN] Nenhum arquivo será salvo.")
        logger.info("Registros: %d | Erros críticos: %d", len(df), resumo["inconsistencias_criticas"])
        return

    # Salvar CSV principal
    csv_path = OUT_DIR / "processos_hidreletricas.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    logger.info("CSV salvo: %s (%d registros)", csv_path.name, len(df))

    # Salvar GeoJSON
    geojson_path = OUT_DIR / "processos_hidreletricas.geojson"
    _save_geojson(df, geojson_path)

    # Salvar erros de validação
    erros_path = OUT_DIR / "erros_validacao.csv"
    df_errors.to_csv(erros_path, index=False, encoding="utf-8-sig")
    logger.info("Erros de validação: %s (%d registros)", erros_path.name, len(df_errors))

    # Salvar indicadores
    ind_path = OUT_DIR / "resumo_indicadores.json"
    with open(ind_path, "w", encoding="utf-8") as f:
        json.dump(indicadores, f, ensure_ascii=False, indent=2, default=str)

    # Salvar metadados de execução
    meta = {
        "data_hora_execucao": inicio.isoformat(),
        "arquivo_lido": nome_arquivo,
        "md5_arquivo": md5,
        "aba_utilizada": config["excel"]["sheet_name"],
        "total_registros": len(df),
        "registros_validos": resumo["registros_validos"],
        "sem_coordenada": resumo["sem_coordenada"],
        "coordenada_invalida": resumo.get("coordenada_invalida", 0),
        "inconsistencias_criticas": resumo["inconsistencias_criticas"],
        "inconsistencias_medias": resumo["inconsistencias_medias"],
        "inconsistencias_baixas": resumo["inconsistencias_baixas"],
        "registros_com_critico": resumo.get("registros_com_critico", 0),
        "licencas_vencidas": resumo["licencas_vencidas"],
        "a_vencer_90_dias": resumo["a_vencer_90_dias"],
        "status": status,
        "erros": erros_exec,
        "duracao_segundos": round((datetime.now() - inicio).total_seconds(), 2),
    }
    meta_path = OUT_DIR / "metadados_execucao.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    logger.info("Pipeline concluído em %.1fs", meta["duracao_segundos"])
    logger.info("Licenças vencidas: %d | A vencer (90d): %d", resumo["licencas_vencidas"], resumo["a_vencer_90_dias"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline de dados — Hidrelétricas IAT")
    parser.add_argument("--dry-run", action="store_true", help="Executa sem salvar arquivos")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
