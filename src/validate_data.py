"""Validação dos dados transformados e geração de relatório de inconsistências."""
import logging
from datetime import date
from collections import Counter

import pandas as pd

logger = logging.getLogger(__name__)

CRITICO = "CRITICO"
MEDIO = "MEDIO"
BAIXO = "BAIXO"

# Situações que indicam processo ativo/deferido (campos como nº de licença passam a ser exigíveis)
_SIT_ATIVAS = {"DEFERIDO", "VIGENTE", "REGULAR"}
# Situações encerradas (vencimento de licença deixa de ser inconsistência relevante)
_SIT_ENCERRADAS = {"ARQUIVADO", "ENCERRADO", "CANCELADO", "INDEFERIDO", "DEVOLVIDO"}


def _is_null(v) -> bool:
    if v is None:
        return True
    try:
        return bool(pd.isna(v))
    except (TypeError, ValueError):
        return False


def _add_error(errors, linha, protocolo, empreendimento, campo, problema, gravidade, recomendacao):
    errors.append({
        "linha_original": linha,
        "protocolo": protocolo,
        "empreendimento": empreendimento,
        "campo": campo,
        "problema": problema,
        "gravidade": gravidade,
        "recomendacao": recomendacao,
    })


def validate(df: pd.DataFrame, config: dict) -> tuple[pd.DataFrame, dict]:
    errors = []
    hoje = date.today()

    protocolo_counter = Counter()
    for v in df["protocolo"].dropna():
        protocolo_counter[v] += 1

    # Só exige data_protocolo se a coluna for majoritariamente preenchida
    exige_data_protocolo = (
        "data_protocolo" in df.columns and df["data_protocolo"].notna().mean() > 0.5
    )

    # Coordenada compartilhada por empreendimentos DIFERENTES (provável imprecisão/placeholder)
    coord_emps = {}
    if "tem_coordenada" in df.columns:
        for _, rr in df[df["tem_coordenada"] == True].iterrows():
            try:
                key = (round(float(rr["latitude"]), 6), round(float(rr["longitude"]), 6))
            except (TypeError, ValueError):
                continue
            nome = str(rr.get("empreendimento") or "").strip().upper()
            coord_emps.setdefault(key, set()).add(nome)
    coord_compartilhada = {k for k, v in coord_emps.items() if len(v) > 1}

    for _, row_raw in df.iterrows():
        # Normaliza NaN/NaT → None (NaN é truthy em Python e quebraria os testes)
        row = {k: (None if _is_null(v) else v) for k, v in row_raw.items()}
        linha = row.get("linha_original", "?")
        proto = row.get("protocolo")
        emp = row.get("empreendimento")
        situacao = str(row.get("situacao") or "").upper()
        encerrado = situacao in _SIT_ENCERRADAS

        # ───────────── CRÍTICOS ─────────────
        if not proto:
            _add_error(errors, linha, proto, emp, "protocolo", "Registro sem protocolo", CRITICO,
                       "Preencher número do protocolo no sistema de origem")

        if not emp:
            _add_error(errors, linha, proto, emp, "empreendimento", "Registro sem nome do empreendimento", CRITICO,
                       "Preencher nome do empreendimento na planilha")

        if not row.get("municipio"):
            _add_error(errors, linha, proto, emp, "municipio", "Registro sem município", CRITICO,
                       "Preencher município(s) afetado(s)")

        if row.get("coord_fora_pr"):
            _add_error(errors, linha, proto, emp, "latitude/longitude",
                       "Coordenada informada está fora dos limites do Paraná", CRITICO,
                       "Conferir sinal/ordem de latitude e longitude (WGS84, graus decimais)")
        elif not row.get("tem_coordenada"):
            _add_error(errors, linha, proto, emp, "latitude/longitude",
                       "Registro sem coordenada geográfica válida", CRITICO,
                       "Verificar e preencher latitude/longitude no Paraná (WGS84)")

        if proto and protocolo_counter[proto] > 1:
            _add_error(errors, linha, proto, emp, "protocolo",
                       f"Protocolo duplicado ({protocolo_counter[proto]} ocorrências)", CRITICO,
                       "Verificar se registros são fases distintas do mesmo processo ou duplicidade real")

        # Validade vencida — relevante apenas para processos não encerrados
        validade = row.get("data_validade")
        if validade and validade < hoje and not encerrado:
            _add_error(errors, linha, proto, emp, "data_validade",
                       f"Licença vencida em {validade}", CRITICO,
                       "Verificar se houve renovação não registrada ou se o processo está encerrado")

        # ───────────── MÉDIOS ─────────────
        if not row.get("tecnico_responsavel"):
            _add_error(errors, linha, proto, emp, "tecnico_responsavel", "Técnico responsável ausente", MEDIO,
                       "Atribuir técnico responsável pelo processo")

        if not row.get("tipologia"):
            _add_error(errors, linha, proto, emp, "tipologia", "Tipologia ausente (CGH/PCH/UHE/etc)", MEDIO,
                       "Classificar tipologia do empreendimento")

        if not row.get("tipo_licenca"):
            _add_error(errors, linha, proto, emp, "tipo_licenca", "Tipo de licença ausente", MEDIO,
                       "Preencher tipo de licença (LP, LI, LO, etc)")

        if not row.get("situacao"):
            _add_error(errors, linha, proto, emp, "situacao", "Situação do processo ausente", MEDIO,
                       "Preencher situação atual do processo")

        if not row.get("bacia_hidrografica"):
            _add_error(errors, linha, proto, emp, "bacia_hidrografica", "Bacia hidrográfica ausente", MEDIO,
                       "Preencher bacia hidrográfica")

        if exige_data_protocolo and not row.get("data_protocolo"):
            _add_error(errors, linha, proto, emp, "data_protocolo", "Data de protocolo ausente", MEDIO,
                       "Preencher a data de protocolo do processo")

        # Nº de licença exigível quando o processo está deferido/vigente
        if situacao in _SIT_ATIVAS and not row.get("numero_licenca"):
            _add_error(errors, linha, proto, emp, "numero_licenca",
                       "Processo deferido sem número de licença", MEDIO,
                       "Preencher o número do documento de licença emitido")

        # ───────────── BAIXOS ─────────────
        if not row.get("rio"):
            _add_error(errors, linha, proto, emp, "rio", "Rio/corpo hídrico ausente", BAIXO,
                       "Preencher o rio ou corpo hídrico associado")

        if not row.get("potencia"):
            _add_error(errors, linha, proto, emp, "potencia", "Potência (MW) ausente", BAIXO,
                       "Preencher a potência solicitada em MW")

        # Precisão e coordenada compartilhada (apoio à conferência de coordenadas)
        if row.get("tem_coordenada"):
            if row.get("precisao_coord") == "baixa":
                nd = row.get("n_decimais_coord")
                _add_error(errors, linha, proto, emp, "latitude/longitude",
                           f"Coordenada de baixa precisão ({nd} casas decimais, ~1 km ou pior)", BAIXO,
                           "Refinar a coordenada com mais casas decimais (≥5 ≈ metros)")
            try:
                key = (round(float(row["latitude"]), 6), round(float(row["longitude"]), 6))
            except (TypeError, ValueError):
                key = None
            if key in coord_compartilhada:
                n_emp = len(coord_emps.get(key, ()))
                _add_error(errors, linha, proto, emp, "latitude/longitude",
                           f"Mesma coordenada usada por {n_emp} empreendimentos distintos", MEDIO,
                           "Conferir se a coordenada é genérica/placeholder e individualizar cada ponto")

    df_errors = pd.DataFrame(errors)
    if df_errors.empty:
        df_errors = pd.DataFrame(columns=["linha_original", "protocolo", "empreendimento",
                                           "campo", "problema", "gravidade", "recomendacao"])

    # ───────────── Resumo ─────────────
    total = len(df)
    sem_coord = int((~df["tem_coordenada"]).sum()) if "tem_coordenada" in df.columns else 0
    coord_invalida = int(df["coord_fora_pr"].sum()) if "coord_fora_pr" in df.columns else 0
    sem_proto = int(df["protocolo"].isna().sum())
    sem_mun = int(df["municipio"].isna().sum()) if "municipio" in df.columns else 0
    sem_tipo = int(df["tipologia"].isna().sum()) if "tipologia" in df.columns else 0
    sem_sit = int(df["situacao"].isna().sum()) if "situacao" in df.columns else 0
    sem_tecnico = int(df["tecnico_responsavel"].isna().sum()) if "tecnico_responsavel" in df.columns else 0
    duplicados = int(sum(1 for k, v in protocolo_counter.items() if v > 1))

    vencidas = a_vencer = vigentes = 0
    if "alerta_validade" in df.columns:
        vencidas = int((df["alerta_validade"] == "vencida").sum())
        a_vencer = int((df["alerta_validade"] == "a_vencer").sum())
        vigentes = int((df["alerta_validade"] == "vigente").sum())

    criticos = int((df_errors["gravidade"] == CRITICO).sum()) if not df_errors.empty else 0
    medios = int((df_errors["gravidade"] == MEDIO).sum()) if not df_errors.empty else 0
    baixos = int((df_errors["gravidade"] == BAIXO).sum()) if not df_errors.empty else 0
    # Registros distintos com ao menos uma inconsistência crítica
    registros_criticos = int(df_errors[df_errors["gravidade"] == CRITICO]["linha_original"].nunique()) if not df_errors.empty else 0

    # Precisão das coordenadas
    prec_baixa = prec_media = prec_alta = 0
    if "precisao_coord" in df.columns:
        prec_baixa = int((df["precisao_coord"] == "baixa").sum())
        prec_media = int((df["precisao_coord"] == "media").sum())
        prec_alta = int((df["precisao_coord"] == "alta").sum())
    # registros que dividem coordenada com empreendimento diferente
    coord_compart_regs = 0
    if "tem_coordenada" in df.columns:
        for _, rr in df[df["tem_coordenada"] == True].iterrows():
            try:
                k = (round(float(rr["latitude"]), 6), round(float(rr["longitude"]), 6))
            except (TypeError, ValueError):
                continue
            if k in coord_compartilhada:
                coord_compart_regs += 1

    resumo = {
        "total_registros": total,
        "registros_validos": total - sem_proto,
        "sem_coordenada": sem_coord,
        "coordenada_invalida": coord_invalida,
        "sem_protocolo": sem_proto,
        "sem_municipio": sem_mun,
        "sem_tipologia": sem_tipo,
        "sem_situacao": sem_sit,
        "sem_tecnico": sem_tecnico,
        "duplicados": duplicados,
        "licencas_vencidas": vencidas,
        "a_vencer_90_dias": a_vencer,
        "licencas_vigentes": vigentes,
        "inconsistencias_criticas": criticos,
        "inconsistencias_medias": medios,
        "inconsistencias_baixas": baixos,
        "registros_com_critico": registros_criticos,
        "coord_precisao_alta": prec_alta,
        "coord_precisao_media": prec_media,
        "coord_precisao_baixa": prec_baixa,
        "coord_compartilhada": coord_compart_regs,
        "coord_compartilhada_grupos": len(coord_compartilhada),
    }

    logger.info("Validação: %d críticos (%d registros) | %d médios | %d baixos",
                criticos, registros_criticos, medios, baixos)
    return df_errors, resumo
