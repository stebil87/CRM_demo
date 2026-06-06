import streamlit as st
from datetime import date
import json
from db import (
    lista_offerte, get_offerta, crea_offerta, aggiorna_offerta,
    nuova_versione_offerta, get_cliente, lista_template, get_template
)
from auth import can_edit
from pdf_offerta import genera_pdf_offerta

STATI_OFFERTA = ["bozza", "inviata", "accettata", "rifiutata", "scaduta"]
VALUTE = ["CHF", "EUR", "USD"]


def pagina_offerte(utente, cliente_id=None, cliente_nome=None):
    col1, col2 = st.columns([1, 8])
    with col1:
        if st.button("Indietro"):
            st.session_state.pagina = "clienti" if cliente_id else "dashboard"
            st.rerun()

    titolo = f"Offerte — {cliente_nome}" if cliente_nome else "Tutte le offerte"
    st.title(titolo)
    st.markdown("---")

    tab_lista, tab_nuova = st.tabs(["Lista offerte", "Nuova offerta"])

    with tab_nuova:
        if not can_edit(utente):
            st.warning("Non hai i permessi per creare offerte.")
        elif not cliente_id:
            st.info("Seleziona un cliente dalla sezione Clienti per creare un'offerta.")
        else:
            _form_nuova_offerta(utente, cliente_id)

    with tab_lista:
        offerte = lista_offerte(cliente_id)
        if not offerte:
            st.info("Nessuna offerta trovata.")
        else:
            for o in offerte:
                cliente_info = o.get("clienti") or {}
                nome_cl = cliente_info.get("ragione_sociale") or \
                    f"{cliente_info.get('nome','')} {cliente_info.get('cognome','')}".strip()
                label = f"{o['numero']}   |   {o['titolo']}"
                if not cliente_id:
                    label += f"   |   {nome_cl}"
                label += f"   |   {o.get('valuta','CHF')} {float(o.get('importo') or 0):,.2f}"
                label += f"   |   {o.get('stato','').upper()}   |   v{o.get('versione',1)}"
                with st.expander(label):
                    _scheda_offerta(o, utente)


def _scheda_offerta(o, utente):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Numero:** {o['numero']}")
        st.markdown(f"**Titolo:** {o['titolo']}")
        st.markdown(f"**Stato:** {o['stato'].upper()}")
        st.markdown(f"**Versione:** {o.get('versione', 1)}")
    with col2:
        st.markdown(f"**Importo:** {o.get('valuta','CHF')} {float(o.get('importo') or 0):,.2f}")
        st.markdown(f"**Emessa il:** {o.get('data_emissione','—')}")
        st.markdown(f"**Scade il:** {o.get('data_scadenza','—')}")

    if o.get("descrizione"):
        st.markdown(f"**Descrizione:** {o['descrizione']}")

    righe = o.get("righe") or []
    if isinstance(righe, str):
        try:
            righe = json.loads(righe)
        except:
            righe = []

    # Separa righe base da upgrade
    righe_base = [r for r in righe if not r.get("upgrade")]
    righe_upgrade = [r for r in righe if r.get("upgrade")]

    totale_base = sum(float(r.get("totale", 0)) for r in righe_base)
    totale_upgrade = sum(float(r.get("totale", 0)) for r in righe_upgrade)
    valuta = o.get("valuta", "CHF")

    if righe_base:
        st.markdown("**Pacchetto base:**")
        for r in righe_base:
            st.markdown(
                f"- {r.get('descrizione','—')}   "
                f"{r.get('qta',1)} x {float(r.get('prezzo',0)):,.2f} = "
                f"**{float(r.get('totale',0)):,.2f}**"
            )
        st.markdown(
            f"<div style='background:#f4f4f8;border-radius:6px;padding:8px 12px;"
            f"font-size:13px;font-weight:600;color:#1a1a2e;margin:4px 0;'>"
            f"Totale base: {valuta} {totale_base:,.2f}</div>",
            unsafe_allow_html=True
        )

    if righe_upgrade:
        st.markdown("**Opzioni upgrade:**")
        for r in righe_upgrade:
            st.markdown(
                f"- {r.get('descrizione','—')}   "
                f"{r.get('qta',1)} x {float(r.get('prezzo',0)):,.2f} = "
                f"**{float(r.get('totale',0)):,.2f}**"
            )
        st.markdown(
            f"<div style='background:#fff3cd;border:1px solid #ffc107;border-radius:6px;"
            f"padding:8px 12px;font-size:13px;font-weight:600;color:#856404;margin:4px 0;'>"
            f"Valore upgrade opzionale: {valuta} {totale_upgrade:,.2f} &nbsp;·&nbsp; "
            f"Totale con upgrade: {valuta} {totale_base + totale_upgrade:,.2f}</div>",
            unsafe_allow_html=True
        )

    if o.get("note"):
        st.markdown(f"**Note:** {o['note']}")

    if o.get("offerta_padre"):
        st.caption(f"Revisione di offerta precedente (ID: {o['offerta_padre'][:8]}...)")

    # Download PDF
    cliente_dati = get_cliente(o["cliente_id"]) if o.get("cliente_id") else {}
    pdf_bytes = genera_pdf_offerta(o, cliente_dati)
    if pdf_bytes:
        st.download_button(
            label="Scarica PDF offerta",
            data=pdf_bytes,
            file_name=f"{o['numero']}.pdf",
            mime="application/pdf",
            key=f"pdf_{o['id']}"
        )

    # Conferma d'ordine
    if o.get("stato") == "accettata" and can_edit(utente):
        st.markdown("---")
        st.markdown("**Conferma d'ordine**")
        email_cliente = cliente_dati.get("email", "")

        if not email_cliente:
            st.warning("Nessuna email salvata per questo cliente.")
        else:
            from email_service import corpo_conferma_ordine
            corpo_default = corpo_conferma_ordine(cliente_dati, o)

            with st.expander("Anteprima e invio conferma d'ordine"):
                email_dest = st.text_input(
                    "Email destinatario",
                    value=email_cliente,
                    key=f"email_dest_{o['id']}"
                )
                oggetto = st.text_input(
                    "Oggetto",
                    value=f"Conferma d'ordine — {o.get('numero','')}",
                    key=f"oggetto_{o['id']}"
                )
                st.markdown("**Anteprima email:**")
                st.components.v1.html(corpo_default, height=400, scrolling=True)

                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("Invia conferma d'ordine", key=f"invia_conf_{o['id']}"):
                        from email_service import invia_email
                        err = invia_email(
                            email_dest, oggetto, corpo_default,
                            tipo="conferma_ordine",
                            riferimento_id=o["id"]
                        )
                        if err:
                            st.error(f"Errore invio: {err}")
                        else:
                            st.success("Conferma d'ordine inviata.")
                            st.session_state[f"conf_inviata_{o['id']}"] = True
                            st.rerun()

                if st.session_state.get(f"conf_inviata_{o['id']}"):
                    with col_b:
                        if st.button(
                            "Crea evento per questa offerta",
                            key=f"crea_ev_{o['id']}"
                        ):
                            st.session_state.pagina = "eventi"
                            st.session_state.offerta_per_evento = o
                            st.rerun()

    st.markdown("---")

    if can_edit(utente):
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Modifica", key=f"omod_{o['id']}"):
                st.session_state[f"edit_offerta_{o['id']}"] = True
        with col2:
            if st.button("Nuova versione", key=f"onv_{o['id']}"):
                nuova = nuova_versione_offerta(o["id"], st.session_state.utente["id"])
                if nuova:
                    st.success(f"Creata versione {nuova['versione']}.")
                    st.rerun()
        with col3:
            stati_successivi = [s for s in STATI_OFFERTA if s != o["stato"]]
            nuovo_stato = st.selectbox(
                "Cambia stato", ["—"] + stati_successivi,
                key=f"ost_{o['id']}"
            )
            if nuovo_stato != "—":
                aggiorna_offerta(o["id"], {"stato": nuovo_stato})
                st.rerun()

    if st.session_state.get(f"edit_offerta_{o['id']}"):
        st.markdown("---")
        _form_modifica_offerta(o, utente)


def _form_righe(righe_default=None, key_prefix="nr"):
    if "righe_temp" not in st.session_state or \
            st.session_state.get(f"{key_prefix}_init") != key_prefix:
        st.session_state.righe_temp = righe_default or []
        st.session_state[f"{key_prefix}_init"] = key_prefix

    # Separa visivamente base da upgrade
    righe_base = [r for r in st.session_state.righe_temp if not r.get("upgrade")]
    righe_upgrade = [r for r in st.session_state.righe_temp if r.get("upgrade")]

    totale_base = 0.0
    totale_upgrade = 0.0
    righe_aggiornate = []

    # ── RIGHE BASE ──
    st.markdown(
        "<div style='background:#1a1a2e;color:white;border-radius:6px 6px 0 0;"
        "padding:8px 14px;font-size:12px;font-weight:700;letter-spacing:0.5px;'>"
        "PACCHETTO BASE</div>",
        unsafe_allow_html=True
    )

    indici_base = [i for i, r in enumerate(st.session_state.righe_temp) if not r.get("upgrade")]
    for idx in indici_base:
        r = st.session_state.righe_temp[idx]
        col1, col2, col3, col4, col5 = st.columns([4, 1, 2, 1, 1])
        with col1:
            desc = st.text_input(
                "Descrizione", value=r.get("descrizione", ""),
                key=f"{key_prefix}_d{idx}"
            )
        with col2:
            qta = st.number_input(
                "Qta", min_value=0.0, value=float(r.get("qta", 1)),
                step=1.0, key=f"{key_prefix}_q{idx}"
            )
        with col3:
            prezzo = st.number_input(
                "Prezzo", min_value=0.0, value=float(r.get("prezzo", 0)),
                step=10.0, key=f"{key_prefix}_p{idx}"
            )
        with col4:
            tot = qta * prezzo
            st.metric("Tot.", f"{tot:,.2f}")
        with col5:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("X", key=f"{key_prefix}_del{idx}"):
                st.session_state.righe_temp.pop(idx)
                st.rerun()
        righe_aggiornate.append({
            "descrizione": desc, "qta": qta,
            "prezzo": prezzo, "totale": tot,
            "upgrade": False
        })
        totale_base += tot

    if st.button("+ Aggiungi voce base", key=f"{key_prefix}_add_base"):
        st.session_state.righe_temp.append({
            "descrizione": "", "qta": 1,
            "prezzo": 0.0, "totale": 0.0,
            "upgrade": False
        })
        st.rerun()

    st.markdown(
        f"<div style='background:#f4f4f8;border-radius:0 0 6px 6px;"
        f"padding:8px 14px;font-size:12px;font-weight:700;color:#1a1a2e;"
        f"margin-bottom:12px;'>Totale base: {totale_base:,.2f}</div>",
        unsafe_allow_html=True
    )

    # ── RIGHE UPGRADE ──
    st.markdown(
        "<div style='background:#856404;color:white;border-radius:6px 6px 0 0;"
        "padding:8px 14px;font-size:12px;font-weight:700;letter-spacing:0.5px;'>"
        "OPZIONI UPGRADE (opzionali)</div>",
        unsafe_allow_html=True
    )

    indici_upgrade = [i for i, r in enumerate(st.session_state.righe_temp) if r.get("upgrade")]
    for idx in indici_upgrade:
        r = st.session_state.righe_temp[idx]
        col1, col2, col3, col4, col5 = st.columns([4, 1, 2, 1, 1])
        with col1:
            desc = st.text_input(
                "Descrizione upgrade", value=r.get("descrizione", ""),
                key=f"{key_prefix}_d{idx}"
            )
        with col2:
            qta = st.number_input(
                "Qta", min_value=0.0, value=float(r.get("qta", 1)),
                step=1.0, key=f"{key_prefix}_q{idx}"
            )
        with col3:
            prezzo = st.number_input(
                "Prezzo", min_value=0.0, value=float(r.get("prezzo", 0)),
                step=10.0, key=f"{key_prefix}_p{idx}"
            )
        with col4:
            tot = qta * prezzo
            st.metric("Tot.", f"{tot:,.2f}")
        with col5:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("X", key=f"{key_prefix}_del{idx}"):
                st.session_state.righe_temp.pop(idx)
                st.rerun()
        righe_aggiornate.append({
            "descrizione": desc, "qta": qta,
            "prezzo": prezzo, "totale": tot,
            "upgrade": True
        })
        totale_upgrade += tot

    if st.button("+ Aggiungi opzione upgrade", key=f"{key_prefix}_add_upgrade"):
        st.session_state.righe_temp.append({
            "descrizione": "", "qta": 1,
            "prezzo": 0.0, "totale": 0.0,
            "upgrade": True
        })
        st.rerun()

    if totale_upgrade > 0:
        st.markdown(
            f"<div style='background:#fff3cd;border:1px solid #ffc107;"
            f"border-radius:0 0 6px 6px;padding:8px 14px;font-size:12px;"
            f"font-weight:700;color:#856404;margin-bottom:4px;'>"
            f"Upgrade opzionale: {totale_upgrade:,.2f} &nbsp;·&nbsp; "
            f"Totale con upgrade: {totale_base + totale_upgrade:,.2f}</div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            "<div style='background:#f4f4f8;border-radius:0 0 6px 6px;"
            "padding:8px 14px;font-size:12px;color:#888;margin-bottom:4px;'>"
            "Nessun upgrade aggiunto</div>",
            unsafe_allow_html=True
        )

    # Ricostruisce la lista nell'ordine corretto (base prima, upgrade dopo)
    st.session_state.righe_temp = righe_aggiornate

    return st.session_state.righe_temp, totale_base


def _form_nuova_offerta(utente, cliente_id):
    st.subheader("Nuova offerta")

    templates = lista_template(utente["id"])
    if templates:
        st.markdown("**Parti da un template**")
        opzioni_tmpl = {"— Nessun template —": None}
        opzioni_tmpl.update({t["titolo"]: t["id"] for t in templates})

        tmpl_presel = st.session_state.get("template_selezionato")
        default_idx = 0
        if tmpl_presel:
            nomi = list(opzioni_tmpl.keys())
            if tmpl_presel.get("titolo") in nomi:
                default_idx = nomi.index(tmpl_presel["titolo"])

        sel = st.selectbox(
            "Carica template",
            list(opzioni_tmpl.keys()),
            index=default_idx,
            key="sel_template"
        )
        tmpl_id = opzioni_tmpl[sel]

        if tmpl_id and st.button("Carica voci dal template"):
            tmpl = get_template(tmpl_id)
            if tmpl:
                righe = tmpl.get("righe") or []
                if isinstance(righe, str):
                    try:
                        righe = json.loads(righe)
                    except:
                        righe = []
                # Assicura che tutte le righe template abbiano il flag upgrade
                for r in righe:
                    if "upgrade" not in r:
                        r["upgrade"] = False
                st.session_state.righe_temp = righe
                st.session_state.template_selezionato = None
                st.success(f"Template '{tmpl['titolo']}' caricato.")
                st.rerun()

        st.markdown("---")

    offerta_ref = st.session_state.get("offerta_per_evento")

    with st.form("form_nuova_offerta"):
        col1, col2 = st.columns(2)
        with col1:
            titolo = st.text_input(
                "Titolo offerta *",
                value=offerta_ref.get("titolo", "") if offerta_ref else ""
            )
            valuta = st.selectbox("Valuta", VALUTE)
            data_emissione = st.date_input("Data emissione", value=date.today())
        with col2:
            stato = st.selectbox("Stato iniziale", STATI_OFFERTA)
            data_scadenza = st.date_input("Data scadenza", value=None)
        descrizione = st.text_area(
            "Descrizione",
            value=offerta_ref.get("descrizione", "") if offerta_ref else ""
        )
        note = st.text_area("Note interne")
        submitted = st.form_submit_button("Crea e genera PDF")

    if submitted:
        if not titolo:
            st.error("Il titolo e obbligatorio.")
        else:
            righe = st.session_state.get("righe_temp", [])
            # Importo = solo righe base per default
            righe_base = [r for r in righe if not r.get("upgrade")]
            importo = sum(r.get("totale", 0) for r in righe_base)
            nuova = crea_offerta({
                "cliente_id": cliente_id,
                "titolo": titolo,
                "descrizione": descrizione,
                "importo": importo,
                "valuta": valuta,
                "stato": stato,
                "data_emissione": data_emissione.isoformat(),
                "data_scadenza": data_scadenza.isoformat() if data_scadenza else None,
                "righe": righe,
                "note": note,
            }, utente["id"])
            st.session_state.righe_temp = []
            st.session_state.offerta_per_evento = None
            if nuova:
                cliente_dati = get_cliente(cliente_id) or {}
                pdf_bytes = genera_pdf_offerta(nuova, cliente_dati)
                st.success(f"Offerta {nuova['numero']} creata.")
                if pdf_bytes:
                    st.download_button(
                        label="Scarica PDF offerta",
                        data=pdf_bytes,
                        file_name=f"{nuova['numero']}.pdf",
                        mime="application/pdf",
                        key="pdf_nuova"
                    )
            st.rerun()

    st.markdown("---")
    _form_righe(key_prefix="nr")


def _form_modifica_offerta(o, utente):
    righe_esistenti = o.get("righe") or []
    if isinstance(righe_esistenti, str):
        try:
            righe_esistenti = json.loads(righe_esistenti)
        except:
            righe_esistenti = []

    # Assicura flag upgrade su tutte le righe esistenti
    for r in righe_esistenti:
        if "upgrade" not in r:
            r["upgrade"] = False

    with st.form(f"form_edit_offerta_{o['id']}"):
        col1, col2 = st.columns(2)
        with col1:
            titolo = st.text_input("Titolo *", value=o["titolo"])
            valuta = st.selectbox(
                "Valuta", VALUTE,
                index=VALUTE.index(o.get("valuta", "CHF"))
                if o.get("valuta") in VALUTE else 0
            )
            data_emissione = st.date_input(
                "Data emissione",
                value=date.fromisoformat(o["data_emissione"])
                if o.get("data_emissione") else date.today()
            )
        with col2:
            stato = st.selectbox(
                "Stato", STATI_OFFERTA,
                index=STATI_OFFERTA.index(o["stato"])
                if o["stato"] in STATI_OFFERTA else 0
            )
            data_scadenza = st.date_input(
                "Scadenza",
                value=date.fromisoformat(o["data_scadenza"])
                if o.get("data_scadenza") else None
            )
        descrizione = st.text_area("Descrizione", value=o.get("descrizione", ""))
        note = st.text_area("Note", value=o.get("note", ""))
        col1, col2 = st.columns(2)
        with col1:
            salva = st.form_submit_button("Salva", use_container_width=True)
        with col2:
            annulla = st.form_submit_button("Annulla", use_container_width=True)

    if salva:
        righe = st.session_state.get("righe_temp", righe_esistenti)
        righe_base = [r for r in righe if not r.get("upgrade")]
        importo = sum(r.get("totale", 0) for r in righe_base)
        aggiorna_offerta(o["id"], {
            "titolo": titolo,
            "descrizione": descrizione,
            "importo": importo,
            "valuta": valuta,
            "stato": stato,
            "data_emissione": data_emissione.isoformat(),
            "data_scadenza": data_scadenza.isoformat() if data_scadenza else None,
            "righe": righe,
            "note": note,
        })
        st.session_state[f"edit_offerta_{o['id']}"] = False
        st.rerun()
    if annulla:
        st.session_state[f"edit_offerta_{o['id']}"] = False
        st.rerun()

    st.markdown("---")
    _form_righe(righe_default=righe_esistenti, key_prefix=f"er_{o['id']}")
