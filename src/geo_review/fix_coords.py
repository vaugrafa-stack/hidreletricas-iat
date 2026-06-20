"""Corrige 3 registros com formato de coordenadas claramente errado."""
import pandas as pd

df = pd.read_csv("data/processed/pendentes_geo.csv", encoding="utf-8-sig")

fixes = []

for idx, row in df.iterrows():
    proto = str(row.get("protocolo", "")).strip()
    lat = row.get("latitude_barragem_original")
    lon = row.get("longitude_barragem_original")

    # CGH BOA ESPERANÇA (226854193): lat/lon trocados
    # lat=-51.454 (Argentina), lon=-24.828 (oceano) -> inverter
    if proto == "226854193":
        lat_corr = float(lon)   # -24.828...
        lon_corr = float(lat)   # -51.454...
        print(f"BOA ESPERANCA: ({lat:.4f},{lon:.4f}) -> ({lat_corr:.6f},{lon_corr:.6f})")
        fixes.append((idx, lat_corr, lon_corr, "Coordenadas lat/lon trocadas — corrigido por inspeção de limites geográficos (lat fora do PR)."))

    # CGH BARRA DO AMPÉRE (251681180): valor sem ponto decimal × 10^-6
    elif proto == "251681180":
        lat_corr = float(lat) / 1_000_000   # -25.871039
        lon_corr = float(lon) / 1_000_000   # -53.551703
        print(f"BARRA AMPÉRE: ({lat},{lon}) -> ({lat_corr:.6f},{lon_corr:.6f})")
        fixes.append((idx, lat_corr, lon_corr, "Coordenadas sem ponto decimal — corrigido dividindo por 10^6."))

    # PCH SANTO ANTONIO (24.829.461-2): mesmo problema
    elif proto == "24.829.461-2":
        lat_corr = float(lat) / 1_000_000   # -23.257117
        lon_corr = float(lon) / 1_000_000   # -50.211371
        print(f"SANTO ANTONIO: ({lat},{lon}) -> ({lat_corr:.6f},{lon_corr:.6f})")
        fixes.append((idx, lat_corr, lon_corr, "Coordenadas sem ponto decimal — corrigido dividindo por 10^6."))

# Aplicar correções
for idx, lat_corr, lon_corr, obs in fixes:
    df.at[idx, "latitude_barragem_original"] = lat_corr
    df.at[idx, "longitude_barragem_original"] = lon_corr
    df.at[idx, "observacao_geoespacial"] = obs
    df.at[idx, "status_georreferenciamento"] = "Corrigido"
    df.at[idx, "grau_confianca"] = "Médio"

df.to_csv("data/processed/pendentes_geo.csv", index=False, encoding="utf-8-sig")
print(f"\n{len(fixes)} registros corrigidos.")
