"""Testes de transform_data — foca nos bugs corrigidos (NaN, matching, precisão, links)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import transform_data as T


# ── Helpers puros ─────────────────────────────────────────────────────────────
def test_isna_reconhece_nulos_e_tokens():
    assert T._isna(None)
    assert T._isna(np.nan)
    assert T._isna("nan")
    assert T._isna("   ")
    assert not T._isna("ABC")
    assert not T._isna(0)


def test_norm_upper_nan_vira_none_nao_string_nan():
    # Bug corrigido: NaN não pode virar a string "NAN".
    assert T._norm_upper(np.nan) is None
    assert T._norm_upper(None) is None
    assert T._norm_upper("  felipe ") == "FELIPE"


def test_colkey_tolerante_a_acentos_e_simbolos():
    # 'º' (ordinal) vs '°' (grau) devem casar; acentos são ignorados.
    assert T._colkey("Nº DOC (licença)") == T._colkey("N° DOC (licença)")
    assert T._colkey("SITUAÇÃO") == T._colkey("situacao")
    assert T._colkey("LATITUDE BARRAGEM") == "LATITUDE BARRAGEM"


def test_to_float_aceita_virgula_decimal():
    assert T._to_float("-24,28") == -24.28
    assert T._to_float(-49.69) == -49.69
    assert T._to_float(None) is None
    assert T._to_float("xyz") is None


def test_decimais_conta_casas():
    assert T._decimais(-53.99) == 2
    assert T._decimais(-24.281655) == 6
    assert T._decimais(-24.5) == 1


# ── Integração transform() ────────────────────────────────────────────────────
def test_transform_nao_gera_string_nan(raw_df, config):
    df = T.transform(raw_df, config)
    # valores ausentes ficam NULOS (não a string literal "NAN")
    assert pd.isna(df.loc[1, "tecnico_responsavel"])
    assert pd.isna(df.loc[1, "situacao"])
    for col in ("tecnico_responsavel", "situacao", "tipologia"):
        valores_nao_nulos = set(df[col].dropna().astype(str).str.upper())
        assert "NAN" not in valores_nao_nulos


def test_transform_mapeia_colunas_problematicas(raw_df, config):
    df = T.transform(raw_df, config)
    # 'Nº DOC (licença)' e coords precisam ter sido mapeados
    assert "numero_licenca" in df.columns
    assert "latitude" in df.columns and "longitude" in df.columns


def test_transform_coordenadas_e_precisao(raw_df, config):
    df = T.transform(raw_df, config)
    assert bool(df.loc[0, "tem_coordenada"]) is True
    assert df.loc[0, "precisao_coord"] == "alta"
    assert df.loc[2, "precisao_coord"] == "baixa"
    # fora do PR: descartada e marcada como inválida
    assert bool(df.loc[3, "tem_coordenada"]) is False
    assert bool(df.loc[3, "coord_fora_pr"]) is True
    # sem coordenada: precisão indefinida
    assert bool(df.loc[4, "tem_coordenada"]) is False
    assert pd.isna(df.loc[4, "precisao_coord"])


def test_transform_gera_os_tres_links(raw_df, config):
    df = T.transform(raw_df, config)
    assert df.loc[0, "link_qgis"].startswith("qgis://")
    assert df.loc[0, "link_gearth"].startswith("gearth://")
    assert df.loc[0, "link_google_earth"].startswith("https://earth.google.com")
    # sem coordenada -> sem links de mapa
    assert pd.isna(df.loc[4, "link_qgis"])
    assert pd.isna(df.loc[4, "link_gearth"])
