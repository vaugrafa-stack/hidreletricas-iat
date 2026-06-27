# 🛡️ Módulo de Fiscalização, Prazos e Notificações — IAT/PR

Acompanhamento do **atendimento de condicionantes** e dos **vencimentos de licenças** por
empreendimento, com **notificação por e-mail ao empreendedor** (com pedido de confirmação de
leitura) com antecedência configurável.

## O que entrou

| Pedido | Onde |
|---|---|
| Fiscalização de condicionantes por empreendimento | Página **🛡️ Fiscalização → Condicionantes** |
| Acompanhar licenças, prazo, vencimento | Página **🛡️ Fiscalização → Agenda de prazos** (+ a já existente *Licenças e Vencimentos*) |
| E-mail ao empreendedor com confirmação de leitura, meses antes | **🛡️ Fiscalização → Notificações** e o CLI `src/notificacoes.py` |
| Busca por CNPJ ou nome | Campo **🔎 Buscar por CNPJ ou nome** na barra lateral (vale para todo o painel) |
| Alterar coordenada e corrigir "na planilha" | Ficha do empreendimento → **✏️ Corrigir coordenada (interno)** |
| Acesso só para funcionários internos | **🔧 Acesso interno (edição)** na barra lateral (senha) |
| Redimensionar as janelas | **⚙️ Tamanho dos painéis** na barra lateral (altura de mapa e tabelas) |
| Clicar numa categoria do gráfico filtra tudo | Visão Geral → **clique numa barra** (ex.: tipo de licença *LO*) |
| Ponto pelo registro mais recente em nomes duplicados | Mapa → **📌 Mostrar 1 ponto por empreendimento (mais recente)** |

## Acesso interno (edição)

As funções de **edição** (corrigir coordenada, cadastrar/editar condicionantes e contatos,
enviar e-mail) ficam atrás de um desbloqueio na barra lateral (**🔧 Acesso interno**) e são
**ocultas no modo público** (nuvem). Senha padrão: **`FISCAL2026`**.

Para trocar a senha interna, gere o hash e defina a variável `IAT_INTERNO_HASH` no `.env`
(ou edite `_INTERNO_HASH` em `dashboard/app.py`):

```bash
python -c "import hashlib;print(hashlib.sha256('NOVASENHA'.encode()).hexdigest())"
```

## Correção de coordenada — a planilha original **nunca** é alterada

Ao salvar uma correção, ela vai para `data/processed/correcoes_coordenadas.csv` (chave =
protocolo) e é **aplicada por cima** ao carregar os dados (`utils.apply_correcoes`). O `.xlsm`
original permanece intacto — é a regra dura do projeto.

## Condicionantes e contatos (arquivos de dados)

A planilha original **não** traz condicionantes nem e-mail. Estes arquivos são criados sob
demanda e populados pelo usuário (interno) dentro do dashboard:

- `data/fiscalizacao/condicionantes.csv` — uma linha por condicionante (descrição, prazo,
  periodicidade, status, responsável, evidência).
- `data/fiscalizacao/emails_empreendedores.csv` — e-mail por **CNPJ** ou por **nome do
  empreendedor** (aba *Configuração*).
- `data/fiscalizacao/notificacoes_log.csv` — histórico de notificações (token, status, leitura).

## E-mail com confirmação de leitura

Cada e-mail inclui os cabeçalhos de **confirmação de leitura** (MDN):
`Disposition-Notification-To`, `Return-Receipt-To`, `X-Confirm-Reading-To`. Opcionalmente, um
**pixel de rastreio** (`IAT_PIXEL_BASE`) é embutido se você hospedar um endpoint próprio.

- **Sem SMTP configurado:** o sistema gera a **prévia**, o arquivo **`.eml`** e o link
  **`mailto:`** — nada é enviado automaticamente.
- **Com SMTP configurado** (e acesso interno, modo local): botão **✉️ Enviar agora** e envio em
  lote pelo CLI.

### Configurar o SMTP (`.env` na raiz do projeto)

Veja `.env.example`. Variáveis:

```env
IAT_SMTP_HOST=smtp.seuservidor.gov.br
IAT_SMTP_PORT=587
IAT_SMTP_USER=usuario
IAT_SMTP_PASS=senha
IAT_SMTP_FROM=licenciamento@iat.pr.gov.br
IAT_SMTP_TLS=1
IAT_SMTP_CONFIRM_TO=licenciamento@iat.pr.gov.br
# IAT_PIXEL_BASE=https://seu-endpoint/pixel   # (opcional)
```

### Envio em lote / agendado

```bash
py src/notificacoes.py --dias 90            # dry-run: lista o que seria enviado
py src/notificacoes.py --dias 90 --eml out  # gera arquivos .eml (sem enviar)
py src/notificacoes.py --dias 90 --enviar   # envia via SMTP (.env)
```

A janela considera vencimentos **futuros** dentro de N dias e vencidos há ≤ 30 dias (evita
disparar e-mail sobre licenças vencidas há anos). Cada item é reenviado no máximo 1× a cada
25 dias. Pode ser agendado no **Agendador de Tarefas do Windows** apontando para o comando
`--enviar`.
