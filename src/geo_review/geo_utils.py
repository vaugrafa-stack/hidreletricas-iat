"""Utilitários compartilhados para revisão geoespacial."""
import math
from typing import Optional


# Limites aproximados do Paraná (WGS84)
PR_BOUNDS = {"lat_min": -27.0, "lat_max": -22.0, "lon_min": -55.0, "lon_max": -48.0}

STATUS_VALIDOS = [
    "Validado",
    "Corrigido",
    "Pendente de validação",
    "Sem imagem suficiente",
    "Coordenada inconsistente",
    "Não construído",
    "Não identificado",
]

GRAU_VALIDOS = ["Alto", "Médio", "Baixo", "Pendente"]


def coords_validas(lat: Optional[float], lon: Optional[float]) -> bool:
    """Verifica se o par de coordenadas está dentro do bounding box do Paraná."""
    if lat is None or lon is None:
        return False
    try:
        lat = float(lat)
        lon = float(lon)
    except (ValueError, TypeError):
        return False
    return (
        PR_BOUNDS["lat_min"] <= lat <= PR_BOUNDS["lat_max"]
        and PR_BOUNDS["lon_min"] <= lon <= PR_BOUNDS["lon_max"]
    )


def distancia_metros(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância Haversine entre dois pontos, em metros."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def link_google_earth(lat: float, lon: float, zoom: int = 500) -> str:
    """Gera link Google Earth Web para um ponto."""
    return f"https://earth.google.com/web/@{lat:.6f},{lon:.6f},{zoom}a,0d,60y,0h,0t,0r"


def safe_float(value) -> Optional[float]:
    """Converte para float sem lançar exceção."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        return float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return None
