"""Utilitários compartilhados pelo dashboard."""
import json
from pathlib import Path

import pandas as pd
import yaml

BASE_DIR = Path(__file__).parent.parent
PROCESSED = BASE_DIR / "data" / "processed"
CONFIG_PATH = BASE_DIR / "config.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_data() -> tuple:
    """Carrega CSV, indicadores e metadados. Retorna (df, indicadores, meta)."""
    csv_path = PROCESSED / "processos_hidreletricas.csv"
    ind_path = PROCESSED / "resumo_indicadores.json"
    meta_path = PROCESSED / "metadados_execucao.json"

    if not csv_path.exists():
        return pd.DataFrame(), {}, {}

    df = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)

    # Correções manuais de coordenada (planilha SEPARADA — o .xlsm nunca é alterado).
    df = apply_correcoes(df)
    # Conferência geoespacial: situação/fase/grau/observação VERIFICADOS (merge por protocolo).
    df = merge_conferencia(df)
    # Contatos do empreendedor + consultoria responsável (merge por protocolo).
    df = merge_contatos(df)

    for dc in ["data_protocolo", "data_emissao", "data_validade"]:
        if dc in df.columns:
            df[dc] = pd.to_datetime(df[dc], errors="coerce").dt.date

    for bc in ["tem_coordenada", "processo_encerrado"]:
        if bc in df.columns:
            df[bc] = df[bc].astype(str).str.lower().isin(["true", "1", "yes"])

    indicadores = {}
    if ind_path.exists():
        with open(ind_path, encoding="utf-8") as f:
            indicadores = json.load(f)

    meta = {}
    if meta_path.exists():
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)

    return df, indicadores, meta


def load_errors() -> pd.DataFrame:
    path = PROCESSED / "erros_validacao.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig")


def cor_situacao(situacao: str, config: dict) -> str:
    cores = config.get("cores_situacao", {})
    if situacao is None:
        return cores.get("DEFAULT", "#64748b")
    chave = str(situacao).upper().strip()
    for k, v in cores.items():
        if k.upper() in chave or chave in k.upper():
            return v
    return cores.get("DEFAULT", "#64748b")


def cor_tipologia(tipologia: str, config: dict) -> str:
    cores = config.get("cores_tipologia", {})
    if tipologia is None:
        return cores.get("DEFAULT", "#64748b")
    return cores.get(str(tipologia).upper().strip(), cores.get("DEFAULT", "#64748b"))


# Cores da SITUAÇÃO VERIFICADA (conferência geoespacial). Fallback embutido caso o
# config.yaml não traga `cores_situacao_verificada`.
_CORES_SIT_VERIF_FALLBACK = {
    "VALIDADO": "#22c55e", "CORRIGIDO": "#3b82f6",
    "PENDENTE DE VALIDACAO": "#f59e0b", "PENDENTE": "#f59e0b",
    "SEM IMAGEM SUFICIENTE": "#f97316", "NAO IDENTIFICADO": "#ef4444",
    "NAO CONSTRUIDO": "#94a3b8", "DEFAULT": "#64748b",
}


def _sem_acento(s: str) -> str:
    tab = str.maketrans("ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ", "AAAAAEEEEIIIIOOOOOUUUUC")
    return str(s).upper().strip().translate(tab)


def cor_situacao_verificada(valor, config: dict) -> str:
    cores = config.get("cores_situacao_verificada", _CORES_SIT_VERIF_FALLBACK)
    if valor is None or str(valor) in ("nan", "None", ""):
        return cores.get("DEFAULT", "#64748b")
    chave = _sem_acento(valor)
    for k, v in cores.items():
        if _sem_acento(k) == chave:
            return v
    # casamento parcial tolerante (ex.: "Pendente de validação")
    for k, v in cores.items():
        kk = _sem_acento(k)
        if kk != "DEFAULT" and (kk in chave or chave in kk):
            return v
    return cores.get("DEFAULT", "#64748b")


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    for col, values in filters.items():
        if not values or col not in df.columns:
            continue
        if isinstance(values, list) and len(values) > 0:
            df = df[df[col].isin(values)]
    return df


# ── Formatação (pt-BR) ────────────────────────────────────────────────────────
def fmt_int(n) -> str:
    try:
        return f"{int(round(float(n))):,}".replace(",", ".")
    except (ValueError, TypeError):
        return "—"


def fmt_mw(n) -> str:
    try:
        v = float(n)
    except (ValueError, TypeError):
        return "—"
    if v >= 1000:
        return f"{v:,.0f}".replace(",", ".") + " MW"
    return f"{v:,.1f}".replace(".", ",") + " MW"


def fmt_data(d) -> str:
    if d is None or (isinstance(d, float)):
        return "—"
    try:
        return d.strftime("%d/%m/%Y")
    except (AttributeError, ValueError):
        s = str(d)
        return s if s and s.lower() not in ("nan", "nat", "none") else "—"


# ── Tema unificado para gráficos Plotly ───────────────────────────────────────
PLOT_FONT = "Inter, Segoe UI, sans-serif"


def style_fig(fig, height=300, show_legend=False):
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=14, t=42, b=8),
        plot_bgcolor="white",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family=PLOT_FONT, size=12, color="#334155"),
        title_font=dict(size=14, color="#1e293b", family=PLOT_FONT),
        title_x=0.01,
        showlegend=show_legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    font=dict(size=11)),
        xaxis=dict(gridcolor="#eef2f6", zerolinecolor="#e2e8f0"),
        yaxis=dict(gridcolor="#eef2f6", zerolinecolor="#e2e8f0"),
        hoverlabel=dict(font_family=PLOT_FONT, font_size=12, bgcolor="white"),
    )
    return fig


def merge_conferencia(df: pd.DataFrame) -> pd.DataFrame:
    """Mescla a conferência geoespacial (situação/fase/grau/observação VERIFICADOS) por protocolo.

    Lê `data/processed/conferencia_para_dashboard.csv` (gerado pela rotina de conferência).
    Não altera coordenadas — isso é feito por `apply_correcoes`; aqui só ENRIQUECE o df com
    colunas de status verificado para colorir o mapa, filtrar e exibir na ficha. Silencioso
    se o arquivo não existir."""
    path = PROCESSED / "conferencia_para_dashboard.csv"
    if not path.exists() or "protocolo" not in df.columns:
        return df
    try:
        conf = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
    except (OSError, ValueError):
        return df
    if conf.empty or "protocolo" not in conf.columns:
        return df
    ren = {
        "status_barragem": "situacao_verificada",
        "status_casa_forca": "status_casa_forca_verif",
        "fase_verificada": "fase_verificada",
        "grau_confianca": "grau_confianca",
        "observacao": "obs_conferencia",
        "coordenada_status": "coordenada_status",
    }
    keep = ["protocolo"] + [c for c in ren if c in conf.columns]
    conf = conf[keep].rename(columns=ren)
    conf["_proto_key"] = conf["protocolo"].astype(str).str.strip()
    conf = conf.drop(columns=["protocolo"]).drop_duplicates("_proto_key", keep="first")
    df = df.copy()
    df["_proto_key"] = df["protocolo"].astype(str).str.strip()
    df = df.merge(conf, on="_proto_key", how="left").drop(columns=["_proto_key"])
    return df


def merge_contatos(df: pd.DataFrame) -> pd.DataFrame:
    """Mescla os contatos (empreendedor + consultoria responsável) por protocolo.

    Lê `data/fiscalizacao/contatos.csv` e adiciona as colunas emp_contato/emp_telefone/
    emp_email e consultoria/cons_telefone/cons_email para exibição na ficha e no relatório
    e para uso como destinatários de notificações. Silencioso se o arquivo não existir."""
    path = BASE_DIR / "data" / "fiscalizacao" / "contatos.csv"
    if not path.exists() or "protocolo" not in df.columns:
        return df
    try:
        ct = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
    except (OSError, ValueError):
        return df
    if ct.empty or "protocolo" not in ct.columns:
        return df
    cols = [c for c in ["emp_contato", "emp_telefone", "emp_email",
                        "consultoria", "cons_telefone", "cons_email"] if c in ct.columns]
    if not cols:
        return df
    df = df.copy()
    # 1) casa por PROTOCOLO
    ctp = ct[["protocolo"] + cols].copy()
    ctp["_proto_key"] = ctp["protocolo"].astype(str).str.strip()
    ctp = ctp.drop(columns=["protocolo"]).drop_duplicates("_proto_key", keep="last")
    df["_proto_key"] = df["protocolo"].astype(str).str.strip()
    df = df.merge(ctp, on="_proto_key", how="left").drop(columns=["_proto_key"])
    # 2) fallback por NOME do empreendimento (contato cadastrado num protocolo representativo)
    if "empreendimento" in ct.columns and "empreendimento" in df.columns:
        ctn = ct[["empreendimento"] + cols].copy()
        ctn["_nome_key"] = ctn["empreendimento"].astype(str).str.strip().str.upper()
        ctn = ctn.drop(columns=["empreendimento"]).drop_duplicates("_nome_key", keep="last")
        ctn = ctn.rename(columns={c: c + "__n" for c in cols})
        df["_nome_key"] = df["empreendimento"].astype(str).str.strip().str.upper()
        df = df.merge(ctn, on="_nome_key", how="left").drop(columns=["_nome_key"])
        for c in cols:
            nc = c + "__n"
            if nc in df.columns:
                vazio = ~df[c].notna() | (df[c].astype(str).str.strip() == "")
                df.loc[vazio, c] = df.loc[vazio, nc]
                df = df.drop(columns=[nc])
    return df


def apply_correcoes(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica correções manuais de coordenada por cima do DataFrame carregado.

    Lê `data/processed/correcoes_coordenadas.csv` (chave = protocolo). Para cada
    protocolo corrigido, sobrescreve latitude/longitude (e casa de força, se houver),
    marca `fonte_coord` = 'Correção manual (dashboard)' e recalcula `tem_coordenada`.
    O .xlsm ORIGINAL nunca é tocado — esta é a camada de correção do projeto.
    """
    path = PROCESSED / "correcoes_coordenadas.csv"
    if not path.exists() or "protocolo" not in df.columns:
        return df
    try:
        cor = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
    except (OSError, ValueError):
        return df
    if cor.empty or "protocolo" not in cor.columns:
        return df

    def _num(v):
        try:
            f = float(str(v).replace(",", "."))
            return f if not pd.isna(f) else None
        except (ValueError, TypeError):
            return None

    cor_idx = {str(r.get("protocolo")).strip(): r for _, r in cor.iterrows()}
    proto = df["protocolo"].astype(str).str.strip()
    for col in ["latitude", "longitude", "lat_casa_forca", "lon_casa_forca"]:
        if col not in df.columns:
            df[col] = pd.NA
    if "fonte_coord" not in df.columns:
        df["fonte_coord"] = pd.NA

    for i, p in proto.items():
        rc = cor_idx.get(p)
        if rc is None:
            continue
        lat, lon = _num(rc.get("latitude")), _num(rc.get("longitude"))
        if lat is not None and lon is not None:
            df.at[i, "latitude"] = lat
            df.at[i, "longitude"] = lon
            df.at[i, "fonte_coord"] = "Correção manual (dashboard)"
            if "tem_coordenada" in df.columns:
                df.at[i, "tem_coordenada"] = True
            if "tem_coord_barragem" in df.columns:
                df.at[i, "tem_coord_barragem"] = True
        lcf, ocf = _num(rc.get("lat_casa_forca")), _num(rc.get("lon_casa_forca"))
        if lcf is not None and ocf is not None:
            df.at[i, "lat_casa_forca"] = lcf
            df.at[i, "lon_casa_forca"] = ocf
    return df


def _chave_recencia(row) -> tuple:
    """Ordena registros de um mesmo empreendimento do MAIS recente para o mais antigo,
    pelo protocolo/licença mais recente (data_protocolo > data_emissao > data_validade)."""
    def _key(v):
        try:
            return v.toordinal() if hasattr(v, "toordinal") and v else -1
        except (AttributeError, ValueError):
            return -1
    return (_key(row.get("data_protocolo")), _key(row.get("data_emissao")),
            _key(row.get("data_validade")))


def representativos(df: pd.DataFrame) -> pd.DataFrame:
    """Um registro por empreendimento: o do protocolo/licença MAIS RECENTE.

    Para nomes duplicados na planilha (mesmo empreendimento, vários protocolos),
    escolhe o ponto do registro mais recente. Empreendimentos sem nome são mantidos
    como estão (cada linha vira seu próprio grupo)."""
    if df.empty or "empreendimento" not in df.columns:
        return df
    df = df.copy()
    df["_rec"] = df.apply(_chave_recencia, axis=1)
    nome = df["empreendimento"].fillna("").astype(str).str.strip()
    df["_grp"] = nome.where(nome != "", df.index.astype(str))
    df = df.sort_values("_rec", ascending=False)
    out = df.drop_duplicates("_grp", keep="first").drop(columns=["_rec", "_grp"])
    return out.sort_index()


def build_point_index(df: pd.DataFrame) -> dict:
    """Indexa registros com coordenada por (lat, lon) arredondados para lookup do mapa."""
    idx = {}
    if "tem_coordenada" not in df.columns:
        return idx
    for _, row in df[df["tem_coordenada"] == True].iterrows():
        try:
            key = (round(float(row["latitude"]), 5), round(float(row["longitude"]), 5))
        except (ValueError, TypeError):
            continue
        idx.setdefault(key, row.to_dict())
    return idx
