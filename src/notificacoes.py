"""Motor de notificações por e-mail — IAT/PR (linha de comando / agendável).

Varre as licenças (data de validade) e as condicionantes a vencer dentro de uma
janela e, para cada empreendedor com e-mail cadastrado, envia uma notificação com
PEDIDO DE CONFIRMAÇÃO DE LEITURA (cabeçalhos MDN). Pensado para rodar no Agendador
de Tarefas do Windows / cron, sem o servidor Streamlit.

Uso:
    py src/notificacoes.py --dias 90            # apenas LISTA o que seria enviado (dry-run)
    py src/notificacoes.py --dias 90 --enviar   # envia de fato (requer SMTP no .env)
    py src/notificacoes.py --dias 90 --eml saida/   # gera arquivos .eml (sem enviar)

Sem --enviar e sem --eml, é só prévia (não envia nada).
O envio exige SMTP configurado no .env (IAT_SMTP_*). Cada destinatário é notificado
no máximo 1× a cada 25 dias por item (evita spam de reenvio).
"""
from __future__ import annotations

import sys
import argparse
from pathlib import Path
from datetime import date, datetime

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "dashboard"))
import fiscal_core as fc  # noqa: E402

CSV = BASE_DIR / "data" / "processed" / "processos_hidreletricas.csv"


def _carregar_processos() -> pd.DataFrame:
    if not CSV.exists():
        print(f"[ERRO] CSV não encontrado: {CSV}. Rode o pipeline antes.")
        sys.exit(1)
    df = pd.read_csv(CSV, encoding="utf-8-sig", low_memory=False)
    for dc in ("data_validade",):
        if dc in df.columns:
            df[dc] = pd.to_datetime(df[dc], errors="coerce").dt.date
    if "processo_encerrado" in df.columns:
        df["processo_encerrado"] = df["processo_encerrado"].astype(str).str.lower().isin(
            ["true", "1", "yes"])
    return df


def _coletar(df: pd.DataFrame, dias: int, grace: int = 30) -> list[dict]:
    hoje = date.today()
    cache = fc.mapa_emails()
    itens = []
    if "data_validade" in df.columns:
        enc = df["processo_encerrado"] if "processo_encerrado" in df.columns else pd.Series(False, index=df.index)
        for _, r in df[df["data_validade"].notna() & ~enc].iterrows():
            dl = r["data_validade"] if isinstance(r["data_validade"], date) else fc.parse_data(r["data_validade"])
            if not dl:
                continue
            d = (dl - hoje).days
            if d > dias or d < -grace:
                continue
            itens.append({
                "tipo": "licenca", "ref": str(r.get("protocolo") or ""),
                "empreendimento": r.get("empreendimento"), "protocolo": r.get("protocolo"),
                "cnpj": str(r.get("cnpj") or ""), "numero_licenca": str(r.get("numero_licenca") or ""),
                "data_alvo": dl, "data_alvo_br": fc.fmt_br(dl), "dias_restantes": d,
                "destino": fc.email_do_empreendedor(r.get("cnpj"), r.get("empreendedor"), cache),
            })
    for c in fc.ler_condicionantes():
        if fc.status_efetivo(c, hoje) in ("Atendida", "Dispensada"):
            continue
        dl = fc.parse_data(c.get("data_limite"))
        if not dl or (dl - hoje).days > dias or (dl - hoje).days < -grace:
            continue
        itens.append({
            "tipo": "condicionante", "ref": str(c.get("id") or ""),
            "empreendimento": c.get("empreendimento"), "protocolo": c.get("protocolo"),
            "cnpj": str(c.get("cnpj") or ""), "descricao": c.get("descricao"),
            "data_alvo": dl, "data_alvo_br": fc.fmt_br(dl), "dias_restantes": (dl - hoje).days,
            "destino": fc.email_do_empreendedor(c.get("cnpj"), c.get("empreendedor"), cache),
        })
    itens.sort(key=lambda x: x["dias_restantes"])
    return itens


def main():
    ap = argparse.ArgumentParser(description="Notificações de vencimento — IAT/PR")
    ap.add_argument("--dias", type=int, default=90, help="janela de antecedência (padrão 90)")
    ap.add_argument("--enviar", action="store_true", help="enviar de fato via SMTP (.env)")
    ap.add_argument("--eml", metavar="DIR", help="gerar arquivos .eml neste diretório (sem enviar)")
    args = ap.parse_args()

    fc.carregar_env()
    df = _carregar_processos()
    itens = _coletar(df, args.dias)
    cfg = fc.smtp_config()

    print(f"== Notificações IAT/PR — janela {args.dias} dias ==")
    print(f"Itens a vencer: {len(itens)} | com e-mail: {sum(1 for x in itens if x['destino'])}")
    if args.enviar and not cfg:
        print("[ERRO] --enviar pedido mas SMTP não está configurado no .env. Abortando envio.")
        args.enviar = False

    saida = Path(args.eml) if args.eml else None
    if saida:
        saida.mkdir(parents=True, exist_ok=True)

    enviados = gerados = pulados = 0
    for x in itens:
        if not x["destino"]:
            continue
        if fc.ja_notificado_recente(x["tipo"], x["ref"], dias=25):
            pulados += 1
            continue
        token = fc.uuid.uuid4().hex[:16]
        assunto = fc.montar_assunto(x["tipo"], x)
        txt, html = fc.montar_corpo(x["tipo"], x, token=token,
                                    pixel_base=cfg.get("pixel_base", "") if cfg else "")
        remetente = cfg["from"] if cfg else "licenciamento@iat.pr.gov.br"
        msg = fc.construir_email(remetente, x["destino"], assunto, txt, html,
                                 cfg.get("confirm_to", "") if cfg else "")
        if args.enviar:
            try:
                fc.enviar_email(msg, cfg)
                fc.registrar_notificacao({
                    "token": token, "tipo": x["tipo"], "ref": x["ref"],
                    "empreendimento": x["empreendimento"], "cnpj": x["cnpj"], "destino": x["destino"],
                    "assunto": assunto, "data_alvo": x["data_alvo_br"], "dias_restantes": x["dias_restantes"],
                    "metodo": "smtp", "status": "enviado",
                    "enviado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
                })
                enviados += 1
                print(f"  [enviado] {x['tipo']:13} {x['empreendimento']} -> {x['destino']} ({x['dias_restantes']}d)")
            except Exception as e:  # noqa: BLE001
                print(f"  [FALHA]   {x['empreendimento']} -> {x['destino']}: {e}")
        elif saida:
            nome = "".join(ch if ch.isalnum() else "_" for ch in str(x["empreendimento"] or "email"))[:40]
            (saida / f"{nome}_{token[:6]}.eml").write_bytes(msg.as_bytes())
            gerados += 1
        else:
            print(f"  [previa]  {x['tipo']:13} {x['empreendimento']} -> {x['destino']} "
                  f"(vence {x['data_alvo_br']}, {x['dias_restantes']}d)")

    if args.enviar:
        print(f"\nEnviados: {enviados} | pulados (já notificados <25d): {pulados}")
    elif saida:
        print(f"\n.eml gerados em {saida}: {gerados} | pulados: {pulados}")
    else:
        print("\n(dry-run — nada enviado. Use --enviar para enviar ou --eml DIR para gerar arquivos.)")


if __name__ == "__main__":
    main()
