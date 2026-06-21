# CHECKPOINT — Reforma do Dashboard IAT Hidrelétricas

> Arquivo de retomada automática. Se a sessão for interrompida (limite de uso, fechar o app),
> ao voltar basta dizer **"continue"** que o trabalho segue daqui. Atualizado a cada bloco grande.

**Última atualização:** 2026-06-20 (modelo Opus 4.8) — camadas temáticas WMS do GeoPR adicionadas

---

## ✅ Concluído — Pipeline (dados já regenerados em `data/processed/`)

1. **Bug crítico NaN→"NAN"** (`src/transform_data.py`)
   - `_strip_text(np.nan)` retornava `"nan"` → `_norm_upper` virava `"NAN"`.
   - Efeito: gráficos `por_tecnico`/`por_situacao` tinham categoria fantasma `"NAN"`; validação de
     inconsistências MÉDIAS nunca disparava (`"NAN"` é truthy).
   - Correção: helper `_isna` + conjunto `_NULL_TOKENS`; todos os conversores tratam NaN/NaT.

2. **Matching de colunas robusto** (`_colkey` em `transform_data.py`)
   - Tolera acento/símbolo (`º` vs `°`, `ª`, diacríticos).
   - Consertou `N° DOC (licença)` → `numero_licenca` e `LINK EARTH NAVEGADOR WEB` → `link_google_earth`
     (antes ficavam sem mapear; link do mapa e nº de licença quebrados).
   - Log de colunas não encontradas.

3. **`config.yaml`** — adicionada chave `"LINK EARTH NAVEGADOR WEB": link_google_earth`.

4. **`src/validate_data.py` reescrito**
   - Normaliza cada linha NaN→None (evita NaN truthy).
   - Distingue coordenada **inválida** (fora do PR) vs **ausente** (`coord_fora_pr` vindo do transform).
   - "Licença vencida" só é crítica para processos **não encerrados**.
   - Popula MÉDIAS (técnico, tipologia, tipo_licença, situação, bacia, data_protocolo, nº licença
     quando deferido) e BAIXAS (rio, potência).
   - Resumo enriquecido: `sem_tecnico`, `coordenada_invalida`, `registros_com_critico`, `licencas_vigentes`.

5. **`src/run_pipeline.py`** — metadados incluem os novos campos.

6. **Resultado da re-execução:** 683 críticos (682 registros) / 405 médios / 19 baixos.
   Indicadores limpos (sem "NAN"). 1590 pontos no GeoJSON. CSV com `numero_licenca` e `link_google_earth`.

7. **`dashboard/utils.py`** — adicionados `fmt_int`, `fmt_mw`, `fmt_data`, `style_fig`, `build_point_index`.

---

## ✅ Concluído — `dashboard/app.py` reescrito (sintaxe validada com py_compile)

- [x] Fonte **Inter** + CSS refinado (cards com sombra suave, hover, espaçamento).
- [x] Header institucional (título, subtítulo, badge de atualização + fonte).
- [x] Navegação topo com botões `type="primary"` (ativo) / `"secondary"`.
- [x] Cards KPI com ícone, número grande, cor semântica, subtexto.
- [x] **Chips de filtros ativos** + contador + "Limpar filtros".
- [x] **Mapa** maior (7:3) + painel lateral **estruturado** via `build_point_index` + `last_object_clicked`; legenda; toggle situação/tipologia.
- [x] Gráficos via `style_fig` (rótulos, hover, ordenação maior→menor).
- [x] Qualidade: cards médias/baixas, distribuição por gravidade, campos com mais erros, completude.
- [x] Tabela com `st.column_config` (LinkColumn Google Earth, datas, números) + export CSV.

## ✅ CONCLUÍDO — Validação no preview (2026-06-18)

Todas as 5 páginas validadas no Streamlit 1.58 (preview headless):
- **Visão Geral**: 8 cards (1.598 / 101 / 208 / 685 / 19 / 682 / 8 / 55.598 MW), 4+4 gráficos. Sem "NAN".
- **Mapa**: trocado Folium→`px.scatter_map` (MapLibre, sem token) por performance (1590 pontos);
  seleção por clique via `on_select="rerun"` → painel lateral estruturado; legenda semântica; toggle Situação/Tipologia.
- **Licenças**: 685 vencidas / 19 a vencer / 208 vigentes / 686 sem validade (soma 1.598 ✓), 3 abas.
- **Qualidade**: 683 críticas / 405 médias / 19 baixas / 1.067 registros afetados; completude.
- **Relatório**: busca, tabela `st.column_config` (LinkColumn/datas/números), export CSV + JSON.

### Correções de UI aplicadas na validação
- CSS vazava como texto: bloco começava com `<link>` (HTML tipo-6, cortado em linha em branco).
  Corrigido iniciando com `<style>` + `@import` da fonte Inter.
- `.streamlit/config.toml` tinha BOM (gerado via PowerShell) que quebrava o parser TOML → reescrito limpo + tema.
- Cards KPI quebravam número em várias linhas → `white-space:nowrap` + `clamp()`; potência sem "MW" no valor.
- Mapa Folium travava (>30s p/ 1590 marcadores) → Plotly nativo.

**Observação:** a ferramenta de screenshot do preview expira em páginas com mapa vivo (network-idle dos tiles);
não afeta o usuário em navegador real. Validação feita via snapshot + JS eval.

## ✅ CONCLUÍDO — Coluna "Abrir no QGIS" (2026-06-19)

Parità com a coluna do Google Earth, mas para o QGIS desktop (que não abre por URL).
- **Handler de protocolo `qgis://`** em `src/qgis_handler/`: `qgis_open.py` (parser lat,lon — aceita
  ponto decimal, vírgula pt-BR e URL-encoded; acha o qgis-bin.exe), `startup_open_qgis.py` (roda dentro
  do QGIS via `--code`: adiciona OSM + camada GeoJSON e centraliza no ponto), `instalar_handler.bat` /
  `desinstalar_handler.bat` (registra HKCU\Software\Classes\qgis, sem admin), `README_QGIS.md`.
- **Handler já registrado NESTE PC** (via reg add) e **testado ponta-a-ponta**: log
  `%TEMP%\qgis_open_handler.log` = "OK -> centralizado em -24.281655,-49.695021". QGIS abriu e centralizou.
- **Pipeline**: `transform_data.py` gera `link_qgis = qgis://lat,lon` (1590/1598; vazio quando sem coord).
- **Dashboard**: coluna LinkColumn "QGIS 🗺️" na tabela do Relatório + link no painel de detalhes do mapa.
- **Planilha**: NÃO alterada por código (regra). O usuário adiciona a coluna no Excel com a fórmula
  `=SE(...;HIPERLINK("qgis://"&SUBSTITUIR(...);"Abrir no QGIS"))` documentada no README_QGIS.md.
  Em outros PCs, rodar `instalar_handler.bat` uma vez.

## ✅ CONCLUÍDO — 3 formas de abrir + menu no mapa (2026-06-19)

Pedido: replicar no dashboard as 3 formas de abrir (navegador / Google Earth desktop / QGIS).
- **Novo handler `gearth://`** em `src/gearth_handler/` (análogo ao QGIS): `gearth_open.py` gera KML
  temporário com `<LookAt>` e abre o **Google Earth Pro** (`C:\Program Files\Google\Google Earth Pro\client\googleearth.exe`).
  **Registrado neste PC** e **testado** (googleearth.exe abriu no ponto; KML com lat/lon corretos).
- **Pipeline**: `transform_data.py` gera `link_gearth = gearth://lat,lon` (além de `link_qgis` e `link_google_earth`).
- **Mapa voltou para Folium** (estava Plotly) porque o Plotly não faz popup clicável sobre o ponto.
  Ao clicar no ponto abre um **popup-menu com 3 botões** (🌐 Navegador / 🖥️ Google Earth / 🗺️ QGIS).
  Mapa Folium é cacheado por assinatura de filtro (`@st.cache_resource`) p/ performance. Imports folium re-adicionados.
- **Relatório Analítico**: 3 LinkColumns — "Abrir no navegador" (link_google_earth/GE web),
  "Google Earth desktop" (link_gearth), "Abrir no QGIS" (link_qgis).
- Helpers novos em app.py: `menu_links()`, `_popup_menu()`, `build_folium_map()`.

Verificado no preview: mapa Folium OK (Leaflet + clusters; popups com 1590 qgis, 1590 gearth, 1588 navegador),
Relatório sem erro com as 3 colunas. (Screenshot da ferramenta trava no network-idle — limitação da captura, não do app.)

## ✅ CONCLUÍDO — Precisão das coordenadas + planilha Excel (2026-06-19)

**Precisão (apoio à conferência de coordenadas do usuário):**
- `transform`: `n_decimais_coord` e `precisao_coord` (alta≥4 / media=3 / baixa≤2 casas). Trata NaN (sem coord → vazio).
- `validate`: BAIXO p/ baixa precisão; MEDIO p/ coordenada repetida entre empreendimentos DIFERENTES.
- Resumo: alta=1578 / media=5 / baixa=7 ; coord_compartilhada=75 em 16 grupos.
- Dashboard: filtro "Precisão da Coordenada"; seção "Precisão das Coordenadas" no Qualidade (4 cards +
  tabela "pontos a conferir" + export CSV); precisão/fonte/coordenada no detalhe do mapa.
- `link_google_earth` agora é preenchido pelas coords quando ausente (1590/1590 com coord).

**Planilha Excel entregue:** `Central_de_Processos_HIDRELETRICAS_COM_MACRO e Links_COM_QGIS.xlsm` (em Downloads, ao lado do original).
- Gerada por `src/gerar_planilha_qgis.py` via **cirurgia no XML do ZIP** — o COM do Excel RECUSA abrir este .xlsm
  (erro 0x800A03EC, mesmo com PV off/eventos off/CorruptLoad); o openpyxl descartaria os 12 gráficos.
- Edita só o XML da 1ª aba (header AG "ABRIR NO QGIS" + fórmula HYPERLINK por linha) e reescreve o ZIP
  preservando tudo byte-a-byte. Verificado: 51 partes, 12 charts, 5 drawings, 11 tabelas, vbaProject — todos intactos.
- Fórmula `=IF(S{n}="","",HYPERLINK("qgis://"&SUBSTITUTE(S{n}&"",",",".")&","&SUBSTITUTE(U{n}&...),"Abrir no QGIS"))`
  → auto-atualiza quando o usuário corrigir lat/lon (S/U). Excel→qgis:// confirmado (Excel `.Follow` disparou o handler).
- pywin32 instalado (tentativa COM, descartada). Sandbox precisa ficar OFF p/ COM (mas a versão final ZIP nem usa COM).

## Status: TODAS AS FRENTES CONCLUÍDAS E VALIDADAS no preview (Qualidade c/ precisão, Mapa Folium, Relatório 3 colunas).
Handlers `qgis://` e `gearth://` registrados NESTE PC. Em outros PCs: rodar os respectivos `instalar_handler.bat`.
README principal ATUALIZADO com todas as features (handlers, 3 modos de abrir, precisão, gerador Excel).
Testes criados e passando: `tests/conftest.py` + `test_transform_data.py` + `test_validate_data.py` → **14 passed**
(cobrem NaN→None, `_colkey`, precisão, 3 links, gravidades, coord repetida, vencida-só-se-não-encerrado).
Planilha COM_QGIS revalidada: 12 gráficos + macros preservados, coluna AG ok.
Mapa: adicionado **seletor de camadas** (`build_folium_map`, LayerControl visível): 🗺️ Mapa claro (padrão),
🛰️ Satélite (Esri World Imagery, imagem real), 🛣️ OpenStreetMap, 🏷️ Rótulos (overlay). Marcadores com borda
branca p/ contraste no satélite.
⚠️ GOTCHA CORRIGIDO: `build_folium_map` NÃO pode ser cacheado com `@st.cache_resource` — reaproveitar o objeto
`folium.Map` entre reruns faz o `st_folium` renderizar o iframe com **altura 0** (mapa some). Removido o cache;
reconstrói a cada run (rápido: st_folium só faz rerun ao clicar, pois `returned_objects=["last_object_clicked"]`).
Validado: iframe 600px, 5 camadas no controle, satélite Esri carrega ao alternar.
⚠️ GOTCHA CORRIGIDO (abrir programas): os links do popup do mapa NÃO abrem QGIS/GE/navegador — o iframe do
st_folium tem `sandbox` sem `allow-top-navigation`, então o navegador bloqueia. SOLUÇÃO: como o app é LOCAL,
o SERVIDOR abre o programa via `launch_desktop()` em `dashboard/app.py` (webbrowser.open p/ navegador;
`subprocess.Popen([sys.executable, src/<kind>_handler/<kind>_open.py, "<kind>://lat,lon"])` p/ qgis/gearth).
Botões no painel de detalhes do mapa (ao clicar no ponto) e na tabela do Relatório (selecionar linha).
⚠️ BUG 2 CORRIGIDO (não abria nada): o `st_folium` retorna `last_object_clicked=None` no rerun disparado por
OUTRO widget (o botão), então `row` sumia e o botão nem chamava `launch_desktop`. FIX: persistir o ponto
clicado em `st.session_state["mapa_sel"]` e usar isso (não só o retorno do st_folium). Testado: clicar no
botão QGIS do painel → log "OK -> centralizado". O servidor de fato lança o app (testado: preview server abriu QGIS).
⚠️ BUG 3 CORRIGIDO ("não deixa clicar em nada"): o **popup do marcador** (1) cobria o mapa/controles bloqueando
cliques E (2) fazia o `st_folium` capturar só `last_object_clicked_popup`, NÃO `last_object_clicked` — então a
coordenada não chegava e os botões do painel NUNCA apareciam. FIX: **removido o popup do CircleMarker** (fica só
tooltip no hover). Agora: clicar no marcador → `last_object_clicked` capturado (DEBUG confirmou
{lat,lng}) → painel mostra detalhes + botões → clicar abre o programa (testado fluxo REAL: clique no marcador →
botão QGIS do painel → log "OK -> centralizado", mapa segue aberto). Também removidos: `_popup_icons`, `_popup_menu`
(sem uso) e o handler `?abrir` (a abordagem de nova aba mostrava "pode fechar esta aba", que o usuário não quis).
Abertura = só pelos BOTÕES DO PAINEL (`launch_desktop`, servidor), que NÃO navegam.
NOME DO EMPREENDIMENTO ao abrir: `launch_desktop` passa o nome como argv[2] aos handlers.
gearth_open.py põe `<name>` no Document+Placemark do KML (GE desktop mostra o rótulo).
qgis_open.py grava o nome no temp (`lat|lon|geojson|nome`); startup_open_qgis.py nomeia a camada com o
empreendimento e adiciona RÓTULO (QgsPalLayerSettings, texto branco c/ contorno preto). Testado: KML com
`<name>PCH RANCHO GRANDE</name>`, temp com `|PCH RANCHO GRANDE`, log sem "rótulo falhou". Botões de abrir = **4** (painel do mapa em grade 2×2; Relatório em linha). Painel do mapa: NOME → botões →
caixa descritiva (botões ACIMA do descritivo). 🌐 Navegador (GE Web — usa `web/search/lat,lon` que MARCA o ponto
com pino; o `@lat,lon` antigo só posicionava a câmera sem pino; GE Web não aceita rótulo de nome via URL),
📍 **Maps** (NOVO — Google Maps `?q=lat,lon(NOME)` via `quote(nome)`: marca o
ponto na coordenada exata COM o nome), 🖥️ Earth (GE Pro desktop, KML com nome), 🗺️ QGIS (satélite + rótulo).
`launch_desktop` tem os tipos: navegador/maps/gearth/qgis. Maps não testável no preview (abre navegador real
server-side); URL validada: `https://www.google.com/maps?q=-26.318541,-52.165949(PCH%20RANCHO%20GRANDE)`.
QGIS ZOOM: `startup_open_qgis.py` reescrito — basemap **satélite Esri** + marcador vermelho no ponto +
`QTimer.singleShot(1500/3500, _zoom)` reaplica o zoom (d=400 m) DEPOIS que o QGIS carrega (antes o QGIS
sobrescrevia o zoom e mostrava o PR inteiro). Premissa: app roda LOCAL (servidor na máquina do usuário).
Limitação do PREVIEW: links http externos (GE Web) são bloqueados; o botão Navegador do painel usa
`webbrowser.open` no servidor → abre o navegador real do usuário (funciona fora do preview).
Esses botões NÃO precisam do protocolo registrado (chamam o script direto). Testado: subprocess pelo python do
Streamlit disparou o handler (log "OK -> centralizado").
Marcadores: mudados de círculo preenchido (tapava a construção no satélite) para **anel vazado** (borda colorida
semântica, `fill_opacity` baixo) + **slider "Transparência dos pontos"** na página do mapa (param `fill_op` em
`build_folium_map`, default 0.30). Validado por print: centro do anel deixa ver a imagem de satélite. (Pontos
co-localizados ainda viram badge do MarkerCluster — são justamente os casos de coordenada repetida.)
Autoria: cabeçalho (abaixo do título, no lugar do antigo subtítulo) e rodapé (todas as páginas) mostram
"Rafael Valgrande Augusto · Engenheiro Sanitarista e Ambiental · IAT/PR · bol.rafaelaugusto@iat.pr.gov.br".
Nova aba "Mais Informações" (6ª página) com card de contato (Eng. Rafa + email + site https://www.iat.pr.gov.br),
"Sobre o painel" e "Como usar".
Logo COMBINADA (IAT + Paraná/SEDEST lado a lado) em `dashboard/assets/logos_combinado.png`, gerada por
`dashboard/assets/montar_logos.py` a partir de `logo_iat.png` (clip_image003, transparente) + `logo_parana_sedest.png`
(clip_image001) — fontes vieram do clipboard do Office do usuário (msohtmlclip). O script recorta bordas, iguala
altura (200px, sem distorcer). Gera DUAS versões: `logos_combinado.png` (cartão branco arredondado → SIDEBAR,
fundo escuro, via `st.image`) e `logos_combinado_header.png` (fundo #f1f5f9 = cor do cabeçalho, branco trocado
por essa cor via numpy → CABEÇALHO mescla sem caixa branca, base64 via `_logo_uri()` ACIMA do "Atualizado").
Para regenerar: `python dashboard/assets/montar_logos.py`. (`iat_logo.png` antigo sem uso.)
Título alterado para "Central de Projetos Hidrelétricos do Estado do Paraná" (config.yaml `dashboard.titulo`
+ page_title + fallback no app.py). NÃO confundir com `excel.sheet_name` "Central de Processos HIDREL" (aba do Excel).
Botões renomeados: Google Earth Web / Google Maps / Programa Google Earth Desktop / Programa QGIS (empilhados no
painel; 2×2 no Relatório). Contador ao lado de "🔍 Filtros" (badge `N de M`, verde quando filtrado; via `st.empty()`).
CAMADA DE BACIAS (PR): `data/bacias_parana.geojson` (298 KB, WGS84, 18 polígonos, campo NOME). Origem: baixei
`bacias.rar` do IAT (.../documento/2020-07/bacias.rar), extraí com `tar.exe` (bsdtar lê RAR4), converti com `ogr2ogr`
do QGIS: `-s_srs EPSG:31982 -t_srs EPSG:4326 -simplify 250 -oo ENCODING=ISO-8859-1`. `load_bacias()` (cache) lê o
GeoJSON + centroides; `build_folium_map` adiciona FeatureGroup "🌊 Bacias hidrográficas" (oculto, alternável) com
GeoJson (limite azul + fill 5%) + tooltip NOME + rótulos DivIcon (halo branco). Validado: 19 paths + nomes corretos.
## ✅ CONCLUÍDO — CAMADAS TEMÁTICAS do GeoPR/IAT no mapa (2026-06-20)

Implementado via **WMS por streaming** do ArcGIS Server do GeoPR (decisão melhor que baixar shapefiles:
sem download, sempre atualizado, e adicionar nova camada = 1 linha no `config.yaml`).

**Descoberta da infraestrutura (para futuras camadas):**
- GeoPR roda **ArcGIS Server** (não GeoServer): raiz `https://geopr.iat.pr.gov.br/server/rest/services` (ArcGIS 11.5).
- Catálogo principal: pasta **`00_PUBLICACOES`** com **960 camadas** (cada uma como FeatureServer + MapServer).
  Listar: `curl -sk ".../server/rest/services/00_PUBLICACOES?f=json"`.
- ⚠️ Certificado: `curl`/navegador VALIDAM (`ssl_verify_result: 0`), mas o **WebFetch** falha ("unable to verify
  first certificate") e o **urllib do Python** também — por isso o helper de legenda usa `ssl.CERT_NONE`.
- WMS habilitado por serviço: `.../server/services/<pasta>/<camada>/MapServer/WMSServer` (layer name = `"0"`).
  Testar: `...WMSServer?request=GetCapabilities&service=WMS` (200 = habilitado; 400 = sem WMS).
- ⚠️ MapBiomas (`Uso_e_Cobertura_MapBiomas_2023`, raiz) tem WMS **desligado** (400) e não é cacheado (tile XYZ
  indisponível). Ficou de fora (precisaria esri-leaflet ou o /export REST, que o folium não consome como XYZ).
- Pasta `06_APP_PARANAMAISVERDE` veio **vazia** via REST (restrita) → APP vem de `00_PUBLICACOES/fbds_app`.

**Camadas adicionadas (8, em `config.yaml` → `camadas_wms`), todas overlays OCULTAS por padrão:**
🏺 Sítios Arqueológicos (`iap_sitios_arqueologicos_cnsa`, pontos) · 🌱 APP (`fbds_app`) · 🌳 Vegetação Nativa 2021
(`vegetacao_nativa_2021`) · 🏞️ UC Estaduais (`unidades_conservacao_estaduais`) · 🏞️ UC Federais (`uc_federal_cnuc_mma`)
· 🌿 RPPN Estaduais (`iap_rppn_estadual_pr`) · ⛰️ Solos EMBRAPA (`solos_parana_embrapa`) · 🪨 Geologia ZEE (`zee_geologia`).
⏱️ Performance (1ª tile, zoom~12): pontos ~rápido, vegetação 2,8s; pesadas (APP, solos, geologia, UC) 8-12s a frio
(ArcGIS cacheia depois). Aceitável por serem opt-in. Uso/Cobertura 2012 (`map_uso_cobertura_terra_2012`) = timeout
>25s, NÃO incluída.

**Código:** `config.yaml` ganhou `geopr_wms_base`, `geopr_rest_base` e a lista `camadas_wms` (nome+service+opacidade).
`dashboard/app.py`: imports `ssl`/`urllib.request`; helper `load_wms_legend()` (REST `/MapServer/legend?f=json`,
cache 1h, swatch base64 + rótulo); `build_folium_map` faz loop em `camadas_wms` adicionando `folium.raster_layers.
WmsTileLayer(layers="0", version="1.1.1", overlay, show=False, opacity)` ANTES do `LayerControl`; página Mapa ganhou
expander "🎨 Legenda das camadas temáticas" (selectbox de camada → swatches) + caption atualizado.
Para ADICIONAR camada nova: achar o service em `00_PUBLICACOES`, confirmar WMS (200), e pôr 1 entrada em `camadas_wms`.

**Validado no preview (2026-06-20, servidor reiniciado limpo):** 8 camadas no LayerControl; ao ligar Sítios
Arqueológicos as **12 tiles WMS carregaram** (loaded:12, failed:0) — cert OK no navegador; sem erro no console;
helper de legenda retorna 227 classes (solos) / 4 (vegetação) / 1 (sítios). `py_compile` OK.

## ✅ CONCLUÍDO — Controles de camadas tirados de CIMA do mapa → menu nativo (2026-06-20)
Pedido do usuário: o painel do Leaflet (LayerControl `collapsed=False`) ficou GRANDE demais sobre o mapa (8 temáticas
+ base + bacias) e atrapalhava ver o mapa. SOLUÇÃO: tirar do mapa e usar **widgets nativos do Streamlit**.
- `build_folium_map` agora recebe `base_map`, `show_labels`, `show_bacias`, `wms_on` e adiciona SÓ o que está marcado;
  **removido o `folium.LayerControl`** e o dict global `BASE_MAPS` (rótulo→tiles/attr/maxzoom) define os 3 mapas base.
- Posição final (2ª iteração, pedido do usuário): o menu fica **ENTRE a caption "Exibindo…" e o mapa** (não embaixo).
  Como os widgets vêm ANTES do mapa no código, é direto: `st.container(border=True)` com `st.radio("🗺️ Mapa base")`
  + `st.multiselect("Camadas …")` (Rótulos, Bacias e as 8 temáticas) + expander de legenda; DEPOIS `build_folium_map`
  com as seleções; DEPOIS `st.columns([7,3])` → `st_folium` no `map_col`. (1ª iteração usava `map_slot`/`st.container()`
  para pôr o mapa acima dos controles — descartado quando o usuário pediu o menu acima do mapa.)
- ⚠️ Se o usuário vir "duplicado", pode ser aba com versão antiga em cache (LayerControl do Leaflet ainda no mapa) —
  recarregar resolve; no app servido `.leaflet-control-layers` não existe.
- 3ª iteração (pedido do usuário: "2 menus parecidos"): o usuário achou que o `st.multiselect` (que LIGA camadas) e o
  expander de legenda (que tinha um `st.selectbox` "Camada:" só p/ MOSTRAR cores) eram dois menus duplicados. FIX:
  multiselect → **checkboxes** (10: 8 temáticas em `st.columns(2)` + Rótulos + Bacias), helper `_cam_key()` p/ key
  segura. Legenda virou **contextual**: expander "🎨 Cores das camadas ligadas (N)" mostra swatches SÓ das camadas
  marcadas (`wms_on`), cap 12 classes/camada + "… +N classes" (solos tem 227). Sem 2º dropdown. Validado: 10 checkboxes,
  0 multiselect de camadas, marcar Sítios Arqueológicos → 12 tiles WMS + legenda "(1)". `py_compile` OK.
- ⚠️ GOTCHA CSS (ícones viram texto): a regra `[data-testid="stAppViewContainer"] * { font-family: Inter }` no `<style>`
  (topo do app.py) sobrescrevia a fonte de ícones do Streamlit → seta do expander e colapso da sidebar apareciam como
  texto literal ("keyboard_arrow_right", "keyboard_double_arrow_left"). FIX: regra restaurando
  `font-family:'Material Symbols Rounded',… !important` em `[data-testid="stIconMaterial"], span[class*="material-symbols"]`.
  (A fonte Material já carrega via Streamlit; era só o override do `*`.) NÃO remover ao mexer no CSS de fonte.
- ⚠️ Risco evitado: toggle de camada dispara rerun → rebuild do mapa. TESTADO que o `st_folium` (key fixa "mapa_folium")
  **preserva zoom/centro** entre reruns (setView Curitiba z12 → rerun → continuou lá). Sem reset de vista.
- Validado no preview: LayerControl removido do mapa (`.leaflet-control-layers` ausente); radio+multiselect abaixo do
  mapa (controlsTop 1214 > mapBottom 1175); clicar "🛰️ Satélite" trocou tiles p/ Esri World_Imagery; headless: bacias
  GeoJson + 8x WMSServer no HTML. `py_compile` OK.

## ✅ CONCLUÍDO — Botão recolher sidebar sempre visível + AUDITORIA COMPLETA (2026-06-20)
**Botão de recolher a barra de filtros:** estava `visibility:hidden` (só no hover). CSS: `[data-testid=
"stSidebarCollapseButton"]{visibility:visible!important;opacity:1!important}` + texto antes da flecha via
`[data-testid="stSidebarHeader"]::before{content:"Clique na flecha para recolher a aba de filtros →";flex:1…}`.

**Auditoria (pedida pelo usuário) — bugs encontrados e corrigidos:**
1. ⚠️ BUG (página Licenças, exceção): `st.dataframe(...) if cond else st.success(...)` como STATEMENT solto disparava o
   "magic write" do Streamlit no valor de retorno → `SyntaxError: '(' was never closed`. FIX: virou `if/else` explícito
   (2 abas: Vencidas e A Vencer). REGRA: nunca usar ternário `A if c else B` como statement com funções `st.*` multilinha.
2. ⚠️ BUG (Limpar Filtros não funcionava): os `st.multiselect` não tinham `key=`, então o botão apagava chaves `f_*`/
   "Tipologia"/"Situação" inexistentes. FIX: cada filtro ganhou `key="f_<nome>"` e o botão apaga `k.startswith("f_")`.
   Testado: PCH → "499 de 1.598" → Limpar → "1.598 de 1.598" + chips zerados.
3. 🧹 Código morto removido: `menu_links()` e `_popup_menu()` (definidos, sem nenhuma chamada; checkpoint já previa remoção).
4. (ícones Material já corrigidos acima — ver gotcha CSS.)
**Auditoria — sem problemas:** gramática/ortografia dos textos OK (PT-BR com acentuação correta); 14 testes do pipeline
passam (`pytest -q`); as 6 páginas carregam sem exceção; console só com warnings de lib (Plotly/popper, inofensivos);
log do servidor só com `ConnectionResetError` benigno (navegador fecha conexão no reload, Windows/asyncio).

## ✅ CONCLUÍDO — Projeto PRONTO para deploy público (Streamlit Cloud) (2026-06-20)
Usuário quer link público compartilhável; escolheu **Streamlit Community Cloud** + acesso **público**.
- **PUBLIC_MODE** (`app.py`): `os.environ.get("IAT_PUBLIC")=="1" or not sys.platform.startswith("win")`. Na nuvem
  (Linux) ou com `IAT_PUBLIC=1` fica True. Botões de abrir refeitos em `open_buttons(row, key_prefix)`:
  - PUBLIC_MODE → `st.link_button` (Earth Web `_earth_web_url`, Maps `_maps_url`) que abrem no navegador do VISITANTE;
    QGIS/Earth Desktop ocultos (só fazem sentido local). Local (Windows) → mantém os 4 botões via `launch_desktop`.
  - Substituídos os 2 blocos antigos (painel do mapa `open_buttons(row,"open")`; Relatório `open_buttons(srow,"rel")`).
- **requirements.txt** ENXUTO (só dashboard: streamlit, streamlit-folium, folium, plotly, pandas, pyyaml). Tirado
  `arcgis` (gigante, estoura o build) e libs de pipeline → movidas p/ **requirements-pipeline.txt**. Streamlit Cloud
  usa sempre o requirements.txt da raiz, por isso ele tem que ser o do dashboard.
- **.gitignore**: `data/processed/` voltou a ser ignorado MAS com exceções `!` p/ os 4 arquivos que o dashboard lê
  (`processos_hidreletricas.csv`, `resumo_indicadores.json`, `metadados_execucao.json`, `erros_validacao.csv`);
  `data/bacias_parana.geojson` já não era ignorado. Adicionado `.claude/`. O `.geojson` GRANDE de pontos NÃO é
  usado pelo dashboard (mapa é montado do CSV) → fica de fora.
- **git** inicializado (branch main, 1º commit, 59 arquivos; identidade local Rafael/bol.rafaelaugusto@iat.pr.gov.br).
  Falta só: criar repo no GitHub + push + conectar no share.streamlit.io (main file `dashboard/app.py`). Passo a passo
  completo em **DEPLOY.md**.
- Validado: `py_compile` OK; 6 páginas sem exceção após refactor (modo local, 4 botões intactos); PUBLIC_MODE testado
  por env (False no Windows, True com IAT_PUBLIC=1); `.gitignore` sobe só os 5 arquivos de dados certos.
- ⚠️ Para futuro: se quiser senha, usar `st.secrets` (acesso hoje é público). Atualizar dados = rodar pipeline local +
  commit/push → Streamlit Cloud redeploya sozinho.

## ✅ CONCLUÍDO — Botões QGIS e Google Earth Desktop FUNCIONANDO na nuvem p/ visitantes (2026-06-20)
Pedido: no app publicado, qualquer visitante com os PROGRAMAS instalados deve conseguir abrir o ponto no
QGIS / Google Earth Desktop da própria máquina. SOLUÇÃO escolhida (mais robusta): o botão **baixa um arquivo**
que o programa abre por **associação de arquivo** — `.kml`→Google Earth Pro, `.qgs`→QGIS. Requer SÓ o programa
instalado (sem handler/protocolo/Python por visitante). Associações confirmadas no Windows: `.kml`→GoogleEarth,
`.qgs`/`.qgz`→QGIS Project.
- `dashboard/app.py`: `build_kml(lat,lon,nome)` (LookAt+Placemark) e `build_qgs(lat,lon,nome)` (satélite Esri
  centralizado, half=600 m). `open_buttons` em PUBLIC_MODE agora rende 4: 🌐 GE Web + 📍 Maps (`st.link_button`)
  e 🖥️ GE Desktop (.kml) + 🗺️ QGIS (.qgs) (`st.download_button`). Local segue com `launch_desktop` (4 botões diretos).
- ⚠️ O `.qgs` é gerado a partir de **template escrito pelo PRÓPRIO QGIS** (`dashboard/assets/qgis_template.qgs`),
  não à mão (XML à mão abria mas NÃO renderizava/zoom). Gerado via `src/gerar_template_qgis.py` (roda no Console
  Python do QGIS: `proj.write(...)`), depois parametrizado: os 4 valores do `<mapcanvas><extent>` viraram
  `__IAT_XMIN/YMIN/XMAX/YMAX__` e `projectname` virou `__IAT_NOME__`. `build_qgs` faz `_to3857(lat,lon)` e
  `str.replace`. Para regenerar o template: abrir QGIS → Console Python → rodar `src/gerar_template_qgis.py` →
  reparametrizar (substituir os 4 nº do extent do mapcanvas pelos placeholders + projectname).
- VALIDADO no QGIS 4.0.3 (2 pontos: Curitiba e oeste do PR): `.qgs` abre por duplo-clique, satélite Esri
  renderiza, centralizado no ponto (escala ~1:18 mil), EPSG:3857. VALIDADO no app PUBLICADO: os 4 botões aparecem
  no painel do ponto (print confirmou 🖥️ GE Desktop (.kml) e 🗺️ QGIS (.qgs) + legenda). py_compile OK; pushado
  (commit c75a208) e Streamlit Cloud redeployou sozinho.
- Limitação aceita: sem marcador no QGIS (só satélite centralizado); marcador exigiria `.qgz` com geojson embutido.

## ✅ CONCLUÍDO — UI pt-BR, regras de gestão, semáforo, ficha, marcador QGIS (2026-06-21)
Pedidos do usuário: traduzir inglês, mover Limpar, e "fazer tudo" da avaliação técnica (manter dados públicos).
**UI:** `st.multiselect` placeholder → "Selecione uma ou mais opções" (era "Choose options"); labels pt-BR;
botão "🔄 Limpar" movido do fim p/ o TOPO ao lado do contador (compacto, `filtros_header.container()` + colunas);
card Visão Geral "Pendências Críticas"→"Registros c/ Crítica" (682 = registros; 683 = inconsistências, eram conceitos
distintos — não bug); rótulos pt-BR nas colunas do Relatório.
**Pipeline (regras de gestão):** `transform_data.py` → `processo_encerrado` (situação encerrada) + `alerta_validade`
ganhou valor **`data_suspeita`** (validade <1980, >hoje+40 anos, ou < emissão). `validate_data.py` → datas suspeitas
viram CRÍTICO (não "vencida"); vencida real só p/ não-encerrados; **tipologia × potência** (MCH≤0,075 / MGH≤0,5 /
CGH≤5 / PCH≤30 / UHE>30 MW) vira MÉDIO. Resumo: `licencas_vencidas_ativas` (666), `_encerradas` (14),
`datas_suspeitas` (5). Reprocessado: 683 críticos / 512 médios / 26 baixos. 14 testes passam.
**Aba Licenças:** cards "Vencidas (ativas) / A vencer / Vigentes / Sem validade" + "Arquivadas vencidas / Datas
suspeitas"; abas: Vencidas ativas (coluna **dias vencida**), A vencer (**dias p/ vencer**), Datas suspeitas,
Arquivadas vencidas, Análise temporal. Visão Geral "Licenças Vencidas" agora = vencidas ATIVAS; banner de datas suspeitas.
**Semáforo técnico** (`semaforo(row)` + `_GRAV_LINHA` por linha): 🔴 crítico > ⚪ histórico(encerrado) > 🟡 médio > 🟢 ok.
Usado no mapa (3ª opção "Colorir por: Semáforo" + legenda), na tabela do Relatório (coluna 🚦) e na ficha.
**Ficha do Empreendimento** (`render_ficha(row, key_prefix)`): semáforo + situação + pendências (N críticas/médias) +
botões de abrir + **coordenada copiável** (`st.code`) + lat/lon separados + dados. Usada no painel do mapa e no
Relatório (ao selecionar linha → "Ficha do Empreendimento"). Camadas do mapa agora em `st.expander` (recolhível).
**Marcador no QGIS (.qgs autossuficiente):** ⚠️ `.qgz` com geojson embutido NÃO funciona (QGIS não extrai dados de
camada de dentro do .qgz → "camadas indisponíveis"). SOLUÇÃO: **GeoJSON INLINE como datasource** —
`QgsVectorLayer('{...geojson...}', nome, "ogr")` é válido (testado: `INLINE_VALID: True 1`) e o `.qgs` salva a string
embutida → autossuficiente. Template gerado pelo QGIS (`src/gerar_template_qgis.py`, roda no Console Python: satélite
+ ponto inline com marcador vermelho + rótulo `nome`), parametrizado em `dashboard/assets/qgis_template.qgs` com
`__IAT_XMIN/YMIN/XMAX/YMAX__` (extent 3857), `__IAT_LON__`/`__IAT_LAT__` (3x cada) e `__IAT_NOME__` (3x). `build_qgs`
substitui tudo (nome sanitizado p/ JSON+XML: remove `" \\ < > &`). VALIDADO no QGIS 4.0.3: abre com satélite +
marcador vermelho + nome "PCH TESTE OESTE" centralizado. Para regenerar template: rodar `gerar_template_qgis.py` no
Console Python do QGIS → reparametrizar (extent do mapcanvas + nome 3x + lon 3x + lat 3x).
Commits: f85f57b (frentes 1-4) + 6bc0d8a (marcador QGIS) + 580487d (UI). Tudo no GitHub; Streamlit Cloud redeploya.

## ✅ CONCLUÍDO — Suficiência da coordenada + cards reagrupados (2026-06-21, commit 5d60db7)
- **Suficiência técnica da coordenada:** `transform_data.py` mantém `lat_casa_forca`/`lon_casa_forca` (não dropa mais)
  e gera `tem_coord_barragem`, `tem_coord_casa_forca`, `suficiencia_coord` (completa=732 / so_barragem=854 /
  so_casa_forca=4 / ausente=8). Ficha (`render_ficha`) mostra coord da casa de força + `suf_label()`; aba Qualidade
  ganhou seção "Suficiência técnica da coordenada" (4 cards). (Restituição/tomada d'água NÃO existem na fonte.)
- **Visão Geral:** cards reagrupados em 2 linhas rotuladas — "Base e situação" (Total / Em Análise / Sem Coordenada /
  Potência) e "Licenças e qualidade" (Vigentes / Vencidas ativas / A Vencer / Registros c/ Crítica).
- **Paleta:** avaliada — cores SEMÂNTICAS já consistentes (semáforo vermelho/amarelo/verde/cinza + banners); as
  paletas CATEGÓRICAS (situação/tipologia) precisam de muitas cores p/ distinção, então NÃO foram achatadas (achatar
  pioraria). Não houve mudança de paleta (risco cosmético sem ganho claro).

## ✅ CONCLUÍDO — +8 camadas WMS, min_zoom, e status ArcGIS/MapBiomas (2026-06-21, commit 2a962f6)
- **+8 camadas temáticas** (WMS verificado 200 + GetMap real): 🗺️ Uso e Cobertura da Terra (FBDS 2013),
  🦋 Áreas Estratégicas de Conservação, 🪶 Terras Indígenas (CAR), 💧 Hidrografia/Rios, 🏔️ Geomorfologia (ZEE),
  🌾 Aptidão do Solo (ZEE), 📐 Declividade (ZEE), 🌿 RPPN Federais. Total: **16 camadas** em `config.yaml`.
- **min_zoom: 8** nas 7 pesadas (uso/cobertura, solos, geologia, geomorfologia, aptidão, declividade, hidrografia) —
  só carregam ao aproximar (mapa estadual rápido). `build_folium_map` passa `min_zoom` (folium renderiza `minZoom`).
  Caption avisa. Validado: Terras Indígenas → 12 tiles WMS.
- ⚠️ **MapBiomas** (`Uso_e_Cobertura_MapBiomas_2023`) e **Limites_Municipais**: WMS DESLIGADO (400) no GeoPR — não
  dá p/ adicionar como WMS. Usei **FBDS Uso e Cobertura 2013** (WMS ok) como camada de uso/cobertura. MapBiomas exigiria
  integração com o tile service GEE deles (token instável) — fora de escopo.
- ⚠️ **ArcGIS Online**: `src/publish_arcgis.py` pronto, mas exige credenciais do usuário (`ARCGIS_USERNAME`/`PASSWORD`
  ou `ARCGIS_TOKEN` no `.env`) + lib `arcgis`. NÃO executável por mim (não posso ter/digitar senha). Passo p/ o usuário:
  pôr as credenciais no `.env`, `pip install arcgis`, `python src/publish_arcgis.py`.

Auditoria final (2026-06-21): `py_compile` OK; **14 testes passam**; **6 páginas sem exceção**; **0 erros de console**;
camadas novas renderizam. Tudo no GitHub (vaugrafa-stack/hidreletricas-iat); Streamlit Cloud redeploya automático.
