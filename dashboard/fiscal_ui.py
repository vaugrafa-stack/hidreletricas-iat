"""Página de Fiscalização (condicionantes + agenda de prazos + notificações por e-mail).

Renderiza a aba "🛡️ Fiscalização" do dashboard. Mantido separado de `app.py` para
não inflar o arquivo principal. Usa `fiscal_core` (dados/e-mail, sem Streamlit) e
`utils` (formatação). As funções de edição só aparecem quando `eh_interno` é True.
"""
from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import streamlit as st

import fiscal_core as fc
from utils import fmt_int


# ── Helpers visuais locais (usam as classes CSS já definidas em app.py) ────────
def _kpi(icon, label, value, sub="", color="blue"):
    return (f'<div class="kpi {color}"><div class="kpi-top"><span class="kpi-ico">{icon}</span>'
            f'<span class="kpi-label">{label}</span></div><div class="kpi-val">{value}</div>'
            f'<div class="kpi-sub">{sub}</div></div>')


def _section(title):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


def _semaforo_prazo(dias):
    """(emoji, rótulo, cor) por proximidade do vencimento."""
    if dias is None:
        return ("⚪", "Sem prazo", "#94a3b8")
    if dias < 0:
        return ("🔴", f"Vencido há {abs(dias)}d", "#ef4444")
    if dias <= 30:
        return ("🟠", f"{dias}d", "#f97316")
    if dias <= 90:
        return ("🟡", f"{dias}d", "#f59e0b")
    return ("🟢", f"{dias}d", "#22c55e")


def _opcoes_empreendimentos(df_full):
    if "empreendimento" not in df_full.columns:
        return []
    return sorted(df_full["empreendimento"].dropna().astype(str).unique().tolist())


def _dados_empreendimento(df_full, nome):
    """Retorna (protocolo, cnpj, empreendedor, numero_licenca) do registro mais
    recente do empreendimento escolhido — para pré-preencher o cadastro."""
    sub = df_full[df_full["empreendimento"].astype(str) == str(nome)]
    if sub.empty:
        return {"protocolo": "", "cnpj": "", "empreendedor": "", "numero_licenca": ""}
    if "data_protocolo" in sub.columns:
        sub = sub.sort_values("data_protocolo", ascending=False, na_position="last")
    r = sub.iloc[0]
    return {
        "protocolo": str(r.get("protocolo") or ""),
        "cnpj": str(r.get("cnpj") or ""),
        "empreendedor": str(r.get("empreendedor") or ""),
        "numero_licenca": str(r.get("numero_licenca") or ""),
    }


# ══════════════════════════════════════════════════════════════════════════════
# ABA — AGENDA DE PRAZOS (licenças + condicionantes)
# ══════════════════════════════════════════════════════════════════════════════
def _agenda(df_full, janela):
    hoje = date.today()
    itens = []

    # Licenças com validade (não encerradas)
    if "data_validade" in df_full.columns:
        enc = df_full["processo_encerrado"] if "processo_encerrado" in df_full.columns else pd.Series(False, index=df_full.index)
        for i, r in df_full[df_full["data_validade"].notna() & ~enc].iterrows():
            dv = r["data_validade"]
            dl = dv if isinstance(dv, date) else fc.parse_data(dv)
            if not dl:
                continue
            dias = (dl - hoje).days
            itens.append({
                "Tipo": "Licença", "Empreendimento": r.get("empreendimento"),
                "Protocolo": r.get("protocolo"), "Detalhe": f"Licença nº {r.get('numero_licenca') or '—'}",
                "Prazo": dl, "dias": dias,
            })

    # Condicionantes ainda não atendidas
    for c in fc.ler_condicionantes():
        st_ef = fc.status_efetivo(c, hoje)
        if st_ef in ("Atendida", "Dispensada"):
            continue
        dl = fc.parse_data(c.get("data_limite"))
        dias = (dl - hoje).days if dl else None
        itens.append({
            "Tipo": "Condicionante", "Empreendimento": c.get("empreendimento"),
            "Protocolo": c.get("protocolo"), "Detalhe": c.get("descricao") or c.get("tipo") or "Condicionante",
            "Prazo": dl, "dias": dias,
        })

    venc = [x for x in itens if x["dias"] is not None and x["dias"] < 0]
    j30 = [x for x in itens if x["dias"] is not None and 0 <= x["dias"] <= 30]
    j90 = [x for x in itens if x["dias"] is not None and 30 < x["dias"] <= 90]
    cards = [
        ("🔴", "Vencidos", len(venc), "prazo já passou", "red"),
        ("🟠", "≤ 30 dias", len(j30), "ação imediata", "yellow"),
        ("🟡", "31–90 dias", len(j90), "planejar", "yellow"),
        ("📅", "Total monitorado", len(itens), "licenças + condicionantes", "blue"),
    ]
    for col, (ico, lbl, val, sub, color) in zip(st.columns(4), cards):
        col.markdown(_kpi(ico, lbl, fmt_int(val), sub, color), unsafe_allow_html=True)

    dentro = [x for x in itens if x["dias"] is not None and x["dias"] <= janela]
    dentro.sort(key=lambda x: x["dias"])
    st.markdown("<br>", unsafe_allow_html=True)
    st.caption(f"Mostrando os **{len(dentro)}** prazos que vencem em até **{janela} dias** "
               "(ou já vencidos), ordenados pelo mais urgente.")
    if not dentro:
        st.success("Nenhum prazo dentro da janela selecionada. ✅")
        return
    linhas = []
    for x in dentro:
        emoji, lbl, _cor = _semaforo_prazo(x["dias"])
        linhas.append({
            "🚦": emoji, "Situação": lbl, "Tipo": x["Tipo"],
            "Empreendimento": x["Empreendimento"], "Protocolo": x["Protocolo"],
            "Detalhe": x["Detalhe"], "Prazo": x["Prazo"], "Dias": x["dias"],
        })
    dft = pd.DataFrame(linhas)
    st.dataframe(dft, use_container_width=True, hide_index=True, height=420,
                 column_config={
                     "🚦": st.column_config.TextColumn("🚦", width="small"),
                     "Prazo": st.column_config.DateColumn("Prazo", format="DD/MM/YYYY"),
                     "Dias": st.column_config.NumberColumn("Dias", format="%d"),
                 })
    st.download_button("⬇️ Exportar agenda (CSV)",
                       dft.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
                       "agenda_prazos.csv", "text/csv")


# ══════════════════════════════════════════════════════════════════════════════
# ABA — CONDICIONANTES
# ══════════════════════════════════════════════════════════════════════════════
def _condicionantes(df_full, eh_interno):
    conds = fc.ler_condicionantes()
    hoje = date.today()
    for c in conds:
        c["_status_ef"] = fc.status_efetivo(c, hoje)
        dl = fc.parse_data(c.get("data_limite"))
        c["_dias"] = (dl - hoje).days if dl else None

    pend = [c for c in conds if c["_status_ef"] == "Pendente"]
    atraso = [c for c in conds if c["_status_ef"] == "Em atraso"]
    avencer = [c for c in pend if c["_dias"] is not None and 0 <= c["_dias"] <= 90]
    atend = [c for c in conds if c["_status_ef"] == "Atendida"]
    cards = [
        ("📋", "Cadastradas", len(conds), "no total", "blue"),
        ("🔴", "Em atraso", len(atraso), "prazo vencido", "red"),
        ("🟡", "A vencer (90d)", len(avencer), "atenção", "yellow"),
        ("✅", "Atendidas", len(atend), "concluídas", "green"),
    ]
    for col, (ico, lbl, val, sub, color) in zip(st.columns(4), cards):
        col.markdown(_kpi(ico, lbl, fmt_int(val), sub, color), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Filtro por empreendimento
    nomes = sorted({c.get("empreendimento") for c in conds if c.get("empreendimento")})
    fcol1, fcol2 = st.columns([2, 1])
    filtro_emp = fcol1.selectbox("Filtrar por empreendimento", ["(todos)"] + nomes, key="cond_filtro_emp")
    filtro_st = fcol2.selectbox("Status", ["(todos)"] + fc.COND_STATUS + ["Em atraso"], key="cond_filtro_st")
    vis = conds
    if filtro_emp != "(todos)":
        vis = [c for c in vis if c.get("empreendimento") == filtro_emp]
    if filtro_st != "(todos)":
        vis = [c for c in vis if c["_status_ef"] == filtro_st]

    if vis:
        df_show = pd.DataFrame([{
            "ID": c.get("id"), "Empreendimento": c.get("empreendimento"),
            "Descrição": c.get("descricao"), "Tipo": c.get("tipo"),
            "Prazo": fc.parse_data(c.get("data_limite")), "Status": c["_status_ef"],
            "Periodicidade": c.get("periodicidade"), "Responsável": c.get("responsavel"),
            "Atendida em": fc.parse_data(c.get("data_atendimento")),
        } for c in vis])
        st.dataframe(df_show, use_container_width=True, hide_index=True, height=360,
                     column_config={
                         "Prazo": st.column_config.DateColumn("Prazo", format="DD/MM/YYYY"),
                         "Atendida em": st.column_config.DateColumn("Atendida em", format="DD/MM/YYYY"),
                     })
        st.download_button("⬇️ Exportar condicionantes (CSV)",
                           df_show.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
                           "condicionantes.csv", "text/csv")
    else:
        st.info("Nenhuma condicionante cadastrada ainda." if not conds
                else "Nenhuma condicionante para o filtro atual.")

    if not eh_interno:
        st.caption("🔒 O cadastro/edição de condicionantes é restrito ao **acesso interno** "
                   "(desbloqueie na barra lateral).")
        return

    # ── Cadastro / edição (interno) ──
    st.markdown("---")
    _section("➕ Cadastrar / editar condicionante")
    ids = [""] + [c.get("id") for c in conds]
    edit_id = st.selectbox("Editar existente (ou deixe vazio para nova)", ids,
                           format_func=lambda x: "— nova condicionante —" if not x
                           else f"#{x} · {next((c.get('empreendimento') for c in conds if c.get('id') == x), '')}",
                           key="cond_edit_id")
    atual = next((c for c in conds if c.get("id") == edit_id), {}) if edit_id else {}

    nomes_emp = _opcoes_empreendimentos(df_full)
    pre_nome = atual.get("empreendimento") or (nomes_emp[0] if nomes_emp else "")

    with st.form("form_cond", clear_on_submit=False):
        c1, c2 = st.columns([2, 1])
        emp = c1.selectbox("Empreendimento", nomes_emp or [pre_nome],
                           index=(nomes_emp.index(pre_nome) if pre_nome in nomes_emp else 0) if nomes_emp else 0)
        dd = _dados_empreendimento(df_full, emp)
        tipo = c2.selectbox("Tipo", fc.COND_TIPOS,
                            index=fc.COND_TIPOS.index(atual["tipo"]) if atual.get("tipo") in fc.COND_TIPOS else 0)
        desc = st.text_area("Descrição da condicionante", value=atual.get("descricao", ""), height=80)
        c3, c4, c5 = st.columns(3)
        dl_default = fc.parse_data(atual.get("data_limite")) or date.today()
        prazo = c3.date_input("Prazo de atendimento", value=dl_default, format="DD/MM/YYYY")
        per = c4.selectbox("Periodicidade", fc.COND_PERIODOS,
                          index=fc.COND_PERIODOS.index(atual["periodicidade"]) if atual.get("periodicidade") in fc.COND_PERIODOS else 0)
        status = c5.selectbox("Status", fc.COND_STATUS,
                             index=fc.COND_STATUS.index(atual["status"]) if atual.get("status") in fc.COND_STATUS else 0)
        c6, c7 = st.columns(2)
        resp = c6.text_input("Responsável (IAT)", value=atual.get("responsavel", ""))
        atend_default = fc.parse_data(atual.get("data_atendimento"))
        atend_dt = c7.date_input("Data de atendimento (se houver)",
                                 value=atend_default, format="DD/MM/YYYY")
        evid = st.text_input("Evidência (link/processo)", value=atual.get("evidencia", ""))
        obs = st.text_input("Observações", value=atual.get("obs", ""))
        salvar = st.form_submit_button("💾 Salvar condicionante", type="primary", use_container_width=True)

    if salvar:
        reg = {
            "id": edit_id or "", "protocolo": dd["protocolo"], "empreendimento": emp,
            "cnpj": dd["cnpj"], "empreendedor": dd["empreendedor"], "numero_licenca": dd["numero_licenca"],
            "descricao": desc, "tipo": tipo, "data_limite": prazo.strftime("%Y-%m-%d"),
            "periodicidade": per, "status": status,
            "data_atendimento": atend_dt.strftime("%Y-%m-%d") if (status == "Atendida" and atend_dt) else "",
            "responsavel": resp, "evidencia": evid, "obs": obs,
        }
        fc.salvar_condicionante(reg)
        st.success(f"Condicionante salva para **{emp}**.")
        st.rerun()

    if edit_id:
        if st.button("🗑️ Excluir esta condicionante", key="cond_del"):
            fc.excluir_condicionante(edit_id)
            st.warning("Condicionante excluída.")
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ABA — NOTIFICAÇÕES POR E-MAIL
# ══════════════════════════════════════════════════════════════════════════════
def _due_items(df_full, janela, grace=30):
    """Itens (licenças + condicionantes) a vencer dentro da janela, prontos para e-mail.

    Para a notificação ("avisar meses antes") consideramos vencimentos FUTUROS dentro
    da janela e os vencidos há no máximo `grace` dias — evita disparar e-mail sobre
    licenças vencidas há anos (ruído de base)."""
    hoje = date.today()
    cache = fc.mapa_emails()
    cache_ct = fc.mapa_contatos()
    cache_ct_nome = fc.mapa_contatos_nome()

    def _dest(proto, cnpj, emp, empnome):
        ds = fc.destinatarios(proto, cnpj, emp, empnome, _contatos=cache_ct,
                              _emails=cache, _contatos_nome=cache_ct_nome)
        return ds, (ds[0]["email"] if ds else "")

    itens = []
    if "data_validade" in df_full.columns:
        enc = df_full["processo_encerrado"] if "processo_encerrado" in df_full.columns else pd.Series(False, index=df_full.index)
        for _, r in df_full[df_full["data_validade"].notna() & ~enc].iterrows():
            dl = r["data_validade"] if isinstance(r["data_validade"], date) else fc.parse_data(r["data_validade"])
            if not dl:
                continue
            dias = (dl - hoje).days
            if dias > janela or dias < -grace:
                continue
            ds, prim = _dest(r.get("protocolo"), r.get("cnpj"), r.get("empreendedor"), r.get("empreendimento"))
            itens.append({
                "tipo": "licenca", "ref": str(r.get("protocolo") or ""),
                "empreendimento": r.get("empreendimento"), "protocolo": r.get("protocolo"),
                "cnpj": str(r.get("cnpj") or ""), "empreendedor": str(r.get("empreendedor") or ""),
                "numero_licenca": str(r.get("numero_licenca") or ""),
                "data_alvo": dl, "data_alvo_br": fc.fmt_br(dl), "dias_restantes": dias,
                "destino": prim, "destinos": ds,
            })
    for c in fc.ler_condicionantes():
        if fc.status_efetivo(c, hoje) in ("Atendida", "Dispensada"):
            continue
        dl = fc.parse_data(c.get("data_limite"))
        if not dl:
            continue
        dias = (dl - hoje).days
        if dias > janela or dias < -grace:
            continue
        ds, prim = _dest(c.get("protocolo"), c.get("cnpj"), c.get("empreendedor"), c.get("empreendimento"))
        itens.append({
            "tipo": "condicionante", "ref": str(c.get("id") or ""),
            "empreendimento": c.get("empreendimento"), "protocolo": c.get("protocolo"),
            "cnpj": str(c.get("cnpj") or ""), "empreendedor": str(c.get("empreendedor") or ""),
            "numero_licenca": str(c.get("numero_licenca") or ""), "descricao": c.get("descricao"),
            "data_alvo": dl, "data_alvo_br": fc.fmt_br(dl), "dias_restantes": dias,
            "destino": prim, "destinos": ds,
        })
    itens.sort(key=lambda x: x["dias_restantes"])
    return itens


def _notificacoes(df_full, eh_interno, public_mode):
    cfg = fc.smtp_config()
    if cfg:
        st.success(f"📧 SMTP configurado — remetente **{cfg['from']}** · servidor `{cfg['host']}:{cfg['port']}`. "
                   "O envio automático está disponível.")
    else:
        st.info("📭 **SMTP não configurado.** O sistema gera a prévia do e-mail, o arquivo **.eml** "
                "e o link **mailto:** (abre no seu cliente de e-mail). Para envio automático com "
                "**confirmação de leitura**, configure as variáveis `IAT_SMTP_*` no arquivo `.env` "
                "(veja a aba **Configuração**).")

    janela = st.slider("Antecedência (dias antes do vencimento)", 30, 365, 90, 30, key="notif_janela")
    itens = _due_items(df_full, janela)
    com_email = [x for x in itens if x["destino"]]
    sem_email = [x for x in itens if not x["destino"]]
    for col, (ico, lbl, val, sub, color) in zip(st.columns(4), [
        ("📨", "A notificar", len(itens), f"vencem em ≤{janela}d", "blue"),
        ("✅", "Com e-mail", len(com_email), "prontos p/ enviar", "green"),
        ("⚠️", "Sem e-mail", len(sem_email), "cadastrar contato", "yellow"),
        ("📜", "Já enviadas", len(fc.ler_notif_log()), "no histórico", "gray")]):
        col.markdown(_kpi(ico, lbl, fmt_int(val), sub, color), unsafe_allow_html=True)

    if not itens:
        st.success("Nenhum vencimento dentro da janela. ✅")
    else:
        st.markdown("<br>", unsafe_allow_html=True)
        df_itens = pd.DataFrame([{
            "Tipo": x["tipo"], "Empreendimento": x["empreendimento"], "Protocolo": x["protocolo"],
            "Prazo": x["data_alvo"], "Dias": x["dias_restantes"],
            "Destinatários": ", ".join(f"{d['papel'][:4]}: {d['email']}" for d in (x.get("destinos") or []))
                             or "— sem cadastro —",
        } for x in itens])
        st.dataframe(df_itens, use_container_width=True, hide_index=True, height=300,
                     column_config={"Prazo": st.column_config.DateColumn("Prazo", format="DD/MM/YYYY"),
                                    "Dias": st.column_config.NumberColumn("Dias", format="%d")})

    # ── Compor / enviar um e-mail ──
    st.markdown("---")
    _section("✉️ Compor notificação")
    if not itens:
        return
    rotulos = [f"[{x['tipo']}] {x['empreendimento']} · vence {x['data_alvo_br']} ({x['dias_restantes']}d)"
               for x in itens]
    idx = st.selectbox("Selecione o item", range(len(itens)), format_func=lambda i: rotulos[i], key="notif_sel")
    item = itens[idx]
    cfg_pixel = cfg.get("pixel_base", "") if cfg else ""
    token = fc.uuid.uuid4().hex[:16]
    assunto = fc.montar_assunto(item["tipo"], item)
    txt, html = fc.montar_corpo(item["tipo"], item, token=token, pixel_base=cfg_pixel)

    # Destinatários: empreendedor + consultoria já cadastrados (ficha/Configuração) + manual
    sugeridos = item.get("destinos") or []
    op_labels = [f"{d['papel']}: {d['email']}" + (f" — {d['nome']}" if d.get("nome") else "")
                 for d in sugeridos]
    if op_labels:
        sel_dest = st.multiselect("Destinatários (empreendedor / consultoria)", op_labels,
                                  default=op_labels, key="notif_dest_sel")
        emails_sel = [sugeridos[op_labels.index(l)]["email"] for l in sel_dest]
    else:
        st.caption("Nenhum contato cadastrado para este empreendimento — informe o e-mail abaixo "
                   "ou cadastre na ficha / aba Configuração.")
        emails_sel = []
    extra = st.text_input("Adicionar e-mail (opcional, separe por vírgula)",
                          key="notif_dest_extra", placeholder="outro@exemplo.com")
    if extra.strip():
        emails_sel += [e.strip() for e in extra.replace(";", ",").split(",") if e.strip()]
    destino = ", ".join(dict.fromkeys(emails_sel))  # dedup preservando ordem
    st.text_input("Assunto", value=assunto, key="notif_assunto", disabled=True)
    with st.expander("👁️ Prévia do e-mail", expanded=True):
        st.markdown(html, unsafe_allow_html=True)
    with st.expander("📄 Texto puro (.eml / mailto)"):
        st.code(txt, language=None)

    bcols = st.columns(3)
    # Enviar via SMTP (interno + configurado + local)
    pode_enviar = bool(cfg) and eh_interno and not public_mode and bool(destino)
    if bcols[0].button("✉️ Enviar agora", type="primary", use_container_width=True,
                       disabled=not pode_enviar,
                       help=None if pode_enviar else "Requer SMTP configurado, acesso interno e e-mail do destinatário"):
        try:
            assunto_f = st.session_state.get("notif_assunto", assunto)
            msg = fc.construir_email(cfg["from"], destino, assunto_f, txt, html, cfg.get("confirm_to", ""))
            fc.enviar_email(msg, cfg)
            fc.registrar_notificacao({
                "token": token, "tipo": item["tipo"], "ref": item["ref"],
                "empreendimento": item["empreendimento"], "cnpj": item["cnpj"], "destino": destino,
                "assunto": assunto_f, "data_alvo": item["data_alvo_br"],
                "dias_restantes": item["dias_restantes"], "metodo": "smtp", "status": "enviado",
                "enviado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
            st.success(f"E-mail enviado para {destino}. Pedido de confirmação de leitura incluído.")
        except Exception as e:  # noqa: BLE001
            fc.registrar_notificacao({
                "token": token, "tipo": item["tipo"], "ref": item["ref"],
                "empreendimento": item["empreendimento"], "cnpj": item["cnpj"], "destino": destino,
                "assunto": assunto, "data_alvo": item["data_alvo_br"],
                "dias_restantes": item["dias_restantes"], "metodo": "smtp", "status": "falha",
            })
            st.error(f"Falha no envio: {e}")

    # Baixar .eml (abre em qualquer cliente de e-mail)
    msg_eml = fc.construir_email(cfg["from"] if cfg else "iat@iat.pr.gov.br",
                                 destino or "destinatario@exemplo.com", assunto, txt, html,
                                 cfg.get("confirm_to", "") if cfg else "")
    safe = "".join(ch if ch.isalnum() else "_" for ch in str(item["empreendimento"] or "email"))[:40]
    bcols[1].download_button("⬇️ Baixar .eml", msg_eml.as_bytes(), file_name=f"{safe}.eml",
                             mime="message/rfc822", use_container_width=True, key="notif_eml")
    if destino:
        bcols[2].link_button("📧 Abrir no cliente (mailto)", fc.mailto_url(destino, assunto, txt),
                             use_container_width=True)

    if st.button("📝 Registrar como gerada (sem enviar)", key="notif_log_only"):
        fc.registrar_notificacao({
            "token": token, "tipo": item["tipo"], "ref": item["ref"],
            "empreendimento": item["empreendimento"], "cnpj": item["cnpj"],
            "destino": destino, "assunto": assunto, "data_alvo": item["data_alvo_br"],
            "dias_restantes": item["dias_restantes"], "metodo": "eml", "status": "gerado",
        })
        st.info("Registrada no histórico (status: gerado).")
        st.rerun()

    # Histórico
    log = fc.ler_notif_log()
    if log:
        st.markdown("---")
        _section("📜 Histórico de notificações")
        dl = pd.DataFrame(log)[["gerado_em", "enviado_em", "tipo", "empreendimento",
                                "destino", "status", "metodo", "lido_em"]]
        st.dataframe(dl.iloc[::-1], use_container_width=True, hide_index=True, height=240)


# ══════════════════════════════════════════════════════════════════════════════
# ABA — CONFIGURAÇÃO
# ══════════════════════════════════════════════════════════════════════════════
def _configuracao(eh_interno):
    _section("👥 Contatos por empreendimento (empreendedor + consultoria)")
    st.caption("A planilha original não traz telefone/e-mail. Cadastre aqui, **por protocolo**, os dados do "
               "**empreendedor** e da **consultoria responsável**. Esses contatos aparecem na ficha, no relatório "
               "e são os **destinatários** das notificações/encaminhamentos. (Também dá para editar empreendimento "
               "a empreendimento na **ficha** do ponto.)")
    contatos = fc.ler_contatos()
    df_ct = pd.DataFrame(contatos) if contatos else pd.DataFrame(columns=fc.CONTATOS_COLS)

    _ccfg = {
        "protocolo": st.column_config.TextColumn("Protocolo", help="Chave — copie da aba Relatório"),
        "empreendimento": st.column_config.TextColumn("Empreendimento"),
        "cnpj": st.column_config.TextColumn("CNPJ"),
        "empreendedor": st.column_config.TextColumn("Empreendedor"),
        "emp_contato": st.column_config.TextColumn("Empreend.: contato"),
        "emp_telefone": st.column_config.TextColumn("Empreend.: telefone"),
        "emp_email": st.column_config.TextColumn("Empreend.: e-mail"),
        "consultoria": st.column_config.TextColumn("Consultoria"),
        "cons_telefone": st.column_config.TextColumn("Consultoria: telefone"),
        "cons_email": st.column_config.TextColumn("Consultoria: e-mail"),
        "obs": st.column_config.TextColumn("Obs"),
    }
    if eh_interno:
        edt = st.data_editor(df_ct, num_rows="dynamic", use_container_width=True, height=300,
                             key="contatos_editor", column_config=_ccfg)
        if st.button("💾 Salvar contatos", type="primary"):
            linhas = [r for r in edt.fillna("").to_dict("records")
                      if str(r.get("protocolo") or "").strip()]
            fc.escrever_tabela(fc.CONTATOS_PATH, fc.CONTATOS_COLS, linhas)
            st.success(f"{len(linhas)} contato(s) salvos.")
            st.rerun()
    else:
        st.dataframe(df_ct, use_container_width=True, hide_index=True, height=260)
        st.caption("🔒 Edição restrita ao acesso interno.")

    st.markdown("---")
    _section("⚙️ Servidor de e-mail (SMTP)")
    cfg = fc.smtp_config()
    if cfg:
        st.success(f"Configurado: `{cfg['host']}:{cfg['port']}` · remetente **{cfg['from']}** · "
                   f"TLS {'ligado' if cfg['tls'] else 'desligado'}.")
    else:
        st.warning("Não configurado. O envio automático fica indisponível (a geração de .eml/mailto continua funcionando).")
    st.markdown("""
Para habilitar o **envio automático com confirmação de leitura**, crie/edite o arquivo `.env`
na raiz do projeto com:

```env
IAT_SMTP_HOST=smtp.seuservidor.gov.br
IAT_SMTP_PORT=587
IAT_SMTP_USER=usuario
IAT_SMTP_PASS=senha
IAT_SMTP_FROM=licenciamento@iat.pr.gov.br
IAT_SMTP_TLS=1
IAT_SMTP_CONFIRM_TO=licenciamento@iat.pr.gov.br
# (opcional) pixel de rastreio de leitura, se você hospedar um endpoint:
# IAT_PIXEL_BASE=https://seu-endpoint/pixel
```

O envio em lote, fora do dashboard, pode ser agendado com:
```
py src/notificacoes.py --dias 90 --enviar
```
""")


# ══════════════════════════════════════════════════════════════════════════════
# ENTRADA
# ══════════════════════════════════════════════════════════════════════════════
def render(df_full, config, eh_interno=False, public_mode=False):
    _section("🛡️ Fiscalização de Condicionantes e Prazos")
    st.caption("Acompanhe o **atendimento das condicionantes** e os **vencimentos de licenças** por "
               "empreendimento, e **notifique o empreendedor por e-mail** com antecedência.")

    t_ag, t_cond, t_notif, t_cfg = st.tabs([
        "📅 Agenda de prazos", "📋 Condicionantes", "✉️ Notificações", "⚙️ Configuração"])
    with t_ag:
        janela = st.slider("Janela (dias)", 30, 365, 90, 30, key="ag_janela")
        _agenda(df_full, janela)
    with t_cond:
        _condicionantes(df_full, eh_interno)
    with t_notif:
        _notificacoes(df_full, eh_interno, public_mode)
    with t_cfg:
        _configuracao(eh_interno)
