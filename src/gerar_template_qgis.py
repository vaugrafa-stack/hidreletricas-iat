"""Roda DENTRO do QGIS (Console Python) para gerar um template .qgs válido,
escrito pelo próprio QGIS (garante satélite renderizando + zoom no ponto).
Depois o app substitui o <extent> e o nome por ponto."""
from qgis.core import (QgsRasterLayer, QgsProject, QgsCoordinateReferenceSystem,
                       QgsPointXY, QgsCoordinateTransform, QgsRectangle)
from qgis.utils import iface

LAT, LON, D = -25.4284, -49.2733, 600.0  # Curitiba (amostra)
proj = QgsProject.instance()
proj.clear()
crs = QgsCoordinateReferenceSystem("EPSG:3857")
proj.setCrs(crs)
uri = ("type=xyz&url=https://server.arcgisonline.com/ArcGIS/rest/services/"
       "World_Imagery/MapServer/tile/%7Bz%7D/%7By%7D/%7Bx%7D&zmax=19&zmin=0")
sat = QgsRasterLayer(uri, "Satelite (Esri)", "wms")
proj.addMapLayer(sat)
canvas = iface.mapCanvas()
canvas.setDestinationCrs(crs)
ct = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:4326"), crs, proj)
p = ct.transform(QgsPointXY(LON, LAT))
canvas.setExtent(QgsRectangle(p.x() - D, p.y() - D, p.x() + D, p.y() + D))
canvas.refresh()
out = r"C:\Users\rafae\Downloads\IAT\Dashboard\data\template_qgis.qgs"
proj.write(out)
print("TEMPLATE_SAVED:", out)
