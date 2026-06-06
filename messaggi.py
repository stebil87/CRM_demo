import streamlit as st
from db import (lista_messaggi_ricevuti, lista_messaggi_inviati,
                invia_messaggio, segna_come_letto, lista_utenti)
from datetime import datetime

def pagina_messaggi(utente):
    st.title("Posta interna")
    st.markdown("---")

    tab_ricevuti, tab_inviati, tab_nuovo = st.tabs(["In arrivo", "Inviati", "Nuovo messaggio"])

    with tab_ricevuti:
        messaggi = lista_messaggi_ricevuti(utente["id"])
        if not messaggi:
            st.info("Nessun messaggio ricevuto.")
        else:
            for m in messaggi:
                mitt = m.get("mittente") or {}
                nome_mitt = f"{mitt.get('nome','')} {mitt.get('cognome','')}".strip() or "—"
                data_str = (m.get("created_at") or "")[:16].replace("T", " ")
                non_letto = not m.get("letto", True)

                stile_titolo = "font-weight:700;" if non_letto else "font-weight:400;"
                badge = "<span style='background:#e94560;color:white;font-size:9px;padding:2px 6px;border-radius:10px;margin-left:8px;'>NUOVO</span>" if non_letto else ""

                with st.expander(f"{nome_mitt}   |   {m.get('oggetto','—')}   |   {data_str}"):
                    if non_letto:
                        segna_come_letto(m["id"])
                    st.markdown(f"<p style='font-size:12px;color:#888;margin-bottom:8px;'>Da: <b>{nome_mitt}</b> &nbsp;·&nbsp; {data_str}</p>", unsafe_allow_html=True)
                    st.markdown(f"<p style='font-size:13px;font-weight:600;margin-bottom:12px;'>{m.get('oggetto','')}</p>", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-size:13px;line-height:1.7;white-space:pre-wrap;'>{m.get('corpo','')}</div>", unsafe_allow_html=True)

                    st.markdown("---")
                    if st.button("Rispondi", key=f"risp_{m['id']}"):
                        st.session_state.reply_to = m
                        st.rerun()

    with tab_inviati:
        inviati = lista_messaggi_inviati(utente["id"])
        if not inviati:
            st.info("Nessun messaggio inviato.")
        else:
            for m in inviati:
                dest = m.get("destinatario") or {}
                nome_dest = f"{dest.get('nome','')} {dest.get('cognome','')}".strip() or "—"
                data_str = (m.get("created_at") or "")[:16].replace("T", " ")
                letto_str = "Letto" if m.get("letto") else "Non letto"
                with st.expander(f"A: {nome_dest}   |   {m.get('oggetto','—')}   |   {data_str}   |   {letto_str}"):
                    st.markdown(f"<p style='font-size:12px;color:#888;margin-bottom:8px;'>A: <b>{nome_dest}</b> &nbsp;·&nbsp; {data_str} &nbsp;·&nbsp; {letto_str}</p>", unsafe_allow_html=True)
                    st.markdown(f"<p style='font-size:13px;font-weight:600;margin-bottom:12px;'>{m.get('oggetto','')}</p>", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-size:13px;line-height:1.7;white-space:pre-wrap;'>{m.get('corpo','')}</div>", unsafe_allow_html=True)

    with tab_nuovo:
        _form_nuovo_messaggio(utente)

    # Risposta rapida
    if st.session_state.get("reply_to"):
        m = st.session_state.reply_to
        mitt = m.get("mittente") or {}
        nome_mitt = f"{mitt.get('nome','')} {mitt.get('cognome','')}".strip()
        st.markdown("---")
        st.subheader(f"Risposta a {nome_mitt}")
        with st.form("form_risposta"):
            oggetto = st.text_input("Oggetto", value=f"Re: {m.get('oggetto','')}")
            corpo = st.text_area("Messaggio", height=150)
            col1, col2 = st.columns(2)
            with col1:
                invia = st.form_submit_button("Invia risposta", use_container_width=True)
            with col2:
                annulla = st.form_submit_button("Annulla", use_container_width=True)
        if invia:
            invia_messaggio(utente["id"], mitt.get("id") or m.get("mittente_id"), oggetto, corpo)
            st.session_state.reply_to = None
            st.success("Risposta inviata.")
            st.rerun()
        if annulla:
            st.session_state.reply_to = None
            st.rerun()

def _form_nuovo_messaggio(utente):
    st.subheader("Nuovo messaggio")
    utenti = lista_utenti()
    altri = [u for u in utenti if u["id"] != utente["id"]]

    if not altri:
        st.info("Nessun altro utente disponibile.")
        return

    opzioni = {f"{u['nome']} {u['cognome']} ({u['email']})": u["id"] for u in altri}

    reply = st.session_state.get("reply_to")
    default_dest = None
    if reply:
        mitt = reply.get("mittente") or {}
        mitt_id = mitt.get("id") or reply.get("mittente_id")
        ids = list(opzioni.values())
        if mitt_id in ids:
            default_dest = ids.index(mitt_id)

    with st.form("form_nuovo_msg"):
        destinatario_label = st.selectbox(
            "Destinatario",
            list(opzioni.keys()),
            index=default_dest or 0
        )
        oggetto = st.text_input("Oggetto")
        corpo = st.text_area("Messaggio", height=180)
        invia = st.form_submit_button("Invia", use_container_width=True)

    if invia:
        if not oggetto or not corpo:
            st.error("Oggetto e messaggio sono obbligatori.")
        else:
            dest_id = opzioni[destinatario_label]
            err = invia_messaggio(utente["id"], dest_id, oggetto, corpo)
            if err:
                st.error(f"Errore: {err}")
            else:
                st.success("Messaggio inviato.")
                st.rerun()
