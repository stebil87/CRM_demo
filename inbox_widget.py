import streamlit as st
from db import lista_inbox_nuove, lista_inbox_storico, prendi_in_carico_email
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
        try:
            data_str = datetime.fromisoformat(
                e["data_ricezione"].replace("Z", "")
            ).strftime("%d/%m %H:%M")
        except:
            data_str = ""

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


def pagina_inbox(utente):
    """Pagina completa inbox con storico."""
    st.title("📧 Email")
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
        try:
            data_str = datetime.fromisoformat(
                e["data_ricezione"].replace("Z", "")
            ).strftime("%d/%m/%Y %H:%M")
        except:
            data_str = ""

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
            _form_risposta(e, utente)

        yield e


def _estrai_email(mittente):
    """Pesca l'indirizzo e-mail dal campo mittente (anche nei formati
    'Nome · +41... · mail@dominio.ch' usati dalle richieste del sito)."""
    import re
    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", str(mittente or ""))
    return m.group(0) if m else ""


def _form_risposta(e, utente):
    from email_service import invia_email
    dest_default = _estrai_email(e.get("mittente"))
    with st.form(f"risposta_{e['id']}", clear_on_submit=False):
        st.markdown("**Rispondi al cliente**")
        dest = st.text_input("A", value=dest_default, key=f"rd_{e['id']}")
        oggetto = st.text_input(
            "Oggetto", value=f"Re: {e.get('oggetto','')}", key=f"ro_{e['id']}"
        )
        testo = st.text_area(
            "Messaggio", height=160, key=f"rt_{e['id']}",
            placeholder="Buongiorno,\n\n...\n\nCordiali saluti\nRickCars",
        )
        invia = st.form_submit_button("📤 Invia risposta")
    if invia:
        if not dest.strip() or not testo.strip():
            st.error("Servono destinatario e messaggio.")
            return
        corpo_html = "<p>" + testo.strip().replace("\n", "<br>") + "</p>"
        err = invia_email(dest.strip(), oggetto.strip() or "RickCars",
                          corpo_html, tipo="risposta_inbox",
                          riferimento_id=e["id"])
        if err:
            st.error("Invio non riuscito (configurazione SMTP mancante o errata).")
            st.caption(f"Dettaglio tecnico: {err}")
        else:
            if not e.get("presa_in_carico"):
                prendi_in_carico_email(e["id"], utente["id"])
            st.success(f"Risposta inviata a {dest.strip()}.")
            st.rerun()


def _email_storico(e):
    try:
        data_str = datetime.fromisoformat(
            e["data_ricezione"].replace("Z", "")
        ).strftime("%d/%m/%Y %H:%M")
    except:
        data_str = ""

    gestore = e.get("gestore") or {}
    nome_gestore = f"{gestore.get('nome','')} {gestore.get('cognome','')}".strip()

    try:
        data_pic = datetime.fromisoformat(
            e["presa_in_carico_at"].replace("Z", "")
        ).strftime("%d/%m/%Y %H:%M") if e.get("presa_in_carico_at") else ""
    except:
        data_pic = ""

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
