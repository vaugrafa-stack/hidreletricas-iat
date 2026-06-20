"""Handler do protocolo gearth:// — abre o Google Earth Pro (desktop) no ponto.

Invocado pelo Windows ao clicar num link `gearth://lat,lon` (registrado por
instalar_handler.bat). Gera um KML temporário com um LookAt na coordenada e
lança o Google Earth Pro, que "voa" até o empreendimento.

Aceita `gearth://-24.28,-49.69` (ponto) e a forma com vírgula decimal do
Excel pt-BR `gearth://-24,28,-49,69`.
"""
import sys
import os
import glob
import subprocess
import tempfile
import urllib.parse
from xml.sax.saxutils import escape as _xesc

_KML = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{nome}</name>
    <LookAt>
      <longitude>{lon}</longitude>
      <latitude>{lat}</latitude>
      <altitude>0</altitude>
      <range>2500</range>
      <tilt>0</tilt>
      <heading>0</heading>
      <altitudeMode>relativeToGround</altitudeMode>
    </LookAt>
    <Placemark>
      <name>{nome}</name>
      <description>Lat {lat}, Lon {lon}</description>
      <Style><IconStyle><scale>1.2</scale></IconStyle>
        <LabelStyle><scale>1.0</scale></LabelStyle></Style>
      <Point><coordinates>{lon},{lat},0</coordinates></Point>
    </Placemark>
  </Document>
</kml>
"""


def find_google_earth() -> str | None:
    cands = [
        r"C:\Program Files\Google\Google Earth Pro\client\googleearth.exe",
        r"C:\Program Files (x86)\Google\Google Earth Pro\client\googleearth.exe",
        r"C:\Program Files\Google\Google Earth\client\googleearth.exe",
    ]
    for c in cands:
        if os.path.exists(c):
            return c
    for pat in [r"C:\Program Files*\Google\Google Earth*\client\googleearth.exe"]:
        m = sorted(glob.glob(pat))
        if m:
            return m[-1]
    return None


def parse_latlon(uri: str):
    raw = uri
    if raw.lower().startswith("gearth://"):
        raw = raw[len("gearth://"):]
    raw = urllib.parse.unquote(raw).strip().strip("/").replace(" ", "")
    nums = [n for n in raw.split(",") if n != ""]
    try:
        if len(nums) == 2:
            return float(nums[0]), float(nums[1])
        if len(nums) == 4:            # vírgula decimal pt-BR
            return float(nums[0] + "." + nums[1]), float(nums[2] + "." + nums[3])
    except ValueError:
        return None, None
    return None, None


def main() -> int:
    if len(sys.argv) < 2:
        return 1
    lat, lon = parse_latlon(sys.argv[1])
    if lat is None:
        return 1
    nome = _xesc(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].strip() else "Empreendimento"
    kml = _KML.format(lat=lat, lon=lon, nome=nome)
    tmp = os.path.join(tempfile.gettempdir(), "gearth_open.kml")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(kml)
    ge = find_google_earth()
    if not ge:
        return 1
    subprocess.Popen([ge, tmp])
    return 0


if __name__ == "__main__":
    sys.exit(main())
