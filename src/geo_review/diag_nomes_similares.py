"""
Analisa nomes similares (ex.: 'CGH Foz da Pedra' vs 'CGH Foz da Pedra II')
para distinguir empreendimentos DISTINTOS de DUPLICATAS lançadas.

Critério: agrupa por 'nome-base' (sem sufixos I/II/2/MONTANTE/JUSANTE etc.).
Para cada grupo com variantes, mede a distância entre as barragens:
  - <= 500 m  -> provável MESMO empreendimento (duplicata / relançamento)
  - >  500 m  -> empreendimentos DISTINTOS (estágios/usinas diferentes no rio)
"""
import os, sys, re, unicodedata
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from geo_utils import safe_float, distancia_metros

rast = pd.read_csv("data/processed/conferencia_rastreador.csv",
                   encoding="utf-8-sig", dtype=str).fillna("")

def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", str(s))
                   if unicodedata.category(c) != "Mn")

TIPOS = {"CGH", "PCH", "UHE", "MGH", "MCH"}
SUFIXOS = {"I", "II", "III", "IV", "V", "VI", "1", "2", "3", "4", "5",
           "MONTANTE", "JUSANTE", "A", "B", "MONT", "JUS"}

def nome_base(nome):
    s = sem_acento(nome).upper()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    toks = s.split()
    while toks and toks[0] in TIPOS:
        toks = toks[1:]
    while toks and toks[-1] in SUFIXOS:
        toks = toks[:-1]
    return " ".join(toks)

rast["nome_base"] = rast["empreendimento"].apply(nome_base)

# distância entre dois registros (barragem navegável)
def dist(r1, r2):
    la1, lo1 = safe_float(r1["nav_lat_barragem"]), safe_float(r1["nav_lon_barragem"])
    la2, lo2 = safe_float(r2["nav_lat_barragem"]), safe_float(r2["nav_lon_barragem"])
    if None in (la1, lo1, la2, lo2):
        return None
    return distancia_metros(la1, lo1, la2, lo2)

# Considera 1 registro por chave_local (já dedup por coord) para não poluir
locais = rast.drop_duplicates(subset=["chave_local"]).copy()

linhas = []
distintos = duplicatas = indef = 0
for base, grp in locais.groupby("nome_base"):
    nomes = grp["empreendimento"].unique()
    if base == "" or len(grp) < 2:
        continue
    # só interessa quando há variação de nome OU múltiplos locais p/ mesmo base
    regs = list(grp.itertuples(index=False))
    # matriz de distâncias
    dmax = 0.0; tem_none = False
    for i in range(len(regs)):
        for j in range(i + 1, len(regs)):
            d = dist(regs[i]._asdict(), regs[j]._asdict())
            if d is None:
                tem_none = True
            else:
                dmax = max(dmax, d)
    if tem_none and dmax == 0:
        verd = "INDEFINIDO (sem coord)"; indef += 1
    elif dmax <= 500:
        verd = "PROVÁVEL DUPLICATA (mesmo local)"; duplicatas += 1
    else:
        verd = "DISTINTOS (locais diferentes)"; distintos += 1
    nomes_str = " | ".join(sorted(set(grp["empreendimento"])))
    linhas.append({"nome_base": base, "n_locais": len(grp),
                   "variantes": nomes_str, "dist_max_m": round(dmax, 0),
                   "veredito": verd})

res = pd.DataFrame(linhas).sort_values(["veredito", "dist_max_m"])
res.to_csv("data/processed/analise_nomes_similares.csv", index=False, encoding="utf-8-sig")

print(f"Grupos de nome-base com 2+ locais distintos: {len(res)}")
print(f"  DISTINTOS (locais diferentes):     {distintos}")
print(f"  PROVÁVEL DUPLICATA (mesmo local):  {duplicatas}")
print(f"  INDEFINIDO (sem coordenada):       {indef}")

print("\n=== PROVÁVEIS DUPLICATAS (mesma usina, nomes variando, <=500 m) ===")
dup = res[res["veredito"].str.startswith("PROVÁVEL")]
for r in dup.itertuples():
    print(f"  [{r.dist_max_m:>5.0f} m] {r.variantes}")

print("\n=== EXEMPLOS 'X' vs 'X II' DISTINTOS (>500 m) — primeiros 20 ===")
dis = res[res["veredito"].str.startswith("DISTINTOS")].head(20)
for r in dis.itertuples():
    print(f"  [{r.dist_max_m:>6.0f} m] {r.variantes}")

# Busca específica pedida pelo usuário
print("\n=== Busca 'FOZ DA PEDRA' ===")
fp = rast[rast["empreendimento"].apply(lambda x: "FOZ DA PEDRA" in sem_acento(x).upper())]
if len(fp):
    for r in fp.itertuples():
        print(f"  {r.empreendimento} | {r.nav_lat_barragem},{r.nav_lon_barragem} | {r.situacao}")
else:
    print("  (não encontrado na base)")
