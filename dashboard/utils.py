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

    for dc in ["data_protocolo", "data_emissao", "data_validade"]:
        if dc in df.columns:
            df[dc] = pd.to_datetime(df[dc], errors="coerce").dt.date

    if "tem_coordenada" in df.columns:
        df["tem_coordenada"] = df["tem_coordenada"].astype(str).str.lower().isin(["true", "1", "yes"])

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
