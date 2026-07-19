"""Pannello azioni condiviso per ogni email (richiesta sito o diretta):
rispondere, fissare un appuntamento nel proprio calendario o di un collega,
creare un follow-up con nota. Usato da dashboard, pagina Email, storico."""
import streamlit as st
from datetime import date, datetime, time as _time
from db import (get_sb, prendi_in_carico_email, lista_utenti,
                get_calendari_modificabili, crea_evento, crea_voce_diario)


def _estrai_email(mittente):
    import re
    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", str(mittente or ""))
    return m.group(0) if m else ""


def _opzioni_utenti_calendario(utente):
    """Utenti sui cui calendari posso scrivere (io + colleghi autorizzati)."""
    ids = get_calendari_modificabili(utente["id"])
    out = []
    for u in (lista_utenti() or []):
        if u["id"] in ids:
            etich = f"{u.get('nome','')} {u.get('cognome','')}".strip()
            if u["id"] == utente["id"]:
                etich += " (io)"
            out.append((u["id"], etich))
    if not out:
        out = [(utente["id"], "io")]
    return out


def pannello_azioni_email(e, utente, key):
    """Tre schede: Rispondi · Appuntamento · Follow-up.
    Funziona sia per email nuove che già prese in carico."""
    cliente_id = e.get("cliente_id")
    tab_r, tab_a, tab_f = st.tabs(["✉️ Rispondi", "📅 Appuntamento", "🔔 Follow-up"])

    with tab_r:
        _tab_rispondi(e, utente, key)
    with tab_a:
        _tab_appuntamento(e, utente, key, cliente_id)
    with tab_f:
        _tab_followup(e, utente, key, cliente_id)


def _tab_rispondi(e, utente, key):
    from email_composer import compositore_email
    if st.session_state.get(f"risp_ok_{key}"):
        st.success("✅ Risposta inviata.")
        return
    dest = _estrai_email(e.get("mittente"))
    if not dest:
        st.info("Nessun indirizzo e-mail nel mittente: usa il campo «A» per scriverlo.")

    def _dopo():
        if not e.get("presa_in_carico"):
            prendi_in_carico_email(e["id"], utente["id"])
        st.session_state[f"risp_ok_{key}"] = True
        st.rerun()

    compositore_email(
        key=f"resp_{key}",
        dest_default=dest,
        oggetto_default=f"Re: {e.get('oggetto','')}",
        riferimento_id=e["id"],
        tipo="risposta_inbox",
        on_sent=_dopo,
        titolo="",
        compatto=True,
    )


def _tab_appuntamento(e, utente, key, cliente_id):
    if st.session_state.get(f"app_ok_{key}"):
        st.success("✅ Appuntamento creato in calendario.")
        return
    opz = _opzioni_utenti_calendario(utente)
    with st.form(f"app_{key}"):
        _nome = str(e.get("mittente", "")).split("·")[0].strip()
        titolo = st.text_input("Titolo *", value=f"Appuntamento — {_nome}")
        col1, col2 = st.columns(2)
        with col1:
            giorno = st.date_input("Data *", value=date.today())
        with col2:
            ora = st.time_input("Ora *", value=_time(9, 0))
        proprietario = st.selectbox(
            "Calendario di *", opz, format_func=lambda x: x[1])
        descrizione = st.text_area("Note", height=80,
                                   placeholder="Dettagli dell'appuntamento...")
        ok = st.form_submit_button("📅 Crea appuntamento")
    if ok:
        if not titolo.strip():
            st.error("Il titolo è obbligatorio.")
            return
        dt = datetime.combine(giorno, ora).isoformat()
        dati = {
            "titolo": titolo.strip(),
            "data_inizio": dt,
            "descrizione": descrizione.strip() or None,
            "proprietario_id": proprietario[0],
            "cliente_id": cliente_id,
        }
        res = crea_evento(dati, utente["id"])
        if res:
            st.session_state[f"app_ok_{key}"] = True
            st.rerun()
        else:
            st.error("Appuntamento non creato.")


def _tab_followup(e, utente, key, cliente_id):
    if st.session_state.get(f"fu_ok_{key}"):
        st.success("✅ Follow-up creato.")
        return

    # se l'email non è agganciata a un cliente, faccio scegliere dalla lista
    if not cliente_id:
        from db import lista_clienti
        clienti = lista_clienti() or []
        def _nome_c(c):
            if c.get("tipo") == "giuridica":
                return c.get("ragione_sociale") or "—"
            return f"{c.get('nome','')} {c.get('cognome','')}".strip() or "—"
        opz_cli = [("", "— Cliente non registrato —")] + [
            (c["id"], _nome_c(c)) for c in sorted(clienti, key=lambda c: _nome_c(c).lower())
        ]
        scelta_cli = st.selectbox(
            "Cliente", opz_cli, format_func=lambda x: x[1], key=f"fucli_{key}",
            help="Aggancia il follow-up a un cliente esistente, o lascia «non registrato».")
        cliente_id = scelta_cli[0] or None

    opz = _opzioni_utenti_calendario(utente)
    with st.form(f"fu_{key}"):
        titolo = st.text_input("Oggetto del follow-up *",
                               value=f"Ricontattare — {e.get('oggetto','')[:40]}")
        col1, col2 = st.columns(2)
        with col1:
            quando = st.date_input("Data promemoria *", value=date.today())
        with col2:
            assegnato = st.selectbox("Assegnato a *", opz, format_func=lambda x: x[1])
        nota = st.text_area("Nota / cosa fare", height=100,
                            placeholder="Es. richiamare per confermare il preventivo...")
        ok = st.form_submit_button("🔔 Crea follow-up")
    if ok:
        if not titolo.strip():
            st.error("L'oggetto è obbligatorio.")
            return
        if not cliente_id:
            # follow-up senza cliente: lo salvo con nota che riporta il mittente
            nota_finale = (nota.strip() + "\n\n[Cliente non registrato — "
                           + str(e.get("mittente","")) + "]").strip()
        else:
            nota_finale = nota.strip()
        dati = {
            "cliente_id": cliente_id,
            "tipo": "followup",
            "titolo": titolo.strip(),
            "contenuto": nota_finale,
            "data_contatto": date.today().isoformat(),
            "followup_data": quando.isoformat(),
            "followup_assegnato_a": assegnato[0],
        }
        res = crea_voce_diario(dati, utente["id"])
        if res:
            st.session_state[f"fu_ok_{key}"] = True
            st.rerun()
        else:
            st.error("Follow-up non creato.")


def form_nuovo_followup(utente, key="dash"):
    """Form autonomo per creare un follow-up dalla dashboard.
    Sceglie cliente (o 'non registrato'), nota, data, assegnatario."""
    from db import lista_clienti, crea_voce_diario
    if st.session_state.get(f"funew_ok_{key}"):
        st.success("✅ Follow-up creato.")
        if st.button("Nuovo", key=f"funew_reset_{key}"):
            st.session_state[f"funew_ok_{key}"] = False
            st.rerun()
        return
    clienti = lista_clienti() or []
    def _nome_c(c):
        if c.get("tipo") == "giuridica":
            return c.get("ragione_sociale") or "—"
        return f"{c.get('nome','')} {c.get('cognome','')}".strip() or "—"
    opz_cli = [("", "— Cliente non registrato —")] + [
        (c["id"], _nome_c(c)) for c in sorted(clienti, key=lambda c: _nome_c(c).lower())]
    opz_u = _opzioni_utenti_calendario(utente)
    with st.form(f"funew_{key}"):
        cli = st.selectbox("Cliente", opz_cli, format_func=lambda x: x[1])
        titolo = st.text_input("Oggetto *", placeholder="Es. richiamare per preventivo")
        col1, col2 = st.columns(2)
        with col1:
            quando = st.date_input("Data promemoria *", value=date.today())
        with col2:
            assegnato = st.selectbox("Assegnato a *", opz_u, format_func=lambda x: x[1])
        nota = st.text_area("Nota / cosa fare", height=90)
        ok = st.form_submit_button("🔔 Crea follow-up", use_container_width=True)
    if ok:
        if not titolo.strip():
            st.error("L'oggetto è obbligatorio.")
            return
        dati = {
            "cliente_id": cli[0] or None,
            "tipo": "followup",
            "titolo": titolo.strip(),
            "contenuto": nota.strip(),
            "data_contatto": date.today().isoformat(),
            "followup_data": quando.isoformat(),
            "followup_assegnato_a": assegnato[0],
        }
        if crea_voce_diario(dati, utente["id"]):
            st.session_state[f"funew_ok_{key}"] = True
            st.rerun()
        else:
            st.error("Follow-up non creato.")
