import streamlit as st
from auth import check_auth, pagina_login, do_logout, is_admin, cambia_password, valida_password
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
from inbox_widget import pagina_inbox
from assistente import pagina_assistente, widget_assistente_sidebar
from db import lista_messaggi_non_letti, log_attivita
import time as _time

TIMEOUT_SECONDI = 600  # 10 minuti

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

header[data-testid="stHeader"] {
    display: none !important;
    height: 0 !important;
}
.main > div:first-child {
    padding-top: 0 !important;
}
[data-testid="stAppViewContainer"] > section > div:first-child {
    padding-top: 0 !important;
}
[data-testid="collapsedControl"] { display: none !important; }
button[data-testid="baseButton-header"] { display: none !important; }

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d0d1a 0%, #1a1a2e 60%, #16213e 100%) !important;
    border-right: 1px solid #2a2a4a !important;
    transform: none !important;
    visibility: visible !important;
    display: flex !important;
    min-width: 260px !important;
    width: 260px !important;
    position: relative !important;
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
section[data-testid="stSidebar"] .streamlit-expanderHeader {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid #2a2a4a !important;
    border-radius: 6px !important;
    color: #9999bb !important;
    font-size: 12px !important;
    padding: 8px 12px !important;
}
section[data-testid="stSidebar"] .streamlit-expanderContent {
    background: rgba(0,0,0,0.2) !important;
    border: 1px solid #2a2a4a !important;
    border-top: none !important;
    border-radius: 0 0 6px 6px !important;
    padding: 12px !important;
}

.main .block-container {
    padding: 0rem 2.5rem 2rem 2.5rem;
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
.stButton > button[kind="secondary"]:hover {
    background: #eaeaf4 !important;
}

.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    border: 1px solid #dddde8;
    border-radius: 6px;
    font-size: 13px;
    color: #1a1a2e;
    background: #fafafa;
    transition: border 0.2s;
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
.streamlit-expanderHeader:hover { background: #f0f0f8; }
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

.stDataFrame {
    border: 1px solid #eaeaf0;
    border-radius: 8px;
    overflow: hidden;
}

.sidebar-user {
    background: rgba(255,255,255,0.06);
    border-radius: 8px;
    padding: 12px 14px;
    margin: 8px 0 12px 0;
}
.sidebar-nav-label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    color: #666888 !important;
    padding: 14px 16px 6px 16px;
}

/* ── LOGIN PAGE ── */
.login-page-bg {
    position: fixed;
    top: 0; left: 0;
    width: 100vw; height: 100vh;
    background: linear-gradient(135deg, #0d0d1a 0%, #1a1a2e 60%, #0f3460 100%);
    z-index: 0;
}
.login-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 16px;
    padding: 40px 48px;
    backdrop-filter: blur(10px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    position: relative;
    z-index: 1;
}
.login-card .stTextInput > div > div > input {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    color: white !important;
    border-radius: 8px !important;
}
.login-card .stTextInput > div > div > input:focus {
    border-color: rgba(255,255,255,0.4) !important;
    box-shadow: 0 0 0 2px rgba(255,255,255,0.08) !important;
}
.login-card label {
    color: rgba(255,255,255,0.6) !important;
}
.login-label {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: rgba(255,255,255,0.4);
    text-align: center;
    margin-bottom: 24px;
}
.login-footer {
    font-size: 11px;
    color: rgba(255,255,255,0.25);
    text-align: center;
    margin-top: 28px;
    letter-spacing: 0.3px;
    position: relative;
    z-index: 1;
}
</style>
""", unsafe_allow_html=True)

# ── SESSION STATE ──────────────────────────────────────────────────────────
for k, v in {
    "pagina": "dashboard",
    "cliente_id": None,
    "cliente_nome": None,
    "reply_to": None,
    "template_selezionato": None,
    "offerta_per_evento": None,
    "conferma_logout": False,
    "assistente_history": [],
    "assistente_state": {},
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── AUTH ───────────────────────────────────────────────────────────────────
utente = check_auth()

if utente:
    ora_corrente = _time.time()
    ultima_attivita = st.session_state.get("ultima_attivita", ora_corrente)
    secondi_inattivi = ora_corrente - ultima_attivita

    if secondi_inattivi > TIMEOUT_SECONDI:
        st.session_state.utente = None
        st.session_state.pagina = "dashboard"
        st.session_state.msg_notificati = set()
        utente = None
        st.warning("Sessione scaduta per inattività. Effettua nuovamente il login.")
        st.stop()
    else:
        st.session_state.ultima_attivita = ora_corrente

        if secondi_inattivi > TIMEOUT_SECONDI - 120:
            minuti_rimasti = int((TIMEOUT_SECONDI - secondi_inattivi) / 60) + 1
            st.sidebar.warning(
                f"Sessione in scadenza tra {minuti_rimasti} minuto/i."
            )

if not utente:
    st.markdown(
        """<style>
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(135deg, #0d0d1a 0%, #1a1a2e 60%, #0f3460 100%) !important;
        }
        [data-testid="stAppViewBlockContainer"] {
            background: transparent !important;
        }
        .main {
            background: transparent !important;
        }
        section[data-testid="stSidebar"] {
            display: none !important;
        }
        .block-container {
            padding-top: 4rem !important;
        }
        /* Input login */
        .stTextInput > div > div > input,
        .stTextInput > div > div > input:focus,
        .stTextInput > div > div > input:active {
            background: rgba(255,255,255,0.85) !important;
            border: none !important;
            border-radius: 8px !important;
            color: #1a1a2e !important;
            -webkit-text-fill-color: #1a1a2e !important;
            caret-color: #1a1a2e !important;
            box-shadow: none !important;
        }
        .stTextInput > div > div > input:-webkit-autofill,
        .stTextInput > div > div > input:-webkit-autofill:hover,
        .stTextInput > div > div > input:-webkit-autofill:focus {
            -webkit-box-shadow: 0 0 0 30px rgba(255,255,255,0.85) inset !important;
            -webkit-text-fill-color: #1a1a2e !important;
        }
        .stTextInput > div > div > input::placeholder {
            color: rgba(26,26,46,0.4) !important;
            -webkit-text-fill-color: rgba(26,26,46,0.4) !important;
        }
        /* Label input */
        .stTextInput label {
            color: rgba(255,255,255,0.5) !important;
            font-size: 12px !important;
        }

        /* Autofill browser */
        .stTextInput > div > div > input:-webkit-autofill,
        .stTextInput > div > div > input:-webkit-autofill:hover,
        .stTextInput > div > div > input:-webkit-autofill:focus,
        .stTextInput > div > div > input:-webkit-autofill:active {
            -webkit-box-shadow: 0 0 0 30px #1a1a2e inset !important;
            -webkit-text-fill-color: white !important;
            caret-color: white !important;
        }
        
        /* Bottone Entra */
        .stForm .stFormSubmitButton > button,
        .stForm [data-testid="stFormSubmitButton"] > button {
            background: white !important;
            color: #1a1a2e !important;
            font-weight: 700 !important;
            border-radius: 8px !important;
            width: 100% !important;
            padding: 12px !important;
            font-size: 14px !important;
            letter-spacing: 0.5px !important;
        }
        .stForm .stFormSubmitButton > button:hover,
        .stForm [data-testid="stFormSubmitButton"] > button:hover {
            background: #e8e8f0 !important;
        }
        /* Messaggi errore */
        .stAlert {
            background: rgba(233,69,96,0.15) !important;
            border: 1px solid rgba(233,69,96,0.3) !important;
            color: white !important;
        }
        </style>""",
        unsafe_allow_html=True
    )

    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        # Logo
        logo1, logo2, logo3 = st.columns([1, 2, 1])
        with logo2:
            try:
                st.image("1908_Group_White.png", use_container_width=True)
            except:
                st.markdown(
                    "<h2 style='text-align:center;color:white;'>"
                    "1908 Group SA</h2>",
                    unsafe_allow_html=True
                )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            "<p style='font-size:11px;font-weight:700;letter-spacing:1.5px;"
            "text-transform:uppercase;color:rgba(255,255,255,0.35);"
            "text-align:center;margin-bottom:24px;'>Accesso riservato</p>",
            unsafe_allow_html=True
        )

        pagina_login()

        st.markdown(
            "<p style='font-size:11px;color:rgba(255,255,255,0.2);"
            "text-align:center;margin-top:24px;letter-spacing:0.3px;'>"
            "1908 Group SA &nbsp;·&nbsp; Piattaforma CRM &nbsp;·&nbsp; "
            "Uso riservato</p>",
            unsafe_allow_html=True
        )

    st.stop()

# ── MESSAGGI NON LETTI ─────────────────────────────────────────────────────
non_letti = lista_messaggi_non_letti(utente["id"])
n_non_letti = len(non_letti)

# ── NOTIFICHE TOAST GLOBALI ────────────────────────────────────────────────
if not st.session_state.get("notifiche_disattivate", False):
    if "msg_notificati" not in st.session_state:
        st.session_state.msg_notificati = {m["id"] for m in non_letti}
    gia_notificati = st.session_state.msg_notificati
    nuovi_toast = [m for m in non_letti if m["id"] not in gia_notificati]
    if nuovi_toast:
        for m in nuovi_toast:
            mitt = m.get("mittente") or {}
            nome_mitt = f"{mitt.get('nome','')} {mitt.get('cognome','')}".strip() or "Utente"
            oggetto = m.get("oggetto") or "(nessun oggetto)"
            st.toast(f"Nuovo messaggio da {nome_mitt}: {oggetto}", icon="✉")
            gia_notificati.add(m["id"])
        st.session_state.msg_notificati = gia_notificati

# ── SIDEBAR ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<br>", unsafe_allow_html=True)
    try:
        st.image("1908_Group_White.png", width=150)
    except:
        st.markdown("**1908 Group SA**")

    st.markdown(
        "<hr style='border-color:#2a2a4a;margin:16px 0;'>",
        unsafe_allow_html=True
    )

    # ── BOX UTENTE ──
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

    # ── CAMBIO PASSWORD ──
    with st.expander("Cambia password"):
        nuova = st.text_input(
            "Nuova password",
            type="password",
            key="sidebar_nuova_pwd"
        )
        conferma = st.text_input(
            "Conferma password",
            type="password",
            key="sidebar_conferma_pwd"
        )
        st.markdown(
            "<div style='font-size:10px;color:#9999bb;line-height:1.6;"
            "margin-bottom:6px;'>"
            "Requisiti: 8+ caratteri, maiuscola,<br>"
            "minuscola, numero, carattere speciale</div>",
            unsafe_allow_html=True
        )
        if st.button("Aggiorna password", key="btn_cambia_pwd",
                     width='stretch'):
            if not nuova or not conferma:
                st.error("Compila entrambi i campi.")
            elif nuova != conferma:
                st.error("Le password non coincidono.")
            else:
                errori = valida_password(nuova)
                if errori:
                    st.error("Password non valida: " + ", ".join(errori) + ".")
                else:
                    err = cambia_password(nuova)
                    if err:
                        st.error(f"Errore: {err}")
                    else:
                        st.success("Password aggiornata.")
                        log_attivita(
                            utente["id"], "modificato",
                            "password", utente["id"]
                        )

    st.markdown(
        "<hr style='border-color:#2a2a4a;margin:12px 0;'>",
        unsafe_allow_html=True
    )

    # ── NAVIGAZIONE ──
    st.markdown(
        '<div class="sidebar-nav-label">Navigazione</div>',
        unsafe_allow_html=True
    )

    if n_non_letti > 0:
        label_msg = f"Messaggi  ·  {n_non_letti} nuovi"
    else:
        label_msg = "Messaggi"

    nav_items = [
        ("dashboard",   "Dashboard"),
        ("clienti",     "Clienti"),
        ("offerte_all", "Offerte"),
        ("template",    "Template offerte"),
        ("eventi",      "Eventi"),
        ("calendario",  "Calendario"),
        ("messaggi",    label_msg),
        ("assistente",  "Assistente AI"),
        ("vacanze",     "Gestione vacanze"),
        ("cucina",      "Cucina"),
        ("magazzino",   "Magazzino"),
        # ("inbox", "Posta condivisa"),
    ]
    if is_admin(utente):
        nav_items.append(("admin", "Amministrazione"))

    for pagina_key, label in nav_items:
        if st.button(label, key=f"nav_{pagina_key}", width='stretch'):
            st.session_state.pagina = pagina_key
            st.session_state.pagina_precedente = st.session_state.pagina
            if pagina_key == "offerte_all":
                st.session_state.cliente_id = None
                st.session_state.cliente_nome = None
            st.rerun()

    st.markdown(
        "<hr style='border-color:#2a2a4a;margin:12px 0;'>",
        unsafe_allow_html=True
    )

    # ── ASSISTENTE WIDGET ──
    widget_assistente_sidebar(utente)

    st.markdown(
        "<hr style='border-color:#2a2a4a;margin:12px 0;'>",
        unsafe_allow_html=True
    )

    notifiche_on = not st.session_state.get("notifiche_disattivate", False)
    label_notifiche = "Notifiche: ON" if notifiche_on else "Notifiche: OFF"
    if st.button(label_notifiche, key="toggle_notifiche", width='stretch'):
        st.session_state.notifiche_disattivate = notifiche_on
        st.rerun()

    # ── ESCI CON CONFERMA ──
    if st.session_state.get("conferma_logout"):
        st.markdown(
            "<div style='background:#e94560;border-radius:8px;"
            "padding:12px 14px;margin:8px 0;text-align:center;'>"
            "<div style='font-size:12px;font-weight:600;color:white;'>"
            "Sicuro di voler uscire?</div>"
            "</div>",
            unsafe_allow_html=True
        )
        col_si, col_no = st.columns(2)
        with col_si:
            if st.button("Si, esci", key="logout_si", width='stretch'):
                st.session_state.conferma_logout = False
                do_logout()
        with col_no:
            if st.button("Annulla", key="logout_no", width='stretch'):
                st.session_state.conferma_logout = False
                st.rerun()
    else:
        if st.button("Esci", key="nav_logout", width='stretch'):
            st.session_state.conferma_logout = True
            st.rerun()

# ── BREADCRUMB ─────────────────────────────────────────────────────────────
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
    "inbox":       "Posta condivisa",
    "assistente":  "Assistente AI",
    "vacanze":     "Gestione vacanze",
    "cucina":      "Cucina",
    "magazzino":   "Magazzino",
    "admin":       "Amministrazione",
}
breadcrumb = breadcrumb_map.get(p, "")
st.markdown(
    f"<p style='font-size:11px;color:#aaa;letter-spacing:0.5px;"
    f"margin-bottom:4px;text-transform:uppercase;'>{breadcrumb}</p>",
    unsafe_allow_html=True
)

# ── ROUTING ────────────────────────────────────────────────────────────────
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
elif p == "inbox":
    pagina_inbox(utente)
elif p == "assistente":
    pagina_assistente(utente)

elif p == "vacanze":
    st.title("Gestione vacanze")
    st.info("Sezione in sviluppo.")
elif p == "cucina":
    st.title("Cucina")
    st.info("Sezione in sviluppo.")
elif p == "magazzino":
    st.title("Magazzino")
    st.info("Sezione in sviluppo.")
elif p == "admin":
    pagina_admin(utente)
