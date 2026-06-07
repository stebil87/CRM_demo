# admin.py
import streamlit as st
from datetime import datetime
from db import lista_utenti, aggiorna_ruolo_utente, disattiva_utente, get_sb, get_impostazione, set_impostazione
from auth import is_admin

RUOLI = ["visualizza", "modifica", "admin", "event_manager"]


def pagina_admin(utente):
    if not is_admin(utente):
        st.error("Accesso riservato agli amministratori.")
        return

    st.title("Amministrazione")
    st.markdown("---")

    tab_utenti, tab_nuovo, tab_impostazioni, tab_log = st.tabs([
        "Gestione utenti", "Nuovo utente", "Impostazioni", "Activity Log"
    ])

    with tab_utenti:
        _tab_utenti(utente)

    with tab_nuovo:
        _tab_nuovo_utente()

    with tab_impostazioni:
        _tab_impostazioni()

    with tab_log:
        _tab_log()


def _tab_utenti(utente_corrente):
    utenti = lista_utenti()
    if not utenti:
        st.info("Nessun utente trovato.")
        return

    for u in utenti:
        nome_completo = f"{u['nome']} {u['cognome']}"
        stato_badge = "Attivo" if u.get("attivo", True) else "Disattivato"
        ruolo_display = u["ruolo"].upper()
        if u["ruolo"] == "event_manager":
            ruolo_display += " (ha anche permessi modifica)"

        with st.expander(
            f"{nome_completo} — {u['email']} [{ruolo_display}] — {stato_badge}"
        ):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Ruolo attuale:** {u['ruolo']}")
                nuovo_ruolo = st.selectbox(
                    "Cambia ruolo", RUOLI,
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
                if u.get("attivo", True) and u["id"] != utente_corrente["id"]:
                    if st.button("Disattiva", key=f"dis_{u['id']}"):
                        disattiva_utente(u["id"])
                        st.rerun()
            with col3:
                st.markdown(
                    f"**Creato il:** {(u.get('created_at') or '')[:10]}"
                )
                st.markdown(f"**ID:** {u['id'][:8]}...")


def _tab_nuovo_utente():
    st.subheader("Crea nuovo utente")
    st.caption(
        "L'utente riceverà le credenziali e potrà accedere subito. "
        "event_manager ha automaticamente anche i permessi di modifica."
    )

    with st.form("form_nuovo_utente"):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome *")
            email = st.text_input("Email *")
        with col2:
            cognome = st.text_input("Cognome *")
            ruolo = st.selectbox("Ruolo", RUOLI)
        password_temp = st.text_input(
            "Password temporanea *", type="password",
            help="L'utente potrà cambiarla dopo il primo accesso."
        )
        submitted = st.form_submit_button(
            "Crea utente", use_container_width=True)

    if submitted:
        if not all([nome, cognome, email, password_temp]):
            st.error("Tutti i campi sono obbligatori.")
            return

        try:
            sb = get_sb()
            res = sb.auth.admin.create_user({
                "email": email,
                "password": password_temp,
                "email_confirm": True
            })
            new_user = res.user
            if not new_user:
                st.error("Errore nella creazione dell'utente Auth.")
                return

            from db import crea_utente_profilo
            err = crea_utente_profilo(
                new_user.id, nome, cognome, email, ruolo
            )
            if err:
                st.error(f"Utente Auth creato ma errore profilo: {err}")
            else:
                st.success(
                    f"Utente {nome} {cognome} creato con successo "
                    f"con ruolo '{ruolo}'."
                )
                st.rerun()
        except Exception as e:
            st.error(f"Errore: {str(e)}")


def _tab_impostazioni():
    st.subheader("Impostazioni generali")
    st.markdown("---")

    # ── OBIETTIVO FATTURATO ──
    st.markdown("**Obiettivo fatturato annuo**")
    st.caption(
        "Imposta l'obiettivo di fatturato per l'anno corrente. "
        "Appare nella dashboard come barra di avanzamento."
    )

    try:
        val_attuale = float(get_impostazione("obiettivo_fatturato_annuo", "0"))
    except:
        val_attuale = 0.0

    anno_corrente = datetime.now().year

    col1, col2 = st.columns([2, 1])
    with col1:
        nuovo_obiettivo = st.number_input(
            f"Obiettivo CHF {anno_corrente}",
            min_value=0.0,
            value=val_attuale,
            step=10000.0,
            format="%.0f",
            help="Inserisci 0 per disattivare il contatore"
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Salva obiettivo", key="salva_obiettivo",
                     use_container_width=True):
            set_impostazione("obiettivo_fatturato_annuo", str(nuovo_obiettivo))
            st.success(
                f"Obiettivo impostato a CHF {nuovo_obiettivo:,.0f}"
                if nuovo_obiettivo > 0 else "Obiettivo disattivato."
            )
            st.rerun()

    if val_attuale > 0:
        st.markdown(
            f"<div style='background:#f4f4f8;border-radius:8px;"
            f"padding:12px 16px;font-size:13px;color:#555;margin-top:8px;'>"
            f"Obiettivo attuale: <strong>CHF {val_attuale:,.0f}</strong> "
            f"per l'anno {anno_corrente}</div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            "<div style='background:#fff3cd;border-radius:8px;"
            "padding:12px 16px;font-size:13px;color:#856404;margin-top:8px;'>"
            "Nessun obiettivo impostato — la barra di avanzamento "
            "non verrà mostrata in dashboard.</div>",
            unsafe_allow_html=True
        )

    st.markdown("---")

    # ── ALTRE IMPOSTAZIONI FUTURE ──
    st.markdown("**Altre impostazioni**")
    st.caption("Ulteriori impostazioni di sistema appariranno qui.")
    st.info("Sezione in sviluppo.")


def _tab_log():
    st.subheader("Activity Log")
    st.caption("Tutte le operazioni registrate sulla piattaforma — ultimi 200 eventi.")

    sb = get_sb()
    try:
        res = sb.table("activity_log").select(
            "*, utente:utenti(nome, cognome)"
        ).order("created_at", desc=True).limit(200).execute()
        log = res.data or []
    except:
        log = []
        st.warning("Tabella activity_log non trovata. Esegui il SQL di creazione.")
        return

    if not log:
        st.info("Nessuna attività registrata.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        filtro_entita = st.selectbox(
            "Tipo", ["tutti", "cliente", "offerta", "evento",
                     "diario", "documento", "messaggio", "template"],
            key="log_filtro_entita"
        )
    with col2:
        filtro_azione = st.selectbox(
            "Azione", ["tutti", "creato", "modificato",
                       "eliminato", "inviato", "accesso"],
            key="log_filtro_azione"
        )
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"**{len(log)} operazioni totali**")

    if filtro_entita != "tutti":
        log = [l for l in log if l.get("entita") == filtro_entita]
    if filtro_azione != "tutti":
        log = [l for l in log if l.get("azione") == filtro_azione]

    st.markdown(f"**{len(log)} risultati**")
    st.markdown("---")

    COLORI_AZIONE = {
        "creato":     "#2d6a4f",
        "modificato": "#0f3460",
        "eliminato":  "#e94560",
        "inviato":    "#533483",
        "accesso":    "#888888",
    }

    for l in log:
        u = l.get("utente") or {}
        nome_u = f"{u.get('nome','')} {u.get('cognome','')}".strip() or "—"
        azione = l.get("azione", "—")
        entita = l.get("entita", "—")
        dettagli = l.get("dettagli") or {}
        colore = COLORI_AZIONE.get(azione, "#888")

        try:
            import pytz
            tz = pytz.timezone("Europe/Zurich")
            dt = datetime.fromisoformat(l["created_at"].replace("Z", "+00:00"))
            data_str = dt.astimezone(tz).strftime("%d/%m/%Y %H:%M")
        except:
            data_str = (l.get("created_at") or "")[:16]

        dettagli_str = ""
        if dettagli:
            dettagli_str = " — " + ", ".join(
                f"{v}" for k, v in dettagli.items() if v
            )

        st.markdown(
            f"<div style='display:flex;align-items:center;gap:12px;"
            f"padding:8px 0;border-bottom:1px solid #f0f0f0;'>"
            f"<span style='background:{colore};color:white;font-size:9px;"
            f"font-weight:700;padding:2px 8px;border-radius:4px;"
            f"min-width:70px;text-align:center;text-transform:uppercase;'>"
            f"{azione}</span>"
            f"<span style='font-size:12px;color:#1a1a2e;font-weight:600;"
            f"min-width:80px;'>{entita}</span>"
            f"<span style='font-size:12px;color:#555;flex:1;'>"
            f"{nome_u}{dettagli_str}</span>"
            f"<span style='font-size:11px;color:#aaa;white-space:nowrap;'>"
            f"{data_str}</span>"
            f"</div>",
            unsafe_allow_html=True
        )
