"""
Integra a base oficial ANEEL/SIGA ao rastreador de conferência.

- Casa SIGA (PR, UHE/PCH/CGH) com cada localização do rastreador por nome + distância.
- Acrescenta colunas: siga_match, siga_nome, siga_fase, siga_lat, siga_lon, siga_dist_m, prioridade.
- NÃO marca revisado (a verificação visual confirma cada ponto) — o SIGA é o candidato
  PRIMÁRIO de coordenada + a fase oficial. Preserva todo o progresso existente.
- prioridade: 0=Operação, 1=Construção, 2=Construção não iniciada, 3=sem match (provável não construído).

Fonte: data/external/siga_aneel.csv  (ANEEL Dados Abertos — SIGA)
"""
import os, sys, re, unicodedata
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from geo_utils import distancia_metros, safe_float

RAST = "data/processed/conferencia_rastreador.csv"
SIGA = "data/external/siga_aneel.csv"

def ok(x): return x is not None and x == x  # not None / not NaN

def norm(s):
    s = "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn").upper()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    for t in ["UHE","PCH","CGH","MGH","MCH","USINA","HIDRELETRICA","CENTRAL","GERADORA"]:
        s = s.replace(t, " ")
    return " ".join(s.split())

FASE_PRIOR = {"Operação": 0, "Construção": 1, "Construção não iniciada": 2}

def main():
    siga = pd.read_csv(SIGA, sep=";", encoding="latin-1", dtype=str, low_memory=False).fillna("")
    siga = siga[(siga["SigUFPrincipal"] == "PR") &
                (siga["SigTipoGeracao"].isin(["UHE", "PCH", "CGH"]))].copy()
    siga["lat"] = siga["NumCoordNEmpreendimento"].apply(safe_float)
    siga["lon"] = siga["NumCoordEEmpreendimento"].apply(safe_float)
    siga["nb"] = siga["NomEmpreendimento"].apply(norm)
    siga_names = set(siga["nb"])

    rast = pd.read_csv(RAST, encoding="utf-8-sig", dtype=str).fillna("")

    # match por localização única
    loc = rast.drop_duplicates("chave_local").copy()
    loc["lat"] = loc["nav_lat_barragem"].apply(safe_float)
    loc["lon"] = loc["nav_lon_barragem"].apply(safe_float)
    loc["nb"] = loc["empreendimento"].apply(norm)

    match = {}  # chave_local -> dict
    for l in loc.itertuples():
        best = None
        if ok(l.lat) and ok(l.lon):
            for s in siga.itertuples():
                if ok(s.lat) and ok(s.lon):
                    d = distancia_metros(l.lat, l.lon, s.lat, s.lon)
                    if ok(d) and (best is None or d < best[0]):
                        best = (d, s)
        name_eq = l.nb in siga_names and l.nb != ""
        hit_dist = best is not None and best[0] <= 2000
        # match por nome só conta se a distância também for plausível (<25 km) p/ evitar homônimos longe
        hit_name = name_eq and (best is None or best[0] <= 25000)
        if hit_dist or hit_name:
            s = best[1]
            fase = s.DscFaseUsina
            match[l.chave_local] = {
                "siga_match": "SIM", "siga_nome": s.NomEmpreendimento, "siga_fase": fase,
                "siga_lat": f"{s.lat:.6f}" if ok(s.lat) else "",
                "siga_lon": f"{s.lon:.6f}" if ok(s.lon) else "",
                "siga_dist_m": str(int(round(best[0]))) if (best and ok(best[0])) else "",
                "prioridade": str(FASE_PRIOR.get(fase, 2)),
            }
        else:
            match[l.chave_local] = {
                "siga_match": "NAO", "siga_nome": "", "siga_fase": "", "siga_lat": "",
                "siga_lon": "", "siga_dist_m": "", "prioridade": "3",
            }

    cols = ["siga_match", "siga_nome", "siga_fase", "siga_lat", "siga_lon", "siga_dist_m", "prioridade"]
    for c in cols:
        rast[c] = rast["chave_local"].map(lambda k: match.get(k, {}).get(c, ""))

    rast.to_csv(RAST, index=False, encoding="utf-8-sig")

    print("Integração SIGA concluída.")
    nloc = loc.shape[0]
    nmatch = sum(1 for k in match if match[k]["siga_match"] == "SIM")
    print(f"  Localizações: {nloc} | com match SIGA: {nmatch} | sem match: {nloc - nmatch}")
    pr = pd.Series([match[k]["prioridade"] for k in match]).value_counts().sort_index()
    rot = {"0": "Operação", "1": "Construção", "2": "Constr. não iniciada/—", "3": "Sem match (provável não construído)"}
    print("  Por prioridade (locais únicos):")
    for k, v in pr.items():
        print(f"    {k} {rot.get(k,k):38s} {v}")

if __name__ == "__main__":
    main()
