import streamlit as st
from db import login_utente, logout_utente, get_profilo_utente

def check_auth():
    """Controlla se l'utente è loggato. Restituisce il profilo o None."""
    if "utente" not in st.session_state:
        st.session_state.utente = None
    return st.session_state.utente

def pagina_login():
    st.title("🔐 CRM — Accesso")
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("form_login"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Entra", use_container_width=True)
        if submitted:
            if not email or not password:
                st.error("Inserisci email e password.")
                return
            with st.spinner("Accesso in corso..."):
                user, err = login_utente(email, password)
            
            if err:
                st.error(f"Errore login: {err}")
                return
            
            st.write(f"DEBUG - User ID: {user.id}")
            
            profilo = get_profilo_utente(user.id)
            st.write(f"DEBUG - Profilo: {profilo}")
            
            if not profilo:
                st.error("Utente non trovato nel sistema. Contatta un amministratore.")
                return
            if not profilo.get("attivo", True):
                st.error("Account disattivato.")
                return
            st.session_state.utente = profilo
            st.session_state.supabase_user = user
            st.rerun()

def do_logout():
    logout_utente()
    st.session_state.utente = None
    st.session_state.supabase_user = None
    st.rerun()

def can_edit(utente):
    return utente and utente["ruolo"] in ("admin", "modifica")

def is_admin(utente):
    return utente and utente["ruolo"] == "admin"
