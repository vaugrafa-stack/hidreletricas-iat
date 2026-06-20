"""Gera KML técnico com resultados da revisão visual de pendentes_geo.csv."""
import pandas as pd
import xml.etree.ElementTree as ET
import zipfile, os
from xml.dom import minidom

df = pd.read_csv("data/processed/pendentes_geo.csv", encoding="utf-8-sig")

# Paleta de cores por status (formato KML: aabbggrr)
CORES = {
    "Validado":             "ff00aa00",   # verde
    "Corrigido":            "ff00aaff",   # amarelo
    "Pendente de validação":"ff0077ff",   # laranja
    "Sem imagem suficiente":"ff0000ff",   # vermelho
    "Não identificado":     "ffaaaaaa",   # cinza
}

def kml_placemark(pm_parent, row):
    lat = row.get("latitude_barragem_original")
    lon = row.get("longitude_barragem_original")
    if pd.isna(lat) or pd.isna(lon):
        return

    status = row.get("status_georreferenciamento", "")
    cor = CORES.get(status, "ffaaaaaa")
    nome = f"{row['protocolo']} — {row['empreendimento']}"
    desc = (
        f"Tipologia: {row.get('tipologia','')}\n"
        f"Município: {row.get('municipio','')}\n"
        f"Rio: {row.get('rio','')}\n"
        f"Status: {status}\n"
        f"Confiança: {row.get('grau_confianca','')}\n"
        f"Obs: {row.get('observacao_geoespacial','')}"
    )

    pm = ET.SubElement(pm_parent, "Placemark")
    ET.SubElement(pm, "name").text = nome
    ET.SubElement(pm, "description").text = desc
    style = ET.SubElement(pm, "Style")
    icon_style = ET.SubElement(style, "IconStyle")
    ET.SubElement(icon_style, "color").text = cor
    ET.SubElement(icon_style, "scale").text = "1.0"
    icon = ET.SubElement(icon_style, "Icon")
    ET.SubElement(icon, "href").text = "http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png"
    pt = ET.SubElement(pm, "Point")
    ET.SubElement(pt, "coordinates").text = f"{float(lon):.6f},{float(lat):.6f},0"


root = ET.Element("kml", xmlns="http://www.opengis.net/kml/2.2")
doc = ET.SubElement(root, "Document")
ET.SubElement(doc, "name").text = "Revisão Geoespacial — Hidrelétricas IAT"

folders = {}
for status in CORES:
    f = ET.SubElement(doc, "Folder")
    ET.SubElement(f, "name").text = status
    folders[status] = f

f_sem_coord = ET.SubElement(doc, "Folder")
ET.SubElement(f_sem_coord, "name").text = "Sem coordenadas"

for _, row in df.iterrows():
    lat = row.get("latitude_barragem_original")
    lon = row.get("longitude_barragem_original")
    if pd.isna(lat) or pd.isna(lon):
        kml_placemark(f_sem_coord, row)
        continue
    status = row.get("status_georreferenciamento", "")
    folder = folders.get(status, f_sem_coord)
    kml_placemark(folder, row)

# Serializar
tree = ET.ElementTree(root)
kml_path = "data/processed/pontos_corrigido_tecnico.kml"
tree.write(kml_path, encoding="utf-8", xml_declaration=True)

# KMZ
kmz_path = kml_path.replace(".kml", ".kmz")
with zipfile.ZipFile(kmz_path, "w", zipfile.ZIP_DEFLATED) as z:
    z.write(kml_path, "doc.kml")

# Contagens
total = len(df)
com_coord = df[df["latitude_barragem_original"].notna()].shape[0]
print(f"KML: {kml_path}")
print(f"KMZ: {kmz_path}")
print(f"Total registros: {total} | Com coordenadas: {com_coord} | Sem: {total - com_coord}")
print("\nDistribuição:")
print(df["status_georreferenciamento"].value_counts().to_string())
