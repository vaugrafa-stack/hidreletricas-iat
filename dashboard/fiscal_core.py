"""Núcleo de Fiscalização e Notificações — IAT/PR (SEM Streamlit).

Concentra a lógica de dados e e-mail que é compartilhada entre o dashboard
(`dashboard/app.py`) e o motor de notificações em linha de comando
(`src/notificacoes.py`). Não importa Streamlit de propósito, para poder rodar
em um agendador (Agendador de Tarefas do Windows / cron) sem o servidor web.

Stores (CSV, UTF-8-sig), criados sob demanda:
  data/fiscalizacao/condicionantes.csv          — condicionantes por empreendimento
  data/fiscalizacao/emails_empreendedores.csv   — CNPJ/empreendedor -> e-mail
  data/fiscalizacao/notificacoes_log.csv        — histórico de notificações + leitura
  data/processed/correcoes_coordenadas.csv      — correções manuais de coordenada

Regra dura do projeto: o .xlsm ORIGINAL nunca é alterado. As correções de
coordenada vão para um arquivo SEPARADO e são aplicadas por cima ao carregar.
"""
from __future__ import annotations

import os
import csv
import ssl
import uuid
import smtplib
from email.utils import formatdate, make_msgid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FISCAL_DIR = BASE_DIR / "data" / "fiscalizacao"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

COND_PATH = FISCAL_DIR / "condicionantes.csv"
EMAILS_PATH = FISCAL_DIR / "emails_empreendedores.csv"        # legado (lookup por CNPJ)
CONTATOS_PATH = FISCAL_DIR / "contatos.csv"                   # por protocolo: empreendedor + consultoria
NOTIF_LOG_PATH = FISCAL_DIR / "notificacoes_log.csv"
CORRECOES_PATH = PROCESSED_DIR / "correcoes_coordenadas.csv"

# ── Esquemas das tabelas (ordem das colunas) ──────────────────────────────────
COND_COLS = [
    "id", "protocolo", "empreendimento", "cnpj", "empreendedor", "numero_licenca",
    "descricao", "tipo", "data_limite", "periodicidade", "status",
    "data_atendimento", "responsavel", "evidencia", "obs", "criado_em", "atualizado_em",
]
EMAILS_COLS = ["cnpj", "empreendedor", "email", "contato", "obs"]
# Contatos por EMPREENDIMENTO (chave = protocolo): dados do empreendedor + da consultoria
# responsável. Usado na ficha, no relatório e como destinatário das notificações/encaminhamentos.
CONTATOS_COLS = [
    "protocolo", "empreendimento", "cnpj", "empreendedor",
    "emp_contato", "emp_telefone", "emp_email",
    "consultoria", "cons_telefone", "cons_email", "obs",
]
NOTIF_COLS = [
    "token", "tipo", "ref", "empreendimento", "cnpj", "destino", "assunto",
    "data_alvo", "dias_restantes", "metodo", "status", "gerado_em", "enviado_em", "lido_em",
]
CORRECOES_COLS = [
    "protocolo", "empreendimento", "latitude", "longitude",
    "lat_casa_forca", "lon_casa_forca", "autor", "data", "obs",
]

COND_TIPOS = ["Monitoramento", "Relatório", "Obra/Estrutura", "Compensação",
              "Documental", "Social", "Outorga/Uso da água", "Outro"]
COND_PERIODOS = ["Única", "Mensal", "Trimestral", "Semestral", "Anual", "Eventual"]
COND_STATUS = ["Pendente", "Atendida", "Em atraso", "Dispensada"]


# ── .env mínimo (sem dependência de python-dotenv) ────────────────────────────
def carregar_env(env_path: Path | None = None) -> None:
    """Lê um arquivo .env simples (KEY=VALUE) para os.environ, sem sobrescrever
    variáveis já definidas no ambiente. Silencioso se o arquivo não existir."""
    p = env_path or (BASE_DIR / ".env")
    if not p.exists():
        return
    try:
        for linha in p.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, _, valor = linha.partition("=")
            chave, valor = chave.strip(), valor.strip().strip('"').strip("'")
            os.environ.setdefault(chave, valor)
    except OSError:
        pass


# ── IO genérico de CSV ────────────────────────────────────────────────────────
def _garantir(path: Path, cols: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerow(cols)


def ler_tabela(path: Path, cols: list[str]) -> list[dict]:
    _garantir(path, cols)
    with open(path, newline="", encoding="utf-8-sig") as f:
        linhas = list(csv.DictReader(f))
    # normaliza para garantir todas as colunas
    return [{c: (r.get(c) or "") for c in cols} for r in linhas]


def escrever_tabela(path: Path, cols: list[str], linhas: list[dict]) -> None:
    _garantir(path, cols)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in linhas:
            w.writerow({c: r.get(c, "") for c in cols})


# ── Condicionantes ────────────────────────────────────────────────────────────
def ler_condicionantes() -> list[dict]:
    return ler_tabela(COND_PATH, COND_COLS)


def _proximo_id(linhas: list[dict]) -> int:
    ids = []
    for r in linhas:
        try:
            ids.append(int(float(r.get("id") or 0)))
        except (ValueError, TypeError):
            continue
    return (max(ids) + 1) if ids else 1


def salvar_condicionante(reg: dict) -> dict:
    """Insere (sem id) ou atualiza (com id) uma condicionante. Retorna o registro salvo."""
    linhas = ler_condicionantes()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M")
    rid = str(reg.get("id") or "").strip()
    novo = {c: (reg.get(c) or "") for c in COND_COLS}
    if rid:
        achou = False
        for i, r in enumerate(linhas):
            if str(r.get("id")) == rid:
                novo["criado_em"] = r.get("criado_em") or agora
                novo["atualizado_em"] = agora
                linhas[i] = novo
                achou = True
                break
        if not achou:
            rid = ""
    if not rid:
        novo["id"] = str(_proximo_id(linhas))
        novo["criado_em"] = agora
        novo["atualizado_em"] = agora
        linhas.append(novo)
    escrever_tabela(COND_PATH, COND_COLS, linhas)
    return novo


def excluir_condicionante(rid: str) -> None:
    linhas = [r for r in ler_condicionantes() if str(r.get("id")) != str(rid)]
    escrever_tabela(COND_PATH, COND_COLS, linhas)


def status_efetivo(reg: dict, hoje: date | None = None) -> str:
    """Status considerando o prazo: 'Atendida'/'Dispensada' mandam; senão,
    se houver data_limite no passado e não atendida -> 'Em atraso'."""
    hoje = hoje or date.today()
    st = (reg.get("status") or "Pendente").strip()
    if st in ("Atendida", "Dispensada"):
        return st
    dl = parse_data(reg.get("data_limite"))
    if dl and dl < hoje:
        return "Em atraso"
    return "Pendente"


def dias_para(d: date | None, hoje: date | None = None) -> int | None:
    if not d:
        return None
    return (d - (hoje or date.today())).days


# ── E-mails dos empreendedores ────────────────────────────────────────────────
def ler_emails() -> list[dict]:
    return ler_tabela(EMAILS_PATH, EMAILS_COLS)


def mapa_emails() -> dict:
    """Indexa e-mail por CNPJ (normalizado) e por nome de empreendedor (upper)."""
    m = {}
    for r in ler_emails():
        email = (r.get("email") or "").strip()
        if not email:
            continue
        cnpj = _so_digitos(r.get("cnpj"))
        if cnpj:
            m[("cnpj", cnpj)] = r
        nome = (r.get("empreendedor") or "").strip().upper()
        if nome:
            m[("nome", nome)] = r
    return m


def email_do_empreendedor(cnpj=None, empreendedor=None, _cache=None) -> str:
    m = _cache if _cache is not None else mapa_emails()
    cnpj = _so_digitos(cnpj)
    if cnpj and ("cnpj", cnpj) in m:
        return (m[("cnpj", cnpj)].get("email") or "").strip()
    nome = (empreendedor or "").strip().upper()
    if nome and ("nome", nome) in m:
        return (m[("nome", nome)].get("email") or "").strip()
    return ""


# ── Contatos por empreendimento (empreendedor + consultoria responsável) ──────
def ler_contatos() -> list[dict]:
    return ler_tabela(CONTATOS_PATH, CONTATOS_COLS)


def mapa_contatos() -> dict:
    """Indexa o registro de contatos por protocolo (str)."""
    return {str(r.get("protocolo") or "").strip(): r
            for r in ler_contatos() if str(r.get("protocolo") or "").strip()}


def mapa_contatos_nome() -> dict:
    """Indexa contatos por NOME de empreendimento (upper) — fallback quando o contato foi
    cadastrado num protocolo representativo e deve valer para todos os protocolos do mesmo nome."""
    m = {}
    for r in ler_contatos():
        nome = str(r.get("empreendimento") or "").strip().upper()
        if nome:
            m[nome] = r  # último cadastrado vence
    return m


def contato_do_protocolo(protocolo, _cache=None) -> dict:
    m = _cache if _cache is not None else mapa_contatos()
    return m.get(str(protocolo or "").strip(), {})


def salvar_contato(reg: dict) -> dict:
    """Insere/atualiza o contato de um empreendimento (chave = protocolo)."""
    linhas = ler_contatos()
    proto = str(reg.get("protocolo") or "").strip()
    novo = {c: (reg.get(c) or "") for c in CONTATOS_COLS}
    achou = False
    for i, r in enumerate(linhas):
        if str(r.get("protocolo") or "").strip() == proto and proto:
            linhas[i] = novo
            achou = True
            break
    if not achou:
        linhas.append(novo)
    escrever_tabela(CONTATOS_PATH, CONTATOS_COLS, linhas)
    return novo


def destinatarios(protocolo=None, cnpj=None, empreendedor=None, empreendimento=None,
                  _contatos=None, _emails=None, _contatos_nome=None) -> list[dict]:
    """Lista de destinatários para notificação/encaminhamento de um empreendimento.

    Retorna [{papel, nome, email}] do EMPREENDEDOR e da CONSULTORIA. Procura o contato
    por PROTOCOLO no `contatos.csv`; se não achar, cai para o mesmo NOME de empreendimento
    (contato cadastrado num protocolo representativo) e, por fim, para o
    `emails_empreendedores.csv` (por CNPJ). Só inclui quem tem e-mail."""
    c = contato_do_protocolo(protocolo, _contatos) if protocolo else {}
    if not c and empreendimento:
        mn = _contatos_nome if _contatos_nome is not None else mapa_contatos_nome()
        c = mn.get(str(empreendimento).strip().upper(), {})
    out = []
    emp_email = (c.get("emp_email") or "").strip()
    if not emp_email:
        emp_email = email_do_empreendedor(cnpj, empreendedor, _emails)
    if emp_email:
        out.append({"papel": "Empreendedor",
                    "nome": (c.get("emp_contato") or c.get("empreendedor") or empreendedor or "").strip(),
                    "email": emp_email})
    cons_email = (c.get("cons_email") or "").strip()
    if cons_email:
        out.append({"papel": "Consultoria",
                    "nome": (c.get("consultoria") or "").strip(), "email": cons_email})
    return out


# ── Correções de coordenada (planilha separada — nunca o .xlsm) ───────────────
def ler_correcoes() -> list[dict]:
    return ler_tabela(CORRECOES_PATH, CORRECOES_COLS)


def salvar_correcao(reg: dict) -> dict:
    """Grava/atualiza a correção de coordenada de um protocolo (chave única)."""
    linhas = ler_correcoes()
    proto = str(reg.get("protocolo") or "").strip()
    novo = {c: (reg.get(c) or "") for c in CORRECOES_COLS}
    novo["data"] = novo.get("data") or datetime.now().strftime("%Y-%m-%d %H:%M")
    achou = False
    for i, r in enumerate(linhas):
        if str(r.get("protocolo")).strip() == proto and proto:
            linhas[i] = novo
            achou = True
            break
    if not achou:
        linhas.append(novo)
    escrever_tabela(CORRECOES_PATH, CORRECOES_COLS, linhas)
    return novo


# ── Log de notificações ───────────────────────────────────────────────────────
def ler_notif_log() -> list[dict]:
    return ler_tabela(NOTIF_LOG_PATH, NOTIF_COLS)


def registrar_notificacao(reg: dict) -> dict:
    linhas = ler_notif_log()
    novo = {c: (reg.get(c) or "") for c in NOTIF_COLS}
    if not novo.get("token"):
        novo["token"] = uuid.uuid4().hex[:16]
    novo["gerado_em"] = novo.get("gerado_em") or datetime.now().strftime("%Y-%m-%d %H:%M")
    linhas.append(novo)
    escrever_tabela(NOTIF_LOG_PATH, NOTIF_COLS, linhas)
    return novo


def ja_notificado_recente(tipo: str, ref: str, dias: int = 25) -> bool:
    """Evita reenviar a mesma notificação dentro de `dias`."""
    lim = date.today() - timedelta(days=dias)
    for r in ler_notif_log():
        if r.get("tipo") == tipo and str(r.get("ref")) == str(ref) and r.get("status") == "enviado":
            d = parse_data((r.get("enviado_em") or "")[:10])
            if d and d >= lim:
                return True
    return False


# ── Helpers ───────────────────────────────────────────────────────────────────
def parse_data(v) -> date | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() in ("nan", "nat", "none", ""):
        return None
    s = s[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _so_digitos(v) -> str:
    return "".join(ch for ch in str(v or "") if ch.isdigit())


def fmt_br(d: date | None) -> str:
    return d.strftime("%d/%m/%Y") if d else "—"


# ══════════════════════════════════════════════════════════════════════════════
# E-MAIL
# ══════════════════════════════════════════════════════════════════════════════
ASSINATURA = (
    "Instituto Água e Terra — IAT/PR\n"
    "Diretoria de Licenciamento e Outorga\n"
    "Acompanhamento de Empreendimentos Hidrelétricos\n"
    "www.iat.pr.gov.br"
)


def smtp_config() -> dict | None:
    """Lê a configuração de SMTP do ambiente (.env). Retorna None se incompleta.

    Variáveis: IAT_SMTP_HOST, IAT_SMTP_PORT, IAT_SMTP_USER, IAT_SMTP_PASS,
    IAT_SMTP_FROM (remetente), IAT_SMTP_TLS (1/0, padrão 1).
    """
    carregar_env()
    host = os.environ.get("IAT_SMTP_HOST", "").strip()
    user = os.environ.get("IAT_SMTP_USER", "").strip()
    frm = os.environ.get("IAT_SMTP_FROM", "").strip() or user
    if not host or not frm:
        return None
    try:
        porta = int(os.environ.get("IAT_SMTP_PORT", "587"))
    except ValueError:
        porta = 587
    return {
        "host": host, "port": porta, "user": user,
        "pass": os.environ.get("IAT_SMTP_PASS", ""), "from": frm,
        "tls": os.environ.get("IAT_SMTP_TLS", "1").strip() != "0",
        "confirm_to": os.environ.get("IAT_SMTP_CONFIRM_TO", frm).strip() or frm,
        "pixel_base": os.environ.get("IAT_PIXEL_BASE", "").strip(),
    }


def montar_assunto(tipo: str, item: dict) -> str:
    nome = item.get("empreendimento") or "Empreendimento"
    if tipo == "licenca":
        return f"[IAT/PR] Vencimento de licença — {nome}"
    return f"[IAT/PR] Prazo de condicionante — {nome}"


def montar_corpo(tipo: str, item: dict, token: str = "", pixel_base: str = "") -> tuple[str, str]:
    """Retorna (texto_plano, html). `item` traz os campos já formatados."""
    nome = item.get("empreendimento") or "o empreendimento"
    proto = item.get("protocolo") or "—"
    lic = item.get("numero_licenca") or "—"
    data_alvo = item.get("data_alvo_br") or "—"
    dias = item.get("dias_restantes")
    quando = (f"em {dias} dias" if isinstance(dias, int) and dias >= 0
              else (f"há {abs(dias)} dias" if isinstance(dias, int) else "em breve"))

    if tipo == "licenca":
        objeto = (f"a <b>licença ambiental</b> (nº {lic}) do empreendimento "
                  f"<b>{nome}</b> (protocolo {proto})")
        objeto_txt = f"a licença ambiental (nº {lic}) do empreendimento {nome} (protocolo {proto})"
        acao = ("Solicitamos que o pedido de <b>renovação</b> seja protocolado com a "
                "antecedência prevista na legislação, a fim de evitar a interrupção da regularidade ambiental.")
        acao_txt = ("Solicitamos que o pedido de renovação seja protocolado com a antecedência "
                    "prevista na legislação, a fim de evitar a interrupção da regularidade ambiental.")
        venc = f"<b>vence {quando}</b> (em {data_alvo})"
        venc_txt = f"vence {quando} (em {data_alvo})"
    else:
        desc = item.get("descricao") or "condicionante da licença"
        objeto = (f"o <b>prazo de atendimento</b> da condicionante do empreendimento "
                  f"<b>{nome}</b> (protocolo {proto}): <i>{desc}</i>")
        objeto_txt = (f"o prazo de atendimento da condicionante do empreendimento {nome} "
                      f"(protocolo {proto}): {desc}")
        acao = ("Solicitamos a comprovação do atendimento dentro do prazo, com o envio da "
                "documentação/evidências ao IAT.")
        acao_txt = ("Solicitamos a comprovação do atendimento dentro do prazo, com o envio da "
                    "documentação/evidências ao IAT.")
        venc = f"tem prazo <b>{quando}</b> (em {data_alvo})"
        venc_txt = f"tem prazo {quando} (em {data_alvo})"

    txt = (
        f"Prezado(a) empreendedor(a),\n\n"
        f"Informamos que {objeto_txt} {venc_txt}.\n\n"
        f"{acao_txt}\n\n"
        f"Esta é uma comunicação automática de acompanhamento do IAT/PR. "
        f"Por gentileza, confirme o recebimento/leitura desta mensagem.\n\n"
        f"Atenciosamente,\n{ASSINATURA}\n"
    )

    pixel = ""
    if pixel_base and token:
        sep = "&" if "?" in pixel_base else "?"
        pixel = (f'<img src="{pixel_base}{sep}t={token}" width="1" height="1" '
                 f'alt="" style="display:none">')

    html = f"""<!doctype html><html><body style="font-family:Segoe UI,Arial,sans-serif;
color:#1e293b;font-size:14px;line-height:1.6">
  <div style="border-left:4px solid #0c2d54;padding:4px 0 4px 14px;margin-bottom:14px">
    <div style="font-size:13px;color:#64748b;text-transform:uppercase;letter-spacing:.5px">
      Instituto Água e Terra — IAT/PR</div>
    <div style="font-size:18px;font-weight:700;color:#0c2d54">Acompanhamento de prazo</div>
  </div>
  <p>Prezado(a) empreendedor(a),</p>
  <p>Informamos que {objeto} {venc}.</p>
  <p>{acao}</p>
  <p style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:10px 14px">
     Esta é uma comunicação automática de acompanhamento do IAT/PR.
     Por gentileza, <b>confirme o recebimento/leitura</b> desta mensagem.</p>
  <p style="color:#475569;white-space:pre-line;margin-top:18px;font-size:13px">{ASSINATURA}</p>
  {pixel}
</body></html>"""
    return txt, html


def construir_email(remetente: str, destino: str, assunto: str, corpo_txt: str,
                    corpo_html: str, confirm_to: str = "") -> MIMEMultipart:
    """Monta a mensagem MIME com pedido de confirmação de leitura (MDN)."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"] = remetente
    msg["To"] = destino
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="iat.pr.gov.br")
    # Confirmação de leitura (Message Disposition Notification)
    alvo_conf = confirm_to or remetente
    msg["Disposition-Notification-To"] = alvo_conf
    msg["Return-Receipt-To"] = alvo_conf
    msg["X-Confirm-Reading-To"] = alvo_conf
    msg.attach(MIMEText(corpo_txt, "plain", "utf-8"))
    msg.attach(MIMEText(corpo_html, "html", "utf-8"))
    return msg


def enviar_email(msg: MIMEMultipart, cfg: dict) -> None:
    """Envia via SMTP. Lança exceção em caso de falha (o chamador trata/loga)."""
    if cfg.get("tls"):
        ctx = ssl.create_default_context()
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as s:
            s.starttls(context=ctx)
            if cfg.get("user"):
                s.login(cfg["user"], cfg["pass"])
            s.send_message(msg)
    else:
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as s:
            if cfg.get("user"):
                s.login(cfg["user"], cfg["pass"])
            s.send_message(msg)


def mailto_url(destino: str, assunto: str, corpo_txt: str) -> str:
    """Link mailto: para abrir no cliente de e-mail do usuário (fallback sem SMTP)."""
    from urllib.parse import quote
    return (f"mailto:{destino}?subject={quote(assunto)}&body={quote(corpo_txt)}")
