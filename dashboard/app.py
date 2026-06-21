"""Dashboard Central de Projetos Hidrelétricos do Estado do Paraná — IAT/PR"""
import os
import re
import sys
import ssl
import json
import math
import base64
import subprocess
import webbrowser
import urllib.request
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape as _xesc

import pandas as pd
import plotly.express as px
import streamlit as st
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

sys.path.insert(0, str(Path(__file__).parent))
from utils import (
    load_config, load_data, load_errors, cor_situacao, cor_tipologia,
    apply_filters, fmt_int, fmt_mw, fmt_data, style_fig, build_point_index,
)

# PUBLIC_MODE = app publicado na nuvem (ex.: Streamlit Cloud). Nesse caso os botões de
# abrir viram LINKS que abrem no navegador do VISITANTE (Earth Web / Maps), pois o
# servidor não pode abrir programas na máquina de quem acessa. Local (Windows) mantém
# os botões que abrem QGIS/Google Earth na própria máquina. Força com env IAT_PUBLIC=1.
PUBLIC_MODE = os.environ.get("IAT_PUBLIC", "").strip() == "1" or not sys.platform.startswith("win")

# ── Configuração da página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Central de Projetos Hidrelétricos do Estado do Paraná — IAT/PR",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS institucional ─────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
  html, body, [class*="css"], [data-testid="stAppViewContainer"] * {
    font-family: 'Inter', 'Segoe UI', sans-serif;
  }
  /* A regra * acima sobrepunha a fonte de ícones do Streamlit, fazendo a seta do
     expander e o colapso da sidebar virarem texto ("keyboard_arrow_*"). Restaura: */
  [data-testid="stIconMaterial"], span[class*="material-symbols"],
  .material-icons, .material-icons-outlined, .material-icons-round {
    font-family: 'Material Symbols Rounded', 'Material Symbols Outlined', 'Material Icons' !important;
  }
  [data-testid="stAppViewContainer"] { background: #f1f5f9; }
  [data-testid="stHeader"] { background: rgba(0,0,0,0); }
  .block-container { padding-top: 1.6rem; padding-bottom: 2rem; max-width: 1500px; }

  /* Sidebar */
  [data-testid="stSidebar"] { background: #0c2d54; }
  [data-testid="stSidebar"] * { color: #e2e8f0 !important; }
  [data-testid="stSidebar"] h3 { color: #fff !important; font-size: 15px !important; }
  [data-testid="stSidebar"] label { color: #9fb6d4 !important; font-size: 12px !important; font-weight: 500 !important; }
  [data-testid="stSidebar"] [data-baseweb="tag"] { background: #1e5aa0 !important; }
  /* Botão de recolher a barra de filtros: SEMPRE visível + instrução antes da flecha */
  [data-testid="stSidebarCollapseButton"] { visibility: visible !important; opacity: 1 !important; }
  [data-testid="stSidebarHeader"] { align-items: center !important; }
  [data-testid="stSidebarHeader"]::before {
    content: "Clique na flecha para recolher a aba de filtros →";
    flex: 1 1 auto; padding-right: 8px; white-space: normal;
    color: #9fb6d4 !important; font-size: 11px; font-weight: 600; line-height: 1.2;
  }

  /* Header */
  .app-header { display:flex; justify-content:space-between; align-items:flex-end;
    border-bottom: 3px solid #0c2d54; padding-bottom: 12px; margin-bottom: 6px; }
  .app-title { font-size: 26px; font-weight: 800; color: #0c2d54; line-height:1.1; margin:0; }
  .app-sub { font-size: 13px; color: #64748b; margin-top: 2px; }
  .app-meta { text-align:right; font-size: 12px; color:#475569; line-height:1.5; }
  .app-meta .badge { display:inline-block; background:#e0f2fe; color:#075985; padding:3px 10px;
    border-radius:20px; font-weight:600; font-size:11px; }

  /* KPI cards */
  .kpi { background:#fff; border-radius:12px; padding:12px 13px;
    border:1.5px solid #3b82f6; box-shadow:0 0 0 1px rgba(59,130,246,.18), 0 3px 12px rgba(59,130,246,.22);
    min-height:98px; display:flex; flex-direction:column; justify-content:space-between;
    gap:6px; overflow:hidden; transition: box-shadow .15s, transform .15s; }
  .kpi:hover { transform: translateY(-2px); }
  .kpi-top { display:flex; align-items:center; gap:5px; }
  .kpi-ico { font-size:14px; }
  .kpi-label { font-size:10px; color:#64748b; text-transform:uppercase; letter-spacing:.3px; font-weight:600; line-height:1.15; }
  .kpi-val { font-size:clamp(20px,1.9vw,28px); font-weight:800; color:#0f172a; line-height:1; white-space:nowrap; }
  .kpi-sub { font-size:10px; color:#94a3b8; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .kpi.blue   { border-color:#3b82f6; box-shadow:0 0 0 1px rgba(59,130,246,.18), 0 3px 12px rgba(59,130,246,.24); }
  .kpi.green  { border-color:#22c55e; box-shadow:0 0 0 1px rgba(34,197,94,.18),  0 3px 12px rgba(34,197,94,.24); }
  .kpi.yellow { border-color:#f59e0b; box-shadow:0 0 0 1px rgba(245,158,11,.20), 0 3px 12px rgba(245,158,11,.26); }
  .kpi.red    { border-color:#ef4444; box-shadow:0 0 0 1px rgba(239,68,68,.18),  0 3px 12px rgba(239,68,68,.24); }
  .kpi.purple { border-color:#8b5cf6; box-shadow:0 0 0 1px rgba(139,92,246,.18), 0 3px 12px rgba(139,92,246,.24); }
  .kpi.gray   { border-color:#94a3b8; box-shadow:0 0 0 1px rgba(148,163,184,.18),0 3px 12px rgba(148,163,184,.24); }
  .kpi.teal   { border-color:#14b8a6; box-shadow:0 0 0 1px rgba(20,184,166,.18), 0 3px 12px rgba(20,184,166,.24); }

  /* Section titles */
  .section-title { font-size:15px; font-weight:700; color:#1e293b; margin:18px 0 10px 0;
    display:flex; align-items:center; gap:8px; }
  .section-title::before { content:""; width:4px; height:16px; background:#0c2d54; border-radius:3px; display:inline-block; }

  /* Alert banners */
  .alert-banner { padding:11px 16px; border-radius:9px; margin-bottom:9px; font-size:13px; display:flex; align-items:center; gap:8px; }
  .alert-red { background:#fef2f2; border-left:4px solid #ef4444; color:#991b1b; }
  .alert-yellow { background:#fffbeb; border-left:4px solid #f59e0b; color:#854d0e; }

  /* Filter chips */
  .chips { display:flex; flex-wrap:wrap; gap:6px; margin:2px 0 10px 0; }
  .chip { background:#e2e8f0; color:#334155; border-radius:16px; padding:3px 11px; font-size:11.5px; font-weight:500; }
  .chip b { color:#0c2d54; }

  /* Detail panel */
  .detail-card { background:#fff; border-radius:12px; padding:16px; box-shadow:0 1px 3px rgba(15,23,42,.08); font-size:12.5px; }
  .detail-card h4 { margin:0 0 2px 0; font-size:15px; color:#0c2d54; }
  .detail-card .tag { display:inline-block; padding:2px 9px; border-radius:6px; font-size:11px; font-weight:600; color:#fff; }
  .detail-row { display:flex; justify-content:space-between; padding:5px 0; border-bottom:1px solid #f1f5f9; gap:10px; }
  .detail-row .k { color:#64748b; font-weight:500; } .detail-row .v { color:#1e293b; font-weight:600; text-align:right; }
  .legend-item { display:flex; align-items:center; gap:7px; font-size:12px; color:#334155; padding:2px 0; }
  .legend-dot { width:11px; height:11px; border-radius:50%; display:inline-block; }

  /* Nav buttons */
  .stButton > button { border-radius:8px; font-size:13px; font-weight:600; border:1px solid #cbd5e1; padding:7px 4px; }
  /* Botões de navegação (ícone em cima + nome embaixo = 2 parágrafos): altura uniforme + ícone + sombra cinza */
  .stButton > button:has(p + p) { min-height:84px; line-height:1.25;
    box-shadow:0 0 9px 1px rgba(100,116,139,.40); transition:box-shadow .15s, transform .15s; }
  .stButton > button:has(p + p):hover { box-shadow:0 0 13px 2px rgba(71,85,105,.55); transform:translateY(-1px); }
  .stButton > button:has(p + p) p:first-child { font-size:21px; margin-bottom:3px; }
  .stButton > button[kind="primary"] { background:#0c2d54; border-color:#0c2d54; color:#fff; }
  .stButton > button[kind="secondary"] { background:#fff; color:#334155; }
  .stButton > button[kind="secondary"]:hover { border-color:#0c2d54; color:#0c2d54; }
  div[data-testid="stHorizontalBlock"] { gap:0.55rem; }
</style>
""", unsafe_allow_html=True)


# ── Dados ────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def _load():
    return load_config(), *load_data(), load_errors()

config, df_full, indicadores, meta, df_errors = _load()
dash_cfg = config.get("dashboard", {})
NO_DATA = df_full.empty


# ── Helpers de UI ─────────────────────────────────────────────────────────────
def kpi(icon, label, value, sub="", color="blue"):
    return (f'<div class="kpi {color}"><div class="kpi-top"><span class="kpi-ico">{icon}</span>'
            f'<span class="kpi-label">{label}</span></div><div class="kpi-val">{value}</div>'
            f'<div class="kpi-sub">{sub}</div></div>')


def section(title):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


def opts(col):
    if col not in df_full.columns:
        return []
    return sorted(df_full[col].dropna().astype(str).unique().tolist())


def ranked_bar(series, title, color="#3b82f6", top_n=20, color_fn=None):
    """Barra horizontal de contagem, ordenada (maior no topo)."""
    vc = series.dropna().astype(str).value_counts().head(top_n)
    d = vc.iloc[::-1].reset_index()
    d.columns = ["cat", "total"]
    if color_fn:
        colors = [color_fn(c) for c in d["cat"]]
        fig = px.bar(d, x="total", y="cat", orientation="h", title=title, text="total")
        fig.update_traces(marker_color=colors)
    else:
        fig = px.bar(d, x="total", y="cat", orientation="h", title=title, text="total",
                     color_discrete_sequence=[color])
    fig.update_traces(textposition="outside", textfont_size=11, cliponaxis=False,
                      hovertemplate="%{y}: %{x}<extra></extra>")
    h = max(240, len(d) * 26 + 70)
    style_fig(fig, height=h)
    fig.update_layout(yaxis_title="", xaxis_title="", uniformtext_minsize=9, uniformtext_mode="hide")
    fig.update_xaxes(range=[0, d["total"].max() * 1.16])
    return fig


def _ok(v):
    return v is not None and str(v) not in ("nan", "NaT", "None", "")


# ── Abertura de programas no DESKTOP (servidor local) ─────────────────────────
# O dashboard roda localmente (localhost), então o servidor abre os programas na
# própria máquina do usuário. Isso é confiável — não depende de o navegador
# conseguir disparar protocolos a partir do iframe do mapa (que é bloqueado).
_SRC_DIR = Path(__file__).resolve().parent.parent / "src"
_NO_WINDOW = 0x08000000  # CREATE_NO_WINDOW (Windows) — evita piscar console


def launch_desktop(kind, row):
    lat, lon = row.get("latitude"), row.get("longitude")
    nome = str(row.get("empreendimento") or "Empreendimento").strip() or "Empreendimento"
    try:
        if kind == "navegador":          # Google Earth Web — search/lat,lon MARCA o ponto (pino)
            if _ok(lat) and _ok(lon):
                url = f"https://earth.google.com/web/search/{float(lat):.6f},{float(lon):.6f}"
                webbrowser.open(url, new=2)
                return True
            url = row.get("link_google_earth")
            if _ok(url):
                webbrowser.open(str(url), new=2)
                return True
            return False
        if kind == "maps":               # Google Maps: marca o ponto na coordenada COM o nome
            if _ok(lat) and _ok(lon):
                url = (f"https://www.google.com/maps?q={float(lat):.6f},{float(lon):.6f}"
                       f"({quote(nome)})")
                webbrowser.open(url, new=2)
                return True
            return False
        script = _SRC_DIR / f"{kind}_handler" / f"{kind}_open.py"
        uri = f"{kind}://{float(lat):.6f},{float(lon):.6f}"
        flags = _NO_WINDOW if sys.platform.startswith("win") else 0
        subprocess.Popen([sys.executable, str(script), uri, nome], creationflags=flags)
        return True
    except Exception as e:  # noqa: BLE001
        st.warning(f"Não consegui abrir ({kind}): {e}")
        return False


def _earth_web_url(row):
    lat, lon = row.get("latitude"), row.get("longitude")
    if _ok(lat) and _ok(lon):
        return f"https://earth.google.com/web/search/{float(lat):.6f},{float(lon):.6f}"
    u = row.get("link_google_earth")
    return str(u) if _ok(u) else None


def _maps_url(row):
    lat, lon = row.get("latitude"), row.get("longitude")
    nome = str(row.get("empreendimento") or "Empreendimento").strip() or "Empreendimento"
    if _ok(lat) and _ok(lon):
        return f"https://www.google.com/maps?q={float(lat):.6f},{float(lon):.6f}({quote(nome)})"
    return None


# Geração de arquivos para abrir os PROGRAMAS no computador do VISITANTE (modo nuvem).
# .kml abre no Google Earth Pro e .qgs no QGIS por associação de arquivo — basta o
# programa estar instalado (nenhum handler/Python extra é necessário).
_KML_TPL = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{nome}</name>
    <LookAt><longitude>{lon}</longitude><latitude>{lat}</latitude><altitude>0</altitude>
      <range>2500</range><tilt>0</tilt><heading>0</heading>
      <altitudeMode>relativeToGround</altitudeMode></LookAt>
    <Placemark><name>{nome}</name><description>Lat {lat}, Lon {lon}</description>
      <Point><coordinates>{lon},{lat},0</coordinates></Point></Placemark>
  </Document>
</kml>
"""


def _to3857(lat, lon):
    x = float(lon) * 20037508.342789244 / 180.0
    y = math.log(math.tan((90.0 + float(lat)) * math.pi / 360.0)) / (math.pi / 180.0)
    return x, y * 20037508.342789244 / 180.0


def build_kml(lat, lon, nome="Empreendimento"):
    return _KML_TPL.format(nome=_xesc(str(nome)), lat=f"{float(lat):.6f}",
                           lon=f"{float(lon):.6f}").encode("utf-8")


def build_qgs(lat, lon, nome="Empreendimento", half_m=600.0):
    """Projeto QGIS (satélite Esri centralizado no ponto) a partir do template gerado
    pelo próprio QGIS (dashboard/assets/qgis_template.qgs)."""
    x, y = _to3857(lat, lon)
    tpl = (Path(__file__).parent / "assets" / "qgis_template.qgs").read_text(encoding="utf-8")
    return (tpl.replace("__IAT_XMIN__", f"{x - half_m:.5f}")
               .replace("__IAT_YMIN__", f"{y - half_m:.5f}")
               .replace("__IAT_XMAX__", f"{x + half_m:.5f}")
               .replace("__IAT_YMAX__", f"{y + half_m:.5f}")
               .replace("__IAT_NOME__", _xesc(str(nome)))).encode("utf-8")


def open_buttons(row, key_prefix):
    """Botões para abrir o local. Na nuvem (PUBLIC_MODE): 🌐/📍 abrem no navegador do
    visitante; 🖥️/🗺️ baixam .kml/.qgs que abrem o programa NA MÁQUINA do visitante (se
    instalado). Local: launch_desktop abre os programas direto (servidor = PC do usuário)."""
    if PUBLIC_MODE:
        ew, mp = _earth_web_url(row), _maps_url(row)
        lat, lon = row.get("latitude"), row.get("longitude")
        nome = str(row.get("empreendimento") or "Empreendimento").strip() or "Empreendimento"
        if ew:
            st.link_button("🌐 Google Earth Web", ew, use_container_width=True)
        if mp:
            st.link_button("📍 Google Maps", mp, use_container_width=True)
        if _ok(lat) and _ok(lon):
            safe = re.sub(r"[^A-Za-z0-9]+", "_", nome).strip("_")[:40] or "ponto"
            st.download_button("🖥️ Google Earth Desktop (.kml)", build_kml(lat, lon, nome),
                               file_name=f"{safe}.kml", mime="application/vnd.google-earth.kml+xml",
                               use_container_width=True, key=f"{key_prefix}_kml")
            try:
                st.download_button("🗺️ QGIS (.qgs)", build_qgs(lat, lon, nome),
                                   file_name=f"{safe}.qgs", mime="application/x-qgis-project",
                                   use_container_width=True, key=f"{key_prefix}_qgs")
            except OSError:
                pass
        st.caption("**Google Earth Desktop** e **QGIS** baixam um arquivo que abre o programa "
                   "**no seu computador** (se estiver instalado). **Google Earth Web** e "
                   "**Google Maps** abrem no navegador.")
    else:
        if st.button("🌐 Google Earth Web", key=f"{key_prefix}_nav", use_container_width=True):
            launch_desktop("navegador", row)
        if st.button("📍 Google Maps", key=f"{key_prefix}_maps", use_container_width=True):
            launch_desktop("maps", row)
        if st.button("🖥️ Programa Google Earth Desktop", key=f"{key_prefix}_gearth", use_container_width=True):
            launch_desktop("gearth", row)
        if st.button("🗺️ Programa QGIS", key=f"{key_prefix}_qgis", use_container_width=True):
            launch_desktop("qgis", row)


PREC_COR = {"alta": "#22c55e", "media": "#f59e0b", "baixa": "#ef4444"}
PREC_LABEL = {"alta": "Alta (~10 m)", "media": "Média (~100 m)", "baixa": "Baixa (~1 km)"}


def prec_label(p, nd=None):
    if not _ok(p):
        return "—"
    c = PREC_COR.get(p, "#64748b")
    dec = "" if not _ok(nd) else f" · {int(float(nd))} casas"
    return f'<span style="color:{c};font-weight:700">{PREC_LABEL.get(p, p)}{dec}</span>'


_ESRI_SAT = ("https://server.arcgisonline.com/ArcGIS/rest/services/"
             "World_Imagery/MapServer/tile/{z}/{y}/{x}")
_ESRI_LABELS = ("https://server.arcgisonline.com/ArcGIS/rest/services/"
                "Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}")


@st.cache_data(show_spinner=False)
def load_bacias():
    """Carrega as bacias hidrográficas do PR (GeoJSON) + centroides p/ rótulos."""
    p = Path(__file__).parent.parent / "data" / "bacias_parana.geojson"
    if not p.exists():
        return None
    try:
        gj = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    labels = []
    for feat in gj.get("features", []):
        nome = (feat.get("properties") or {}).get("NOME")
        geom = feat.get("geometry") or {}
        coords = geom.get("coordinates")
        if not nome or not coords:
            continue
        if geom.get("type") == "Polygon":
            ring = coords[0]
        elif geom.get("type") == "MultiPolygon":
            ring = max(coords, key=lambda poly: len(poly[0]))[0]
        else:
            continue
        xs = [c[0] for c in ring]
        ys = [c[1] for c in ring]
        labels.append((nome, sum(ys) / len(ys), sum(xs) / len(xs)))
    return gj, labels


@st.cache_data(show_spinner=False, ttl=3600)
def load_wms_legend(rest_base, service):
    """Busca a legenda (rótulo + swatch base64) de uma camada do ArcGIS do GeoPR.

    Usa o endpoint REST /MapServer/legend?f=json. O certificado do GeoPR valida
    no navegador, mas a cadeia pode falhar no cliente Python — por isso o contexto
    SSL não verifica (só leitura de legenda pública, app local). Cacheado por 1h.
    """
    if not rest_base or not service:
        return []
    url = f"{rest_base}/{service}/MapServer/legend?f=json"
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(url, timeout=20, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return []
    items = []
    for lyr in data.get("layers", []):
        for leg in lyr.get("legend", []):
            lbl = (leg.get("label") or "").strip()
            img = leg.get("imageData") or ""
            if img:
                items.append((lbl, img))
    return items


# Opções de mapa base — rótulo exibido nos controles → (tiles, attr, max_zoom)
BASE_MAPS = {
    "🗺️ Mapa claro": ("CartoDB positron", None, 20),
    "🛰️ Satélite": (_ESRI_SAT, "Tiles &copy; Esri — Maxar, Earthstar Geographics, USDA, USGS, IGN", 19),
    "🛣️ Ruas (OSM)": ("OpenStreetMap", None, 19),
}


def build_folium_map(_records, signature, cor_por, _config, base_map="🗺️ Mapa claro",
                     show_labels=False, show_bacias=False, wms_on=(), fill_op=0.35, radius=7):
    """Mapa Folium controlado por widgets EXTERNOS (abaixo do mapa), não pelo painel do Leaflet.

    Só adiciona o mapa base escolhido e as sobreposições marcadas (`wms_on` = conjunto de
    services WMS ligados). Sem `LayerControl` no mapa — os controles ficam no Streamlit.
    NÃO cacheado: reaproveitar um folium.Map entre reruns quebra o st_folium (iframe altura 0).
    `fill_op` controla a transparência do preenchimento dos pontos.
    """
    m = folium.Map(location=[_config["dashboard"].get("mapa_centro_lat", -24.7),
                             _config["dashboard"].get("mapa_centro_lon", -51.3)],
                   zoom_start=_config["dashboard"].get("mapa_zoom_inicial", 7),
                   tiles=None, control_scale=True)

    # Mapa base escolhido (sem controle interno — seleção é externa)
    _tiles, _attr, _mz = BASE_MAPS.get(base_map, BASE_MAPS["🗺️ Mapa claro"])
    folium.TileLayer(_tiles, name=base_map, attr=_attr, max_zoom=_mz, control=False).add_to(m)

    # Sobreposição de rótulos (cidades/limites) — útil junto do satélite
    if show_labels:
        folium.TileLayer(_ESRI_LABELS, name="🏷️ Rótulos", attr="Esri",
                         overlay=True, control=False, show=True).add_to(m)

    # Bacias hidrográficas do PR (limites + nomes)
    if show_bacias:
        _bacias = load_bacias()
        if _bacias:
            gj_bacias, bacia_labels = _bacias
            fg_bacias = folium.FeatureGroup(name="🌊 Bacias hidrográficas", show=True, control=False)
            folium.GeoJson(
                gj_bacias, name="bacias_poly",
                style_function=lambda f: {"color": "#0c2d54", "weight": 2,
                                          "fillColor": "#1e5aa0", "fillOpacity": 0.05},
                highlight_function=lambda f: {"weight": 3, "fillOpacity": 0.18},
                tooltip=folium.GeoJsonTooltip(fields=["NOME"], aliases=["Bacia:"]),
            ).add_to(fg_bacias)
            for _n, _la, _lo in bacia_labels:
                folium.Marker(
                    [_la, _lo],
                    icon=folium.DivIcon(html=(
                        f'<div style="font-size:11px;font-weight:700;color:#0c2d54;'
                        f'text-shadow:0 0 3px #fff,0 0 3px #fff,0 0 3px #fff;white-space:nowrap">{_n}</div>')),
                ).add_to(fg_bacias)
            fg_bacias.add_to(m)

    # Camadas temáticas do GeoPR/IAT por WMS (streaming) — só as marcadas em wms_on.
    _wms_base = _config.get("geopr_wms_base", "")
    _on = set(wms_on or ())
    if _wms_base:
        for cam in _config.get("camadas_wms", []) or []:
            svc = cam.get("service")
            if not svc or svc not in _on:
                continue
            folium.raster_layers.WmsTileLayer(
                url=f"{_wms_base}/{svc}/MapServer/WMSServer",
                layers="0", name=cam.get("nome", svc),
                fmt="image/png", transparent=True, version="1.1.1",
                overlay=True, control=False, show=True,
                opacity=float(cam.get("opacidade", 0.7)),
                attr="GeoPR · IAT/PR",
            ).add_to(m)

    cluster = MarkerCluster(name="📍 Empreendimentos").add_to(m)
    for row in _records:
        cor = (cor_situacao(row.get("situacao"), _config) if cor_por == "Situação"
               else cor_tipologia(row.get("tipologia"), _config))
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=radius, color=cor, weight=2.4, opacity=0.95,
            fill=True, fill_color=cor, fill_opacity=fill_op,
            tooltip=f"{row.get('empreendimento', '?')} · {row.get('situacao', '?')}",
        ).add_to(cluster)
    return m


# ── Header ────────────────────────────────────────────────────────────────────
ASSETS = Path(__file__).parent / "assets"
LOGO_PATH = ASSETS / "logos_combinado.png"               # cartão branco → sidebar (fundo escuro)
LOGO_HEADER_PATH = ASSETS / "logos_combinado_header.png"  # mesclada → cabeçalho (fundo claro)


@st.cache_data(show_spinner=False)
def _logo_uri():
    p = LOGO_HEADER_PATH if LOGO_HEADER_PATH.exists() else LOGO_PATH
    if p.exists():
        return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()
    return ""

_dh = meta.get("data_hora_execucao", "")[:10] if meta else ""
dt = f"{_dh[8:10]}/{_dh[5:7]}/{_dh[0:4]}" if len(_dh) == 10 else "—"
fonte = meta.get("arquivo_lido", "—") if meta else "—"
_uri = _logo_uri()
logo_img = (f'<img src="{_uri}" alt="Instituto Água e Terra · Governo do Paraná" '
            f'style="height:46px;margin-bottom:8px"/><br>') if _uri else ""
st.markdown(f"""
<div class="app-header" style="border-bottom:none;margin-bottom:2px;padding-bottom:2px">
  <div>
    <div class="app-title">{dash_cfg.get('titulo', 'Central de Projetos Hidrelétricos do Estado do Paraná')}</div>
  </div>
  <div class="app-meta">
    {logo_img}
    <span class="badge">Atualizado: {dt}</span>
  </div>
</div>
<div style="text-align:center;border-bottom:3px solid #0c2d54;padding-bottom:12px;margin-bottom:8px;
            color:#64748b;font-size:13px;line-height:1.55">
  Painel desenvolvido por <b style="color:#0c2d54">Rafael Valgrande Augusto</b><br>
  Engenheiro Sanitarista e Ambiental · Instituto Água e Terra (IAT/PR) ·
  <a href="mailto:bol.rafaelaugusto@iat.pr.gov.br" target="_self" style="color:#1e5aa0;text-decoration:none;font-weight:600">bol.rafaelaugusto@iat.pr.gov.br</a>
</div>
""", unsafe_allow_html=True)

# ── Navegação ─────────────────────────────────────────────────────────────────
PAGINAS = [("🏠", "Visão Geral"), ("🗺️", "Mapa"), ("📅", "Licenças e Vencimentos"),
           ("🔎", "Qualidade dos Dados"), ("📊", "Relatório Analítico"), ("ℹ️", "Mais Informações")]
if "pagina" not in st.session_state:
    st.session_state["pagina"] = PAGINAS[0][1]

nav_cols = st.columns(len(PAGINAS))
for col, (ico, nome) in zip(nav_cols, PAGINAS):
    with col:
        is_active = st.session_state["pagina"] == nome
        if st.button(f"{ico}\n\n{nome}", key=f"nav_{nome}", use_container_width=True,
                     type="primary" if is_active else "secondary"):
            st.session_state["pagina"] = nome
            st.rerun()
pagina = st.session_state["pagina"]

if NO_DATA:
    st.error("⚠️ Nenhum dado em `data/processed/`. Rode o pipeline:\n\n```\npython src/run_pipeline.py\n```")
    st.stop()


# ── Sidebar — Filtros ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div style="text-align:center;color:#cbd9ea;font-size:11.5px;line-height:1.5;margin-bottom:12px">'
        'Painel desenvolvido por <b style="color:#ffffff">Rafael Valgrande Augusto</b><br>'
        'Engenheiro Sanitarista e Ambiental · Instituto Água e Terra (IAT/PR)<br>'
        '<a href="mailto:bol.rafaelaugusto@iat.pr.gov.br" target="_self" style="color:#93c5fd;text-decoration:none;font-weight:600">'
        'bol.rafaelaugusto@iat.pr.gov.br</a>'
        '</div>', unsafe_allow_html=True)
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), use_container_width=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    filtros_header = st.empty()  # preenchido depois com o contador de resultados
    _PH = "Selecione uma ou mais opções"
    f_tipologia = st.multiselect("Tipologia", opts("tipologia"), key="f_tipologia", placeholder=_PH)
    f_situacao = st.multiselect("Situação", opts("situacao"), key="f_situacao", placeholder=_PH)
    f_licenca = st.multiselect("Tipo de licença", opts("tipo_licenca"), key="f_licenca", placeholder=_PH)
    f_bacia = st.multiselect("Bacia hidrográfica", opts("bacia_hidrografica"), key="f_bacia", placeholder=_PH)
    f_tecnico = st.multiselect("Técnico responsável", opts("tecnico_responsavel"), key="f_tecnico", placeholder=_PH)
    f_municipio = st.multiselect("Município", opts("municipio")[:300], key="f_municipio", placeholder=_PH)
    anos = sorted(df_full["data_protocolo"].dropna().apply(
        lambda d: d.year if hasattr(d, "year") else None).dropna().unique().astype(int).tolist())
    f_ano = st.multiselect("Ano do protocolo", [str(a) for a in anos], key="f_ano", placeholder=_PH)
    f_alerta = st.multiselect("Validade da licença", opts("alerta_validade"), key="f_alerta", placeholder=_PH)
    f_precisao = st.multiselect("Precisão da coordenada", opts("precisao_coord"), key="f_precisao", placeholder=_PH)

# Aplicar filtros
df = apply_filters(df_full.copy(), {
    "tipologia": f_tipologia, "situacao": f_situacao, "tipo_licenca": f_licenca,
    "bacia_hidrografica": f_bacia, "tecnico_responsavel": f_tecnico, "alerta_validade": f_alerta,
    "precisao_coord": f_precisao,
})
if f_municipio:
    df = df[df["municipio"].fillna("").apply(lambda x: any(m in x for m in f_municipio))]
if f_ano:
    anos_int = [int(a) for a in f_ano]
    df = df[df["data_protocolo"].apply(lambda d: d.year if hasattr(d, "year") and d else None).isin(anos_int)]

n_filtrado, n_total = len(df), len(df_full)

# Cabeçalho dos filtros: título + contador e o botão "Limpar" lado a lado (compacto)
_cor_badge = "#1e5aa0" if n_filtrado == n_total else "#16a34a"
with filtros_header.container():
    st.markdown('<div style="font-size:16px;font-weight:700;color:#fff;margin:2px 0 2px 0">🔍 Filtros</div>',
                unsafe_allow_html=True)
    _hc1, _hc2 = st.columns([1.5, 1], vertical_alignment="center")
    with _hc1:
        st.markdown(
            f'<div style="font-size:10.5px;color:#cbd9ea;line-height:1.1;margin-bottom:3px">Projetos encontrados</div>'
            f'<span style="background:{_cor_badge};color:#fff;font-size:14px;font-weight:800;'
            f'padding:2px 11px;border-radius:11px;white-space:nowrap">{fmt_int(n_filtrado)} de {fmt_int(n_total)}</span>',
            unsafe_allow_html=True)
    with _hc2:
        if st.button("🔄 Limpar", key="limpar_filtros", use_container_width=True,
                     help="Limpar todos os filtros"):
            for _k in list(st.session_state.keys()):
                if _k.startswith("f_"):
                    del st.session_state[_k]
            st.rerun()

# Chips de filtros ativos
ativos = []
for nome, vals in [("Tipologia", f_tipologia), ("Situação", f_situacao), ("Licença", f_licenca),
                   ("Bacia", f_bacia), ("Técnico", f_tecnico), ("Município", f_municipio),
                   ("Ano", f_ano), ("Validade", f_alerta), ("Precisão", f_precisao)]:
    if vals:
        ativos.append(f'<span class="chip"><b>{nome}:</b> {", ".join(map(str, vals[:3]))}{"…" if len(vals) > 3 else ""}</span>')
if ativos:
    st.markdown(f'<div class="chips"><span class="chip" style="background:#0c2d54;color:#fff">'
                f'{fmt_int(n_filtrado)} de {fmt_int(n_total)} processos</span>{"".join(ativos)}</div>',
                unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA 1 — VISÃO GERAL
# ══════════════════════════════════════════════════════════════════════════════
if pagina == "Visão Geral":
    av = df["alerta_validade"] if "alerta_validade" in df.columns else pd.Series([], dtype=str)
    vencidas = int((av == "vencida").sum())
    a_vencer = int((av == "a_vencer").sum())
    vigentes = int((av == "vigente").sum())
    sem_coord = int((~df["tem_coordenada"]).sum()) if "tem_coordenada" in df.columns else 0
    em_analise = int((df["situacao"].fillna("").str.upper() == "EM ANALISE").sum()) if "situacao" in df.columns else 0
    linhas_f = set(df["linha_original"]) if "linha_original" in df.columns else set()
    criticos = int(df_errors[(df_errors["gravidade"] == "CRITICO") &
                  (df_errors["linha_original"].isin(linhas_f))]["linha_original"].nunique()) if not df_errors.empty else 0
    pot = fmt_int(df["potencia"].sum()) if "potencia" in df.columns else "—"

    if vencidas:
        st.markdown(f'<div class="alert-banner alert-red">🔴 <strong>{fmt_int(vencidas)} licenças vencidas</strong> no conjunto filtrado — veja "Licenças e Vencimentos".</div>', unsafe_allow_html=True)
    if a_vencer:
        st.markdown(f'<div class="alert-banner alert-yellow">⚠️ <strong>{fmt_int(a_vencer)} licenças</strong> vencem nos próximos 90 dias.</div>', unsafe_allow_html=True)

    section("Indicadores Principais")
    cards = [
        ("📋", "Total de Processos", fmt_int(n_filtrado), "no filtro atual", "blue"),
        ("🔬", "Em Análise", fmt_int(em_analise), "aguardando decisão", "yellow"),
        ("✅", "Licenças Vigentes", fmt_int(vigentes), "dentro da validade", "green"),
        ("🔴", "Licenças Vencidas", fmt_int(vencidas), "requer verificação", "red"),
        ("⏰", "A Vencer (90d)", fmt_int(a_vencer), "atenção próxima", "yellow"),
        ("⚠️", "Registros c/ Crítica", fmt_int(criticos), "empreend. com erro crítico", "red"),
        ("📍", "Sem Coordenada", fmt_int(sem_coord), "fora do mapa", "gray"),
        ("⚡", "Potência Total", pot, "MW · instalada", "purple"),
    ]
    for col, (ico, lbl, val, sub, color) in zip(st.columns(8), cards):
        col.markdown(kpi(ico, lbl, val, sub, color), unsafe_allow_html=True)

    section("Distribuição dos Processos")
    g1, g2, g3, g4 = st.columns(4)
    if "bacia_hidrografica" in df.columns:
        g1.plotly_chart(ranked_bar(df["bacia_hidrografica"], "Por Bacia Hidrográfica", "#0ea5e9"), use_container_width=True)
    if "tipologia" in df.columns:
        g2.plotly_chart(ranked_bar(df["tipologia"], "Por Tipologia",
                        color_fn=lambda c: cor_tipologia(c, config)), use_container_width=True)
    if "situacao" in df.columns:
        g3.plotly_chart(ranked_bar(df["situacao"], "Por Situação",
                        color_fn=lambda c: cor_situacao(c, config)), use_container_width=True)
    if "tipo_licenca" in df.columns:
        g4.plotly_chart(ranked_bar(df["tipo_licenca"], "Por Tipo de Licença", "#6366f1", top_n=12), use_container_width=True)

    section("Análises Complementares")
    h1, h2, h3, h4 = st.columns(4)
    if "data_protocolo" in df.columns:
        anos_s = df["data_protocolo"].dropna().apply(lambda d: d.year if hasattr(d, "year") else None).dropna()
        if not anos_s.empty:
            vc = anos_s.astype(int).value_counts().sort_index().reset_index()
            vc.columns = ["Ano", "Processos"]
            fig = px.area(vc, x="Ano", y="Processos", title="Protocolos por Ano", markers=True,
                          color_discrete_sequence=["#0c2d54"])
            fig.update_traces(fill="tozeroy", fillcolor="rgba(12,45,84,.12)", line_width=2)
            h1.plotly_chart(style_fig(fig, 300), use_container_width=True)
    if "potencia" in df.columns and "tipologia" in df.columns:
        pt = df.groupby("tipologia")["potencia"].sum().reset_index().sort_values("potencia")
        fig = px.bar(pt, x="potencia", y="tipologia", orientation="h", title="Potência por Tipologia (MW)",
                     text="potencia", color="tipologia",
                     color_discrete_map=config.get("cores_tipologia", {}))
        fig.update_traces(texttemplate="%{text:.0f}", textposition="outside", cliponaxis=False)
        h2.plotly_chart(style_fig(fig, 300).update_layout(yaxis_title="", xaxis_title=""), use_container_width=True)
    if "tecnico_responsavel" in df.columns:
        h3.plotly_chart(ranked_bar(df["tecnico_responsavel"], "Por Técnico Responsável", "#14b8a6", top_n=12), use_container_width=True)
    if "municipio" in df.columns:
        mun = df["municipio"].dropna().str.split(" / ").explode().str.strip()
        h4.plotly_chart(ranked_bar(mun, "Top Municípios", "#f97316", top_n=15), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA 2 — MAPA
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "Mapa":
    section("Mapa de Empreendimentos")
    c_cor, c_tr = st.columns([1.1, 2])
    with c_cor:
        cor_por = st.radio("Colorir pontos por:", ["Situação", "Tipologia"], horizontal=True)
    with c_tr:
        transp = st.slider("Transparência dos pontos (%) — aumente para ver a construção no satélite",
                           0, 95, 70, 5)
    fill_op = round((100 - transp) / 100, 2)
    df_map = df[df["tem_coordenada"] == True].copy()
    st.caption(f"Exibindo **{fmt_int(len(df_map))}** de {fmt_int(len(df))} processos com coordenada válida. "
               "**Clique num ponto** → os botões para abrir (🌐 Navegador · 📍 Maps · 🖥️ Earth · 🗺️ QGIS) aparecem no **painel à direita**. "
               "Escolha o **mapa base** e as **camadas** no painel abaixo, logo acima do mapa.")

    _cams = config.get("camadas_wms", []) or []
    records = df_map.to_dict("records")
    try:
        sig_hash = hash(tuple(sorted(int(x) for x in df_map["linha_original"].dropna())))
    except (TypeError, ValueError):
        sig_hash = len(df_map)
    signature = f"{len(df_map)}|{cor_por}|{sig_hash}"
    point_idx = build_point_index(df_map)

    # ── Controles de camadas — ENTRE a frase acima e o mapa (não sobre o mapa) ──
    # Um único controle por tipo: radio p/ mapa base, checkboxes p/ ligar camadas.
    def _cam_key(s):
        return "cam_" + "".join(ch if ch.isalnum() else "_" for ch in str(s))

    with st.container(border=True):
        base_map = st.radio("🗺️ Mapa base", list(BASE_MAPS.keys()),
                            horizontal=True, key="mapa_base")

        st.markdown("**Camadas temáticas do GeoPR/IAT** · _marque para ligar no mapa_")
        st.caption("Vêm por streaming do servidor do IAT — a 1ª vez pode levar alguns segundos "
                   "(depois ficam em cache).")
        wms_on = []
        _cb_cols = st.columns(2)
        for _i, _c in enumerate(_cams):
            with _cb_cols[_i % 2]:
                if st.checkbox(_c.get("nome", _c["service"]), key=_cam_key(_c["service"])):
                    wms_on.append(_c["service"])

        st.markdown("**Sobreposições de apoio**")
        _ov1, _ov2 = st.columns(2)
        show_labels = _ov1.checkbox("🏷️ Rótulos (cidades/limites)", key="ov_labels")
        show_bacias = _ov2.checkbox("🌊 Bacias hidrográficas", key="ov_bacias")

        # Legenda CONTEXTUAL: mostra as cores só das camadas temáticas ligadas (sem 2º menu).
        _ativas = [c for c in _cams if c["service"] in wms_on]
        with st.expander(f"🎨 Cores das camadas ligadas ({len(_ativas)})"):
            if not _ativas:
                st.caption("Marque uma camada temática acima para ver as cores aqui.")
            for _c in _ativas:
                st.markdown(f"**{_c.get('nome', _c['service'])}**")
                _leg = load_wms_legend(config.get("geopr_rest_base", ""), _c["service"])
                if not _leg:
                    st.caption("Legenda indisponível no momento (servidor GeoPR).")
                    continue
                _html = "".join(
                    '<div style="display:flex;align-items:center;gap:8px;margin:3px 0">'
                    f'<img src="data:image/png;base64,{_img}" style="height:18px;flex:0 0 auto"/>'
                    f'<span style="font-size:12px;color:#334155">{_lbl}</span></div>'
                    for _lbl, _img in _leg[:12])
                st.markdown(_html, unsafe_allow_html=True)
                if len(_leg) > 12:
                    st.caption(f"… +{len(_leg) - 12} classes")
    m = build_folium_map(records, signature, cor_por, config, base_map=base_map,
                         show_labels=show_labels, show_bacias=show_bacias,
                         wms_on=wms_on, fill_op=fill_op)

    map_col, detail_col = st.columns([7, 3])
    with map_col:
        map_data = st_folium(m, width=None, height=600, returned_objects=["last_object_clicked"], key="mapa_folium")

    # Persiste o ponto clicado em session_state para sobreviver aos reruns dos botões de abrir
    _clk = map_data.get("last_object_clicked") if map_data else None
    if _clk and _clk.get("lat") is not None:
        st.session_state["mapa_sel"] = _clk
    sel = st.session_state.get("mapa_sel")

    with detail_col:
        row = None
        if sel and sel.get("lat") is not None:
            row = point_idx.get((round(sel["lat"], 5), round(sel["lng"], 5)))
            if row is None:
                for (la, lo), r in point_idx.items():
                    if abs(la - sel["lat"]) < 1e-4 and abs(lo - sel["lng"]) < 1e-4:
                        row = r
                        break
        if row:
            cor = cor_situacao(row.get("situacao"), config)
            alerta = row.get("alerta_validade", "")
            badge = {"vencida": ("🔴 Vencida", "#ef4444"), "a_vencer": ("⏰ A vencer", "#f59e0b"),
                     "vigente": ("✅ Vigente", "#22c55e")}.get(alerta, ("", "#94a3b8"))

            def r_(k, v):
                v = "—" if v is None or str(v) in ("nan", "NaT", "None", "") else v
                return f'<div class="detail-row"><span class="k">{k}</span><span class="v">{v}</span></div>'

            alert_html = f'<span class="tag" style="background:{badge[1]}">{badge[0]}</span>' if badge[0] else ""
            # 1. Título (nome + situação)
            st.markdown(
                f'<div style="font-weight:700;color:#0c2d54;font-size:16px;line-height:1.2">{row.get("empreendimento", "—")}</div>'
                f'<div style="margin:4px 0 8px 0"><span class="tag" style="background:{cor}">{row.get("situacao", "—")}</span> {alert_html}</div>',
                unsafe_allow_html=True)
            # 2. Botões de abrir — ACIMA da caixa descritiva
            st.markdown("<div style='font-weight:600;font-size:12px;color:#334155'>Abrir este local em:</div>", unsafe_allow_html=True)
            open_buttons(row, "open")
            # 3. Caixa descritiva (sem repetir o nome)
            st.markdown(f"""
            <div class="detail-card" style="margin-top:10px">
              {r_("Protocolo", row.get('protocolo'))}
              {r_("Tipologia", row.get('tipologia'))}
              {r_("Tipo de Licença", row.get('tipo_licenca'))}
              {r_("Nº da Licença", row.get('numero_licenca'))}
              {r_("Potência", fmt_mw(row.get('potencia')))}
              {r_("Município", row.get('municipio'))}
              {r_("Rio", row.get('rio'))}
              {r_("Bacia", row.get('bacia_hidrografica'))}
              {r_("Empreendedor", row.get('empreendedor'))}
              {r_("Técnico", row.get('tecnico_responsavel'))}
              {r_("Protocolo em", fmt_data(row.get('data_protocolo')))}
              {r_("Emissão", fmt_data(row.get('data_emissao')))}
              {r_("Validade", fmt_data(row.get('data_validade')))}
              {r_("Precisão coord.", prec_label(row.get('precisao_coord'), row.get('n_decimais_coord')))}
              {r_("Fonte coord.", row.get('fonte_coord'))}
              {r_("Coordenada", f"{row.get('latitude'):.6f}, {row.get('longitude'):.6f}" if _ok(row.get('latitude')) else None)}
            </div>""", unsafe_allow_html=True)
        else:
            st.info("👆 Clique em um ponto para ver os detalhes e os botões de abrir aqui (🌐 Navegador · 📍 Maps · 🖥️ Earth · 🗺️ QGIS).")
            st.markdown("**Legenda**")
            itens = config.get("cores_situacao", {}) if cor_por == "Situação" else config.get("cores_tipologia", {})
            seen = set()
            for nome, c in itens.items():
                if nome == "DEFAULT" or c in seen:
                    continue
                seen.add(c)
                st.markdown(f'<div class="legend-item"><span class="legend-dot" style="background:{c}"></span>{nome}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA 3 — LICENÇAS E VENCIMENTOS
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "Licenças e Vencimentos":
    section("Situação das Licenças e Vencimentos")
    if "alerta_validade" not in df.columns:
        st.warning("Campo de validade não disponível na base.")
    else:
        v_venc = df[df["alerta_validade"] == "vencida"]
        v_av = df[df["alerta_validade"] == "a_vencer"]
        v_vig = df[df["alerta_validade"] == "vigente"]
        v_sem = df[df["alerta_validade"] == "sem_validade"]
        for col, (ico, lbl, d, color) in zip(st.columns(4), [
            ("🔴", "Licenças Vencidas", v_venc, "red"), ("⏰", "A Vencer (90 dias)", v_av, "yellow"),
            ("✅", "Vigentes", v_vig, "green"), ("➖", "Sem Data de Validade", v_sem, "gray")]):
            col.markdown(kpi(ico, lbl, fmt_int(len(d)), "", color), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        cols_lic = [c for c in ["protocolo", "empreendimento", "municipio", "tipologia", "tipo_licenca",
                                 "situacao", "data_validade", "tecnico_responsavel"] if c in df.columns]
        colcfg = {"data_validade": st.column_config.DateColumn("Validade", format="DD/MM/YYYY")}
        t1, t2, t3 = st.tabs([f"🔴 Vencidas ({len(v_venc)})", f"⏰ A Vencer ({len(v_av)})", "📈 Análise Temporal"])
        with t1:
            if not v_venc.empty:
                st.dataframe(v_venc[cols_lic].sort_values("data_validade"), use_container_width=True,
                             height=420, hide_index=True, column_config=colcfg)
            else:
                st.success("Nenhuma licença vencida no filtro.")
        with t2:
            if not v_av.empty:
                st.dataframe(v_av[cols_lic].sort_values("data_validade"), use_container_width=True,
                             height=420, hide_index=True, column_config=colcfg)
            else:
                st.success("Nenhuma licença a vencer em 90 dias.")
        with t3:
            c1, c2 = st.columns(2)
            dv = df[df["data_validade"].notna()].copy()
            if not dv.empty and "tipologia" in dv.columns:
                dv["ano"] = dv["data_validade"].apply(lambda d: d.year if hasattr(d, "year") else None)
                dv = dv.dropna(subset=["ano"])
                dv["ano"] = dv["ano"].astype(int)
                piv = dv.groupby(["ano", "tipologia"]).size().reset_index(name="total")
                fig = px.bar(piv, x="ano", y="total", color="tipologia", title="Vencimentos por Ano e Tipologia",
                             color_discrete_map=config.get("cores_tipologia", {}))
                c1.plotly_chart(style_fig(fig, 340, show_legend=True).update_layout(xaxis_title="Ano", yaxis_title=""), use_container_width=True)
            cross = df[df["alerta_validade"].isin(["vencida", "a_vencer"])]
            if not cross.empty and "tipo_licenca" in cross.columns:
                cg = cross.groupby(["tipo_licenca", "alerta_validade"]).size().reset_index(name="total")
                fig2 = px.bar(cg, x="tipo_licenca", y="total", color="alerta_validade", barmode="group",
                              title="Vencidas e A Vencer por Tipo de Licença",
                              color_discrete_map={"vencida": "#ef4444", "a_vencer": "#f59e0b"})
                c2.plotly_chart(style_fig(fig2, 340, show_legend=True).update_layout(xaxis_title="", yaxis_title=""), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA 4 — QUALIDADE DOS DADOS
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "Qualidade dos Dados":
    section("Painel de Qualidade dos Dados")
    st.caption("Ajuda a identificar registros que precisam de correção na planilha original.")
    if df_errors.empty:
        st.success("Nenhum erro de validação registrado.")
    else:
        crit = df_errors[df_errors["gravidade"] == "CRITICO"]
        med = df_errors[df_errors["gravidade"] == "MEDIO"]
        bax = df_errors[df_errors["gravidade"] == "BAIXO"]
        for col, (ico, lbl, d, sub, color) in zip(st.columns(4), [
            ("🔴", "Críticas", crit, "impedem uso", "red"),
            ("🟡", "Médias", med, "reduzem qualidade", "yellow"),
            ("⚪", "Baixas", bax, "impacto menor", "gray"),
            ("📊", "Registros Afetados", df_errors.drop_duplicates("linha_original"), "linhas únicas", "blue")]):
            col.markdown(kpi(ico, lbl, fmt_int(len(d)), sub, color), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns([1, 1])
        sev = df_errors["gravidade"].value_counts().reindex(["CRITICO", "MEDIO", "BAIXO"]).fillna(0).reset_index()
        sev.columns = ["Gravidade", "Total"]
        fig = px.bar(sev, x="Total", y="Gravidade", orientation="h", title="Inconsistências por Gravidade",
                     text="Total", color="Gravidade",
                     color_discrete_map={"CRITICO": "#ef4444", "MEDIO": "#f59e0b", "BAIXO": "#94a3b8"})
        fig.update_traces(textposition="outside", cliponaxis=False)
        c1.plotly_chart(style_fig(fig, 300).update_layout(yaxis_title="", xaxis_title=""), use_container_width=True)
        campos = df_errors["campo"].value_counts().head(10)
        c2.plotly_chart(ranked_bar(df_errors["campo"], "Campos com Mais Inconsistências", "#ef4444", top_n=10), use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)
        ct, mt, bt, at = st.tabs([f"🔴 Críticas ({len(crit)})", f"🟡 Médias ({len(med)})",
                                  f"⚪ Baixas ({len(bax)})", f"📋 Todas ({len(df_errors)})"])
        for tab, de in [(ct, crit), (mt, med), (bt, bax), (at, df_errors)]:
            with tab:
                if de.empty:
                    st.success("Nenhuma inconsistência nesta categoria.")
                else:
                    st.dataframe(de, use_container_width=True, height=380, hide_index=True)
                    st.download_button("⬇️ Exportar CSV", de.to_csv(index=False).encode("utf-8-sig"),
                                       "inconsistencias.csv", "text/csv", key=f"dl_{len(de)}_{de.iloc[0]['campo']}")

    # ── Precisão das coordenadas (apoio à conferência) ──
    section("Precisão das Coordenadas")
    st.caption("Apoia a conferência da precisão de cada ponto. Quanto mais casas decimais, melhor a localização.")
    n_alta = int((df_full.get("precisao_coord") == "alta").sum()) if "precisao_coord" in df_full.columns else 0
    n_media = int((df_full.get("precisao_coord") == "media").sum()) if "precisao_coord" in df_full.columns else 0
    n_baixa = int((df_full.get("precisao_coord") == "baixa").sum()) if "precisao_coord" in df_full.columns else 0
    n_compart = int(indicadores.get("coord_compartilhada", 0))
    n_grupos = int(indicadores.get("coord_compartilhada_grupos", 0))
    for col, (ico, lbl, val, sub, color) in zip(st.columns(4), [
        ("🎯", "Precisão Alta", n_alta, "≥4 casas (~10 m)", "green"),
        ("📏", "Precisão Média", n_media, "3 casas (~100 m)", "yellow"),
        ("⚠️", "Precisão Baixa", n_baixa, "≤2 casas (~1 km)", "red"),
        ("📌", "Coord. Repetida", n_compart, f"em {n_grupos} grupos", "purple")]):
        col.markdown(kpi(ico, lbl, fmt_int(val), sub, color), unsafe_allow_html=True)

    if "precisao_coord" in df_full.columns and (n_baixa or n_media or n_compart):
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**Pontos a conferir** (baixa/média precisão ou coordenada repetida entre empreendimentos):")
        rev = df_full[(df_full["precisao_coord"].isin(["baixa", "media"]))].copy()
        # marca os que compartilham coordenada
        coord_cnt = (df_full[df_full["tem_coordenada"] == True]
                     .groupby(["latitude", "longitude"])["empreendimento"].nunique())
        compart_keys = {k for k, v in coord_cnt.items() if v > 1}
        df_co = df_full[df_full.apply(
            lambda r: (r.get("latitude"), r.get("longitude")) in compart_keys if r.get("tem_coordenada") else False, axis=1)]
        rev = pd.concat([rev, df_co]).drop_duplicates("linha_original")
        cols_rev = [c for c in ["protocolo", "empreendimento", "municipio", "latitude", "longitude",
                                 "n_decimais_coord", "precisao_coord", "fonte_coord", "link_qgis"] if c in rev.columns]
        st.dataframe(rev[cols_rev].sort_values(["precisao_coord", "empreendimento"]),
                     use_container_width=True, height=320, hide_index=True,
                     column_config={
                         "n_decimais_coord": st.column_config.NumberColumn("Casas dec.", format="%d"),
                         "precisao_coord": st.column_config.TextColumn("Precisão"),
                         "link_qgis": st.column_config.LinkColumn("QGIS", display_text="🗺️ Abrir"),
                     })
        st.download_button("⬇️ Exportar pontos a conferir (CSV)",
                           rev[cols_rev].to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
                           "pontos_conferir_coordenadas.csv", "text/csv")

    section("Completude dos Campos (base completa)")
    campos_check = ["protocolo", "empreendimento", "empreendedor", "municipio", "rio", "bacia_hidrografica",
                    "tipologia", "tipo_licenca", "situacao", "tecnico_responsavel", "numero_licenca",
                    "data_protocolo", "data_validade", "potencia", "latitude"]
    comp = []
    for c in campos_check:
        if c in df_full.columns:
            preench = int(df_full[c].notna().sum())
            comp.append({"Campo": c, "% Preenchido": round(preench / len(df_full) * 100, 1)})
    if comp:
        dc = pd.DataFrame(comp).sort_values("% Preenchido")
        fig = px.bar(dc, x="% Preenchido", y="Campo", orientation="h", text="% Preenchido",
                     title="% de Preenchimento por Campo", color="% Preenchido",
                     color_continuous_scale=["#ef4444", "#f59e0b", "#22c55e"], range_color=[0, 100])
        fig.update_traces(texttemplate="%{text}%", textposition="outside", cliponaxis=False)
        st.plotly_chart(style_fig(fig, 420).update_layout(coloraxis_showscale=False, yaxis_title="", xaxis_title=""), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA 5 — RELATÓRIO ANALÍTICO
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "Relatório Analítico":
    section("Relatório Analítico — Tabela de Processos")
    busca = st.text_input("🔍 Buscar (protocolo, empreendimento, município, técnico…)", "")
    df_view = df
    if busca:
        mask = df.apply(lambda r: r.astype(str).str.contains(busca, case=False, na=False).any(), axis=1)
        df_view = df[mask]
    st.caption(f"**{fmt_int(len(df_view))}** registros exibidos")

    cols_tab = [c for c in ["protocolo", "empreendimento", "empreendedor", "municipio", "rio",
                "bacia_hidrografica", "tipologia", "potencia", "tipo_licenca", "situacao",
                "tecnico_responsavel", "numero_licenca", "data_protocolo", "data_emissao",
                "data_validade", "alerta_validade",
                "link_google_earth", "link_gearth", "link_qgis"] if c in df_view.columns]
    colcfg = {
        "protocolo": st.column_config.TextColumn("Protocolo"),
        "empreendimento": st.column_config.TextColumn("Empreendimento"),
        "empreendedor": st.column_config.TextColumn("Empreendedor"),
        "municipio": st.column_config.TextColumn("Município"),
        "rio": st.column_config.TextColumn("Rio"),
        "bacia_hidrografica": st.column_config.TextColumn("Bacia hidrográfica"),
        "tipologia": st.column_config.TextColumn("Tipologia"),
        "tipo_licenca": st.column_config.TextColumn("Tipo de licença"),
        "situacao": st.column_config.TextColumn("Situação"),
        "tecnico_responsavel": st.column_config.TextColumn("Técnico responsável"),
        "numero_licenca": st.column_config.TextColumn("Nº da licença"),
        "potencia": st.column_config.NumberColumn("Potência (MW)", format="%.1f"),
        "data_protocolo": st.column_config.DateColumn("Protocolo", format="DD/MM/YYYY"),
        "data_emissao": st.column_config.DateColumn("Emissão", format="DD/MM/YYYY"),
        "data_validade": st.column_config.DateColumn("Validade", format="DD/MM/YYYY"),
        "alerta_validade": st.column_config.TextColumn("Alerta"),
        "link_google_earth": st.column_config.LinkColumn("Abrir no navegador", display_text="🌐 Abrir"),
        "link_gearth": st.column_config.LinkColumn("Google Earth desktop", display_text="🖥️ Abrir"),
        "link_qgis": st.column_config.LinkColumn("Abrir no QGIS", display_text="🗺️ Abrir"),
    }
    st.caption("Dica: **selecione uma linha** (caixa à esquerda) para abrir o empreendimento nos botões abaixo.")
    ev = st.dataframe(df_view[cols_tab], use_container_width=True, height=520, hide_index=True,
                      column_config=colcfg, on_select="rerun", selection_mode="single-row", key="tab_rel")

    sel_rows = []
    try:
        sel_rows = ev.selection.rows
    except AttributeError:
        sel_rows = (ev or {}).get("selection", {}).get("rows", [])
    if sel_rows:
        srow = df_view.iloc[sel_rows[0]].to_dict()
        nome = srow.get("empreendimento", "—")
        if srow.get("tem_coordenada"):
            st.markdown(f"**Abrir _{nome}_ em:**")
            open_buttons(srow, "rel")
        else:
            st.info(f"_{nome}_ não tem coordenada válida — não é possível abrir no mapa.")

    e1, e2, _ = st.columns([1, 1, 4])
    e1.download_button("⬇️ Exportar CSV", df_view[cols_tab].to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
                       "processos_filtrados.csv", "text/csv")
    if meta:
        e2.download_button("⬇️ Metadados JSON", json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"),
                           "metadados_execucao.json", "application/json")


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA 6 — MAIS INFORMAÇÕES
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "Mais Informações":
    section("Mais Informações")

    st.markdown(f"""
    <div style="background:#fff;border-radius:12px;padding:22px 26px;box-shadow:0 1px 3px rgba(15,23,42,.08);
                border-top:4px solid #0c2d54;max-width:780px">
      <div style="font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:.6px;font-weight:600">Contato</div>
      <h3 style="margin:6px 0 2px 0;color:#0c2d54;font-size:22px">Rafael Valgrande Augusto</h3>
      <div style="color:#475569;font-size:14px;margin-bottom:16px">Engenheiro Sanitarista e Ambiental — Instituto Água e Terra (IAT/PR)</div>
      <div style="font-size:14px;color:#334155;margin-bottom:14px">
        Tem <b>dúvidas, sugestões</b> ou ideias de melhoria para o painel? Fale com o <b>Eng. Rafa</b>:
      </div>
      <a href="mailto:bol.rafaelaugusto@iat.pr.gov.br?subject=Painel%20Hidrel%C3%A9tricas%20IAT" target="_self"
         style="display:inline-block;background:#0c2d54;color:#fff;padding:11px 20px;border-radius:8px;
                text-decoration:none;font-weight:600;font-size:14px;margin:4px 6px 4px 0">✉️ bol.rafaelaugusto@iat.pr.gov.br</a>
      <a href="https://www.iat.pr.gov.br" target="_blank" rel="noopener"
         style="display:inline-block;background:#fff;color:#0c2d54;border:1.5px solid #0c2d54;padding:10px 18px;
                border-radius:8px;text-decoration:none;font-weight:600;font-size:14px;margin:4px 0">🌐 www.iat.pr.gov.br</a>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### 📌 Sobre o painel")
        st.markdown(
            f"""
- **O que é:** acompanhamento dos processos de licenciamento ambiental de empreendimentos
  hidrelétricos (CGH, MGH, PCH, UHE, MCH) no Paraná.
- **Total de registros:** {fmt_int(indicadores.get('total_registros', len(df_full)))}
- **Última atualização:** {dt}
- **Fonte dos dados:** {fonte}
- A base é gerada automaticamente a partir da planilha oficial; registros sem coordenada
  permanecem na base e são destacados no painel de **Qualidade dos Dados**.
""")
    with col_b:
        st.markdown("#### 🧭 Como usar")
        st.markdown(
            """
Os **filtros** (barra lateral) valem para **todo o painel** — mapa, gráficos e tabela reagem juntos.
Troque de seção pelas **abas** no topo; **🔄 Limpar** (ao lado do contador, no topo da barra lateral) zera os filtros.

- **Mapa:** **clique num ponto** → detalhes + botões para abrir o local: **🌐 Google Earth Web** e **📍 Maps**
  (abrem no navegador) e **🖥️ Google Earth Desktop / 🗺️ QGIS** (baixam um arquivo `.kml`/`.qgs` que abre o
  programa **no seu computador**, se instalado). Troque para **🛰️ Satélite** e ajuste a **transparência**.
- **Licenças e Vencimentos:** o que está **vencido** e **a vencer** (90 dias).
- **Qualidade dos Dados:** o que **corrigir na planilha** (por gravidade) e a **precisão** das coordenadas.
- **Relatório Analítico:** **busque**, **selecione uma linha** para abrir o ponto e **exporte** (CSV/JSON).
""")


# ── Rodapé (autoria) — aparece em todas as páginas ────────────────────────────
st.markdown(
    '<div style="margin-top:30px;padding:14px 0 4px 0;border-top:1px solid #e2e8f0;text-align:center;'
    'color:#64748b;font-size:12.5px;line-height:1.6">'
    'Painel desenvolvido por <span style="color:#0c2d54;font-weight:700">Rafael Valgrande Augusto</span>'
    '<br>Engenheiro Sanitarista e Ambiental · Instituto Água e Terra (IAT/PR) · '
    '<a href="mailto:bol.rafaelaugusto@iat.pr.gov.br" target="_self" style="color:#1e5aa0;text-decoration:none;font-weight:600">'
    'bol.rafaelaugusto@iat.pr.gov.br</a></div>',
    unsafe_allow_html=True)
