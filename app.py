import streamlit as st
from auth import check_auth, pagina_login, do_logout, is_admin
from dashboard import pagina_dashboard
from clienti import pagina_clienti
from diario import pagina_diario
from offerte import pagina_offerte
from documenti import pagina_documenti
from admin import pagina_admin

st.set_page_config(
    page_title="CRM Demo",
    page_icon="💼",
    layout="wide"
)

st.markdown("""
<style>
[data-testid="stToolbar"] { display: none !important; }
footer { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
.stButton>button {
    border-radius: 6px;
}
section[data-testid="stSidebar"] {
    background-color: #1a1a2e;
}
section[data-testid="stSidebar"] * {
    color: white !important;
}
section[data-testid="stSidebar"] .stButton>button {
    background-color: #16213e;
    color: white !important;
    border: 1px solid #0f3460;
    width: 100%;
    text-align: left;
}
section[data-testid="stSidebar"] .stButton>button:hover {
    background-color: #0f3460;
}
</style>
""", unsafe_allow_html=True)

# Defaults session state
for k, v in {
    "pagina": "dashboard",
    "cliente_id": None,
    "cliente_nome": None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Auth check
utente = check_auth()
if not utente:
    pagina_login()
    st.stop()

# Sidebar navigazione
with st.sidebar:
    try:
        st.image("1908_Group_Black.png", width=140)
    except:
        st.markdown("## 💼 CRM")
    st.markdown("---")
    st.markdown(f"**{utente['nome']} {utente['cognome']}**")
    st.caption(f"Ruolo: {utente['ruolo'].upper()}")
    st.markdown("---")

    if st.button("🏠 Dashboard"):
        st.session_state.pagina = "dashboard"
        st.rerun()
    if st.button("👥 Clienti"):
        st.session_state.pagina = "clienti"
        st.rerun()
    if st.button("📄 Tutte le offerte"):
        st.session_state.pagina = "offerte_all"
        st.session_state.cliente_id = None
        st.session_state.cliente_nome = None
        st.rerun()
    if is_admin(utente):
        st.markdown("---")
        if st.button("⚙️ Admin"):
            st.session_state.pagina = "admin"
            st.rerun()
    st.markdown("---")
    if st.button("🚪 Logout"):
        do_logout()

# Routing pagine
p = st.session_state.pagina

if p == "dashboard":
    pagina_dashboard(utente)
elif p == "clienti":
    pagina_clienti(utente)
elif p == "diario":
    pagina_diario(utente, st.session_state.cliente_id, st.session_state.cliente_nome)
elif p in ("offerte", "offerte_all"):
    pagina_offerte(utente, st.session_state.cliente_id, st.session_state.cliente_nome)
elif p == "documenti":
    pagina_documenti(utente, st.session_state.cliente_id, st.session_state.cliente_nome)
elif p == "admin":
    pagina_admin(utente)