import streamlit as st
from db import lista_utenti, aggiorna_ruolo_utente, disattiva_utente, get_supabase
from auth import is_admin

RUOLI = ["visualizza", "modifica", "admin", "event_manager"]

def pagina_admin(utente):
    if not is_admin(utente):
        st.error("Accesso riservato agli amministratori.")
        return

    st.title("Amministrazione")
    st.markdown("---")

    tab_utenti, tab_nuovo = st.tabs(["Gestione utenti", "Nuovo utente"])

    with tab_utenti:
        utenti = lista_utenti()
        if not utenti:
            st.info("Nessun utente trovato.")
        else:
            for u in utenti:
                nome_completo = f"{u['nome']} {u['cognome']}"
                stato_badge = "Attivo" if u.get("attivo", True) else "Disattivato"
                with st.expander(
                    f"{nome_completo} — {u['email']} [{u['ruolo'].upper()}] — {stato_badge}"
                ):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"**Ruolo attuale:** {u['ruolo']}")
                        nuovo_ruolo = st.selectbox(
                            "Cambia ruolo",
                            RUOLI,
                            index=RUOLI.index(u["ruolo"]) if u["ruolo"] in RUOLI else 0,
                            key=f"ruolo_{u['id']}"
                        )
                        if st.button("Salva ruolo", key=f"sr_{u['id']}"):
                            aggiorna_ruolo_utente(u["id"], nuovo_ruolo)
                            st.success("Ruolo aggiornato.")
                            st.rerun()
                    with col2:
                        st.markdown(
                            f"**Stato:** {'Attivo' if u.get('attivo', True) else 'Disattivato'}"
                        )
                        if u.get("attivo", True) and u["id"] != utente["id"]:
                            if st.button("Disattiva", key=f"dis_{u['id']}"):
                                disattiva_utente(u["id"])
                                st.rerun()
                    with col3:
                        st.markdown(
                            f"**Creato il:** {(u.get('created_at') or '')[:10]}"
                        )

    with tab_nuovo:
        st.subheader("Crea nuovo utente")
        with st.form("form_nuovo_utente"):
            col1, col2 = st.columns(2)
            with col1:
                nome = st.text_input("Nome *")
                email = st.text_input("Email *")
            with col2:
                cognome = st.text_input("Cognome *")
                ruolo = st.selectbox("Ruolo", RUOLI)
            password_temp = st.text_input("Password temporanea *", type="password")
            submitted = st.form_submit_button("Crea utente")

        if submitted:
            if not all([nome, cognome, email, password_temp]):
                st.error("Tutti i campi sono obbligatori.")
            else:
                try:
                    sb = get_supabase()
                    res = sb.auth.admin.create_user({
                        "email": email,
                        "password": password_temp,
                        "email_confirm": True
                    })
                    new_user = res.user
                    from db import crea_utente_profilo
                    err = crea_utente_profilo(
                        new_user.id, nome, cognome, email, ruolo
                    )
                    if err:
                        st.error(f"Utente Auth creato ma errore profilo: {err}")
                    else:
                        st.success(
                            f"Utente {nome} {cognome} creato con ruolo '{ruolo}'."
                        )
                        st.rerun()
                except Exception as e:
                    st.error(f"Errore: {str(e)}")
