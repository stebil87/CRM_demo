import streamlit as st
import json
from db import (
    lista_template, get_template, crea_template,
    aggiorna_template, elimina_template,
    get_condivisioni_template, condividi_template,
    rimuovi_condivisione_template, lista_utenti
)
from auth import can_edit

COLORI_VALUTA = ["CHF", "EUR", "USD"]

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

    miei = [t for t in templates if t.get("created_by") == utente["id"]]
    condivisi = [t for t in templates if t.get("created_by") != utente["id"]]

    if miei:
        st.markdown("**I tuoi template**")
        for t in miei:
            _scheda_template(t, utente, is_owner=True)

    if condivisi:
        st.markdown("---")
        st.markdown("**Template condivisi con te**")
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

    with st.expander(
        f"{t['titolo']}   |   {n_righe} voci   |   "
        f"{t.get('valuta','CHF')} {totale:,.2f}"
        + ("   |   tuo" if is_owner else f"   |   da {nome_creatore}")
    ):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Titolo:** {t['titolo']}")
            if t.get("descrizione"):
                st.markdown(f"**Descrizione:** {t['descrizione']}")
            st.markdown(f"**Valuta:** {t.get('valuta','CHF')}")
        with col2:
            st.markdown(f"**Creato da:** {nome_creatore}")
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

            # Gestione condivisioni
            st.markdown("---")
            _gestione_condivisioni(t, utente)


def _gestione_condivisioni(t, utente):
    st.markdown("**Condivisioni**")
    condivisioni = get_condivisioni_template(t["id"])
    tutti_utenti = lista_utenti()
    altri_utenti = [u for u in tutti_utenti if u["id"] != utente["id"]]

    # Chi ha già accesso
    ids_condivisi = [c["utente_id"] for c in condivisioni]
    if condivisioni:
        for c in condivisioni:
            u = c.get("utente") or {}
            nome_u = f"{u.get('nome','')} {u.get('cognome','')}".strip()
            col1, col2 = st.columns([4, 1])
            col1.markdown(
                f"<span style='font-size:13px;'>{nome_u}</span>",
                unsafe_allow_html=True
            )
            if col2.button("Rimuovi", key=f"rem_cond_{t['id']}_{c['utente_id']}"):
                rimuovi_condivisione_template(t["id"], c["utente_id"])
                st.rerun()
    else:
        st.markdown(
            "<span style='font-size:12px;color:#aaa;'>"
            "Non condiviso con nessuno.</span>",
            unsafe_allow_html=True
        )

    # Aggiungi condivisione
    disponibili = [u for u in altri_utenti if u["id"] not in ids_condivisi]
    if disponibili:
        opzioni = {"— Seleziona utente —": None}
        opzioni.update({
            f"{u['nome']} {u['cognome']}": u["id"]
            for u in disponibili
        })
        sel = st.selectbox(
            "Condividi con",
            list(opzioni.keys()),
            key=f"sel_cond_{t['id']}"
        )
        if opzioni[sel] and st.button(
            "Condividi", key=f"btn_cond_{t['id']}"
        ):
            err = condividi_template(t["id"], opzioni[sel])
            if err:
                st.error(f"Errore: {err}")
            else:
                st.success("Template condiviso.")
                st.rerun()
    else:
        st.markdown(
            "<span style='font-size:12px;color:#aaa;'>"
            "Tutti gli utenti hanno già accesso.</span>",
            unsafe_allow_html=True
        )


def _form_nuovo_template(utente):
    st.subheader("Nuovo template")

    with st.form("form_nuovo_template"):
        col1, col2 = st.columns(2)
        with col1:
            titolo = st.text_input("Titolo *")
            valuta = st.selectbox("Valuta", COLORI_VALUTA)
        with col2:
            descrizione = st.text_area("Descrizione", height=80)
        note = st.text_area("Note interne", height=60)
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
            valuta = st.selectbox(
                "Valuta", COLORI_VALUTA,
                index=COLORI_VALUTA.index(t.get("valuta","CHF"))
                if t.get("valuta") in COLORI_VALUTA else 0
            )
        with col2:
            descrizione = st.text_area(
                "Descrizione", value=t.get("descrizione",""), height=80
            )
        note = st.text_area("Note", value=t.get("note",""), height=60)
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
        })
        st.session_state[f"edit_tmpl_{t['id']}"] = False
        st.rerun()
    if annulla:
        st.session_state[f"edit_tmpl_{t['id']}"] = False
        st.rerun()

    st.markdown("---")
    _form_righe_template(
        key_prefix=f"tmpl_{t['id']}",
        state_key=state_key,
        righe_default=righe_esistenti
    )


def _form_righe_template(key_prefix, state_key, righe_default=None):
    if state_key not in st.session_state:
        st.session_state[state_key] = righe_default or []

    st.markdown("**Voci del template**")
    totale_generale = 0.0
    righe_aggiornate = []

    for i, r in enumerate(st.session_state[state_key]):
        col1, col2, col3, col4 = st.columns([4, 1, 2, 1])
        with col1:
            desc = st.text_input(
                "Descrizione", value=r.get("descrizione", ""),
                key=f"{key_prefix}_d{i}"
            )
        with col2:
            qta = st.number_input(
                "Qta", min_value=0.0,
                value=float(r.get("qta", 1)),
                step=1.0, key=f"{key_prefix}_q{i}"
            )
        with col3:
            prezzo = st.number_input(
                "Prezzo", min_value=0.0,
                value=float(r.get("prezzo", 0)),
                step=10.0, key=f"{key_prefix}_p{i}"
            )
        with col4:
            tot = qta * prezzo
            st.metric("Totale", f"{tot:,.2f}")
            if st.button("Rimuovi", key=f"{key_prefix}_del{i}"):
                st.session_state[state_key].pop(i)
                st.rerun()
        righe_aggiornate.append({
            "descrizione": desc, "qta": qta,
            "prezzo": prezzo, "totale": tot
        })
        totale_generale += tot

    st.session_state[state_key] = righe_aggiornate

    if st.button("Aggiungi riga", key=f"{key_prefix}_add"):
        st.session_state[state_key].append({
            "descrizione": "", "qta": 1, "prezzo": 0.0, "totale": 0.0
        })
        st.rerun()

    st.markdown(f"**Totale template: {totale_generale:,.2f}**")
