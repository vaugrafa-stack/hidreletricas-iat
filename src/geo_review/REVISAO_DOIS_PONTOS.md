# Método de Conferência de Dois Pontos — Barragem + Casa de Força

Procedimento para conferir, no Google Earth Pro, **dois pontos** por empreendimento:
o **eixo central da barragem** e o **centro da casa de força**.

## Fluxo por empreendimento

1. **Abrir o ponto da barragem** — colar `lat,lon` (coluna `busca_barragem`) na caixa
   de pesquisa do GEP → Enter → duplo-clique no resultado → rolar para aproximar.

2. **Identificar a BARRAGEM** (marcador amarelo). Procurar:
   - barramento cruzando o rio;
   - reservatório a montante (água parada, mais larga);
   - vertedouro/sangradouro;
   - estrada sobre o coroamento.
   Registrar o **ponto central do barramento** (eixo no meio do rio).

3. **Identificar a CASA DE FORÇA** (marcador verde). Pode estar **longe** da barragem.
   - Se houver `busca_casaforca`, abrir esse ponto.
   - Caso contrário, a partir da barragem **seguir o conduto forçado / canal de adução**
     (linha reta de tubulação ou canal descendo a encosta) até o prédio.
   - Sinais da casa de força: prédio retangular de concreto, **canal de fuga** com água
     clara a jusante, **linhas de transmissão** saindo, pátio de transformadores.
   Registrar o **ponto central do prédio**.

4. **Classificar cada ponto** (status):
   | Status | Quando |
   |--------|--------|
   | Validado | estrutura no ponto (ou movido o marcador para cima dela) |
   | Corrigido | estrutura existe mas em local diferente — registrar nova coord |
   | Pendente de validação | estrutura provável, posição incerta |
   | Sem imagem suficiente | nuvem, baixa resolução, ou **obra em andamento** |
   | Não identificado | nada no local |

5. **Se NÃO houver estrutura**: antes de marcar "Não identificado", validar a **fase**
   pela coluna `situacao` / `fase_provavel`:
   - `Fase prévia` (PROTOCOLADO / EM ANÁLISE) → provavelmente **ainda não construído**;
     marcar `fase = "Não construído (licenciamento)"`, status `Sem imagem suficiente`.
   - `Não licenciado` (ARQUIVADO / INDEFERIDO / CANCELADO) → obra improvável.
   - `Licenciado` (DEFERIDO) e nada visível → checar entorno (imagem antiga? obra recente?).

6. **Grau de confiança** do empreendimento: Alto / Médio / Baixo / Pendente.

## Deduplicação

Vários processos (protocolos) referem-se à **mesma usina física**. A revisão é feita
**uma vez por localização** (`chave_local`) e o resultado é **propagado** a todos os
processos daquele local pelo registrador. 1.598 registros → **726 locais únicos**.

## Scripts

| Script | Função |
|--------|--------|
| `10_montar_rastreador.py` | lê o .xlsm (read-only) e monta o rastreador |
| `12_gerar_lote_revisao.py [N]` | gera o próximo lote (CSV + KML barragem/casa de força) |
| `13_registrar_conferencia.py` | grava `lote_resultados.json` no rastreador + propaga |
| `11_gerar_planilha_conferencia.py` | gera a planilha `.xlsx` de conferência |

O `.xlsm` original **nunca** é alterado. As coordenadas conferidas ficam em colunas
novas, ao lado das originais, na planilha de conferência separada.
