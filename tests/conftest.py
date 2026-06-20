"""Fixtures compartilhadas dos testes."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "src"))

_CONFIG = yaml.safe_load(open(BASE / "config.yaml", encoding="utf-8"))


@pytest.fixture
def config():
    return _CONFIG


@pytest.fixture
def raw_df():
    """DataFrame bruto mínimo, com os nomes ORIGINAIS de coluna da planilha."""
    cols = ["PROTOCOLO", "BACIA", "DATA PROTOCOLO", "TIPO", "NOME", "RIO", "SITUAÇÃO",
            "TÉCNICO", "TIPOS DE LICENÇA", "POT SOLIC (MW)", "REQUERENTE", "CPF/CNPJ",
            "MUNICÍPIOS AFETADOS", "Nº DOC (licença)", "DATA DECISÃO", "DATA VALIDADE",
            "OBS", "LATITUDE BARRAGEM", "LONGITUDE BARRAGEM"]
    rows = [
        # 0: alta precisão, completo
        ["123", "IGUAÇU", None, "CGH", "USINA A", "RIO X", "DEFERIDO", "LUIZ", "LP",
         1.0, "EMP A", "123", "MUN A", "5", None, None, "SGA", -24.281655, -49.695021],
        # 1: técnico/situação NaN (deve virar None, NUNCA a string "NAN")
        ["456", "IVAÍ", None, "PCH", "USINA B", "RIO Y", np.nan, np.nan, "LO",
         2.0, "EMP B", "456", "MUN B", np.nan, None, None, None, -25.1, -50.2],
        # 2: baixa precisão (1–2 casas decimais)
        ["789", "PIQUIRI", None, "UHE", "USINA C", "RIO Z", "DEFERIDO", "ANDREI", "RLO",
         3.0, "EMP C", "789", "MUN C", "7", None, None, None, -24.90, -53.99],
        # 3: coordenada fora dos limites do PR
        ["999", "TIBAGI", None, "CGH", "USINA D", "RIO W", "PROTOCOLADO", "FELIPE", "CP",
         1.0, "EMP D", "999", "MUN D", None, None, None, None, -10.0, -60.0],
        # 4: sem coordenada
        ["111", "CINZAS", None, "MGH", "USINA E", "RIO V", "EM ANALISE", "LENISE", "LI",
         0.5, "EMP E", "111", "MUN E", None, None, None, None, None, None],
    ]
    return pd.DataFrame(rows, columns=cols)
