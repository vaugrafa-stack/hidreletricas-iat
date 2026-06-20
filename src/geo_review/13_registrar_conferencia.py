"""
Registra resultados da revisão visual no rastreador.

Lê data/processed/lote_resultados.json (lista de resultados) e grava no
rastreador (conferencia_rastreador.csv), marcando revisado=sim.

Formato de cada item do JSON:
{
  "id_emp": 123,
  "barragem":   {"lat": -25.6, "lon": -52.6, "status": "Validado"},
  "casa_forca": {"lat": -25.6, "lon": -52.6, "status": "Validado"},
  "grau": "Alto",
  "fase": "Em operação",
  "obs": "texto descritivo"
}
Campos podem ser omitidos/null (ex.: casa de força não encontrada).
"""
import os, sys, json
from datetime import date
import pandas as pd

RASTREADOR = "data/processed/conferencia_rastreador.csv"
RESULTADOS = "data/processed/lote_resultados.json"


def g(d, *keys):
    cur = d
    for k in keys:
        if cur is None or not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def main():
    caminho = sys.argv[1] if len(sys.argv) > 1 else RESULTADOS
    with open(caminho, encoding="utf-8") as f:
        resultados = json.load(f)

    rast = pd.read_csv(RASTREADOR, encoding="utf-8-sig", dtype=str).fillna("")
    rast = rast.set_index("id_emp")
    hoje = date.today().isoformat()

    campos = {
        "lat_barragem_conf": lambda it: g(it, "barragem", "lat"),
        "lon_barragem_conf": lambda it: g(it, "barragem", "lon"),
        "status_barragem_conf": lambda it: g(it, "barragem", "status"),
        "lat_casaforca_conf": lambda it: g(it, "casa_forca", "lat"),
        "lon_casaforca_conf": lambda it: g(it, "casa_forca", "lon"),
        "status_casaforca_conf": lambda it: g(it, "casa_forca", "status"),
        "grau_confianca": lambda it: it.get("grau"),
        "fase_verificada": lambda it: it.get("fase"),
        "obs_conferencia": lambda it: it.get("obs"),
    }

    n_dir, n_prop = 0, 0
    for item in resultados:
        idx = str(item["id_emp"])
        if idx not in rast.index:
            print(f"  AVISO: id_emp {idx} não encontrado — ignorado.")
            continue
        chave = rast.loc[idx, "chave_local"]

        # registro revisado diretamente
        for col, fn in campos.items():
            v = fn(item)
            rast.loc[idx, col] = "" if v is None else str(v)
        rast.loc[idx, "data_conferencia"] = hoje
        rast.loc[idx, "origem_conferencia"] = "direta"
        rast.loc[idx, "revisado"] = "sim"
        n_dir += 1

        # propaga para os demais processos da MESMA localização ainda não revisados
        irmaos = rast.index[(rast["chave_local"] == chave)
                            & (rast.index != idx)
                            & (rast["revisado"].str.lower() != "sim")]
        for j in irmaos:
            for col, fn in campos.items():
                v = fn(item)
                rast.loc[j, col] = "" if v is None else str(v)
            rast.loc[j, "data_conferencia"] = hoje
            rast.loc[j, "origem_conferencia"] = f"propagado:#{idx}"
            rast.loc[j, "revisado"] = "sim"
            n_prop += 1

    rast.reset_index().to_csv(RASTREADOR, index=False, encoding="utf-8-sig")
    total_rev = (rast["revisado"].str.lower() == "sim").sum()
    print(f"Revisados diretamente: {n_dir} | propagados p/ mesma localização: {n_prop}")
    print(f"Total revisado no rastreador: {total_rev}/{len(rast)}")


if __name__ == "__main__":
    main()
