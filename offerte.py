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
    if righe:
        st.markdown("**Voci:**")
        for r in righe:
            st.markdown(
                f"- {r.get('descrizione','—')}   "
                f"{r.get('qta',1)} x {float(r.get('prezzo',0)):,.2f} = "
                f"**{float(r.get('totale',0)):,.2f}**"
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
            nuovo_stato = st.selectbox("Cambia stato", ["—"] + stati_successivi, key=f"ost_{o['id']}")
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

    st.markdown("**Voci dell'offerta**")
    totale_generale = 0.0
    righe_aggiornate = []

    for i, r in enumerate(st.session_state.righe_temp):
        col1, col2, col3, col4 = st.columns([4, 1, 2, 1])
        with col1:
            desc = st.text_input("Descrizione", value=r.get("descrizione", ""), key=f"{key_prefix}_d{i}")
        with col2:
            qta = st.number_input("Qta", min_value=0.0, value=float(r.get("qta", 1)), step=1.0, key=f"{key_prefix}_q{i}")
        with col3:
            prezzo = st.number_input("Prezzo unit.", min_value=0.0, value=float(r.get("prezzo", 0)), step=10.0, key=f"{key_prefix}_p{i}")
        with col4:
            tot = qta * prezzo
            st.metric("Totale", f"{tot:,.2f}")
            if st.button("Rimuovi", key=f"{key_prefix}_del{i}"):
                st.session_state.righe_temp.pop(i)
                st.rerun()
        righe_aggiornate.append({"descrizione": desc, "qta": qta, "prezzo": prezzo, "totale": tot})
        totale_generale += tot

    st.session_state.righe_temp = righe_aggiornate

    if st.button("Aggiungi riga", key=f"{key_prefix}_add"):
        st.session_state.righe_temp.append({"descrizione": "", "qta": 1, "prezzo": 0.0, "totale": 0.0})
        st.rerun()

    st.markdown(f"**Totale: {totale_generale:,.2f}**")
    return st.session_state.righe_temp, totale_generale


def _form_nuova_offerta(utente, cliente_id):
    st.subheader("Nuova offerta")

    # Selezione template
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
                st.session_state.righe_temp = righe
                st.session_state.template_selezionato = None
                st.success(f"Template '{tmpl['titolo']}' caricato.")
                st.rerun()

        st.markdown("---")

    with st.form("form_nuova_offerta"):
        col1, col2 = st.columns(2)
        with col1:
            titolo = st.text_input("Titolo offerta *")
            valuta = st.selectbox("Valuta", VALUTE)
            data_emissione = st.date_input("Data emissione", value=date.today())
        with col2:
            stato = st.selectbox("Stato iniziale", STATI_OFFERTA)
            data_scadenza = st.date_input("Data scadenza", value=None)
        descrizione = st.text_area("Descrizione")
        note = st.text_area("Note interne")
        submitted = st.form_submit_button("Crea e genera PDF")

    if submitted:
        if not titolo:
            st.error("Il titolo e obbligatorio.")
        else:
            righe = st.session_state.get("righe_temp", [])
            importo = sum(r.get("totale", 0) for r in righe)
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

    with st.form(f"form_edit_offerta_{o['id']}"):
        col1, col2 = st.columns(2)
        with col1:
            titolo = st.text_input("Titolo *", value=o["titolo"])
            valuta = st.selectbox(
                "Valuta", VALUTE,
                index=VALUTE.index(o.get("valuta", "CHF")) if o.get("valuta") in VALUTE else 0
            )
            data_emissione = st.date_input(
                "Data emissione",
                value=date.fromisoformat(o["data_emissione"]) if o.get("data_emissione") else date.today()
            )
        with col2:
            stato = st.selectbox(
                "Stato", STATI_OFFERTA,
                index=STATI_OFFERTA.index(o["stato"]) if o["stato"] in STATI_OFFERTA else 0
            )
            data_scadenza = st.date_input(
                "Scadenza",
                value=date.fromisoformat(o["data_scadenza"]) if o.get("data_scadenza") else None
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
        importo = sum(r.get("totale", 0) for r in righe)
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
