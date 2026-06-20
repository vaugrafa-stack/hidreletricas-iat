# Abrir no QGIS — coluna estilo "Google Earth"

Permite **clicar e abrir o QGIS já centralizado no empreendimento**, do mesmo modo
que a coluna `LINK EARTH NAVEGADOR WEB` abre o Google Earth. Como o QGIS é um
programa de desktop (não abre por URL como o Earth), usamos um **handler do
protocolo `qgis://`**: o link é montado a partir das coordenadas e, ao ser
clicado, o handler abre o QGIS com mapa base (OpenStreetMap) + a camada de
empreendimentos, centralizado no ponto.

## 1. Instalar o handler (uma vez por computador)

1. Abra a pasta `src/qgis_handler`.
2. Dê **duplo-clique em `instalar_handler.bat`**.
   - Não precisa de administrador (registra só no seu usuário).
   - Para remover depois: `desinstalar_handler.bat`.
3. Teste rápido — no menu Iniciar/Executar (Win+R) digite:
   ```
   qgis://-24.281655,-49.695021
   ```
   O QGIS deve abrir centralizado nesse ponto (a 1ª abertura demora alguns segundos).

> Pré-requisito: QGIS instalado (detectado automaticamente em `C:\Program Files\QGIS*`).
> Em caso de erro, veja o log em `%TEMP%\qgis_open_handler.log`.

## 2. Adicionar a coluna na planilha (sem alterar macros/fórmulas)

A planilha é uma **Tabela do Excel com macros** — por segurança **não** a
reescrevemos por código. Em vez disso, você adiciona a coluna no próprio Excel
(que preserva tudo):

1. Abra a planilha no Excel.
2. Na primeira coluna vazia à direita, escreva o título, ex.: **`ABRIR NO QGIS`**.
3. Na primeira célula de dados dessa coluna, cole a fórmula abaixo e tecle Enter
   (a Tabela preenche todas as linhas sozinha):

   **Excel em português (pt-BR):**
   ```
   =SE([@[LATITUDE BARRAGEM]]="";"";HIPERLINK("qgis://"&SUBSTITUIR([@[LATITUDE BARRAGEM]]&"";",";".")&","&SUBSTITUIR([@[LONGITUDE BARRAGEM]]&"";",";".");"Abrir no QGIS"))
   ```

   **Excel em inglês:**
   ```
   =IF([@[LATITUDE BARRAGEM]]="","",HYPERLINK("qgis://"&SUBSTITUTE([@[LATITUDE BARRAGEM]]&"",",",".")&","&SUBSTITUTE([@[LONGITUDE BARRAGEM]]&"",",","."),"Abrir no QGIS"))
   ```

   > O `SUBSTITUIR(...;",";".")` garante ponto decimal no link mesmo no Excel pt-BR.
   > Para usar a coordenada da **casa de força** quando a barragem estiver vazia,
   > troque as referências por `[@[LATITUDE CASA FORÇA]]` / `[@[LONGITUDE CASA FORÇA]]`
   > dentro de um `SE([@[LATITUDE BARRAGEM]]="" ; ...)`.

4. Pronto: a coluna mostra **"Abrir no QGIS"** clicável, igual à do Google Earth.

## 3. No dashboard

A coluna `link_qgis` já é gerada pelo pipeline e aparece como botão
**"🗺️ QGIS"** na tabela do Relatório Analítico e no painel de detalhes do mapa.
Para os links funcionarem no navegador, o handler do passo 1 precisa estar instalado.

## Observações
- O link do QGIS aponta para o desktop local; ao contrário do Google Earth (web),
  ele depende do handler instalado em cada PC. Por isso o instalador é simples e
  reversível.
- O handler abre uma nova janela do QGIS a cada clique.
