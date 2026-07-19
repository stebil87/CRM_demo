"""Compositore e-mail condiviso — usato dalla pagina Email e dalla dashboard.
Un'unica interfaccia: destinatario, CC, CCN, oggetto, testo con formattazione
leggera e allegati di qualsiasi formato."""
import streamlit as st
from email_service import invia_email
try:
    from streamlit_quill import st_quill
    _HA_QUILL = True
except Exception:
    _HA_QUILL = False


def _to_html(testo):
    """Testo del compositore -> HTML. Supporta **grassetto**, __corsivo__,
    e righe che iniziano con '- ' diventano elenco puntato."""
    import re, html
    righe_out = []
    for riga in testo.split("\n"):
        r = html.escape(riga)
        r = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", r)
        r = re.sub(r"__(.+?)__", r"<em>\1</em>", r)
        righe_out.append(r)
    corpo = "<br>".join(righe_out)
    return (
        "<div style=\"font-family:'Helvetica Neue',Arial,sans-serif;"
        "font-size:14px;color:#1a1a2e;line-height:1.6\">"
        f"{corpo}"
        "<br><br><hr style='border:none;border-top:1px solid #eee'>"
        "<div style='font-size:12px;color:#888'>RickCars · Via Carlo Maderno 41 · "
        "6850 Mendrisio · +41 91 683 00 00 · info@rickcars.ch</div></div>"
    )


def _wrap_html(corpo_html):
    return (
        "<div style=\"font-family:'Helvetica Neue',Arial,sans-serif;"
        "font-size:14px;color:#1a1a2e;line-height:1.6\">"
        f"{corpo_html}"
        "<br><hr style='border:none;border-top:1px solid #eee'>"
        "<div style='font-size:12px;color:#888'>RickCars · Via Carlo Maderno 41 · "
        "6850 Mendrisio · +41 91 683 00 00 · info@rickcars.ch</div></div>"
    )


def _firma():
    return "Buongiorno,\n\n\n\nCordiali saluti\nRickCars"


def compositore_email(key, dest_default="", oggetto_default="",
                      testo_default=None, riferimento_id=None,
                      tipo="composizione", on_sent=None,
                      titolo="✉️ Scrivi email", compatto=False, utente=None):
    """Riquadro di composizione completo.
    on_sent: callback eseguita dopo un invio riuscito.
    compatto=True nasconde il promemoria formattazione (per la dashboard).
    Ritorna True se l'email è stata inviata in questa esecuzione."""
    if titolo:
        st.markdown(f"**{titolo}**")

    # recupero bozza condivisa, se presente
    from bozze import carica_bozza, salva_bozza, elimina_bozza
    _bz = carica_bozza("email", key)
    if _bz and not st.session_state.get(f"bozza_caricata_{key}"):
        c = _bz.get("contenuto") or {}
        dest_default = c.get("dest", dest_default)
        oggetto_default = c.get("oggetto", oggetto_default)
        if c.get("testo"):
            testo_default = c["testo"]
        a = _bz.get("autore") or {}
        chi = f"{a.get('nome','')} {a.get('cognome','')}".strip()
        st.info(f"📄 Ripresa bozza salvata{' da ' + chi if chi else ''}.")
        st.session_state[f"bozza_caricata_{key}"] = True

    c1, c2 = st.columns(2)
    with c1:
        dest = st.text_input("A *", value=dest_default, key=f"cd_{key}")
    with c2:
        oggetto = st.text_input("Oggetto *", value=oggetto_default, key=f"co_{key}")
    c3, c4 = st.columns(2)
    with c3:
        cc = st.text_input("CC", key=f"cc_{key}",
                           placeholder="più indirizzi separati da virgola")
    with c4:
        ccn = st.text_input("CCN", key=f"cn_{key}",
                            placeholder="copia nascosta")

    st.markdown("<div style='font-size:14px;font-weight:600;margin:4px 0'>Messaggio *</div>",
                unsafe_allow_html=True)
    default_testo = testo_default if testo_default is not None else _firma()
    if _HA_QUILL:
        # editor visuale con barra strumenti (grassetto, corsivo, elenchi, titoli, link...)
        contenuto_html = st_quill(
            value=default_testo.replace("\n", "<br>"),
            html=True,
            toolbar=[
                ["bold", "italic", "underline", "strike"],
                [{"header": [1, 2, 3, False]}],
                [{"list": "ordered"}, {"list": "bullet"}],
                [{"color": []}, {"background": []}],
                ["link", "clean"],
            ],
            key=f"quill_{key}",
        )
        usa_html_diretto = True
    else:
        contenuto_html = st.text_area(
            "Messaggio", height=220 if not compatto else 150,
            value=default_testo, key=f"ct_{key}", label_visibility="collapsed",
        )
        usa_html_diretto = False

    files = st.file_uploader(
        "Allegati (qualsiasi formato, max 15 MB l'uno)",
        accept_multiple_files=True, key=f"cf_{key}",
    )
    col_inv, col_boz = st.columns([2, 1])
    with col_inv:
        invia = st.button("📤 Invia email", type="primary", key=f"send_{key}")
    with col_boz:
        salva = st.button("💾 Salva bozza", key=f"draft_{key}")

    if salva:
        uid = (utente or {}).get("id") if utente else None
        err = salva_bozza("email", key, {
            "dest": dest, "oggetto": oggetto, "testo": contenuto_html,
        }, uid, titolo=f"Email: {oggetto or dest or 'senza oggetto'}")
        if err:
            st.error("Bozza non salvata.")
            st.caption(f"Dettaglio tecnico: {err}")
        else:
            st.success("💾 Bozza salvata. Puoi riprenderla anche da un altro accesso.")

    if invia:
        testo = contenuto_html or ""
        import re as _re
        testo_plain = _re.sub(r"<[^>]+>", "", testo).strip()
        if not dest.strip() or not oggetto.strip() or not testo_plain:
            st.error("Compila destinatario, oggetto e messaggio.")
            return False
        allegati, troppo_grandi = [], []
        for f in (files or []):
            dati = f.getvalue()
            if len(dati) > 15 * 1024 * 1024:
                troppo_grandi.append(f.name)
            else:
                allegati.append((f.name, dati))
        if troppo_grandi:
            st.error("File troppo grandi (>15 MB): " + ", ".join(troppo_grandi))
            return False
        cc_list = [x.strip() for x in cc.split(",") if x.strip()]
        ccn_list = [x.strip() for x in ccn.split(",") if x.strip()]
        corpo_finale = _wrap_html(testo) if usa_html_diretto else _to_html(testo)
        with st.spinner("Invio in corso..."):
            err = invia_email(dest.strip(), oggetto.strip(), corpo_finale,
                              tipo=tipo, riferimento_id=riferimento_id,
                              cc=cc_list, bcc=ccn_list, allegati=allegati)
        if err:
            st.error("Invio non riuscito (controlla la configurazione e-mail).")
            st.caption(f"Dettaglio tecnico: {err}")
            return False
        st.success(f"✅ Email inviata a {dest.strip()}"
                   + (f" · {len(allegati)} allegati" if allegati else ""))
        try:
            elimina_bozza("email", key)
        except Exception:
            pass
        if on_sent:
            on_sent()
        return True
    return False
