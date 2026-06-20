"""Quantifica empreendimentos físicos únicos vs. registros de processo."""
import sys, os
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from geo_utils import safe_float

rast = pd.read_csv("data/processed/conferencia_rastreador.csv",
                   encoding="utf-8-sig", dtype=str).fillna("")

def chave_local(r):
    """Chave de localização física: coord barragem arredondada (~11 m)."""
    la = safe_float(r["nav_lat_barragem"]); lo = safe_float(r["nav_lon_barragem"])
    if la is not None and lo is not None:
        return f"{round(la,4)},{round(lo,4)}"
    # sem coord: usa nome normalizado
    return "NOME:" + str(r["empreendimento"]).strip().upper()

rast["chave_local"] = rast.apply(chave_local, axis=1)

n_reg = len(rast)
n_unico = rast["chave_local"].nunique()
print(f"Registros de processo:        {n_reg}")
print(f"Localizações físicas únicas:  {n_unico}")
print(f"Redução pela deduplicação:    {n_reg - n_unico} ({100*(n_reg-n_unico)/n_reg:.0f}%)")

# por nome
n_nome = rast["empreendimento"].str.strip().str.upper().nunique()
print(f"Nomes de empreendimento únicos: {n_nome}")

print("\nTop 12 localizações com mais registros:")
vc = rast["chave_local"].value_counts().head(12)
for k, v in vc.items():
    nomes = rast[rast["chave_local"] == k]["empreendimento"].iloc[0]
    print(f"  {v:>3}x  {str(nomes)[:45]:<45} [{k[:40]}]")
