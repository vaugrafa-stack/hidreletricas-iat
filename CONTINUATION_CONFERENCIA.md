# CHECKPOINT — Conferência Geoespacial (barragem + casa de força)

> Retomada automática. Ao reabrir o Claude Code neste projeto, basta dizer **"continue"**
> (ou o loop/ScheduleWakeup dispara sozinho) que a conferência segue daqui, SEM reperguntar.
> O usuário autorizou execução contínua sem novas confirmações. Ver memória [[auto-retomada-limite-uso]] e [[conferencia-geoespacial]].

**Última atualização:** 2026-06-19 (Opus 4.8)

---

## Estado atual

- **Locais únicos conferidos:** 30 / 726
- **Registros conferidos (com propagação):** 135 / 1598
- Lote anterior (16) CONCLUÍDO. Próximo passo: rodar `py src/geo_review/12_gerar_lote_revisao.py 20` para gerar o próximo lote e revisar.
- Planilha de conferência: `data/processed/conferencia_coordenadas.xlsx` (46 colunas; 32 originais + 14 de conferência, ao lado das originais).
- O `.xlsm` original **NUNCA** é alterado (MD5 conferido: `3183d4907d125853daeb273c9b7a4770`).
- **CAMINHO DO .xlsm MUDOU (2026-06-19):** o original foi movido para `C:\Users\rafae\Downloads\IAT\Central_de_Processos_HIDRELETRICAS_COM_MACRO e Links.xlsm` (MD5 idêntico). `config.yaml` já aponta para lá. Há também uma versão NOVA diferente na raiz de Downloads: `...COM_MACRO e Links_COM_QGIS.xlsm` (MD5 `7f9d4e2f…`) — PERGUNTAR ao usuário se a conferência deve migrar para a versão QGIS. Resiliência: o gerador cacheia as colunas em `data/processed/origem_xlsm_cache.pkl` e usa o cache se o arquivo sumir de novo.

## Como retomar (loop de conferência) — fazer SEM pedir confirmação

1. Abrir o **Google Earth Pro** (`open_application "Google Earth Pro"`; já está no allowlist, tier full).
2. Gerar o próximo lote (já pula revisados e dedup por localização):
   `py src/geo_review/12_gerar_lote_revisao.py 20`
3. Para cada local do lote, no GEP: caixa de pesquisa → `lat,lon` → **Enter** (fly-to direto; NÃO duplo-clicar no resultado — landa instável). Aguardar ~5 s → screenshot.
   - Identificar **barragem** (barramento/eixo no rio, reservatório a montante, vertedouro) e **casa de força** (prédio retangular + conduto forçado + canal de fuga). A casa de força pode estar deslocada — se houver `busca_casaforca` no lote, abrir esse ponto também.
   - Se nada visível: validar a **fase** (`fase_provavel`/situação) — PROTOCOLADO/EM ANÁLISE = provável obra não iniciada (status "Sem imagem suficiente"); ARQUIVADO/INDEFERIDO = sem obra.
4. Montar `data/processed/lote_resultados.json` (lista de `{id_emp, barragem{lat,lon,status}, casa_forca{...}, grau, fase, obs}`).
5. Registrar + propagar: `py src/geo_review/13_registrar_conferencia.py`
6. Regenerar a planilha: `py src/geo_review/11_gerar_planilha_conferencia.py`
7. Repetir a partir do passo 2 até `revisado == sim` para todos os locais.
8. **Atualizar este arquivo** (contadores acima) ao fim de cada sub-lote.

## Status válidos
`Validado` · `Corrigido` · `Pendente de validação` · `Sem imagem suficiente` · `Coordenada inconsistente` · `Não identificado`
Grau: `Alto` · `Médio` · `Baixo` · `Pendente`

## Achados a não esquecer
- Erros de coordenada de casa de força (apontam ~centenas de km): **#1586 UHE São João**, **#1051 PCH Bela Vista** — marcar `Coordenada inconsistente`.
- 22 prováveis duplicatas de nome (≤370 m) em `data/processed/analise_nomes_similares.csv`; sufixo "II/Montante/Jusante" quase sempre = usina DISTINTA (não mesclar).
- Markers de UHEs grandes às vezes caem no reservatório/terra (não no eixo) → `Pendente`/`Corrigido`.

## Limite de uso (o que funciona)
- Eu **não** detecto sozinho a aproximação do limite. Mecanismo de retomada = `ScheduleWakeup`/skill `loop` (dispara só com o app aberto) + este checkpoint (para quando uma nova sessão abrir). Cron/cloud **não** serve (depende de arquivos locais + GEP local).
