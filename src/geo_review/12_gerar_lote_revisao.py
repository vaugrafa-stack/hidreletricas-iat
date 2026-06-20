"""
Gera o próximo LOTE de revisão a partir do rastreador.

Seleciona os próximos N empreendimentos NÃO revisados, por prioridade
(licenciados primeiro; UHE/PCH antes; maior potência antes) e produz:
  - data/processed/lote_atual.csv  -> lista para revisar (com strings de busca)
  - data/processed/lote_atual.kml  -> barragem (amarelo) + casa de força (verde)

Uso:  py src/geo_review/12_gerar_lote_revisao.py [N]
"""
import os, sys
import pandas as pd
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(__file__))
from geo_utils import safe_float

RASTREADOR = "data/processed/conferencia_rastreador.csv"
LOTE_CSV = "data/processed/lote_atual.csv"
LOTE_KML = "data/processed/lote_atual.kml"

FASE_RANK = {
    "Licenciado (verificar operação/instalação)": 0,
    "Fase prévia (pode não estar construído)": 1,
    "Licenciamento federal (IBAMA)": 2,
    "Não licenciado (provavelmente sem obra)": 3,
    "Indefinido": 4,
}
TIPO_RANK = {"UHE": 0, "PCH": 1, "MGH": 2, "MCH": 3, "CGH": 4}


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    rast = pd.read_csv(RASTREADOR, encoding="utf-8-sig", dtype=str).fillna("")

    pend = rast[rast["revisado"].str.lower() != "sim"].copy()
    pend["_fr"] = pend["fase_provavel"].map(lambda x: FASE_RANK.get(x, 9))
    pend["_tr"] = pend["tipo"].map(lambda x: TIPO_RANK.get(str(x).strip().upper(), 9))
    pend["_pot"] = pend["potencia_mw"].map(lambda x: safe_float(x) or 0.0)
    pend = pend.sort_values(["_fr", "_tr", "_pot"], ascending=[True, True, False])

    # DEDUPLICAÇÃO: 1 representante por localização física única.
    # Mantém o registro de maior prioridade de cada chave_local.
    pend = pend.drop_duplicates(subset=["chave_local"], keep="first")

    lote = pend.head(n).copy()

    # strings de busca p/ colar na caixa do Google Earth
    def busca(la, lo):
        la, lo = safe_float(la), safe_float(lo)
        return f"{la:.6f},{lo:.6f}" if la is not None and lo is not None else ""
    lote["busca_barragem"] = [busca(r.nav_lat_barragem, r.nav_lon_barragem)
                              for r in lote.itertuples()]
    lote["busca_casaforca"] = [busca(r.nav_lat_casaforca, r.nav_lon_casaforca)
                               for r in lote.itertuples()]

    cols = ["id_emp", "chave_local", "codigo", "protocolo", "empreendimento", "tipo",
            "situacao", "fase_provavel", "potencia_mw", "rio", "municipio",
            "busca_barragem", "busca_casaforca"]
    lote[cols].to_csv(LOTE_CSV, index=False, encoding="utf-8-sig")

    # KML
    ns = "http://www.opengis.net/kml/2.2"
    kml = ET.Element("kml", xmlns=ns)
    doc = ET.SubElement(kml, "Document")
    ET.SubElement(doc, "name").text = "Lote de revisão — Hidrelétricas IAT"

    def estilo(id_, cor):
        st = ET.SubElement(doc, "Style", id=id_)
        ic = ET.SubElement(st, "IconStyle")
        ET.SubElement(ic, "color").text = cor
        icon = ET.SubElement(ic, "Icon")
        ET.SubElement(icon, "href").text = \
            "http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png"
    estilo("barragem", "ff00ffff")    # amarelo
    estilo("casaforca", "ff00ff00")   # verde

    for r in lote.itertuples():
        nome = f"{r.id_emp} · {r.empreendimento} ({r.tipo})"
        lab = safe_float(r.nav_lat_barragem); lob = safe_float(r.nav_lon_barragem)
        lac = safe_float(r.nav_lat_casaforca); loc = safe_float(r.nav_lon_casaforca)
        if lab is not None:
            pm = ET.SubElement(doc, "Placemark")
            ET.SubElement(pm, "name").text = f"{nome} — BARRAGEM"
            ET.SubElement(pm, "styleUrl").text = "#barragem"
            ET.SubElement(pm, "description").text = \
                f"Rio: {r.rio} | Situação: {r.situacao} | {r.fase_provavel}"
            p = ET.SubElement(pm, "Point")
            ET.SubElement(p, "coordinates").text = f"{lob:.6f},{lab:.6f},0"
        if lac is not None:
            pm = ET.SubElement(doc, "Placemark")
            ET.SubElement(pm, "name").text = f"{nome} — CASA DE FORÇA"
            ET.SubElement(pm, "styleUrl").text = "#casaforca"
            p = ET.SubElement(pm, "Point")
            ET.SubElement(p, "coordinates").text = f"{loc:.6f},{lac:.6f},0"
        # linha conectando, se ambos
        if lab is not None and lac is not None:
            pm = ET.SubElement(doc, "Placemark")
            ET.SubElement(pm, "name").text = f"{nome} — conexão"
            ls = ET.SubElement(pm, "LineString")
            ET.SubElement(ls, "coordinates").text = \
                f"{lob:.6f},{lab:.6f},0 {loc:.6f},{lac:.6f},0"

    ET.ElementTree(kml).write(LOTE_KML, encoding="utf-8", xml_declaration=True)

    print(f"Lote gerado: {len(lote)} empreendimentos")
    print(f"  CSV: {LOTE_CSV}")
    print(f"  KML: {LOTE_KML}")
    print("\n--- LOTE ATUAL ---")
    for r in lote.itertuples():
        print(f"  #{r.id_emp:<4} {r.tipo:<3} {str(r.empreendimento)[:38]:<38} "
              f"bar={r.busca_barragem or '—':<22} cf={r.busca_casaforca or '—'}")


if __name__ == "__main__":
    main()
