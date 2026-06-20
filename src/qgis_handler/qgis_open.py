"""Handler do protocolo qgis:// — abre o QGIS centralizado em uma coordenada.

Invocado pelo Windows quando se clica em um link `qgis://lat,lon`
(registrado por instalar_handler.bat). Lê a coordenada, grava num arquivo
temporário e lança o QGIS executando o script de inicialização que adiciona
mapa base + camada de pontos e centraliza no empreendimento.

Aceita tanto `qgis://-24.28,-49.69` (ponto decimal) quanto a forma com
vírgula decimal do Excel pt-BR `qgis://-24,28,-49,69`.
"""
import sys
import os
import glob
import subprocess
import tempfile
import urllib.parse


def find_qgis() -> str | None:
    pats = [
        r"C:\Program Files\QGIS*\bin\qgis-bin.exe",
        r"C:\Program Files\QGIS*\bin\qgis-ltr-bin.exe",
        r"C:\OSGeo4W*\bin\qgis-bin.exe",
        r"C:\OSGeo4W*\bin\qgis-ltr-bin.exe",
    ]
    for pat in pats:
        m = sorted(glob.glob(pat))
        if m:
            return m[-1]
    return None


def parse_latlon(uri: str):
    raw = uri
    if raw.lower().startswith("qgis://"):
        raw = raw[len("qgis://"):]
    raw = urllib.parse.unquote(raw).strip().strip("/").replace(" ", "")
    nums = [n for n in raw.split(",") if n != ""]
    try:
        if len(nums) == 2:            # -24.28,-49.69
            return float(nums[0]), float(nums[1])
        if len(nums) == 4:            # vírgula decimal pt-BR: -24,28,-49,69
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
    nome = sys.argv[2].strip() if len(sys.argv) > 2 and sys.argv[2].strip() else "Empreendimento"
    nome = nome.replace("|", "/")  # | é separador do arquivo temp

    here = os.path.dirname(os.path.abspath(__file__))
    geojson = os.path.normpath(os.path.join(here, "..", "..", "data", "processed",
                                            "processos_hidreletricas.geojson"))
    tmp = os.path.join(tempfile.gettempdir(), "qgis_open_latlon.txt")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(f"{lat}|{lon}|{geojson}|{nome}")

    qgis = find_qgis()
    if not qgis:
        return 1
    startup = os.path.join(here, "startup_open_qgis.py")
    subprocess.Popen([qgis, "--code", startup])
    return 0


if __name__ == "__main__":
    sys.exit(main())
