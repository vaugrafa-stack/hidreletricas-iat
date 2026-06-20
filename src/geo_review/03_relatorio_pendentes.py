"""
Passo 3 (opcional) — Gera relatório atualizado de pendentes a partir do CSV corrigido.

Útil para rodar após revisões parciais sem precisar reimportar o KML inteiro.

Uso:
  cd C:/Users/rafae/Downloads/IAT/Dashboard
  python src/geo_review/03_relatorio_pendentes.py
"""
import logging
import sys
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_DIR = Path("data/processed")
CSV_CORRIGIDO = PROCESSED_DIR / "pontos_corrigidos.csv"
REL_PATH = PROCESSED_DIR / "relatorio_validacao_geoespacial.csv"


def main():
    if not CSV_CORRIGIDO.exists():
        logger.error("Arquivo não encontrado: %s", CSV_CORRIGIDO)
        logger.error("Execute primeiro 02_importar_corrigido.py.")
        sys.exit(1)

    df = pd.read_csv(CSV_CORRIGIDO, encoding="utf-8-sig", low_memory=False)
    logger.info("Registros carregados: %d", len(df))

    # Estatísticas por status
    if "status_georreferenciamento" in df.columns:
        logger.info("\nDistribuição por status:")
        for status, qtd in df["status_georreferenciamento"].value_counts().items():
            logger.info("  %-35s: %d", status, qtd)

    if "grau_confianca" in df.columns:
        logger.info("\nDistribuição por grau de confiança:")
        for grau, qtd in df["grau_confianca"].value_counts().items():
            logger.info("  %-20s: %d", grau, qtd)

    # Registros sem casa de força
    sem_cf = df[
        df.get("latitude_casa_forca", pd.Series(dtype=float)).isna() |
        (df.get("latitude_casa_forca", pd.Series(dtype=float)) == "")
    ].copy() if "latitude_casa_forca" in df.columns else pd.DataFrame()

    logger.info("\nRegistros sem casa de força registrada: %d", len(sem_cf))

    # Pendentes críticos
    pendentes = df[
        df.get("status_georreferenciamento", pd.Series(dtype=str)).isin(
            ["Pendente de validação", "Não identificado", "Coordenada inconsistente"]
        )
    ] if "status_georreferenciamento" in df.columns else pd.DataFrame()

    pend_path = PROCESSED_DIR / "pendentes_geo.csv"
    if not pendentes.empty:
        cols = [c for c in [
            "protocolo", "empreendimento", "tipologia", "municipio", "rio",
            "latitude_barragem_original", "longitude_barragem_original",
            "status_georreferenciamento", "grau_confianca", "observacao_geoespacial",
        ] if c in pendentes.columns]
        pendentes[cols].to_csv(pend_path, index=False, encoding="utf-8-sig")
        logger.info("Lista de pendentes exportada: %s (%d registros)", pend_path, len(pendentes))

    # Atualiza o relatório completo
    cols_relatorio = [
        "protocolo", "empreendimento", "tipologia", "municipio", "rio",
        "latitude_barragem_original", "longitude_barragem_original",
        "latitude_barragem_corrigida", "longitude_barragem_corrigida",
        "latitude_casa_forca", "longitude_casa_forca",
        "status_georreferenciamento", "grau_confianca", "observacao_geoespacial",
    ]
    cols_ok = [c for c in cols_relatorio if c in df.columns]
    df_rel = df[cols_ok].copy()
    df_rel["problema_identificado"] = df_rel.get("status_georreferenciamento", pd.Series()).apply(
        lambda s: "Sem coordenada barragem" if s == "Não identificado"
        else "Coordenada não revisada" if s == "Pendente de validação"
        else ""
    )
    df_rel["recomendacao"] = df_rel.get("status_georreferenciamento", pd.Series()).apply(
        lambda s: "Inserir coordenadas após consulta documental" if s == "Não identificado"
        else "Revisão obrigatória no Google Earth Pro" if s == "Pendente de validação"
        else "Nenhuma ação necessária"
    )
    df_rel.to_csv(REL_PATH, index=False, encoding="utf-8-sig")
    logger.info("Relatório atualizado: %s", REL_PATH)


if __name__ == "__main__":
    main()
