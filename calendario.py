import streamlit as st
from datetime import date, datetime, timedelta
import calendar
from db import eventi_del_mese, crea_evento, aggiorna_evento, elimina_evento, lista_utenti
from auth import can_edit

TIPI = ["appuntamento", "riunione", "chiamata", "scadenza", "altro"]
COLORI = {
    "appuntamento": "#1a1a2e",
    "riunione":     "#0f3460",
    "chiamata":     "#533483",
    "scadenza":     "#e94560",
    "altro":        "#6a6aae",
}
MESI_IT = [
    "Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno",
    "Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"
]
GIORNI_IT = ["Lun","Mar","Mer","Gio","Ven","Sab","Dom"]

def pagina_calendario(utente):
    st.title("Calendario")
    st.markdown("---")

    # Stato navigazione mese
    if "cal_anno" not in st.session_state:
        st.session_state.cal_anno = date.today().year
    if "cal_mese" not in st.session_state:
        st.session_state.cal_mese = date.today().month

    anno = st.session_state.cal_anno
    mese = st.session_state.cal_mese

    tab_cal, tab_nuovo = st.tabs(["Calendario", "Nuovo evento"])

    with tab_nuovo:
        _form_nuovo_evento(utente)

    with tab_cal:
        _vista_calendario(utente, anno, mese)

def _vista_calendario(utente, anno, mese):
    # Navigazione mese
    col1, col2, col3 = st.columns([1, 4, 1])
    with col1:
        if st.button("Mese precedente", use_container_width=True):
            if mese == 1:
                st.session_state.cal_mese = 12
                st.session_state.cal_anno = anno - 1
            else:
                st.session_state.cal_mese = mese - 1
            st.rerun()
    with col2:
        st.markdown(
            f"<h2 style='text-align:center;margin:0;'>{MESI_IT[mese-1]} {anno}</h2>",
            unsafe_allow_html=True
        )
    with col3:
        if st.button("Mese successivo", use_container_width=True):
            if mese == 12:
                st.session_state.cal_mese = 1
                st.session_state.cal_anno = anno + 1
            else:
                st.session_state.cal_mese = mese + 1
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Carica eventi
    eventi = eventi_del_mese(anno, mese, utente["id"])

    # Mappa eventi per giorno
    eventi_per_giorno = {}
    for e in eventi:
        try:
            d = datetime.fromisoformat(e["data_inizio"].replace("Z","")).date()
            g = d.day
            if g not in eventi_per_giorno:
                eventi_per_giorno[g] = []
            eventi_per_giorno[g].append(e)
        except:
            pass

    # Griglia calendario
    cal = calendar.monthcalendar(anno, mese)
    oggi = date.today()

    # Header giorni
    cols = st.columns(7)
    for i, g in enumerate(GIORNI_IT):
        cols[i].markdown(
            f"<div style='text-align:center;font-size:11px;font-weight:700;"
            f"text-transform:uppercase;letter-spacing:0.8px;color:#888;"
            f"padding-bottom:8px;'>{g}</div>",
            unsafe_allow_html=True
        )

    # Righe settimane
    for settimana in cal:
        cols = st.columns(7)
        for i, giorno in enumerate(settimana):
            with cols[i]:
                if giorno == 0:
                    st.markdown(
                        "<div style='min-height:80px;border:1px solid #f0f0f0;"
                        "border-radius:6px;background:#fafafa;'></div>",
                        unsafe_allow_html=True
                    )
                else:
                    e_oggi = (date(anno, mese, giorno) == oggi)
                    border_color = "#1a1a2e" if e_oggi else "#eaeaf0"
                    bg_color = "#f0f0f8" if e_oggi else "white"
                    num_style = "font-weight:700;color:#1a1a2e;" if e_oggi else "color:#555;"

                    ev_giorno = eventi_per_giorno.get(giorno, [])
                    ev_html = ""
                    for ev in ev_giorno[:3]:
                        colore = COLORI.get(ev.get("tipo", "altro"), "#1a1a2e")
                        titolo_corto = ev["titolo"][:18] + "…" if len(ev["titolo"]) > 18 else ev["titolo"]
                        ora = ""
                        try:
                            ora = datetime.fromisoformat(
                                ev["data_inizio"].replace("Z","")
                            ).strftime("%H:%M") + " "
                        except:
                            pass
                        ev_html += (
                            f"<div style='background:{colore};color:white;"
                            f"font-size:9px;border-radius:3px;padding:2px 5px;"
                            f"margin-top:2px;overflow:hidden;white-space:nowrap;"
                            f"text-overflow:ellipsis;'>{ora}{titolo_corto}</div>"
                        )
                    if len(ev_giorno) > 3:
                        ev_html += f"<div style='font-size:9px;color:#888;margin-top:2px;'>+{len(ev_giorno)-3} altri</div>"

                    st.markdown(
                        f"<div style='min-height:80px;border:1px solid {border_color};"
                        f"border-radius:6px;background:{bg_color};padding:6px 8px;'>"
                        f"<div style='font-size:12px;{num_style}'>{giorno}</div>"
                        f"{ev_html}</div>",
                        unsafe_allow_html=True
                    )

    # Lista eventi del mese sotto il calendario
    st.markdown("---")
    st.markdown("**Eventi del mese**")

    if not eventi:
        st.info("Nessun evento questo mese.")
    else:
        eventi_ordinati = sorted(eventi, key=lambda x: x.get("data_inizio",""))
        for e in eventi_ordinati:
            colore = COLORI.get(e.get("tipo","altro"), "#1a1a2e")
            try:
                dt_inizio = datetime.fromisoformat(e["data_inizio"].replace("Z",""))
                data_str = dt_inizio.strftime("%d/%m/%Y %H:%M")
            except:
                data_str = e.get("data_inizio","")[:16]

            propr = e.get("proprietario") or {}
            nome_propr = f"{propr.get('nome','')} {propr.get('cognome','')}".strip()

            with st.expander(f"{data_str}   |   {e['titolo']}   |   {e.get('tipo','').upper()}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Tipo:** {e.get('tipo','—')}")
                    st.markdown(f"**Inizio:** {data_str}")
                    if e.get("data_fine"):
                        try:
                            dt_fine = datetime.fromisoformat(e["data_fine"].replace("Z",""))
                            st.markdown(f"**Fine:** {dt_fine.strftime('%d/%m/%Y %H:%M')}")
                        except:
                            pass
                    if e.get("luogo"):
                        st.markdown(f"**Luogo:** {e['luogo']}")
                with col2:
                    st.markdown(f"**Calendario di:** {nome_propr}")
                    if e.get("descrizione"):
                        st.markdown(f"**Note:** {e['descrizione']}")
                    partecipanti = e.get("partecipanti") or []
                    if partecipanti:
                        st.markdown(f"**Partecipanti:** {len(partecipanti)}")

                if can_edit(utente) and (
                    e.get("proprietario_id") == utente["id"] or
                    e.get("creato_da") == utente["id"]
                ):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("Modifica", key=f"emod_{e['id']}"):
                            st.session_state[f"edit_ev_{e['id']}"] = True
                    with col_b:
                        if st.button("Elimina", key=f"edel_{e['id']}"):
                            st.session_state[f"del_ev_{e['id']}"] = True

                if st.session_state.get(f"del_ev_{e['id']}"):
                    st.warning("Confermi l'eliminazione?")
                    c1, c2 = st.columns(2)
                    if c1.button("Sì", key=f"devok_{e['id']}"):
                        elimina_evento(e["id"])
                        st.rerun()
                    if c2.button("No", key=f"devno_{e['id']}"):
                        st.session_state[f"del_ev_{e['id']}"] = False
                        st.rerun()

                if st.session_state.get(f"edit_ev_{e['id']}"):
                    _form_modifica_evento(e, utente)

def _form_evento(dati_default=None, key_prefix="nev"):
    d = dati_default or {}
    utenti = lista_utenti()

    col1, col2 = st.columns(2)
    with col1:
        titolo = st.text_input("Titolo *", value=d.get("titolo",""), key=f"{key_prefix}_tit")
        tipo = st.selectbox("Tipo", TIPI,
            index=TIPI.index(d.get("tipo","appuntamento")) if d.get("tipo") in TIPI else 0,
            key=f"{key_prefix}_tipo")
        luogo = st.text_input("Luogo", value=d.get("luogo",""), key=f"{key_prefix}_luogo")
    with col2:
        tutto_il_giorno = st.checkbox("Tutto il giorno",
            value=d.get("tutto_il_giorno", False), key=f"{key_prefix}_tdg")

        try:
            default_data = datetime.fromisoformat(
                d["data_inizio"].replace("Z","")).date() if d.get("data_inizio") else date.today()
            default_ora_i = datetime.fromisoformat(
                d["data_inizio"].replace("Z","")).time() if d.get("data_inizio") else datetime.strptime("09:00","%H:%M").time()
            default_ora_f = datetime.fromisoformat(
                d["data_fine"].replace("Z","")).time() if d.get("data_fine") else datetime.strptime("10:00","%H:%M").time()
        except:
            default_data = date.today()
            default_ora_i = datetime.strptime("09:00","%H:%M").time()
            default_ora_f = datetime.strptime("10:00","%H:%M").time()

        data = st.date_input("Data *", value=default_data, key=f"{key_prefix}_data")
        if not tutto_il_giorno:
            ora_inizio = st.time_input("Ora inizio", value=default_ora_i, key=f"{key_prefix}_oi")
            ora_fine = st.time_input("Ora fine", value=default_ora_f, key=f"{key_prefix}_of")
        else:
            ora_inizio = datetime.strptime("00:00","%H:%M").time()
            ora_fine = datetime.strptime("23:59","%H:%M").time()

    descrizione = st.text_area("Note", value=d.get("descrizione",""), key=f"{key_prefix}_desc")

    # Proprietario (su cui creare l'evento)
    opzioni_utenti = {f"{u['nome']} {u['cognome']}": u["id"] for u in utenti}
    default_propr = 0
    if d.get("proprietario_id"):
        ids = list(opzioni_utenti.values())
        if d["proprietario_id"] in ids:
            default_propr = ids.index(d["proprietario_id"])

    proprietario_label = st.selectbox(
        "Calendario di", list(opzioni_utenti.keys()),
        index=default_propr, key=f"{key_prefix}_propr"
    )

    # Partecipanti (multi-select)
    altri_utenti = {f"{u['nome']} {u['cognome']}": u["id"] for u in utenti}
    partecipanti_sel = st.multiselect(
        "Partecipanti aggiuntivi",
        list(altri_utenti.keys()),
        key=f"{key_prefix}_part"
    )

    data_inizio_dt = datetime.combine(data, ora_inizio)
    data_fine_dt = datetime.combine(data, ora_fine)

    return {
        "titolo": titolo,
        "tipo": tipo,
        "luogo": luogo,
        "descrizione": descrizione,
        "tutto_il_giorno": tutto_il_giorno,
        "data_inizio": data_inizio_dt.isoformat(),
        "data_fine": data_fine_dt.isoformat(),
        "colore": COLORI.get(tipo, "#1a1a2e"),
        "proprietario_id": opzioni_utenti[proprietario_label],
        "partecipanti": [altri_utenti[p] for p in partecipanti_sel],
    }

def _form_nuovo_evento(utente):
    st.subheader("Nuovo evento")
    with st.form("form_nuovo_evento"):
        dati = _form_evento(key_prefix="nev")
        submitted = st.form_submit_button("Crea evento", use_container_width=True)
    if submitted:
        if not dati["titolo"]:
            st.error("Il titolo e obbligatorio.")
        else:
            crea_evento(dati, utente["id"])
            st.success("Evento creato.")
            st.rerun()

def _form_modifica_evento(e, utente):
    st.markdown("---")
    with st.form(f"form_edit_ev_{e['id']}"):
        dati = _form_evento(dati_default=e, key_prefix=f"ev_{e['id']}")
        col1, col2 = st.columns(2)
        with col1:
            salva = st.form_submit_button("Salva", use_container_width=True)
        with col2:
            annulla = st.form_submit_button("Annulla", use_container_width=True)
    if salva:
        aggiorna_evento(e["id"], dati)
        st.session_state[f"edit_ev_{e['id']}"] = False
        st.rerun()
    if annulla:
        st.session_state[f"edit_ev_{e['id']}"] = False
        st.rerun()
