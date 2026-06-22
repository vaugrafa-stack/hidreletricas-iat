# -*- coding: utf-8 -*-
"""Gera PLANO_2A_PASSADA.md: agrupa as pendencias em niveis acionaveis para a 2a passada."""
import pandas as pd

r = pd.read_csv('data/processed/conferencia_rastreador.csv', encoding='utf-8-sig', dtype=str).fillna('')
locs = r.drop_duplicates('chave_local').copy()

pend = locs[locs['status_barragem_conf'].str.contains('Pendente|Sem imagem|Não identificado|N.o identificado', case=False, regex=True)].copy()


def lc(s):
    return s.lower()


def tier(row):
    obs = lc(row['obs_conferencia'])
    emp = row['empreendimento'].upper()
    aneel_op = ('em opera' in obs) or ('operação (aneel)' in obs)
    is_grande = emp.startswith(('PCH', 'UHE', 'MCH', 'MGH'))
    chopim = ('chopim' in obs) or ('iguaçu' in obs) or ('iguacu' in obs)
    dark = ('imagem esc' in obs) or ('sem imagem' in lc(row['status_barragem_conf']))
    reserv = any(k in obs for k in ['reservat', 'repres', 'represa', 'corpo d', 'açude', 'cachoeira'])
    if aneel_op:
        return 'A'  # ANEEL operacao: so falta fixar eixo/casa de forca -> provavel Validado
    if is_grande or chopim:
        return 'B'  # Grande (PCH/UHE) Chopim/Iguacu: reservatorio confirmado, fixar eixo
    if row['prioridade'] == '3' and reserv:
        return 'C'  # prio-3 sem SIGA com agua/estrutura: DECISAO VISUAL (risco de CGH construida nao descoberta)
    if dark:
        return 'D'  # Imagem escura/insuficiente: precisa slider de imagem historica
    return 'E'  # Demais


pend['tier'] = pend.apply(tier, axis=1)

titulos = {
    'A': 'TIER A — prio-0 "em operação (ANEEL)": usina CONFIRMADA, falta só fixar eixo/casa de força no zoom → provável Validado',
    'B': 'TIER B — PCH/UHE (Chopim/Iguaçu) com reservatório confirmado: fixar eixo do barramento → provável Validado',
    'C': 'TIER C — prio-3 "sem SIGA" com água/estrutura: DECISÃO VISUAL (risco de CGH construída não descoberta, como #445/#234/#25/#490)',
    'D': 'TIER D — imagem escura/insuficiente: precisa do controle de IMAGEM HISTÓRICA (data alternativa) no GEP',
    'E': 'TIER E — demais pendências (sem reservatório evidente na obs)',
}

linhas = []
linhas.append('# Plano de 2ª passada — pendências da conferência geoespacial')
linhas.append('')
linhas.append(f'Total de locais pendentes: **{len(pend)}** (de 726). Conferência principal 100% concluída; estes são refinamentos.')
linhas.append('')
linhas.append('Técnica recomendada por tier abaixo. Coordenada = barragem (nav). Abrir no GEP, aproximar (scroll/zoom) até ~600–900 m e, quando o eixo estiver deslocado do marcador, navegar a jusante.')
linhas.append('')
for t in ['A', 'B', 'C', 'D', 'E']:
    sub = pend[pend['tier'] == t]
    linhas.append(f'## {titulos[t]}  ({len(sub)})')
    linhas.append('')
    if len(sub) == 0:
        linhas.append('_(nenhum)_')
        linhas.append('')
        continue
    for row in sub.sort_values(['prioridade', 'id_emp']).itertuples():
        lat = row.nav_lat_barragem or row.lat_barragem_orig
        lon = row.nav_lon_barragem or row.lon_barragem_orig
        nome = row.empreendimento.strip()
        obs = row.obs_conferencia.strip()
        if len(obs) > 140:
            obs = obs[:140] + '…'
        linhas.append(f'- **#{row.id_emp} {nome}** (prio{row.prioridade}) — `{lat},{lon}`')
        if obs:
            linhas.append(f'  - {obs}')
    linhas.append('')

with open('PLANO_2A_PASSADA.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(linhas))

print('PLANO_2A_PASSADA.md gerado.')
print('Resumo por tier:')
print(pend['tier'].value_counts().sort_index().to_string())
