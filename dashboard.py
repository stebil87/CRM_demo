# dashboard.py
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import random
from db import (
    fmt_data,
    stats_dashboard, followup_oggi, followup_prossimi7,
    eventi_oggi_multi, get_calendari_visibili,
    lista_eventi_catering, lista_messaggi_non_letti,
    compleanni_in_arrivo, get_impostazione
)
from auth import can_edit


def is_event_manager(utente):
    return utente and utente["ruolo"] in ("admin", "event_manager")


def _saluto(utente):
    try:
        import pytz
        tz = pytz.timezone("Europe/Zurich")
        ora = datetime.now(tz).hour
    except:
        ora = datetime.now().hour
    nome = utente.get("nome", "")

    if 5 <= ora < 12:
        saluti = [
            f"Buongiorno {nome}! Ogni mattina è una pagina bianca — scrivila bene.",
            f"Buongiorno {nome}! Il successo è la somma di piccoli sforzi ripetuti ogni giorno.",
            f"Buongiorno {nome}! Chi lavora con passione non conta le ore.",
            f"Buongiorno {nome}! La giornata migliore è quella che non hai ancora vissuto.",
            f"Buongiorno {nome}! Il caffè è pronto, il mondo aspetta.",
            f"Buongiorno {nome}! Ogni cliente soddisfatto è una storia di successo.",
            f"Buongiorno {nome}! Le grandi cose non si fanno con la forza, ma con la perseveranza.",
            f"Buongiorno {nome}! Inizia la giornata con il sorriso — il resto viene da sé.",
            f"Buongiorno {nome}! Non aspettare il momento perfetto, prendi il momento e rendilo perfetto.",
            f"Buongiorno {nome}! Oggi è un buon giorno per fare qualcosa di cui andare fieri.",
            f"Buongiorno {nome}! Il talento vince le partite, ma il lavoro di squadra vince i campionati.",
            f"Buongiorno {nome}! La qualità non è un atto, è un'abitudine.",
            f"Buongiorno {nome}! Il segreto del successo è iniziare.",
            f"Buongiorno {nome}! Non rimandare a domani ciò che puoi fare con entusiasmo oggi.",
            f"Buongiorno {nome}! Un passo alla volta porta lontano.",
            f"Buongiorno {nome}! Sorridi — sei già avanti rispetto a chi ancora dorme.",
        ]
    elif 12 <= ora < 14:
        saluti = [
            f"Buon pranzo {nome}! Ricordati: anche i grandi leader fanno pausa.",
            f"Buon pranzo {nome}! Il corpo si ricarica, la mente si prepara al pomeriggio.",
            f"Buon pranzo {nome}! Una pausa ben vissuta vale quanto un'ora di lavoro.",
            f"Buon pranzo {nome}! Stacca la spina almeno mentre mangi — te lo meriti.",
            f"Buon pranzo {nome}! Il lavoro aspetta, il cibo si raffredda.",
            f"Buon pranzo {nome}! Anche le menti più brillanti hanno bisogno di carburante.",
            f"Buon pranzo {nome}! Metti il telefono giù, almeno per i prossimi venti minuti.",
        ]
    elif 14 <= ora < 18:
        saluti = [
            f"Buon pomeriggio {nome}! Il pomeriggio è il momento dei campioni.",
            f"Buon pomeriggio {nome}! Manca meno di stamattina — tieni duro.",
            f"Buon pomeriggio {nome}! Il successo non è mai lontano da chi ci mette costanza.",
            f"Buon pomeriggio {nome}! Un cliente alla volta, un'offerta alla volta.",
            f"Buon pomeriggio {nome}! Le ore del pomeriggio sono quelle in cui si chiudono le trattative migliori.",
            f"Buon pomeriggio {nome}! Non è stanchezza, è esperienza che si accumula.",
            f"Buon pomeriggio {nome}! Ogni telefonata può essere quella che cambia la giornata.",
            f"Buon pomeriggio {nome}! Il dettaglio fa la differenza tra buono e eccellente.",
            f"Buon pomeriggio {nome}! Sei a buon punto — continua così.",
        ]
    elif 18 <= ora < 22:
        saluti = [
            f"Buonasera {nome}! Ancora qui? Il lavoro ti rispetta quanto tu rispetti lui.",
            f"Buonasera {nome}! La dedizione che mostri oggi costruisce il successo di domani.",
            f"Buonasera {nome}! Chi lavora con passione non si accorge delle ore.",
            f"Buonasera {nome}! Quasi fatta — dai il meglio fino alla fine.",
            f"Buonasera {nome}! La costanza è la virtù più rara e più preziosa.",
            f"Buonasera {nome}! Ancora un po' e poi il meritato riposo.",
            f"Buonasera {nome}! Chi finisce bene la giornata dorme con la coscienza tranquilla.",
        ]
    else:
        saluti = [
            f"Ciao {nome}! A quest'ora o sei un genio o hai una scadenza domani mattina.",
            f"Ciao {nome}! Il CRM è aperto 24 ore — ma tu avresti tutto il diritto di dormire.",
            f"Ciao {nome}! Chi lavora di notte vede le stelle — e anche i dati del CRM.",
            f"Ciao {nome}! Notte fonda, mente lucida — o almeno ci proviamo.",
            f"Ciao {nome}! Anche i migliori si fermano a dormire — prendilo in considerazione.",
        ]

    testo = random.choice(saluti)
    st.markdown(
        f"<div style='background:linear-gradient(135deg,#1a1a2e 0%,#0f3460 100%);"
        f"border-radius:12px;padding:24px 32px;margin-bottom:24px;"
        f"box-shadow:0 4px 16px rgba(26,26,46,0.15);'>"
        f"<div style='font-size:20px;font-weight:700;color:white;"
        f"letter-spacing:-0.3px;line-height:1.4;margin-bottom:6px;'>{testo}</div>"
        f"<div style='font-size:11px;color:rgba(255,255,255,0.35);"
        f"letter-spacing:0.8px;text-transform:uppercase;'>"
        f"RickCars — Piattaforma CRM</div>"
        f"</div>",
        unsafe_allow_html=True
    )


def _widget_messaggi(utente):
    non_letti = lista_messaggi_non_letti(utente["id"])
    st.markdown(
        "<div style='display:flex;align-items:center;"
        "justify-content:space-between;margin-bottom:12px;'>"
        "<span style='font-size:13px;font-weight:600;color:#1a1a2e;'>"
        "Messaggi interni</span>"
        + (
            f"<span style='background:#e94560;color:white;font-size:10px;"
            f"font-weight:700;padding:2px 8px;border-radius:10px;'>"
            f"{len(non_letti)} non letti</span>"
            if non_letti else
            "<span style='font-size:11px;color:#aaa;'>Tutti letti</span>"
        ) +
        "</div>",
        unsafe_allow_html=True
    )

    if not non_letti:
        st.markdown(
            "<div style='background:#f0faf4;border:1px solid #c3e6cb;"
            "border-radius:8px;padding:12px 16px;font-size:13px;color:#2d6a4f;'>"
            "Nessun messaggio non letto.</div>",
            unsafe_allow_html=True
        )
        _componi_messaggio_interno(utente)
        return

    for m in non_letti[:4]:
        mitt = m.get("mittente") or {}
        nome_mitt = f"{mitt.get('nome','')} {mitt.get('cognome','')}".strip() or "—"
        oggetto = m.get("oggetto") or "(nessun oggetto)"
        try:
            import pytz
            tz = pytz.timezone("Europe/Zurich")
            dt = datetime.fromisoformat(
                m["created_at"].replace("Z", "+00:00")
            ).astimezone(tz)
            data_str = dt.strftime("%d/%m %H:%M")
        except:
            data_str = (m.get("created_at") or "")[:16].replace("T", " ")

        st.markdown(
            "<div style='background:white;border:1px solid #eaeaf0;"
            "border-left:4px solid #e94560;border-radius:8px;"
            "padding:10px 14px;margin-bottom:6px;'>"
            "<div style='display:flex;justify-content:space-between;"
            "align-items:flex-start;'>"
            "<div>"
            f"<div style='font-size:12px;font-weight:700;color:#1a1a2e;'>"
            f"{oggetto}</div>"
            f"<div style='font-size:11px;color:#888;margin-top:2px;'>"
            f"Da: {nome_mitt}</div>"
            "</div>"
            f"<div style='font-size:10px;color:#aaa;white-space:nowrap;"
            f"margin-left:8px;'>{data_str}</div>"
            "</div>"
            "</div>",
            unsafe_allow_html=True
        )
        mid_mitt = mitt.get("id")
        if mid_mitt:
            with st.popover("↩️ Rispondi", use_container_width=True):
                from db import invia_messaggio, segna_come_letto
                with st.form(f"rispmsg_{m['id']}"):
                    testo_r = st.text_area("Risposta a " + nome_mitt, height=100,
                                           key=f"rmsg_{m['id']}")
                    inv = st.form_submit_button("Invia risposta")
                if inv and testo_r.strip():
                    err = invia_messaggio(utente["id"], mid_mitt,
                                          f"Re: {oggetto}", testo_r.strip())
                    if not err:
                        segna_come_letto(m["id"])
                        st.success("Risposta inviata.")
                        st.rerun()
                    else:
                        st.error("Invio non riuscito.")

    if len(non_letti) > 4:
        st.markdown(
            f"<div style='font-size:11px;color:#888;margin-bottom:8px;'>"
            f"e altri {len(non_letti) - 4} messaggi...</div>",
            unsafe_allow_html=True
        )

    _componi_messaggio_interno(utente)
    if st.button("Vai ai messaggi", key="dash_vai_msg", use_container_width=True):
        st.session_state.pagina = "messaggi"
        st.rerun()


def _componi_messaggio_interno(utente):
    from db import lista_utenti, invia_messaggio
    with st.popover("✍️ Nuovo messaggio interno", use_container_width=True):
        colleghi = [(u["id"], f"{u.get('nome','')} {u.get('cognome','')}".strip())
                    for u in (lista_utenti() or []) if u["id"] != utente["id"]]
        if not colleghi:
            st.caption("Nessun altro utente a cui scrivere.")
            return
        with st.form("nuovo_msg_interno"):
            dest = st.selectbox("A", colleghi, format_func=lambda x: x[1])
            ogg = st.text_input("Oggetto *")
            corpo = st.text_area("Messaggio *", height=120)
            inv = st.form_submit_button("Invia")
        if inv:
            if not ogg.strip() or not corpo.strip():
                st.error("Oggetto e messaggio obbligatori.")
            else:
                err = invia_messaggio(utente["id"], dest[0], ogg.strip(), corpo.strip())
                if not err:
                    st.success("Messaggio inviato.")
                    st.rerun()
                else:
                    st.error("Invio non riuscito.")


def _card_obiettivo(fatturato_chiuso: float):
    """Card fatturato chiuso + obiettivo annuo con barra progresso."""
    try:
        obiettivo = float(get_impostazione("obiettivo_fatturato_annuo", "0"))
    except:
        obiettivo = 0

    if obiettivo <= 0:
        # Nessun obiettivo impostato — mostra solo fatturato
        return st.markdown(
            "<div style='background:white;border:1px solid #eaeaf0;"
            "border-top:4px solid #2d6a4f;border-radius:10px;"
            "padding:20px 24px;box-shadow:0 1px 4px rgba(0,0,0,0.06);'>"
            "<div style='font-size:11px;font-weight:700;text-transform:uppercase;"
            "letter-spacing:0.8px;color:#888;margin-bottom:8px;'>Fatturato chiuso</div>"
            f"<div style='font-size:28px;font-weight:700;color:#1a1a2e;'>"
            f"CHF {fatturato_chiuso:,.0f}</div>"
            "<div style='font-size:11px;color:#aaa;margin-top:4px;'>offerte accettate</div>"
            "</div>",
            unsafe_allow_html=True
        )

    perc = min(fatturato_chiuso / obiettivo * 100, 100)
    mancante = max(obiettivo - fatturato_chiuso, 0)
    superato = max(fatturato_chiuso - obiettivo, 0)
    superato_perc = max((fatturato_chiuso - obiettivo) / obiettivo * 100, 0)

    # Colore barra in base alla percentuale
    if perc >= 100:
        colore_barra = "#2d6a4f"
        colore_testo = "#2d6a4f"
        label_stato = f"+CHF {superato:,.0f} ({superato_perc:.0f}% oltre obiettivo!)"
    elif perc >= 75:
        colore_barra = "#0f3460"
        colore_testo = "#0f3460"
        label_stato = f"Mancano CHF {mancante:,.0f} ({100-perc:.0f}%)"
    elif perc >= 50:
        colore_barra = "#856404"
        colore_testo = "#856404"
        label_stato = f"Mancano CHF {mancante:,.0f} ({100-perc:.0f}%)"
    else:
        colore_barra = "#e94560"
        colore_testo = "#e94560"
        label_stato = f"Mancano CHF {mancante:,.0f} ({100-perc:.0f}%)"

    st.markdown(
        f"<div style='background:white;border:1px solid #eaeaf0;"
        f"border-top:4px solid #2d6a4f;border-radius:10px;"
        f"padding:20px 24px;box-shadow:0 1px 4px rgba(0,0,0,0.06);'>"
        f"<div style='font-size:11px;font-weight:700;text-transform:uppercase;"
        f"letter-spacing:0.8px;color:#888;margin-bottom:8px;'>Fatturato chiuso</div>"
        f"<div style='font-size:26px;font-weight:700;color:#1a1a2e;'>"
        f"CHF {fatturato_chiuso:,.0f}</div>"
        f"<div style='font-size:10px;color:#aaa;margin-top:2px;margin-bottom:10px;'>"
        f"su obiettivo CHF {obiettivo:,.0f}</div>"
        f"<div style='background:#eaeaf0;border-radius:4px;height:6px;margin-bottom:6px;'>"
        f"<div style='background:{colore_barra};border-radius:4px;height:6px;"
        f"width:{perc:.1f}%;transition:width 0.5s;'></div>"
        f"</div>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
        f"<span style='font-size:10px;color:{colore_testo};font-weight:600;'>"
        f"{label_stato}</span>"
        f"<span style='font-size:11px;font-weight:700;color:{colore_barra};'>"
        f"{perc:.0f}%</span>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True
    )


def pagina_dashboard(utente):
    st.title("Dashboard")
    _saluto(utente)

    stats = stats_dashboard()
    oggi_fu = followup_oggi()
    prossimi_fu = followup_prossimi7()
    ids_visibili = get_calendari_visibili(utente["id"])
    ev_oggi = eventi_oggi_multi(tuple(ids_visibili))

    offerte_df = pd.DataFrame(
        stats["offerte_data"]) if stats["offerte_data"] else pd.DataFrame()
    clienti_df = pd.DataFrame(
        stats["clienti_data"]) if stats["clienti_data"] else pd.DataFrame()

    prossimo = stats["prossimo_evento"]

    st.markdown("---")

    # ── COMPLEANNI IN ARRIVO ──
    compleanni = compleanni_in_arrivo(giorni=30)
    st.markdown(
        "<div style='display:flex;align-items:center;gap:10px;margin-bottom:12px;'>"
        "<span style='font-size:13px;font-weight:600;color:#1a1a2e;'>"
        "Compleanni in arrivo</span>"
        + (
            f"<span style='background:#fff3cd;color:#856404;font-size:10px;"
            f"font-weight:600;padding:2px 8px;border-radius:10px;'>"
            f"{len(compleanni)} nei prossimi 30 giorni</span>"
            if compleanni else ""
        ) +
        "</div>",
        unsafe_allow_html=True
    )
    if not compleanni:
        st.markdown(
            "<div style='background:#f4f4f8;border:1px solid #eaeaf0;"
            "border-radius:8px;padding:12px 16px;font-size:13px;color:#888;'>"
            "Nessun compleanno nei prossimi 30 giorni.</div>",
            unsafe_allow_html=True
        )
    else:
        cols = st.columns(min(len(compleanni), 4))
        for i, c in enumerate(compleanni[:4]):
            nome = f"{c.get('nome','')} {c.get('cognome','')}".strip()
            giorni_m = c["giorni_mancanti"]
            compleanno = c["compleanno"]
            if giorni_m == 0:
                label_giorni = "Oggi!"
                colore = "#e94560"
                bg = "#fff0f3"
            elif giorni_m == 1:
                label_giorni = "Domani"
                colore = "#e94560"
                bg = "#fff0f3"
            elif giorni_m <= 7:
                label_giorni = f"Tra {giorni_m} giorni"
                colore = "#856404"
                bg = "#fff8e1"
            else:
                label_giorni = f"Tra {giorni_m} giorni"
                colore = "#0f3460"
                bg = "#f0f4ff"
            with cols[i]:
                st.markdown(
                    f"<div style='background:{bg};border:1px solid #eaeaf0;"
                    f"border-left:4px solid {colore};border-radius:8px;"
                    f"padding:12px 14px;'>"
                    f"<div style='font-size:13px;font-weight:700;color:#1a1a2e;'>"
                    f"{nome}</div>"
                    f"<div style='font-size:11px;color:{colore};"
                    f"font-weight:600;margin-top:4px;'>{label_giorni}</div>"
                    f"<div style='font-size:10px;color:#aaa;margin-top:2px;'>"
                    f"{compleanno[8:10]}/{compleanno[5:7]}</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
                if st.button("Apri scheda", key=f"bday_{c['id']}"):
                    st.session_state.pagina = "clienti"
                    st.rerun()

    st.markdown("---")

    # ── COMUNICAZIONE IN ARRIVO: richieste sito · email ──
    from inbox_widget import widget_richieste_sito, widget_inbox
    from email_composer import compositore_email
    col_sito, col_mail = st.columns(2)
    with col_sito:
        widget_richieste_sito(utente)
    with col_mail:
        widget_inbox(utente)

    st.markdown("---")

    # ── NOTE + MESSAGGI INTERNI ──
    col_note, col_msg = st.columns(2)
    with col_note:
        from note_dashboard import widget_note
        widget_note(utente)
    with col_msg:
        _widget_messaggi(utente)

    st.markdown("---")

    # ── AZIONI RAPIDE: scrivi email · nuovo follow-up (affiancati) ──
    col_az1, col_az2 = st.columns(2)
    with col_az1:
        st.markdown("**✉️ Scrivi una nuova email**")
        with st.popover("Apri compositore", use_container_width=True):
            compositore_email(key="dash_nuova", titolo="", compatto=True)
    with col_az2:
        st.markdown("**🔔 Nuovo follow-up**")
        with st.popover("Apri modulo", use_container_width=True):
            from azioni_email import form_nuovo_followup
            form_nuovo_followup(utente, key="dash")

    st.markdown("---")

    # ── AGENDA + FOLLOW-UP ──
    col_ev, col_fu_oggi, col_fu_prox = st.columns(3)

    with col_ev:
        st.markdown("**Agenda di oggi**")
        if ev_oggi:
            for e in ev_oggi:
                try:
                    ora = datetime.fromisoformat(
                        e["data_inizio"].replace("Z", "")
                    ).strftime("%H:%M")
                except:
                    ora = ""
                colore = {
                    "appuntamento": "#1a1a2e",
                    "riunione":     "#0f3460",
                    "chiamata":     "#533483",
                    "scadenza":     "#e94560",
                    "altro":        "#6a6aae",
                }.get(e.get("tipo", "altro"), "#1a1a2e")
                propr = e.get("proprietario") or {}
                nome_propr = f"{propr.get('nome','')} {propr.get('cognome','')}".strip()
                st.markdown(
                    "<div style='background:white;border:1px solid #eaeaf0;"
                    "border-left:3px solid " + colore + ";border-radius:8px;"
                    "padding:10px 14px;margin-bottom:8px;'>"
                    "<div style='font-size:13px;font-weight:600;color:#1a1a2e;'>"
                    + ora + "&nbsp;&nbsp;" + e["titolo"] +
                    "</div>"
                    "<div style='font-size:11px;color:#888;margin-top:3px;'>"
                    + e.get("tipo", "").upper()
                    + (" · " + e["luogo"] if e.get("luogo") else "")
                    + (" · " + nome_propr if nome_propr else "")
                    + "</div></div>",
                    unsafe_allow_html=True
                )
        else:
            st.markdown(
                "<div style='background:#f0faf4;border:1px solid #c3e6cb;"
                "border-radius:8px;padding:12px 16px;font-size:13px;color:#2d6a4f;'>"
                "Nessun evento oggi.</div>",
                unsafe_allow_html=True
            )

    with col_fu_oggi:
        st.markdown("**Follow-up di oggi**")
        if oggi_fu:
            for f in oggi_fu:
                cliente = f.get("clienti", {})
                nome_cliente = cliente.get("ragione_sociale") or \
                    f"{cliente.get('nome','')} {cliente.get('cognome','')}".strip()
                st.markdown(
                    "<div style='background:white;border:1px solid #eaeaf0;"
                    "border-left:3px solid #1a1a2e;border-radius:8px;"
                    "padding:10px 14px;margin-bottom:8px;'>"
                    "<div style='font-size:13px;font-weight:600;'>"
                    + f["titolo"] +
                    "</div>"
                    "<div style='font-size:11px;color:#888;margin-top:3px;'>"
                    + nome_cliente +
                    "</div>"
                    + ("<div style='font-size:12px;color:#555;margin-top:6px;"
                       "white-space:pre-wrap;'>" + (f.get("contenuto") or "") + "</div>"
                       if f.get("contenuto") else "") +
                    "</div>",
                    unsafe_allow_html=True
                )
                if can_edit(utente):
                    if st.button("Fatto", key=f"oggi_{f['id']}"):
                        from db import aggiorna_voce_diario
                        aggiorna_voce_diario(f["id"], {"followup_fatto": True})
                        st.rerun()
        else:
            st.markdown(
                "<div style='background:#f0faf4;border:1px solid #c3e6cb;"
                "border-radius:8px;padding:12px 16px;font-size:13px;color:#2d6a4f;'>"
                "Nessun follow-up oggi.</div>",
                unsafe_allow_html=True
            )

    with col_fu_prox:
        st.markdown("**Follow-up prossimi 7 giorni**")
        if prossimi_fu:
            for f in prossimi_fu:
                cliente = f.get("clienti", {})
                nome_cliente = cliente.get("ragione_sociale") or \
                    f"{cliente.get('nome','')} {cliente.get('cognome','')}".strip()
                st.markdown(
                    "<div style='background:white;border:1px solid #eaeaf0;"
                    "border-left:3px solid #6a6aae;border-radius:8px;"
                    "padding:10px 14px;margin-bottom:8px;'>"
                    "<div style='font-size:13px;font-weight:600;'>"
                    + f["titolo"] +
                    "</div>"
                    "<div style='font-size:11px;color:#888;margin-top:3px;'>"
                    + nome_cliente + " · " + f.get("followup_data", "") +
                    "</div>"
                    + ("<div style='font-size:12px;color:#555;margin-top:6px;"
                       "white-space:pre-wrap;'>" + (f.get("contenuto") or "") + "</div>"
                       if f.get("contenuto") else "") +
                    "</div>",
                    unsafe_allow_html=True
                )
                if can_edit(utente):
                    if st.button("Fatto", key=f"prox_{f['id']}"):
                        from db import aggiorna_voce_diario
                        aggiorna_voce_diario(f["id"], {"followup_fatto": True})
                        st.rerun()
        else:
            st.markdown(
                "<div style='background:#f0faf4;border:1px solid #c3e6cb;"
                "border-radius:8px;padding:12px 16px;font-size:13px;color:#2d6a4f;'>"
                "Nessun follow-up in arrivo.</div>",
                unsafe_allow_html=True
            )
