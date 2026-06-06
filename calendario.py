import streamlit as st
from datetime import date, datetime, timedelta
import calendar
from db import (
    eventi_del_mese_multi, eventi_oggi_multi,
    crea_evento, aggiorna_evento, elimina_evento,
    lista_utenti, get_calendari_visibili, get_calendari_modificabili,
    get_autorizzazioni_calendario, salva_autorizzazione_calendario,
    elimina_autorizzazione_calendario
)
from auth import is_admin

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

    if "cal_anno" not in st.session_state:
        st.session_state.cal_anno = date.today().year
    if "cal_mese" not in st.session_state:
        st.session_state.cal_mese = date.today().month
    if "cal_giorno_sel" not in st.session_state:
        st.session_state.cal_giorno_sel = None

    anno = st.session_state.cal_anno
    mese = st.session_state.cal_mese

    # Calendari accessibili
    ids_visibili = get_calendari_visibili(utente["id"])
    ids_modificabili = get_calendari_modificabili(utente["id"])

    tabs = ["Calendario", "Nuovo evento"]
    if is_admin(utente):
        tabs.append("Gestione autorizzazioni")

    tab_list = st.tabs(tabs)

    with tab_list[0]:
        _vista_calendario(utente, anno, mese, ids_visibili, ids_modificabili)

    with tab_list[1]:
        _form_nuovo_evento(utente, ids_modificabili)

    if is_admin(utente):
        with tab_list[2]:
            _gestione_autorizzazioni(utente)

def _vista_calendario(utente, anno, mese, ids_visibili, ids_modificabili):
    # Navigazione mese
    col1, col2, col3 = st.columns([1, 4, 1])
    with col1:
        if st.button("Mese precedente", use_container_width=True):
            if mese == 1:
                st.session_state.cal_mese = 12
                st.session_state.cal_anno = anno - 1
            else:
                st.session_state.cal_mese = mese - 1
            st.session_state.cal_giorno_sel = None
            st.rerun()
    with col2:
        st.markdown(
            f"<h2 style='text-align:center;margin:0;'>"
            f"{MESI_IT[mese-1]} {anno}</h2>",
            unsafe_allow_html=True
        )
    with col3:
        if st.button("Mese successivo", use_container_width=True):
            if mese == 12:
                st.session_state.cal_mese = 1
                st.session_state.cal_anno = anno + 1
            else:
                st.session_state.cal_mese = mese + 1
            st.session_state.cal_giorno_sel = None
            st.rerun()

    # Legenda calendari visibili
    utenti_tutti = {u["id"]: u for u in lista_utenti()}
    if len(ids_visibili) > 1:
        legenda_html = "<div style='display:flex;gap:12px;flex-wrap:wrap;margin:12px 0;'>"
        for uid in ids_visibili:
            u = utenti_tutti.get(uid, {})
            nome = f"{u.get('nome','')} {u.get('cognome','')}".strip()
            indicatore = "TU" if uid == utente["id"] else nome[:2].upper()
            legenda_html += (
                f"<span style='font-size:11px;color:#555;display:flex;"
                f"align-items:center;gap:5px;'>"
                f"<span style='background:#1a1a2e;color:white;font-size:9px;"
                f"font-weight:700;padding:2px 6px;border-radius:3px;'>"
                f"{indicatore}</span>{nome}</span>"
            )
        legenda_html += "</div>"
        st.markdown(legenda_html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Carica eventi
    eventi = eventi_del_mese_multi(anno, mese, ids_visibili)

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

    cal_matrix = calendar.monthcalendar(anno, mese)
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

    # Griglia
    giorno_selezionato = st.session_state.get("cal_giorno_sel")

    for settimana in cal_matrix:
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
                    e_sel = (giorno_selezionato == giorno)
                    border_color = "#e94560" if e_sel else ("#1a1a2e" if e_oggi else "#eaeaf0")
                    bg_color = "#fff8f8" if e_sel else ("#f0f0f8" if e_oggi else "white")
                    num_style = "font-weight:700;color:#1a1a2e;" if e_oggi else "color:#555;"

                    ev_giorno = eventi_per_giorno.get(giorno, [])
                    ev_html = ""
                    for ev in ev_giorno[:3]:
                        colore = COLORI.get(ev.get("tipo","altro"), "#1a1a2e")
                        titolo_corto = ev["titolo"][:16] + "…" if len(ev["titolo"]) > 16 else ev["titolo"]
                        try:
                            ora = datetime.fromisoformat(
                                ev["data_inizio"].replace("Z","")
                            ).strftime("%H:%M") + " "
                        except:
                            ora = ""
                        propr = ev.get("proprietario") or {}
                        iniziali = (
                            propr.get("nome","")[:1] + propr.get("cognome","")[:1]
                        ).upper()
                        ev_html += (
                            f"<div style='background:{colore};color:white;"
                            f"font-size:9px;border-radius:3px;padding:2px 5px;"
                            f"margin-top:2px;overflow:hidden;white-space:nowrap;"
                            f"text-overflow:ellipsis;display:flex;justify-content:space-between;'>"
                            f"<span>{ora}{titolo_corto}</span>"
                            f"<span style='opacity:0.7;margin-left:3px;'>{iniziali}</span>"
                            f"</div>"
                        )
                    if len(ev_giorno) > 3:
                        ev_html += (
                            f"<div style='font-size:9px;color:#888;margin-top:2px;'>"
                            f"+{len(ev_giorno)-3} altri</div>"
                        )

                    st.markdown(
                        f"<div style='min-height:80px;border:1px solid {border_color};"
                        f"border-radius:6px;background:{bg_color};padding:6px 8px;'>"
                        f"<div style='font-size:12px;{num_style}'>{giorno}</div>"
                        f"{ev_html}</div>",
                        unsafe_allow_html=True
                    )

                    if st.button(
                        f"{'Chiudi' if e_sel else 'Apri'}",
                        key=f"cal_g_{anno}_{mese}_{giorno}",
                        use_container_width=True
                    ):
                        if e_sel:
                            st.session_state.cal_giorno_sel = None
                        else:
                            st.session_state.cal_giorno_sel = giorno
                        st.rerun()

    # Pannello giorno selezionato
    if giorno_selezionato:
        st.markdown("---")
        data_sel = date(anno, mese, giorno_selezionato)
        st.markdown(
            f"<h3 style='margin-bottom:12px;'>"
            f"{giorno_selezionato} {MESI_IT[mese-1]} {anno}</h3>",
            unsafe_allow_html=True
        )

        ev_giorno_sel = eventi_per_giorno.get(giorno_selezionato, [])

        col_lista, col_form = st.columns([1, 1])

        with col_lista:
            st.markdown("**Eventi del giorno**")
            if not ev_giorno_sel:
                st.info("Nessun evento. Creane uno dalla colonna a destra.")
            else:
                for e in ev_giorno_sel:
                    try:
                        ora = datetime.fromisoformat(
                            e["data_inizio"].replace("Z","")
                        ).strftime("%H:%M")
                    except:
                        ora = ""
                    colore = COLORI.get(e.get("tipo","altro"), "#1a1a2e")
                    propr = e.get("proprietario") or {}
                    nome_propr = f"{propr.get('nome','')} {propr.get('cognome','')}".strip()
                    puo_mod = e.get("proprietario_id") in ids_modificabili

                st.markdown(
                        f"<div style='background:white;border:1px solid #eaeaf0;"
                        f"border-left:4px solid {colore};border-radius:8px;"
                        f"padding:12px 14px;margin-bottom:8px;'>"
                        f"<div style='font-size:13px;font-weight:600;'>"
                        f"{ora}  {e['titolo']}</div>"
                        f"<div style='font-size:11px;color:#888;margin-top:4px;'>"
                        f"{e.get('tipo','').upper()}"
                        f"{' · ' + e['luogo'] if e.get('luogo') else ''}"
                        f" · {nome_propr}</div>"
                        f"{f'<div style=\"font-size:11px;color:#555;margin-top:4px;\">{e[\"descrizione\"]}</div>' if e.get('descrizione') else ''}"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                    if puo_mod:
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("Modifica", key=f"mod_g_{e['id']}"):
                                st.session_state[f"edit_ev_{e['id']}"] = True
                        with c2:
                            if st.button("Elimina", key=f"del_g_{e['id']}"):
                                st.session_state[f"delconf_{e['id']}"] = True

                        if st.session_state.get(f"delconf_{e['id']}"):
                            st.warning("Confermi eliminazione?")
                            ca, cb = st.columns(2)
                            if ca.button("Si", key=f"dok_{e['id']}"):
                                elimina_evento(e["id"])
                                st.session_state[f"delconf_{e['id']}"] = False
                                st.rerun()
                            if cb.button("No", key=f"dno_{e['id']}"):
                                st.session_state[f"delconf_{e['id']}"] = False
                                st.rerun()

                        if st.session_state.get(f"edit_ev_{e['id']}"):
                            _form_modifica_evento_inline(e, utente, ids_modificabili)

        with col_form:
            st.markdown("**Nuovo evento in questo giorno**")
            _form_evento_rapido(utente, data_sel, ids_modificabili)

def _form_evento_rapido(utente, data_sel, ids_modificabili):
    """Form compatto per creare un evento in un giorno specifico."""
    utenti_tutti = lista_utenti()
    utenti_mod = [u for u in utenti_tutti if u["id"] in ids_modificabili]
    opzioni = {f"{u['nome']} {u['cognome']}": u["id"] for u in utenti_mod}

    with st.form(f"form_rapido_{data_sel.isoformat()}"):
        titolo = st.text_input("Titolo *", key=f"fr_tit_{data_sel}")
        tipo = st.selectbox("Tipo", TIPI, key=f"fr_tipo_{data_sel}")
        col1, col2 = st.columns(2)
        with col1:
            ora_i = st.time_input("Inizio", value=datetime.strptime("09:00","%H:%M").time(), key=f"fr_oi_{data_sel}")
        with col2:
            ora_f = st.time_input("Fine", value=datetime.strptime("10:00","%H:%M").time(), key=f"fr_of_{data_sel}")
        luogo = st.text_input("Luogo", key=f"fr_luogo_{data_sel}")
        desc = st.text_area("Note", height=80, key=f"fr_desc_{data_sel}")
        cal_di = st.selectbox("Calendario di", list(opzioni.keys()), key=f"fr_cal_{data_sel}")
        submitted = st.form_submit_button("Crea evento", use_container_width=True)

    if submitted:
        if not titolo:
            st.error("Il titolo e obbligatorio.")
        else:
            dt_i = datetime.combine(data_sel, ora_i)
            dt_f = datetime.combine(data_sel, ora_f)
            crea_evento({
                "titolo": titolo,
                "tipo": tipo,
                "luogo": luogo,
                "descrizione": desc,
                "tutto_il_giorno": False,
                "data_inizio": dt_i.isoformat(),
                "data_fine": dt_f.isoformat(),
                "colore": COLORI.get(tipo, "#1a1a2e"),
                "proprietario_id": opzioni[cal_di],
                "partecipanti": [],
            }, utente["id"])
            st.success("Evento creato.")
            st.rerun()

def _form_modifica_evento_inline(e, utente, ids_modificabili):
    utenti_tutti = lista_utenti()
    utenti_mod = [u for u in utenti_tutti if u["id"] in ids_modificabili]
    opzioni = {f"{u['nome']} {u['cognome']}": u["id"] for u in utenti_mod}

    try:
        dt_i = datetime.fromisoformat(e["data_inizio"].replace("Z",""))
        dt_f = datetime.fromisoformat(e["data_fine"].replace("Z","")) if e.get("data_fine") else dt_i
    except:
        dt_i = datetime.now()
        dt_f = datetime.now()

    with st.form(f"form_edit_inline_{e['id']}"):
        titolo = st.text_input("Titolo *", value=e["titolo"])
        tipo = st.selectbox("Tipo", TIPI,
            index=TIPI.index(e.get("tipo","appuntamento")) if e.get("tipo") in TIPI else 0)
        col1, col2 = st.columns(2)
        with col1:
            ora_i = st.time_input("Inizio", value=dt_i.time())
        with col2:
            ora_f = st.time_input("Fine", value=dt_f.time())
        luogo = st.text_input("Luogo", value=e.get("luogo",""))
        desc = st.text_area("Note", value=e.get("descrizione",""), height=80)

        default_propr = 0
        if e.get("proprietario_id"):
            ids_list = list(opzioni.values())
            if e["proprietario_id"] in ids_list:
                default_propr = ids_list.index(e["proprietario_id"])
        cal_di = st.selectbox("Calendario di", list(opzioni.keys()), index=default_propr)

        col1, col2 = st.columns(2)
        with col1:
            salva = st.form_submit_button("Salva", use_container_width=True)
        with col2:
            annulla = st.form_submit_button("Annulla", use_container_width=True)

    if salva:
        data_base = dt_i.date()
        aggiorna_evento(e["id"], {
            "titolo": titolo,
            "tipo": tipo,
            "luogo": luogo,
            "descrizione": desc,
            "data_inizio": datetime.combine(data_base, ora_i).isoformat(),
            "data_fine": datetime.combine(data_base, ora_f).isoformat(),
            "colore": COLORI.get(tipo, "#1a1a2e"),
            "proprietario_id": opzioni[cal_di],
        })
        st.session_state[f"edit_ev_{e['id']}"] = False
        st.rerun()
    if annulla:
        st.session_state[f"edit_ev_{e['id']}"] = False
        st.rerun()

def _form_nuovo_evento(utente, ids_modificabili):
    st.subheader("Nuovo evento")
    utenti_tutti = lista_utenti()
    utenti_mod = [u for u in utenti_tutti if u["id"] in ids_modificabili]
    opzioni = {f"{u['nome']} {u['cognome']}": u["id"] for u in utenti_mod}
    opzioni_tutti = {f"{u['nome']} {u['cognome']}": u["id"] for u in utenti_tutti}

    with st.form("form_nuovo_evento"):
        col1, col2 = st.columns(2)
        with col1:
            titolo = st.text_input("Titolo *")
            tipo = st.selectbox("Tipo", TIPI)
            luogo = st.text_input("Luogo")
            cal_di = st.selectbox("Calendario di", list(opzioni.keys()))
        with col2:
            tutto_il_giorno = st.checkbox("Tutto il giorno")
            data = st.date_input("Data *", value=date.today())
            if not tutto_il_giorno:
                ora_i = st.time_input("Ora inizio", value=datetime.strptime("09:00","%H:%M").time())
                ora_f = st.time_input("Ora fine", value=datetime.strptime("10:00","%H:%M").time())
            else:
                ora_i = datetime.strptime("00:00","%H:%M").time()
                ora_f = datetime.strptime("23:59","%H:%M").time()
        desc = st.text_area("Note")
        partecipanti_sel = st.multiselect("Partecipanti", list(opzioni_tutti.keys()))
        submitted = st.form_submit_button("Crea evento", use_container_width=True)

    if submitted:
        if not titolo:
            st.error("Il titolo e obbligatorio.")
        else:
            crea_evento({
                "titolo": titolo,
                "tipo": tipo,
                "luogo": luogo,
                "descrizione": desc,
                "tutto_il_giorno": tutto_il_giorno,
                "data_inizio": datetime.combine(data, ora_i).isoformat(),
                "data_fine": datetime.combine(data, ora_f).isoformat(),
                "colore": COLORI.get(tipo, "#1a1a2e"),
                "proprietario_id": opzioni[cal_di],
                "partecipanti": [opzioni_tutti[p] for p in partecipanti_sel],
            }, utente["id"])
            st.success("Evento creato.")
            st.rerun()

def _gestione_autorizzazioni(utente):
    st.subheader("Gestione autorizzazioni calendario")
    st.markdown("Definisci chi può vedere o modificare il calendario di ogni utente.")
    st.markdown("---")

    utenti = lista_utenti()

    for proprietario in utenti:
        nome_propr = f"{proprietario['nome']} {proprietario['cognome']}"
        with st.expander(f"Calendario di {nome_propr}"):
            altri = [u for u in utenti if u["id"] != proprietario["id"]]
            if not altri:
                st.info("Nessun altro utente.")
                continue

            # Carica autorizzazioni esistenti per questo calendario
            sb_res = _carica_autorizzazioni_per_calendario(proprietario["id"])
            auth_map = {a["utente_id"]: a for a in sb_res}

            for u in altri:
                nome_u = f"{u['nome']} {u['cognome']}"
                auth_corrente = auth_map.get(u["id"], {})

                col1, col2, col3 = st.columns([3, 2, 2])
                col1.markdown(
                    f"<span style='font-size:13px;'>{nome_u}</span>",
                    unsafe_allow_html=True
                )
                with col2:
                    vede = st.checkbox(
                        "Puo vedere",
                        value=auth_corrente.get("puo_vedere", False),
                        key=f"v_{proprietario['id']}_{u['id']}"
                    )
                with col3:
                    modifica = st.checkbox(
                        "Puo modificare",
                        value=auth_corrente.get("puo_modificare", False),
                        key=f"m_{proprietario['id']}_{u['id']}"
                    )

                if st.button("Salva", key=f"save_auth_{proprietario['id']}_{u['id']}"):
                    if not vede and not modifica:
                        elimina_autorizzazione_calendario(u["id"], proprietario["id"])
                    else:
                        salva_autorizzazione_calendario(
                            u["id"], proprietario["id"],
                            vede, modifica
                        )
                    st.success(f"Autorizzazione aggiornata per {nome_u}.")
                    st.rerun()

def _carica_autorizzazioni_per_calendario(calendario_di_id):
    from db import get_sb
    sb = get_sb()
    try:
        res = sb.table("calendario_autorizzazioni").select("*").eq(
            "calendario_di", calendario_di_id
        ).execute()
        return res.data or []
    except:
        return []
