# Central de Processos Hidrelétricos — Dashboard IAT/PR

Dashboard institucional para acompanhamento de processos de licenciamento ambiental de empreendimentos hidrelétricos no Paraná, mantido pelo Instituto Água e Terra (IAT).

---

## Pré-requisitos

- Python 3.10 ou superior
- Arquivo `.xlsm` acessível localmente (via Google Drive for Desktop ou caminho direto)
- Opcional: conta no ArcGIS Online/Enterprise para publicação de Feature Layer

---

## Instalação

```bash
cd C:\Users\rafae\Downloads\IAT\Dashboard

# Instalar dependências
pip install -r requirements.txt

# Copiar e editar variáveis de ambiente
copy .env.example .env
# Edite o .env com o caminho real do Excel
```

---

## Configuração do caminho do Excel

No arquivo `.env`, defina:

```
EXCEL_LOCAL_PATH=C:/Users/rafae/Google Drive/Meu Drive/Central_de_Processos_HIDRELETRICAS_COM_MACRO e Links.xlsm
```

> O arquivo precisa existir localmente. Se usar o Google Drive for Desktop, o caminho típico no Windows é:
> `C:\Users\<usuario>\Google Drive\Meu Drive\<nome_do_arquivo>`
>
> Também é possível usar o caminho de Download direto (como está configurado por padrão no `config.yaml`).

---

## Estrutura do projeto

```
/README.md
/requirements.txt
/.env.example
/.gitignore
/config.yaml           ← parâmetros editáveis (colunas, cores, limites, etc.)
/data/
  raw/                 ← não usado diretamente (reservado para cópias)
  processed/           ← saídas do pipeline
    processos_hidreletricas.csv
    processos_hidreletricas.geojson
    erros_validacao.csv
    resumo_indicadores.json
    metadados_execucao.json
/logs/
  pipeline.log
  watch.log
  arcgis.log
/src/
  extract_excel.py     ← leitura segura do .xlsm
  transform_data.py    ← padronização, limpeza, precisão e links
  validate_data.py     ← validação e relatório de erros
  run_pipeline.py      ← pipeline principal
  watch_file.py        ← monitoramento de alterações
  publish_arcgis.py    ← publicação opcional no ArcGIS
  gerar_planilha_qgis.py  ← gera cópia .xlsm com coluna "ABRIR NO QGIS"
  qgis_handler/        ← handler do protocolo qgis:// (instalar/desinstalar/README)
  gearth_handler/      ← handler do protocolo gearth:// (Google Earth Pro)
/dashboard/
  app.py               ← dashboard Streamlit
  utils.py             ← utilitários compartilhados
/tests/
  test_transform_data.py
  test_validate_data.py
```

---

## Execução

### 1. Atualização manual (uma vez)

```bash
python src/run_pipeline.py
```

### 2. Dry-run (sem salvar arquivos)

```bash
python src/run_pipeline.py --dry-run
```

### 3. Monitoramento automático

Detecta alterações no arquivo Excel após salvar e sincronizar:

```bash
python src/watch_file.py
```

> O script executa o pipeline automaticamente sempre que detectar alteração no arquivo.
> O intervalo de verificação é configurável em `config.yaml` (padrão: 60 segundos).

### 4. Abrir o dashboard

```bash
streamlit run dashboard/app.py
```

O dashboard abrirá em `http://localhost:8501`.

---

## Abrir empreendimentos no mapa (Navegador / Google Earth / QGIS)

Cada ponto pode ser aberto de 3 formas, tanto no **menu do ponto no mapa** quanto nas **3 colunas do Relatório Analítico**:

| Opção | Como funciona | Link gerado |
|-------|---------------|-------------|
| 🌐 **Navegador** | Google Earth Web (abre no browser, funciona em qualquer PC) | `https://earth.google.com/web/@lat,lon,...` (`link_google_earth`) |
| 🖥️ **Google Earth desktop** | Google Earth Pro via handler `gearth://` (gera KML e voa até o ponto) | `gearth://lat,lon` (`link_gearth`) |
| 🗺️ **QGIS** | QGIS via handler `qgis://` (abre mapa base + camada, centralizado no ponto) | `qgis://lat,lon` (`link_qgis`) |

> **Como abrir no dashboard:** clique num ponto do mapa (ou selecione uma linha no Relatório) e use os
> **botões 🌐/🖥️/🗺️ no painel** — o servidor local abre o programa na sua máquina. Esse caminho é o confiável;
> os links dentro do *popup* do mapa podem ser bloqueados pelo navegador (o mapa roda num iframe restrito).
> Os botões do dashboard **não dependem** do handler de protocolo registrado (chamam o script diretamente).

### Instalar os handlers de desktop (uma vez por computador)

O Google Earth Web abre direto no navegador. Os **botões** do dashboard já funcionam sem registro. O handler
de protocolo só é necessário para o **botão da planilha Excel** (`qgis://`) e para clicar links `qgis://`/`gearth://`
fora do dashboard. Para instalá-los (não precisa de administrador):

```bash
src\qgis_handler\instalar_handler.bat      # protocolo qgis://
src\gearth_handler\instalar_handler.bat    # protocolo gearth://
```

Para remover: os respectivos `desinstalar_handler.bat`. Detalhes em `src/qgis_handler/README_QGIS.md`.

> Pré-requisitos: QGIS e/ou Google Earth Pro instalados (detectados automaticamente).
> Logs de diagnóstico em `%TEMP%\qgis_open_handler.log`.

---

## Gerar a planilha Excel com a coluna "ABRIR NO QGIS"

Cria uma **cópia** da planilha original com uma coluna de botão que abre o QGIS em cada empreendimento.
O original **não é alterado**; a edição é feita diretamente no XML interno do `.xlsm`, preservando
macros, gráficos e tabelas intactos.

```bash
python src/gerar_planilha_qgis.py
```

Saída: `<nome_original>_COM_QGIS.xlsm`, ao lado do original. A coluna é uma **fórmula** que se atualiza
sozinha quando você corrigir as coordenadas (basta re-rodar o script após editar a planilha original).

> Requer o handler `qgis://` instalado (passo acima). Na 1ª vez que clicar, o Excel pode exibir um aviso de
> segurança para protocolos personalizados — basta permitir.

---

## Publicação no ArcGIS

### Configurar credenciais no .env

```
ARCGIS_PORTAL_URL=https://www.arcgis.com
ARCGIS_USERNAME=seu_usuario
ARCGIS_PASSWORD=sua_senha
# Ou via token:
# ARCGIS_TOKEN=seu_token
```

### Primeira publicação (cria nova camada)

```bash
python src/publish_arcgis.py
```

O script exibirá o `ARCGIS_FEATURE_LAYER_ID` da nova camada. Adicione ao `.env`.

### Atualizar camada existente

```bash
# Defina ARCGIS_FEATURE_LAYER_ID no .env e execute:
python src/publish_arcgis.py
```

### Dry-run (simula sem publicar)

```bash
python src/publish_arcgis.py --dry-run
```

### Conectar ao ArcGIS Dashboard

1. Abra o ArcGIS Online → Conteúdo → localize a Feature Layer publicada.
2. Crie um novo Dashboard (ArcGIS Dashboards).
3. Adicione a Feature Layer como fonte de dados.
4. Configure widgets de mapa, gráficos e indicadores usando os campos padronizados.

---

## Arquivos de saída

| Arquivo | Descrição |
|---------|-----------|
| `processos_hidreletricas.csv` | Base completa padronizada, incluindo registros sem coordenada |
| `processos_hidreletricas.geojson` | Apenas registros com coordenada válida, em WGS84 (EPSG:4326) |
| `erros_validacao.csv` | Inconsistências por linha com gravidade (CRITICO/MEDIO/BAIXO) |
| `resumo_indicadores.json` | Indicadores agregados (por tipologia, bacia, situação, etc.) |
| `metadados_execucao.json` | Log de execução (data, contagens, status, duração) |

---

## Interpretando o relatório de validação

O arquivo `erros_validacao.csv` contém:

- **CRITICO**: impede uso correto do registro (sem protocolo, sem coordenada, coordenada fora do PR, licença vencida não-encerrada, duplicata)
- **MEDIO**: reduz qualidade (sem técnico, sem situação, sem bacia, sem nº de licença em processo deferido, **coordenada repetida entre empreendimentos diferentes**)
- **BAIXO**: impacto menor (sem rio, sem potência, **coordenada de baixa precisão ≤2 casas decimais**)

### Conferência de precisão das coordenadas

O pipeline classifica cada ponto por `precisao_coord` (a partir de `n_decimais_coord`):

- **alta** (≥4 casas, ~10 m) · **media** (3 casas, ~100 m) · **baixa** (≤2 casas, ~1 km)

Na página **Qualidade dos Dados** do dashboard, a seção *Precisão das Coordenadas* lista os **pontos a conferir**
(baixa/média precisão + coordenadas repetidas) com exportação CSV — apoio direto à revisão das coordenadas.

Para corrigir: abra a planilha original (`coluna linha_original` indica a linha exata), corrija o valor, salve e aguarde sincronização.

---

## Como a atualização automática funciona

```
[Excel editado e salvo]
        ↓
[Google Drive for Desktop sincroniza o arquivo]
        ↓
[watch_file.py detecta alteração de hash MD5]
        ↓
[Pipeline executa automaticamente]
        ↓
[data/processed/ atualizado]
        ↓
[Dashboard Streamlit relê os arquivos]
```

> **Importante:** O arquivo deve ser **salvo** no Excel antes da sincronização. Arquivos com fórmulas não calculadas podem ter valores desatualizados. Salve com Ctrl+S antes de fechar.

---

## Configurações editáveis (config.yaml)

| Parâmetro | Descrição |
|-----------|-----------|
| `excel.local_path` | Caminho padrão do arquivo (substituído pelo .env) |
| `dias_alerta_vencimento` | Dias para considerar licença "a vencer" (padrão: 90) |
| `coordenadas` | Limites de lat/lon válidos para o Paraná |
| `cores_situacao` | Cor hex por situação do processo |
| `cores_tipologia` | Cor hex por tipologia |
| `watch.intervalo_segundos` | Frequência do monitoramento automático |

---

## Limitações conhecidas

1. O campo `link_sga` não possui coluna dedicada na planilha — é inferido da coluna OBS.
2. Municípios com múltiplos nomes (separados por " / ") são tratados como string única nos filtros principais.
3. A publicação no ArcGIS requer o pacote `arcgis` (SDK pesado, ~500 MB). Para uso apenas local, pode ser ignorado.
4. O dashboard Streamlit não atualiza automaticamente em tempo real — recarregue a página após execução do pipeline.
5. Fórmulas do Excel não são recalculadas pelo pipeline. O arquivo deve estar salvo com valores calculados.
6. Os botões **QGIS** e **Google Earth desktop** dependem do handler instalado em cada PC (ver seção própria). O **Navegador** (GE Web) funciona em qualquer lugar.
7. A precisão (`precisao_coord`) é estimada pelas casas decimais informadas — indica a granularidade do dado na planilha, não a exatidão real da localização.

---

## Manutenção futura

- Para adicionar novo campo: editar `config.yaml` (seção `column_mapping`) e reiniciar o pipeline.
- Para alterar cores por situação: editar `config.yaml` (seção `cores_situacao`).
- Para alterar limite de alerta: editar `config.yaml` (`dias_alerta_vencimento`).
- Para adicionar nova aba como fonte: alterar `config.yaml` (`excel.sheet_name`).
- Para reinstalar dependências: `pip install -r requirements.txt`.
