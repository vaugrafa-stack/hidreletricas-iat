"""Executado DENTRO do QGIS (via `qgis-bin --code`).

Lê lat/lon do arquivo temporário, adiciona um mapa base de SATÉLITE (Esri) e um
marcador no empreendimento, e dá zoom no ponto. O zoom é reaplicado com QTimer
porque o QGIS, ao terminar de carregar, sobrescreve o zoom inicial.
Erros em %TEMP%\\qgis_open_handler.log.
"""
import os
import traceback

_LOG = os.path.join(os.environ.get("TEMP", os.path.expanduser("~")), "qgis_open_handler.log")


def _log(msg):
    try:
        with open(_LOG, "a", encoding="utf-8") as f:
            f.write(str(msg) + "\n")
    except OSError:
        pass


try:
    from qgis.core import (QgsRasterLayer, QgsVectorLayer, QgsProject, QgsPointXY,
                           QgsCoordinateReferenceSystem, QgsCoordinateTransform,
                           QgsRectangle, QgsFeature, QgsGeometry)
    from qgis.PyQt.QtCore import QTimer
    from qgis.PyQt.QtGui import QColor
    from qgis.utils import iface

    tmp = os.path.join(os.environ.get("TEMP", os.path.expanduser("~")), "qgis_open_latlon.txt")
    with open(tmp, encoding="utf-8") as f:
        parts = f.read().strip().split("|")
    lat, lon = float(parts[0]), float(parts[1])
    nome = parts[3] if len(parts) > 3 and parts[3].strip() else "Empreendimento"

    proj = QgsProject.instance()

    # Mapa base de SATÉLITE (Esri World Imagery — imagem real, sem token)
    sat_uri = ("type=xyz&url=https://server.arcgisonline.com/ArcGIS/rest/services/"
               "World_Imagery/MapServer/tile/%7Bz%7D/%7By%7D/%7Bx%7D&zmax=19&zmin=0")
    sat = QgsRasterLayer(sat_uri, "Satélite (Esri)", "wms")
    if sat.isValid():
        proj.addMapLayer(sat)
    else:
        _log("Satélite Esri inválido; tentando OSM")
        osm = QgsRasterLayer("type=xyz&url=https://tile.openstreetmap.org/"
                             "%7Bz%7D/%7Bx%7D/%7By%7D.png&zmax=19&zmin=0", "OpenStreetMap", "wms")
        if osm.isValid():
            proj.addMapLayer(osm)

    # Marcador vermelho no empreendimento (camada nomeada com o empreendimento)
    vl = QgsVectorLayer("Point?crs=EPSG:4326&field=nome:string(160)", nome, "memory")
    feat = QgsFeature(vl.fields())
    feat["nome"] = nome
    feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lon, lat)))
    vl.dataProvider().addFeatures([feat])
    vl.updateExtents()
    try:
        sym = vl.renderer().symbol()
        sym.setColor(QColor(231, 76, 60))
        sym.setSize(4.5)
    except Exception:
        pass
    # Rótulo com o nome do empreendimento (branco com contorno preto p/ ler no satélite)
    try:
        from qgis.core import (QgsPalLayerSettings, QgsTextFormat,
                               QgsTextBufferSettings, QgsVectorLayerSimpleLabeling)
        pal = QgsPalLayerSettings()
        pal.fieldName = "nome"
        fmt = QgsTextFormat()
        fmt.setSize(11)
        fmt.setColor(QColor(255, 255, 255))
        buf = QgsTextBufferSettings()
        buf.setEnabled(True)
        buf.setSize(1.2)
        buf.setColor(QColor(0, 0, 0))
        fmt.setBuffer(buf)
        pal.setFormat(fmt)
        vl.setLabeling(QgsVectorLayerSimpleLabeling(pal))
        vl.setLabelsEnabled(True)
    except Exception as _e:
        _log("rótulo falhou: " + str(_e))
    proj.addMapLayer(vl)

    # Centralizar/zoom no ponto (projeto em Web Mercator por causa do basemap)
    canvas = iface.mapCanvas()
    crs3857 = QgsCoordinateReferenceSystem("EPSG:3857")
    canvas.setDestinationCrs(crs3857)
    ct = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:4326"), crs3857, proj)
    p = ct.transform(QgsPointXY(lon, lat))
    d = 400.0  # meia-largura da janela em metros (~zoom bem próximo)

    def _zoom():
        try:
            canvas.setCenter(p)
            canvas.setExtent(QgsRectangle(p.x() - d, p.y() - d, p.x() + d, p.y() + d))
            canvas.refresh()
        except Exception as _e:
            _log("zoom falhou: " + str(_e))

    _zoom()
    # Reaplica depois que o QGIS termina de carregar (senão sobrescreve o zoom)
    QTimer.singleShot(1500, _zoom)
    QTimer.singleShot(3500, _zoom)
    _log(f"OK -> centralizado em {lat},{lon}")
except Exception:
    _log(traceback.format_exc())
