import streamlit as st
import json
import db  # importa tutto il modulo
from auth import can_edit

# Ora prendi le funzioni dal modulo importato
lista_template = db.lista_template
get_template = db.get_template
crea_template = db.crea_template
aggiorna_template = db.aggiorna_template
elimina_template = db.elimina_template

def pagina_template(utente):
    st.title("Template offerte")
    st.markdown("---")

    tab_lista, tab_nuovo = st.tabs(["I miei template", "Nuovo template"])

    with tab_nuovo:
        _form_nuovo_template(utente)

    with tab_lista:
        _lista_template(utente)


def _lista_template(utente):
    templates = lista_template(utente["id"])

    if not templates:
        st.info("Nessun template disponibile. Creane uno dalla scheda accanto.")
        return

    # Dividi miei vs condivisi da altri
    miei = [t for t in templates if t.get("created_by") == utente["id"]]
    condivisi = [t for t in templates if t.get("created_by") != utente["id"] and t.get("condiviso")]

    if miei:
        st.markdown("**I tuoi template**")
        for t in miei:
            _scheda_template(t, utente, is_owner=True)

    if condivisi:
        st.markdown("---")
        st.markdown("**Template condivisi da altri utenti**")
        for t in condivisi:
            _scheda_template(t, utente, is_owner=False)


def _scheda_template(t, utente, is_owner):
    righe = t.get("righe") or []
    if isinstance(righe, str):
        try:
            righe = json.loads(righe)
        except:
            righe = []

    totale = sum(float(r.get("totale", 0)) for r in righe)
    n_righe = len(righe)
    creatore = t.get("creatore") or {}
    nome_creatore = f"{creatore.get('nome','')} {creatore.get('cognome','')}".strip()
    condiviso_badge = "  —  Condiviso" if t.get("condiviso") else ""

    with st.expander(f"{t['titolo']}   |   {n_righe} voci   |   {t.get('valuta','CHF')} {totale:,.2f}{condiviso_badge}"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Titolo:** {t['titolo']}")
            if t.get("descrizione"):
                st.markdown(f"**Descrizione:** {t['descrizione']}")
            st.markdown(f"**Valuta:** {t.get('valuta','CHF')}")
            st.markdown(f"**Creato da:** {nome_creatore}")
        with col2:
            st.markdown(f"**Condiviso con il team:** {'Si' if t.get('condiviso') else 'No'}")
            if t.get("note"):
                st.markdown(f"**Note:** {t['note']}")

        if righe:
            st.markdown("**Voci:**")
            for r in righe:
                st.markdown(
                    f"- {r.get('descrizione','—')}   "
                    f"{r.get('qta',1)} x {float(r.get('prezzo',0)):,.2f} = "
                    f"**{float(r.get('totale',0)):,.2f}**"
                )
            st.markdown(f"**Totale: {t.get('valuta','CHF')} {totale:,.2f}**")

        st.markdown("---")
        col_a, col_b, col_c = st.columns(3)

        with col_a:
            if st.button("Usa per nuova offerta", key=f"usa_{t['id']}"):
                st.session_state.template_selezionato = t
                st.session_state.pagina = "offerte_all"
                st.session_state.cliente_id = None
                st.session_state.cliente_nome = None
                st.success("Template caricato. Vai su Offerte per usarlo.")
                st.rerun()

        if is_owner:
            with col_b:
                if st.button("Modifica", key=f"tmod_{t['id']}"):
                    st.session_state[f"edit_tmpl_{t['id']}"] = True
            with col_c:
                if st.button("Elimina", key=f"tdel_{t['id']}"):
                    st.session_state[f"delconf_tmpl_{t['id']}"] = True

            if st.session_state.get(f"delconf_tmpl_{t['id']}"):
                st.warning("Confermi l'eliminazione del template?")
                c1, c2 = st.columns(2)
                if c1.button("Si, elimina", key=f"tdok_{t['id']}"):
                    elimina_template(t["id"])
                    st.rerun()
                if c2.button("No, annulla", key=f"tdno_{t['id']}"):
                    st.session_state[f"delconf_tmpl_{t['id']}"] = False
                    st.rerun()

            if st.session_state.get(f"edit_tmpl_{t['id']}"):
                st.markdown("---")
                _form_modifica_template(t, utente)


def _form_nuovo_template(utente):
    st.subheader("Nuovo template")

    with st.form("form_nuovo_template"):
        col1, col2 = st.columns(2)
        with col1:
            titolo = st.text_input("Titolo *")
            valuta = st.selectbox("Valuta", ["CHF", "EUR", "USD"])
        with col2:
            condiviso = st.checkbox("Condividi con tutti gli utenti")
        descrizione = st.text_area("Descrizione", height=80)
        note = st.text_area("Note interne", height=80)
        submitted = st.form_submit_button("Crea template", use_container_width=True)

    if submitted:
        if not titolo:
            st.error("Il titolo e obbligatorio.")
        else:
            righe = st.session_state.get("righe_template_new", [])
            crea_template({
                "titolo": titolo,
                "descrizione": descrizione,
                "righe": righe,
                "valuta": valuta,
                "note": note,
                "condiviso": condiviso,
            }, utente["id"])
            st.session_state.righe_template_new = []
            st.success("Template creato.")
            st.rerun()

    st.markdown("---")
    _form_righe_template(key_prefix="tmpl_new", state_key="righe_template_new")


def _form_modifica_template(t, utente):
    righe_esistenti = t.get("righe") or []
    if isinstance(righe_esistenti, str):
        try:
            righe_esistenti = json.loads(righe_esistenti)
        except:
            righe_esistenti = []

    state_key = f"righe_template_{t['id']}"

    with st.form(f"form_edit_tmpl_{t['id']}"):
        col1, col2 = st.columns(2)
        with col1:
            titolo = st.text_input("Titolo *", value=t["titolo"])
            valuta = st.selectbox("Valuta", ["CHF", "EUR", "USD"],
                index=["CHF","EUR","USD"].index(t.get("valuta","CHF")) if t.get("valuta") in ["CHF","EUR","USD"] else 0)
        with col2:
            condiviso = st.checkbox("Condividi con tutti gli utenti", value=t.get("condiviso", False))
        descrizione = st.text_area("Descrizione", value=t.get("descrizione",""), height=80)
        note = st.text_area("Note", value=t.get("note",""), height=80)
        col1, col2 = st.columns(2)
        with col1:
            salva = st.form_submit_button("Salva", use_container_width=True)
        with col2:
            annulla = st.form_submit_button("Annulla", use_container_width=True)

    if salva:
        righe = st.session_state.get(state_key, righe_esistenti)
        aggiorna_template(t["id"], {
            "titolo": titolo,
            "descrizione": descrizione,
            "righe": righe,
            "valuta": valuta,
            "note": note,
            "condiviso": condiviso,
        })
        st.session_state[f"edit_tmpl_{t['id']}"] = False
        st.rerun()
    if annulla:
        st.session_state[f"edit_tmpl_{t['id']}"] = False
        st.rerun()

    st.markdown("---")
    _form_righe_template(key_prefix=f"tmpl_{t['id']}", state_key=state_key, righe_default=righe_esistenti)


def _form_righe_template(key_prefix, state_key, righe_default=None):
    if state_key not in st.session_state:
        st.session_state[state_key] = righe_default or []

    st.markdown("**Voci del template**")
    totale_generale = 0.0
    righe_aggiornate = []

    for i, r in enumerate(st.session_state[state_key]):
        col1, col2, col3, col4 = st.columns([4, 1, 2, 1])
        with col1:
            desc = st.text_input("Descrizione", value=r.get("descrizione", ""), key=f"{key_prefix}_d{i}")
        with col2:
            qta = st.number_input("Qta", min_value=0.0, value=float(r.get("qta", 1)), step=1.0, key=f"{key_prefix}_q{i}")
        with col3:
            prezzo = st.number_input("Prezzo", min_value=0.0, value=float(r.get("prezzo", 0)), step=10.0, key=f"{key_prefix}_p{i}")
        with col4:
            tot = qta * prezzo
            st.metric("Totale", f"{tot:,.2f}")
            if st.button("Rimuovi", key=f"{key_prefix}_del{i}"):
                st.session_state[state_key].pop(i)
                st.rerun()
        righe_aggiornate.append({"descrizione": desc, "qta": qta, "prezzo": prezzo, "totale": tot})
        totale_generale += tot

    st.session_state[state_key] = righe_aggiornate

    if st.button("Aggiungi riga", key=f"{key_prefix}_add"):
        st.session_state[state_key].append({"descrizione": "", "qta": 1, "prezzo": 0.0, "totale": 0.0})
        st.rerun()

    st.markdown(f"**Totale template: {totale_generale:,.2f}**")
