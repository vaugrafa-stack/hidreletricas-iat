"""
Script de teste — simula um KML corrigido com alguns pontos modificados
para validar o passo 02_importar_corrigido.py sem revisão manual.

Uso (somente para testes):
  py src/geo_review/teste_importacao.py
"""
import sys
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, indent, tostring

sys.path.insert(0, str(Path(__file__).parent.parent))
from extract_excel import extract, load_config
from geo_review.geo_utils import safe_float

PROCESSED_DIR = Path("data/processed")
KML_SAIDA = PROCESSED_DIR / "pontos_corrigido_tecnico.kml"


def main():
    config = load_config("config.yaml")
    df_raw, _, _ = extract(config)
    col_map = config.get("column_mapping", {})
    rename = {k: v for k, v in col_map.items() if k in df_raw.columns}
    df = df_raw.rename(columns=rename)

    kml = Element("kml", xmlns="http://www.opengis.net/kml/2.2")
    doc = SubElement(kml, "Document")
    SubElement(doc, "name").text = "KML Teste — Corrigido"

    count = 0
    for _, row in df.iterrows():
        protocolo = str(row.get("protocolo", "")).strip()
        empreend = str(row.get("empreendimento", "")).strip() or "Sem nome"
        lat = safe_float(row.get("latitude"))
        lon = safe_float(row.get("longitude"))
        lat_cf = safe_float(row.get("lat_casa_forca"))
        lon_cf = safe_float(row.get("lon_casa_forca"))

        if not protocolo or lat is None or lon is None:
            continue

        # Placemark barragem — mantém coordenada original (simula validado)
        pm = SubElement(doc, "Placemark")
        SubElement(pm, "name").text = f"[BARR] {protocolo} — {empreend}"
        pt = SubElement(pm, "Point")
        SubElement(pt, "coordinates").text = f"{lon:.6f},{lat:.6f},0"

        # Se tem casa de força, adiciona também
        if lat_cf is not None and lon_cf is not None:
            pm2 = SubElement(doc, "Placemark")
            SubElement(pm2, "name").text = f"[CF] {protocolo} — {empreend}"
            pt2 = SubElement(pm2, "Point")
            SubElement(pt2, "coordinates").text = f"{lon_cf:.6f},{lat_cf:.6f},0"

        count += 1

    indent(kml, space="  ")
    kml_bytes = b'<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(kml, encoding="unicode").encode("utf-8")
    KML_SAIDA.write_bytes(kml_bytes)
    print(f"KML de teste gerado: {KML_SAIDA} ({count} protocolos)")


if __name__ == "__main__":
    main()
