"""Transformação e padronização dos dados brutos."""
import re
import logging
import unicodedata
from datetime import datetime

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# Mapa de normalização de situação (encoding + grafia)
_SITUACAO_NORM = {
    "EM AN LISE": "EM ANALISE",
    "EM ANÁLISE": "EM ANALISE",
    "ANALISE REGIONAL": "EM ANALISE",
    "DEVOLVIDO - SGA": "DEVOLVIDO",
}


_NULL_TOKENS = {"", "nan", "none", "nat", "null", "n/a", "na", "-", "--", "#n/d", "x"}

# Situações encerradas — vencimento de licença deixa de ser urgência operacional
_SIT_ENCERRADAS = {"ARQUIVADO", "ENCERRADO", "CANCELADO", "INDEFERIDO", "DEVOLVIDO"}


def _isna(v) -> bool:
    """True para None, np.nan, pd.NaT e tokens textuais que representam vazio."""
    if v is None:
        return True
    try:
        if pd.isna(v):
            return True
    except (TypeError, ValueError):
        pass
    if isinstance(v, str) and v.strip().lower() in _NULL_TOKENS:
        return True
    return False


def _strip_text(v) -> str:
    if _isna(v):
        return None
    s = str(v).strip()
    s = re.sub(r"\s+", " ", s)
    return s if s and s.lower() not in _NULL_TOKENS else None


def _norm_upper(v) -> str:
    s = _strip_text(v)
    if s is None:
        return None
    return s.upper()


def _protocolo_str(v) -> str:
    """Converte protocolo para string uniforme."""
    if _isna(v):
        return None
    s = str(v).strip()
    # remove .0 de floats lidos como número
    s = re.sub(r"\.0$", "", s)
    return s if s else None


def _clean_cnpj(v) -> str:
    if _isna(v):
        return None
    s = re.sub(r"[^\d]", "", str(v))
    if len(s) == 14:
        return f"{s[:2]}.{s[2:5]}.{s[5:8]}/{s[8:12]}-{s[12:]}"
    if len(s) == 11:
        return f"{s[:3]}.{s[3:6]}.{s[6:9]}-{s[9:]}"
    return str(v).strip()


def _to_float(v) -> float:
    if _isna(v):
        return None
    try:
        if isinstance(v, str):
            v = v.replace(".", "").replace(",", ".").strip() if v.count(",") == 1 and v.count(".") > 1 else v.replace(",", ".").strip()
        return float(v)
    except (ValueError, TypeError):
        return None


def _to_date(v):
    if _isna(v):
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(v.strip(), fmt).date()
            except ValueError:
                continue
    return None


def _decimais(v):
    """Nº de casas decimais efetivas de um número (0..6)."""
    if _isna(v):
        return None
    for n in range(0, 7):
        if round(v, n) == v:
            return n
    return 6


def _colkey(s) -> str:
    """Chave normalizada para casar cabeçalhos tolerando acentos e símbolos (º, °, ª)."""
    s = str(s)
    for ch in "º°ª":
        s = s.replace(ch, "")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.upper()
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _fix_coord(v, lat_min, lat_max, lon_min, lon_max, tipo="lat"):
    f = _to_float(v)
    if f is None:
        return None
    if tipo == "lat" and not (lat_min <= f <= lat_max):
        return None
    if tipo == "lon" and not (lon_min <= f <= lon_max):
        return None
    return f


def transform(df_raw: pd.DataFrame, config: dict) -> pd.DataFrame:
    col_map = config["column_mapping"]
    coord_cfg = config["coordenadas"]

    # Renomear colunas — casamento tolerante a acentos/símbolos (º vs °, etc.)
    col_index = {}
    for col in df_raw.columns:
        col_index.setdefault(_colkey(col), col)

    rename = {}
    nao_encontradas = []
    for orig, dest in col_map.items():
        match = col_index.get(_colkey(orig))
        if match is not None and match not in rename:
            rename[match] = dest
        else:
            nao_encontradas.append(orig)
    df = df_raw.rename(columns=rename)
    logger.info("Colunas mapeadas: %d/%d", len(rename), len(col_map))
    if nao_encontradas:
        logger.warning("Colunas do config não encontradas na planilha: %s", nao_encontradas)

    # Protocolo
    if "protocolo" in df.columns:
        df["protocolo"] = df["protocolo"].apply(_protocolo_str)

    # Textos gerais — strip + espaços duplos
    text_cols = ["empreendimento", "empreendedor", "rio", "municipio", "fonte_coord",
                 "obs_auditoria", "observacoes", "status_coord_barragem", "status_coord_casa_forca"]
    for c in text_cols:
        if c in df.columns:
            df[c] = df[c].apply(_strip_text)

    # Campos categóricos — uppercase + normalização
    cat_cols = ["tipologia", "bacia_hidrografica", "tecnico_responsavel", "tipo_licenca"]
    for c in cat_cols:
        if c in df.columns:
            df[c] = df[c].apply(_norm_upper)

    # Situação — normalizar encoding e grafia
    if "situacao" in df.columns:
        df["situacao"] = df["situacao"].apply(_norm_upper)
        df["situacao"] = df["situacao"].replace(_SITUACAO_NORM)

    # CNPJ
    if "cnpj" in df.columns:
        df["cnpj"] = df["cnpj"].apply(_clean_cnpj)

    # Número licença — tratar 'X' como ausente
    if "numero_licenca" in df.columns:
        df["numero_licenca"] = df["numero_licenca"].apply(
            lambda v: None if str(v).strip().upper() in ("X", "NONE", "") else _strip_text(v)
        )

    # Datas
    for dc in ["data_protocolo", "data_emissao", "data_validade"]:
        if dc in df.columns:
            df[dc] = df[dc].apply(_to_date)

    # Potência
    if "potencia" in df.columns:
        df["potencia"] = df["potencia"].apply(_to_float)

    # Coordenadas — prioridade: barragem → casa de força
    lat_col = "latitude" if "latitude" in df.columns else None
    lon_col = "longitude" if "longitude" in df.columns else None

    # Detectar coordenada informada porém fora dos limites do Paraná (inválida ≠ ausente)
    def _tem_numero(v):
        return _to_float(v) is not None

    raw_tem_coord = pd.Series(False, index=df.index)
    if lat_col and lon_col:
        raw_tem_coord = df["latitude"].apply(_tem_numero) & df["longitude"].apply(_tem_numero)

    if lat_col:
        df["latitude"] = df["latitude"].apply(
            lambda v: _fix_coord(v, coord_cfg["lat_min"], coord_cfg["lat_max"], coord_cfg["lon_min"], coord_cfg["lon_max"], "lat")
        )
    if lon_col:
        df["longitude"] = df["longitude"].apply(
            lambda v: _fix_coord(v, coord_cfg["lat_min"], coord_cfg["lat_max"], coord_cfg["lon_min"], coord_cfg["lon_max"], "lon")
        )

    # Fallback para casa de força quando barragem ausente
    if "lat_casa_forca" in df.columns and "lon_casa_forca" in df.columns:
        df["lat_casa_forca"] = df["lat_casa_forca"].apply(
            lambda v: _fix_coord(v, coord_cfg["lat_min"], coord_cfg["lat_max"], coord_cfg["lon_min"], coord_cfg["lon_max"], "lat")
        )
        df["lon_casa_forca"] = df["lon_casa_forca"].apply(
            lambda v: _fix_coord(v, coord_cfg["lat_min"], coord_cfg["lat_max"], coord_cfg["lon_min"], coord_cfg["lon_max"], "lon")
        )
        mask_sem = df["latitude"].isna() | df["longitude"].isna()
        df.loc[mask_sem, "latitude"] = df.loc[mask_sem, "lat_casa_forca"]
        df.loc[mask_sem, "longitude"] = df.loc[mask_sem, "lon_casa_forca"]

    df["tem_coordenada"] = df["latitude"].notna() & df["longitude"].notna()
    # Coordenada informada na planilha mas descartada por estar fora dos limites do PR
    df["coord_fora_pr"] = raw_tem_coord & (~df["tem_coordenada"])

    # Links por coordenada para os handlers de desktop (abrem centralizado no ponto)
    def _link_proto(r, scheme):
        if not r["tem_coordenada"]:
            return None
        return f"{scheme}://{float(r['latitude']):.6f},{float(r['longitude']):.6f}"
    df["link_qgis"] = df.apply(lambda r: _link_proto(r, "qgis"), axis=1)       # QGIS desktop
    df["link_gearth"] = df.apply(lambda r: _link_proto(r, "gearth"), axis=1)   # Google Earth Pro desktop

    # Precisão da coordenada — nº de casas decimais efetivas (apoia validação de precisão)
    def _ndec(r):
        if not r["tem_coordenada"]:
            return None
        return min(_decimais(r["latitude"]), _decimais(r["longitude"]))

    df["n_decimais_coord"] = df.apply(_ndec, axis=1)

    def _precisao(nd):
        if nd is None or pd.isna(nd):
            return None
        if nd <= 2:
            return "baixa"     # ~1 km ou pior
        if nd == 3:
            return "media"     # ~100 m
        return "alta"          # ~10 m ou melhor
    df["precisao_coord"] = df["n_decimais_coord"].apply(_precisao)

    # Link Google Earth (navegador) — limpa 'sem coordenada' e preenche pelas coordenadas quando ausente
    if "link_google_earth" in df.columns:
        df["link_google_earth"] = df["link_google_earth"].apply(
            lambda v: None if str(v).lower() in ("sem coordenada", "none", "") else _strip_text(v)
        )
    else:
        df["link_google_earth"] = None

    def _ge_web(r):
        cur = r.get("link_google_earth")
        if isinstance(cur, str) and cur.startswith("http"):
            return cur
        if r["tem_coordenada"]:
            return (f"https://earth.google.com/web/@{float(r['latitude']):.6f},"
                    f"{float(r['longitude']):.6f},900a,800d,0y,0h,0t,0r")
        return None
    df["link_google_earth"] = df.apply(_ge_web, axis=1)

    # Extrair link SGA da coluna OBS quando presente
    if "observacoes" in df.columns:
        df["link_sga"] = df["observacoes"].apply(
            lambda v: "SGA" if v and "SGA" in str(v).upper() else None
        )

    # Processo encerrado (situação) — usado para distinguir vencida real de histórica
    if "situacao" in df.columns:
        df["processo_encerrado"] = df["situacao"].apply(
            lambda s: (not _isna(s)) and str(s).upper().strip() in _SIT_ENCERRADAS)
    else:
        df["processo_encerrado"] = False

    # Alerta de validade — distingue datas SUSPEITAS (erro de base) de vencida real
    hoje = pd.Timestamp.today().normalize().date()
    dias = config.get("dias_alerta_vencimento", 90)

    def _data_suspeita(val, emi):
        """True para validade implausível: anterior a 1980, muito futura, ou antes da emissão."""
        if val is None:
            return False
        if val.year < 1980 or val.year > hoje.year + 40:
            return True
        if emi is not None and val < emi:
            return True
        return False

    if "data_validade" in df.columns:
        def _alerta_row(r):
            d = r.get("data_validade")
            emi = r.get("data_emissao")
            d = None if (d is None or (not isinstance(d, str) and pd.isna(d))) else d
            emi = None if (emi is None or (not isinstance(emi, str) and pd.isna(emi))) else emi
            if d is None:
                return "sem_validade"
            if _data_suspeita(d, emi):
                return "data_suspeita"
            if d < hoje:
                return "vencida"
            if (d - hoje).days <= dias:
                return "a_vencer"
            return "vigente"
        df["alerta_validade"] = df.apply(_alerta_row, axis=1)
    else:
        df["alerta_validade"] = "sem_validade"

    # Manter índice original para rastreabilidade
    df["linha_original"] = df.index + 2  # +2 porque header é linha 1 e index começa em 0

    # Remover colunas puramente auxiliares do KMZ e link texto
    cols_drop = [c for c in ["lat_kmz", "lon_kmz", "lat_casa_forca_kmz", "lon_casa_forca_kmz",
                              "_link_earth_texto", "lat_casa_forca", "lon_casa_forca"] if c in df.columns]
    df = df.drop(columns=cols_drop)

    logger.info("Transformação concluída. Shape: %s", df.shape)
    return df
