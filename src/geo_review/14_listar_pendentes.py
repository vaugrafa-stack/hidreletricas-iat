# -*- coding: utf-8 -*-
"""Lista locais Pendentes priorizando os que tem reservatorio/estrutura na obs (candidatos a CGH construida)."""
import pandas as pd

r = pd.read_csv('data/processed/conferencia_rastreador.csv', encoding='utf-8-sig', dtype=str).fillna('')
locs = r.drop_duplicates('chave_local')
p = locs[locs['status_barragem_conf'].str.startswith('Pendente')]

# Palavras que sugerem estrutura/agua represada digna de 2a passada
padrao = r'reservat|repres|cachoeira|estrutura|piscicult|turv|açude|usina|barramento|impound'
key = p[p['obs_conferencia'].str.contains(padrao, case=False, regex=True)]

print(f'PENDENTES (locais unicos): {len(p)}')
print(f'  com reservatorio/estrutura/cachoeira na obs: {len(key)}')
print(f'  prio-3 entre os key: {len(key[key.prioridade == "3"])}')
print()
print('=== CANDIDATOS A 2a PASSADA (reservatorio/estrutura) ===')
for row in key.itertuples():
    lat = row.nav_lat_barragem or row.lat_barragem_orig
    lon = row.nav_lon_barragem or row.lon_barragem_orig
    obs = (row.obs_conferencia[:90] + '...') if len(row.obs_conferencia) > 90 else row.obs_conferencia
    print(f'#{row.id_emp:>4} {row.empreendimento[:34]:34} prio{row.prioridade} | {lat},{lon}')
    print(f'       {obs}')
