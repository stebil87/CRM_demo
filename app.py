import streamlit as st
from auth import check_auth, pagina_login, do_logout, is_admin
from dashboard import pagina_dashboard
from clienti import pagina_clienti
from diario import pagina_diario
from offerte import pagina_offerte
from documenti import pagina_documenti
from admin import pagina_admin
from messaggi import pagina_messaggi
from calendario import pagina_calendario
from template_offerte import pagina_template
from eventi_catering import pagina_eventi
from db import lista_messaggi_non_letti

st.set_page_config(
    page_title="1908 Group — CRM",
    page_icon="1908_Group_Black.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

[data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
[data-testid="stStatusWidget"] { display: none !important; }
footer { display: none !important; }
#MainMenu { visibility: hidden; }

[data-testid="stSidebar"] {
    min-width: 260px !important;
    width: 260px !important;
}

.login-label {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: #aaaabc;
    text-align: center;
    margin-bottom: 24px;
}
.login-footer {
    font-size: 11px;
    color: #c0c0cc;
    text-align: center;
    margin-top: 28px;
    letter-spacing: 0.3px;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d0d1a 0%, #1a1a2e 60%, #16213e 100%);
    border-right: 1px solid #2a2a4a;
}
section[data-testid="stSidebar"] * {
    color: #e8e8f0 !important;
}
section[data-testid="stSidebar"] .stButton > button {
    background: transparent;
    color: #c8c8e0 !important;
    border: none;
    border-radius: 6px;
    width: 100%;
    text-align: left;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 500;
    letter-spacing: 0.3px;
    transition: all 0.2s ease;
    margin: 1px 0;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.08) !important;
    color: #ffffff !important;
    border-left: 3px solid #4a9eff;
    padding-left: 13px;
}

.main .block-container {
    padding: 2rem 2.5rem;
    max-width: 1400px;
}

h1 {
    font-size: 22px !important;
    font-weight: 600 !important;
    color: #0d0d1a !important;
    letter-spacing: -0.3px;
    margin-bottom: 4px !important;
}
h2 { font-size: 16px !important; font-weight: 600 !important; color: #1a1a2e !important; }
h3 { font-size: 14px !important; font-weight: 600 !important; color: #1a1a2e !important; }

.stButton > button {
    background: #1a1a2e;
    color: white !important;
    border: none;
    border-radius: 6px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 500;
    letter-spacing: 0.2px;
    transition: all 0.2s ease;
    box-shadow: 0 1px 3px rgba(0,0,0,0.15);
}
.stButton > button:hover {
    background: #2d2d5e !important;
    box-shadow: 0 3px 8px rgba(0,0,0,0.2);
    transform: translateY(-1px);
}
.stButton > button[kind="secondary"] {
    background: #f4f4f8;
    color: #1a1a2e !important;
    border: 1px solid #dddde8;
}

.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    border: 1px solid #dddde8;
    border-radius: 6px;
    font-size: 13px;
    color: #1a1a2e;
    background: #fafafa;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #1a1a2e !important;
    box-shadow: 0 0 0 2px rgba(26,26,46,0.08);
    background: white;
}

[data-testid="metric-container"] {
    background: white;
    border: 1px solid #eaeaf0;
    border-radius: 10px;
    padding: 20px 24px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
[data-testid="metric-container"] label {
    font-size: 11px !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #888 !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 26px !important;
    font-weight: 700 !important;
    color: #0d0d1a !important;
}

.streamlit-expanderHeader {
    background: #fafafa;
    border: 1px solid #eaeaf0;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 500;
    color: #1a1a2e;
    padding: 12px 16px;
}
.streamlit-expanderContent {
    border: 1px solid #eaeaf0;
    border-top: none;
    border-radius: 0 0 8px 8px;
    padding: 16px;
    background: white;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 2px solid #eaeaf0;
    background: transparent;
}
.stTabs [data-baseweb="tab"] {
    font-size: 13px;
    font-weight: 500;
    color: #888;
    padding: 10px 20px;
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
}
.stTabs [aria-selected="true"] {
    color: #1a1a2e !important;
    border-bottom: 2px solid #1a1a2e !important;
    font-weight: 600;
}

hr { border: none; border-top: 1px solid #eaeaf0; margin: 16px 0; }
.stAlert { border-radius: 8px; font-size: 13px; }

.stForm [data-testid="stFormSubmitButton"] > button {
    background: #1a1a2e;
    color: white !important;
    font-weight: 600;
    padding: 10px 28px;
    border-radius: 6px;
    font-size: 13px;
}

.sidebar-user {
    background: rgba(255,255,255,0.06);
    border-radius: 8px;
    padding: 12px 14px;
    margin: 8px 0 16px 0;
}
.sidebar-nav-label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    color: #666888 !important;
    padding: 14px 16px 6px 16px;
}
</style>
""", unsafe_allow_html=True)

for k, v in {
    "pagina": "dashboard",
    "cliente_id": None,
    "cliente_nome": None,
    "reply_to": None,
    "template_selezionato": None,
    "offerta_per_evento": None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

utente = check_auth()

if not utente:
    _, col, _ = st.columns([1, 1, 1])
    with col:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        try:
            logo_col1, logo_col2, logo_col3 = st.columns([1, 2, 1])
            with logo_col2:
                st.image("1908_Group_Black.png", use_container_width=True)
        except:
            st.markdown(
                "<h2 style='text-align:center;color:#1a1a2e;'>1908 Group SA</h2>",
                unsafe_allow_html=True
            )
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<p class='login-label'>Accesso riservato</p>", unsafe_allow_html=True)
        pagina_login()
        st.markdown(
            "<p class='login-footer'>1908 Group SA &nbsp;·&nbsp; "
            "Piattaforma CRM &nbsp;·&nbsp; Uso riservato</p>",
            unsafe_allow_html=True
        )
    st.stop()

non_letti = lista_messaggi_non_letti(utente["id"])
n_non_letti = len(non_letti)

with st.sidebar:
    st.markdown("<br>", unsafe_allow_html=True)
    try:
        st.image("1908_Group_Black.png", width=150)
    except:
        st.markdown("**1908 Group SA**")

    st.markdown("<hr style='border-color:#2a2a4a;margin:16px 0;'>", unsafe_allow_html=True)

    st.markdown(f"""
    <div class="sidebar-user">
        <div style="font-size:13px;font-weight:600;color:#ffffff !important;">
            {utente['nome']} {utente['cognome']}
        </div>
        <div style="font-size:11px;color:#9999bb !important;margin-top:3px;">
            {utente['email']}
        </div>
        <div style="margin-top:8px;">
            <span style="background:#2a2a4a;color:#aaaacc !important;font-size:10px;
            font-weight:600;text-transform:uppercase;letter-spacing:0.8px;
            padding:3px 8px;border-radius:4px;">
            {utente['ruolo']}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sidebar-nav-label">Navigazione</div>', unsafe_allow_html=True)

    label_msg = f"Messaggi  ({n_non_letti})" if n_non_letti > 0 else "Messaggi"

    nav_items = [
        ("dashboard",   "Dashboard"),
        ("clienti",     "Clienti"),
        ("offerte_all", "Offerte"),
        ("template",    "Template offerte"),
        ("eventi",      "Eventi"),
        ("calendario",  "Calendario"),
        ("messaggi",    label_msg),
    ]
    if is_admin(utente):
        nav_items.append(("admin", "Amministrazione"))

    for pagina_key, label in nav_items:
        if st.button(label, key=f"nav_{pagina_key}", use_container_width=True):
            st.session_state.pagina = pagina_key
            if pagina_key == "offerte_all":
                st.session_state.cliente_id = None
                st.session_state.cliente_nome = None
            st.rerun()

    st.markdown("<hr style='border-color:#2a2a4a;margin:16px 0;'>", unsafe_allow_html=True)

    notifiche_on = not st.session_state.get("notifiche_disattivate", False)
    label_notifiche = "Notifiche: ON" if notifiche_on else "Notifiche: OFF"
    if st.button(label_notifiche, key="toggle_notifiche", use_container_width=True):
        st.session_state.notifiche_disattivate = notifiche_on
        st.rerun()

    if st.button("Esci", key="nav_logout", use_container_width=True):
        do_logout()

p = st.session_state.pagina
breadcrumb_map = {
    "dashboard":   "Dashboard",
    "clienti":     "Clienti",
    "diario":      f"Clienti  /  {st.session_state.cliente_nome or ''}  /  Diario",
    "offerte":     f"Clienti  /  {st.session_state.cliente_nome or ''}  /  Offerte",
    "offerte_all": "Offerte",
    "documenti":   f"Clienti  /  {st.session_state.cliente_nome or ''}  /  Documenti",
    "template":    "Template offerte",
    "eventi":      "Eventi",
    "calendario":  "Calendario",
    "messaggi":    "Messaggi",
    "admin":       "Amministrazione",
}
breadcrumb = breadcrumb_map.get(p, "")
st.markdown(
    f"<p style='font-size:11px;color:#aaa;letter-spacing:0.5px;"
    f"margin-bottom:4px;text-transform:uppercase;'>{breadcrumb}</p>",
    unsafe_allow_html=True
)

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
elif p == "template":
    pagina_template(utente)
elif p == "eventi":
    pagina_eventi(utente)
elif p == "calendario":
    pagina_calendario(utente)
elif p == "messaggi":
    pagina_messaggi(utente)
elif p == "admin":
    pagina_admin(utente)
