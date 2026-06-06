import streamlit as st
from db import get_supabase, get_profilo_utente

def login_utente(email, password):
    sb = get_supabase()
    try:
        res = sb.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.supabase_session = res.session
        return res.user, None
    except Exception as e:
        return None, str(e)

def logout_utente():
    sb = get_supabase()
    try:
        sb.auth.sign_out()
    except:
        pass

def check_auth():
    if "utente" not in st.session_state:
        st.session_state.utente = None
    return st.session_state.utente

def pagina_login():
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
            if err or not user:
                st.error("Credenziali non valide.")
                return
            profilo = get_profilo_utente(user.id)
            if not profilo:
                st.error("Utente non trovato nel sistema. Contatta un amministratore.")
                return
            if not profilo.get("attivo", True):
                st.error("Account disattivato. Contatta un amministratore.")
                return
            st.session_state.utente = profilo
            st.session_state.supabase_user = user
            st.rerun()

def do_logout():
    logout_utente()
    st.session_state.utente = None
    st.session_state.supabase_user = None
    st.session_state.supabase_session = None
    st.rerun()

def can_edit(utente):
    return utente and utente["ruolo"] in ("admin", "modifica")

def is_admin(utente):
    return utente and utente["ruolo"] == "admin"
