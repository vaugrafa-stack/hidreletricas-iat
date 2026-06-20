"""Testes de validate_data — classificação de gravidade, precisão e coords repetidas."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import transform_data as T
import validate_data as V


def test_validate_classifica_tres_gravidades(raw_df, config):
    df = T.transform(raw_df, config)
    errs, resumo = V.validate(df, config)
    assert resumo["inconsistencias_criticas"] > 0   # sem coord / coord fora do PR
    assert resumo["inconsistencias_medias"] > 0      # sem técnico / sem situação
    assert resumo["inconsistencias_baixas"] > 0      # baixa precisão
    # colunas obrigatórias do relatório
    for c in ["linha_original", "protocolo", "empreendimento", "campo", "problema",
              "gravidade", "recomendacao"]:
        assert c in errs.columns


def test_validate_conta_coordenadas(raw_df, config):
    df = T.transform(raw_df, config)
    _, resumo = V.validate(df, config)
    # linhas 3 (fora do PR) e 4 (sem coord) ficam sem coordenada
    assert resumo["sem_coordenada"] == 2
    assert resumo["coordenada_invalida"] == 1


def test_validate_sinaliza_baixa_precisao(raw_df, config):
    df = T.transform(raw_df, config)
    errs, _ = V.validate(df, config)
    assert errs["problema"].str.contains("baixa precisão", case=False).any()


def test_validate_detecta_coordenada_repetida(raw_df, config):
    # duas linhas extras com a MESMA coordenada da linha 0, mas empreendimentos diferentes
    extra = raw_df.iloc[[0, 0]].copy()
    extra["NOME"] = ["USINA F", "USINA G"]
    extra["PROTOCOLO"] = ["aaa", "bbb"]
    raw2 = pd.concat([raw_df, extra], ignore_index=True)

    df = T.transform(raw2, config)
    errs, resumo = V.validate(df, config)
    assert resumo["coord_compartilhada"] >= 3
    assert resumo["coord_compartilhada_grupos"] >= 1
    assert errs["problema"].str.contains("Mesma coordenada", case=False).any()


def test_validate_vencida_so_conta_se_nao_encerrado(raw_df, config):
    # uma licença vencida ARQUIVADA não deve ser crítica; DEFERIDA deve ser
    raw = raw_df.copy()
    raw.loc[0, "SITUAÇÃO"] = "DEFERIDO"
    raw.loc[1, "SITUAÇÃO"] = "ARQUIVADO"
    raw.loc[0, "DATA VALIDADE"] = pd.Timestamp("2000-01-01")
    raw.loc[1, "DATA VALIDADE"] = pd.Timestamp("2000-01-01")
    df = T.transform(raw, config)
    errs, _ = V.validate(df, config)
    venc = errs[errs["problema"].str.contains("vencida", case=False)]
    linhas = set(venc["linha_original"])
    assert 2 in linhas        # linha original da 1ª linha (index 0 + 2) — DEFERIDO vencido
    assert 3 not in linhas    # ARQUIVADO vencido não é crítico
