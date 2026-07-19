import streamlit as st
from db import lista_inbox_nuove, lista_inbox_storico, prendi_in_carico_email, fmt_data
from datetime import datetime

def _e_richiesta_sito(e):
    return str(e.get("oggetto", "")).startswith("[Sito]")


def widget_richieste_sito(utente):
    """Widget dashboard — richieste arrivate dal modulo del sito."""
    _widget_lista(utente, [e for e in lista_inbox_nuove() if _e_richiesta_sito(e)],
                  titolo="Richieste dal sito", vuoto="Nessuna richiesta in attesa.",
                  colore="#F97316", chiave="sito")


def widget_inbox(utente):
    """Widget dashboard — email normali (non dal sito) da prendere in carico."""
    _widget_lista(utente, [e for e in lista_inbox_nuove() if not _e_richiesta_sito(e)],
                  titolo="Email in arrivo", vuoto="Nessuna email in attesa.",
                  colore="#e94560", chiave="mail")


def _widget_lista(utente, nuove, titolo, vuoto, colore, chiave):

    st.markdown(
        "<div style='display:flex;align-items:center;justify-content:space-between;"
        "margin-bottom:12px;'>"
        f"<span style='font-size:13px;font-weight:600;color:#1a1a2e;'>{titolo}</span>"
        + (
            f"<span style='background:#e94560;color:white;font-size:10px;"
            f"font-weight:700;padding:2px 8px;border-radius:10px;'>"
            f"{len(nuove)} nuove</span>"
            if nuove else
            "<span style='font-size:11px;color:#aaa;'>Tutto gestito</span>"
        ) +
        "</div>",
        unsafe_allow_html=True
    )

    if not nuove:
        st.markdown(
            "<div style='background:#f0faf4;border:1px solid #c3e6cb;"
            "border-radius:8px;padding:12px 16px;font-size:13px;color:#2d6a4f;'>"
            f"{vuoto}</div>",
            unsafe_allow_html=True
        )
        return

    for e in nuove:
        data_str = fmt_data(e.get("data_ricezione"), "%d/%m %H:%M")

        st.markdown(
            "<div style='background:white;border:1px solid #eaeaf0;"
            f"border-left:4px solid {colore};border-radius:8px;"
            "padding:10px 14px;margin-bottom:8px;'>"
            "<div style='display:flex;justify-content:space-between;"
            "align-items:flex-start;'>"
            "<div>"
            f"<div style='font-size:12px;font-weight:700;color:#1a1a2e;'>{e['oggetto']}</div>"
            f"<div style='font-size:11px;color:#888;margin-top:2px;'>Da: {e['mittente']}</div>"
            "</div>"
            f"<div style='font-size:10px;color:#aaa;white-space:nowrap;margin-left:8px;'>{data_str}</div>"
            "</div>"
            "</div>",
            unsafe_allow_html=True
        )

        col1, col2 = st.columns([2, 1])
        with col1:
            if st.button("Apri e prendi in carico", key=f"inbox_apri_{chiave}_{e['id']}"):
                st.session_state[f"inbox_open_{chiave}_{e['id']}"] = True
        with col2:
            if st.button("Prendi in carico", key=f"inbox_pic_{chiave}_{e['id']}"):
                prendi_in_carico_email(e["id"], utente["id"])
                st.rerun()

        if st.session_state.get(f"inbox_open_{chiave}_{e['id']}"):
            st.markdown(
                "<div style='background:#fafafa;border:1px solid #eaeaf0;"
                "border-radius:8px;padding:16px;margin-bottom:8px;'>"
                f"<div style='font-size:12px;color:#888;margin-bottom:8px;'>"
                f"Da: <b>{e['mittente']}</b> — {data_str}</div>"
                f"<div style='font-size:13px;font-weight:600;margin-bottom:12px;'>"
                f"{e['oggetto']}</div>"
                f"<div style='font-size:13px;line-height:1.7;white-space:pre-wrap;'>"
                f"{e.get('corpo','')}</div>"
                "</div>",
                unsafe_allow_html=True
            )
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button(
                    "Prendo in carico io",
                    key=f"inbox_pic2_{chiave}_{e['id']}",
                    use_container_width=True
                ):
                    prendi_in_carico_email(e["id"], utente["id"])
                    st.session_state[f"inbox_open_{chiave}_{e['id']}"] = False
                    st.rerun()
            with col_b:
                if st.button(
                    "Chiudi",
                    key=f"inbox_close_{chiave}_{e['id']}",
                    use_container_width=True
                ):
                    st.session_state[f"inbox_open_{chiave}_{e['id']}"] = False
                    st.rerun()

            # azioni complete: rispondi / appuntamento / follow-up
            from azioni_email import pannello_azioni_email
            pannello_azioni_email(e, utente, key=f"{chiave}_{e['id']}")

def controlla_posta():
    """Scarica i messaggi non letti da info@rickcars.ch (IMAP) e li
    inserisce nella inbox del CRM. Ritorna (importati, errore)."""
    import imaplib
    import email as email_lib
    from email.header import decode_header, make_header
    from db import inserisci_email_inbox

    try:
        server = st.secrets.get("EMAIL_IMAP_SERVER", "imap.mail.hostpoint.ch")
        utente_mail = st.secrets["EMAIL_MITTENTE"]
        password = st.secrets["EMAIL_PASSWORD"]
    except Exception:
        return 0, "Credenziali e-mail non configurate nei Secrets."

    try:
        conn = imaplib.IMAP4_SSL(server, timeout=15)
        conn.login(utente_mail, password)
        conn.select("INBOX")
        stato, dati = conn.search(None, "UNSEEN")
        ids = dati[0].split() if stato == "OK" and dati and dati[0] else []
        importati = 0
        for mid in ids[:30]:  # massimo 30 per volta, per non bloccare la pagina
            stato, msg_dati = conn.fetch(mid, "(RFC822)")
            if stato != "OK" or not msg_dati or not msg_dati[0]:
                continue
            msg = email_lib.message_from_bytes(msg_dati[0][1])

            try:
                oggetto = str(make_header(decode_header(msg.get("Subject", ""))))
            except Exception:
                oggetto = msg.get("Subject", "") or "(senza oggetto)"
            try:
                mittente = str(make_header(decode_header(msg.get("From", ""))))
            except Exception:
                mittente = msg.get("From", "") or "sconosciuto"

            # niente doppioni ne' auto-importazioni
            if oggetto.strip().startswith("[Sito]"):
                continue  # gia' nel CRM per via diretta
            if utente_mail.lower() in mittente.lower():
                continue  # messaggio spedito da noi

            corpo = ""
            if msg.is_multipart():
                for parte in msg.walk():
                    disp = str(parte.get("Content-Disposition") or "")
                    if parte.get_content_type() == "text/plain" and "attachment" not in disp:
                        try:
                            corpo = parte.get_payload(decode=True).decode(
                                parte.get_content_charset() or "utf-8", "ignore")
                        except Exception:
                            corpo = ""
                        break
                if not corpo:
                    for parte in msg.walk():
                        if parte.get_content_type() == "text/html":
                            import re as _re
                            try:
                                html = parte.get_payload(decode=True).decode(
                                    parte.get_content_charset() or "utf-8", "ignore")
                                corpo = _re.sub(r"<[^>]+>", " ", html)
                                corpo = _re.sub(r"\s+", " ", corpo).strip()
                            except Exception:
                                corpo = ""
                            break
            else:
                try:
                    corpo = msg.get_payload(decode=True).decode(
                        msg.get_content_charset() or "utf-8", "ignore")
                except Exception:
                    corpo = str(msg.get_payload() or "")

            err = inserisci_email_inbox(mittente, oggetto, corpo[:10000])
            if not err:
                importati += 1
        conn.logout()
        return importati, None
    except Exception as e:
        return 0, str(e)


def pagina_inbox(utente):
    """Pagina completa inbox con storico."""
    st.title("📧 Email")

    # controllo automatico una volta per sessione
    if not st.session_state.get("posta_controllata"):
        with st.spinner("Controllo la casella info@rickcars.ch..."):
            n, err = controlla_posta()
        st.session_state["posta_controllata"] = True
        if err:
            st.warning(f"Casella non raggiungibile: {err}")
        elif n:
            st.success(f"{n} nuove email importate dalla casella.")

    if st.button("🔄 Controlla posta adesso"):
        with st.spinner("Controllo la casella..."):
            n, err = controlla_posta()
        if err:
            st.error("Controllo non riuscito.")
            st.caption(f"Dettaglio tecnico: {err}")
        elif n:
            st.success(f"{n} nuove email importate.")
            st.rerun()
        else:
            st.info("Nessuna email nuova.")

    st.markdown("---")

    tab_nuove, tab_storico, tab_inserisci = st.tabs([
        "Da gestire", "Storico", "Inserisci manuale"
    ])

    with tab_nuove:
        nuove = lista_inbox_nuove()
        if not nuove:
            st.success("Nessuna email in attesa di gestione.")
        else:
            for e in _scheda_email_completa(nuove, utente, mostra_presa=False):
                pass

    with tab_storico:
        storico = lista_inbox_storico()
        if not storico:
            st.info("Nessuna email nello storico.")
        else:
            st.markdown(f"**{len(storico)} email gestite**")
            for e in storico:
                _email_storico(e)

    with tab_inserisci:
        _form_inserisci_manuale(utente)


def _scheda_email_completa(emails, utente, mostra_presa=True):
    for e in emails:
        data_str = fmt_data(e.get("data_ricezione"))

        with st.expander(
            f"{e['oggetto']}   |   {e['mittente']}   |   {data_str}"
        ):
            st.markdown(
                f"<div style='font-size:12px;color:#888;margin-bottom:8px;'>"
                f"Da: <b>{e['mittente']}</b> — {data_str}</div>",
                unsafe_allow_html=True
            )
            st.markdown(
                f"<div style='font-size:13px;line-height:1.7;"
                f"white-space:pre-wrap;background:#fafafa;"
                f"border:1px solid #eaeaf0;border-radius:8px;"
                f"padding:16px;'>{e.get('corpo','')}</div>",
                unsafe_allow_html=True
            )
            st.markdown("---")
            if not e.get("presa_in_carico"):
                if st.button(
                    "Prendo in carico io",
                    key=f"pic_full_{e['id']}",
                    use_container_width=True
                ):
                    prendi_in_carico_email(e["id"], utente["id"])
                    st.rerun()
            from azioni_email import pannello_azioni_email
            pannello_azioni_email(e, utente, key=f"pag_{e['id']}")

        yield e


def _estrai_email(mittente):
    """Pesca l'indirizzo e-mail dal campo mittente (anche nei formati
    'Nome · +41... · mail@dominio.ch' usati dalle richieste del sito)."""
    import re
    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", str(mittente or ""))
    return m.group(0) if m else ""


def _form_risposta(e, utente):
    from email_composer import compositore_email
    dest_default = _estrai_email(e.get("mittente"))

    if st.session_state.get(f"risposto_{e['id']}"):
        st.success("✅ Risposta inviata. La conversazione è stata presa in carico.")
        return

    def _dopo_invio():
        if not e.get("presa_in_carico"):
            prendi_in_carico_email(e["id"], utente["id"])
        st.session_state[f"risposto_{e['id']}"] = True
        st.rerun()

    compositore_email(
        key=f"risp_{e['id']}",
        dest_default=dest_default,
        oggetto_default=f"Re: {e.get('oggetto','')}",
        riferimento_id=e["id"],
        tipo="risposta_inbox",
        on_sent=_dopo_invio,
        titolo="✉️ Rispondi al cliente",
    )


def _email_storico(e):
    data_str = fmt_data(e.get("data_ricezione"))

    gestore = e.get("gestore") or {}
    nome_gestore = f"{gestore.get('nome','')} {gestore.get('cognome','')}".strip()

    data_pic = fmt_data(e.get("presa_in_carico_at"))

    with st.expander(
        f"{e['oggetto']}   |   {e['mittente']}   |   {data_str}   |   "
        f"Gestita da: {nome_gestore}"
    ):
        st.markdown(
            f"<div style='font-size:12px;color:#888;margin-bottom:8px;'>"
            f"Da: <b>{e['mittente']}</b> — {data_str}<br>"
            f"Presa in carico da: <b>{nome_gestore}</b> il {data_pic}</div>",
            unsafe_allow_html=True
        )
        st.markdown(
            f"<div style='font-size:13px;line-height:1.7;"
            f"white-space:pre-wrap;background:#fafafa;"
            f"border:1px solid #eaeaf0;border-radius:8px;"
            f"padding:16px;'>{e.get('corpo','')}</div>",
            unsafe_allow_html=True
        )
        st.markdown("---")
        from azioni_email import pannello_azioni_email
        pannello_azioni_email(e, utente, key=f"stor_{e['id']}")


def _form_inserisci_manuale(utente):
    st.subheader("Inserisci email manualmente")
    st.caption(
        "Usa questa sezione per inserire email ricevute che vuoi tracciare nel sistema."
    )
    from db import inserisci_email_inbox
    with st.form("form_inbox_manuale"):
        mittente = st.text_input("Mittente (email) *")
        oggetto = st.text_input("Oggetto *")
        corpo = st.text_area("Testo email", height=200)
        submitted = st.form_submit_button("Inserisci", use_container_width=True)

    if submitted:
        if not mittente or not oggetto:
            st.error("Mittente e oggetto sono obbligatori.")
        else:
            err = inserisci_email_inbox(mittente, oggetto, corpo)
            if err:
                st.error(f"Errore: {err}")
            else:
                st.success("Email inserita nella inbox condivisa.")
                st.rerun()
