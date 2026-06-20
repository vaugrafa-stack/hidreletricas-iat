# Rotina de Revisão Geoespacial — Hidrelétricas IAT

## Fluxo de uso

```
PASSO 1 — Exportar KML/KMZ
  py src/geo_review/01_exportar_kml.py

PASSO 2 — Revisão visual (manual, Google Earth Pro ou QGIS)
  Abrir: data/processed/pontos_revisao_google_earth.kmz
  - Conferir cada marcador [BARR] (barragem)
  - Verificar se [CF] (casa de força) está correto
  - Reposicionar marcadores quando necessário
  - NÃO apagar placemarks — apenas reposicionar
  - Exportar como KML → salvar em data/processed/pontos_corrigido_tecnico.kml

PASSO 3 — Importar corrigido e gerar relatório
  py src/geo_review/02_importar_corrigido.py

PASSO 4 (opcional) — Relatório atualizado de pendentes
  py src/geo_review/03_relatorio_pendentes.py
```

## Prefixos dos placemarks no KML

| Prefixo     | Significado                                      |
|-------------|--------------------------------------------------|
| `[BARR]`    | Ponto de barragem (coordenada da planilha)       |
| `[KMZ]`     | Coordenada alternativa KMZ (referência)          |
| `[CF]`      | Casa de força                                    |
| `[SEM COORD]` | Registro sem coordenadas válidas              |

## Status de georreferenciamento

| Status                    | Descrição                                               |
|---------------------------|---------------------------------------------------------|
| `Validado`                | Coordenada confirmada sem alteração                     |
| `Corrigido`               | Coordenada reposicionada pelo técnico                   |
| `Pendente de validação`   | Ainda não revisado visualmente                          |
| `Sem imagem suficiente`   | Imagem histórica insuficiente para confirmar            |
| `Coordenada inconsistente`| Coordenada fora dos limites esperados                   |
| `Não identificado`        | Sem coordenadas disponíveis                             |

## Grau de confiança

| Grau      | Critério                                                    |
|-----------|-------------------------------------------------------------|
| `Alto`    | Estrutura claramente identificável na imagem                |
| `Médio`   | Estrutura provável com alguma incerteza                     |
| `Baixo`   | Estrutura pouco visível, depende de confirmação documental  |
| `Pendente`| Não foi possível concluir                                   |

## Saídas geradas (em data/processed/)

| Arquivo                                | Conteúdo                                      |
|----------------------------------------|-----------------------------------------------|
| `pontos_originais.geojson`             | Pontos exportados da planilha original        |
| `pontos_revisao_google_earth.kml`      | KML para revisão no Google Earth Pro / QGIS   |
| `pontos_revisao_google_earth.kmz`      | Versão comprimida do KML acima                |
| `pontos_corrigidos.csv`                | Base derivada com todos os campos novos       |
| `pontos_corrigidos.geojson`            | GeoJSON com coordenadas corrigidas            |
| `relatorio_validacao_geoespacial.csv`  | Relatório de validação por protocolo          |
| `planilha_atualizacao_coordenadas.xlsx`| Excel com 4 abas: completo, pendentes, relatório, stats |

## Regras de segurança

- A planilha original `.xlsm` nunca é modificada (aberta em `read_only=True`)
- Coordenadas originais são preservadas em `latitude_barragem_original` / `longitude_barragem_original`
- Nenhuma coordenada inferida é gravada sem passar pela revisão visual do técnico
- A classificação automática marca como `Pendente de validação` qualquer ponto não revisado
