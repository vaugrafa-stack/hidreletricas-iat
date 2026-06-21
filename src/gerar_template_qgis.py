"""Roda DENTRO do QGIS (Console Python) para gerar um template de projeto VÁLIDO
(escrito pelo próprio QGIS) com: satélite Esri + ponto (marcador vermelho + rótulo
com o nome) + zoom no ponto. Salva template_marker.qgs + ponto.geojson em data/.

Depois, o app empacota .qgs (extent parametrizado) + ponto.geojson (coord/nome
parametrizados) num .qgz que abre no QGIS já com o marcador e o nome.

Como rodar: QGIS -> Complementos -> Console Python ->
    exec(open(r'C:\\Users\\rafae\\Downloads\\IAT\\Dashboard\\src\\gerar_template_qgis.py').read())
"""
import os
import json
from qgis.core import (QgsRasterLayer, QgsVectorLayer, QgsProject, QgsPointXY,
                       QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsRectangle,
                       QgsPalLayerSettings, QgsTextFormat, QgsTextBufferSettings,
                       QgsVectorLayerSimpleLabeling)
from qgis.PyQt.QtGui import QColor
from qgis.utils import iface

LAT, LON, NOME, D = -25.4284, -49.2733, "PONTO_NOME_PLACEHOLDER", 600.0
base = r"C:\Users\rafae\Downloads\IAT\Dashboard\data"

# GeoJSON INLINE como datasource → projeto .qgs autossuficiente (sem arquivo externo)
gjs = ('{"type":"FeatureCollection","features":[{"type":"Feature",'
       '"properties":{"nome":"%s"},"geometry":{"type":"Point","coordinates":[%s,%s]}}]}'
       % (NOME, LON, LAT))

proj = QgsProject.instance()
proj.clear()
crs = QgsCoordinateReferenceSystem("EPSG:3857")
proj.setCrs(crs)

sat = QgsRasterLayer("type=xyz&url=https://server.arcgisonline.com/ArcGIS/rest/services/"
                     "World_Imagery/MapServer/tile/%7Bz%7D/%7By%7D/%7Bx%7D&zmax=19&zmin=0",
                     "Satelite (Esri)", "wms")
proj.addMapLayer(sat)

vl = QgsVectorLayer(gjs, "Empreendimento", "ogr")
try:
    sym = vl.renderer().symbol()
    sym.setColor(QColor(231, 76, 60))
    sym.setSize(4.5)
except Exception as e:
    print("symbol:", e)
pal = QgsPalLayerSettings()
pal.fieldName = "nome"
fmt = QgsTextFormat()
fmt.setSize(12)
fmt.setColor(QColor(255, 255, 255))
buf = QgsTextBufferSettings()
buf.setEnabled(True)
buf.setSize(1.4)
buf.setColor(QColor(0, 0, 0))
fmt.setBuffer(buf)
pal.setFormat(fmt)
vl.setLabeling(QgsVectorLayerSimpleLabeling(pal))
vl.setLabelsEnabled(True)
proj.addMapLayer(vl)

canvas = iface.mapCanvas()
canvas.setDestinationCrs(crs)
ct = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:4326"), crs, proj)
p = ct.transform(QgsPointXY(LON, LAT))
canvas.setExtent(QgsRectangle(p.x() - D, p.y() - D, p.x() + D, p.y() + D))
canvas.refresh()

out = os.path.join(base, "template_inline.qgs")
proj.write(out)
print("SAVED:", out)
