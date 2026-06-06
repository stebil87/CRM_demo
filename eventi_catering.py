import streamlit as st
from datetime import date, datetime, timedelta
import json
from db import (
    lista_eventi_catering, get_evento_catering, crea_evento_catering,
    aggiorna_evento_catering, lista_collaboratori_evento, aggiungi_collaboratore,
    rimuovi_collaboratore, segna_collaboratore_avvisato, lista_allegati_evento,
    carica_allegato_evento, scarica_allegato_evento, lista_ore_evento,
    inserisci_ore, lista_utenti, utenti_event_manager, get_cliente
)
from auth import can_edit, is_admin

STATI = ["nuovo", "assegnato", "in_corso", "completato", "annullato"]
COLORI_STATO = {
    "nuovo":      "#e94560",
    "assegnato":  "#533483",
    "in_corso":   "#0f3460",
    "completato": "#2d6a4f",
    "annullato":  "#888",
}

def is_event_manager(utente):
    return utente and utente["ruolo"] in ("admin", "event_manager")

def pagina_eventi(utente):
    st.title("Eventi")
    st.markdown("---")

    # Avvisi per event manager
    if is_event_manager(utente):
        nuovi = lista_eventi_catering(solo_nuovo=True)
        if nuovi:
            for ev in nuovi:
                st.markdown(
                    "<div style='background:#fff3cd;border:1px solid #ffc107;"
                    "border-left:4px solid #e94560;border-radius:8px;"
                    "padding:12px 16px;margin-bottom:8px;font-size:13px;'>"
                    "<strong>Nuovo evento da gestire:</strong> " + ev["titolo"] +
                    " — " + (ev.get("data_inizio") or "")[:10] +
                    "</div>",
                    unsafe_allow_html=True
                )

    tabs = ["Lista eventi", "Nuovo evento"]
    tab_list = st.tabs(tabs)

    with tab_list[0]:
        _lista_eventi(utente)

    with tab_list[1]:
        if not can_edit(utente):
            st.warning("Non hai i permessi per creare eventi.")
        else:
            _form_nuovo_evento(utente)


def _lista_eventi(utente):
    eventi = lista_eventi_catering()
    if not eventi:
        st.info("Nessun evento trovato.")
        return

    for ev in eventi:
        stato = ev.get("stato", "nuovo")
        colore_stato = COLORI_STATO.get(stato, "#888")
        cliente = ev.get("cliente") or {}
        nome_cliente = cliente.get("ragione_sociale") or \
            f"{cliente.get('nome','')} {cliente.get('cognome','')}".strip()
        data_str = (ev.get("data_inizio") or "")[:10]
        offerta_info = ev.get("offerta") or {}

        label = (
            ev["titolo"] + "   |   " + nome_cliente +
            "   |   " + data_str +
            "   |   " + stato.upper()
        )

        with st.expander(label):
            _scheda_evento(ev, utente, colore_stato)


def _scheda_evento(ev, utente, colore_stato):
    col1, col2 = st.columns(2)
    cliente = ev.get("cliente") or {}
    offerta_info = ev.get("offerta") or {}
    manager = ev.get("manager") or {}

    with col1:
        st.markdown(f"**Titolo:** {ev['titolo']}")
        st.markdown(f"**Stato:** {ev.get('stato','—').upper()}")
        st.markdown(f"**Data inizio:** {(ev.get('data_inizio') or '')[:10]}")
        st.markdown(f"**Data fine:** {(ev.get('data_fine') or '')[:10]}")
        st.markdown(f"**Orario:** {ev.get('orario_inizio','—')} — {ev.get('orario_fine','—')}")
        st.markdown(f"**Luogo:** {ev.get('luogo','—')}")
    with col2:
        nome_cliente = cliente.get("ragione_sociale") or \
            f"{cliente.get('nome','')} {cliente.get('cognome','')}".strip()
        st.markdown(f"**Cliente:** {nome_cliente}")
        st.markdown(f"**Email cliente:** {cliente.get('email','—')}")
        if offerta_info:
            st.markdown(f"**Offerta:** {offerta_info.get('numero','—')} — {offerta_info.get('titolo','—')}")
            st.markdown(f"**Importo:** {offerta_info.get('valuta','CHF')} {float(offerta_info.get('importo') or 0):,.2f}")
        nome_manager = f"{manager.get('nome','')} {manager.get('cognome','')}".strip()
        st.markdown(f"**Event Manager:** {nome_manager or '—'}")

    if ev.get("note"):
        st.markdown(f"**Note:** {ev['note']}")

    st.markdown("---")

    # Tabs scheda evento
    tab_collab, tab_ore, tab_allegati, tab_modifica = st.tabs([
        "Collaboratori", "Ore prestate", "Allegati", "Modifica"
    ])

    with tab_collab:
        _gestione_collaboratori(ev, utente)

    with tab_ore:
        _gestione_ore(ev, utente)

    with tab_allegati:
        _gestione_allegati(ev, utente)

    with tab_modifica:
        if can_edit(utente):
            _form_modifica_evento(ev, utente)
        else:
            st.info("Non hai i permessi per modificare questo evento.")

def _tab_beo(ev, utente):
    st.markdown("**Banquet Event Order**")
    st.markdown("Compila i dettagli operativi e genera il documento ufficiale.")
    st.markdown("---")

    from db import get_cliente, get_offerta, aggiorna_evento_catering

    cliente = get_cliente(ev.get("cliente_id")) if ev.get("cliente_id") else {}
    offerta = get_offerta(ev.get("offerta_id")) if ev.get("offerta_id") else {}

    # Campi aggiuntivi BEO
    col1, col2 = st.columns(2)
    with col1:
        coperti = st.number_input(
            "Numero coperti",
            min_value=0, value=ev.get("numero_coperti") or 0,
            key=f"beo_coperti_{ev['id']}"
        )
        referente_nome = st.text_input(
            "Referente cliente il giorno dell'evento",
            value=ev.get("referente_cliente_nome") or "",
            key=f"beo_ref_nome_{ev['id']}"
        )
        referente_tel = st.text_input(
            "Telefono referente",
            value=ev.get("referente_cliente_telefono") or "",
            key=f"beo_ref_tel_{ev['id']}"
        )
    with col2:
        setup_sala = st.text_area(
            "Setup sala",
            value=ev.get("setup_sala") or "",
            height=100,
            key=f"beo_setup_{ev['id']}"
        )
        note_allergeni = st.text_area(
            "Note allergeni",
            value=ev.get("note_allergeni") or "",
            height=100,
            key=f"beo_allergeni_{ev['id']}"
        )

    col3, col4 = st.columns(2)
    with col3:
        note_cucina = st.text_area(
            "Note cucina",
            value=ev.get("note_cucina") or "",
            height=100,
            key=f"beo_cucina_{ev['id']}"
        )
    with col4:
        note_servizio = st.text_area(
            "Note servizio",
            value=ev.get("note_servizio") or "",
            height=100,
            key=f"beo_servizio_{ev['id']}"
        )

    # Timeline
    st.markdown("---")
    st.markdown("**Timeline operativa**")
    st.caption("Aggiungi le tappe della giornata in ordine cronologico.")

    state_key_tl = f"timeline_{ev['id']}"
    if state_key_tl not in st.session_state:
        tl = ev.get("timeline") or []
        if isinstance(tl, str):
            import json
            try:
                tl = json.loads(tl)
            except:
                tl = []
        st.session_state[state_key_tl] = tl

    timeline = st.session_state[state_key_tl]

    for i, t in enumerate(timeline):
        col1, col2, col3, col4 = st.columns([1.5, 3, 2, 1])
        with col1:
            orario = st.text_input(
                "Orario", value=t.get("orario", ""),
                placeholder="08:00",
                key=f"tl_ora_{ev['id']}_{i}"
            )
        with col2:
            attivita = st.text_input(
                "Attivita", value=t.get("attivita", ""),
                key=f"tl_att_{ev['id']}_{i}"
            )
        with col3:
            responsabile = st.text_input(
                "Responsabile", value=t.get("responsabile", ""),
                key=f"tl_resp_{ev['id']}_{i}"
            )
        with col4:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Rimuovi", key=f"tl_del_{ev['id']}_{i}"):
                st.session_state[state_key_tl].pop(i)
                st.rerun()
        timeline[i] = {
            "orario": orario,
            "attivita": attivita,
            "responsabile": responsabile,
            "note": t.get("note", "")
        }

    st.session_state[state_key_tl] = timeline

    if st.button("Aggiungi tappa", key=f"tl_add_{ev['id']}"):
        st.session_state[state_key_tl].append({
            "orario": "", "attivita": "", "responsabile": "", "note": ""
        })
        st.rerun()

    st.markdown("---")

    col_salva, col_genera = st.columns(2)

    with col_salva:
        if st.button("Salva dati BEO", key=f"beo_salva_{ev['id']}", use_container_width=True):
            aggiorna_evento_catering(ev["id"], {
                "numero_coperti": coperti,
                "referente_cliente_nome": referente_nome,
                "referente_cliente_telefono": referente_tel,
                "setup_sala": setup_sala,
                "note_allergeni": note_allergeni,
                "note_cucina": note_cucina,
                "note_servizio": note_servizio,
                "timeline": st.session_state[state_key_tl],
            })
            st.success("Dati BEO salvati.")
            st.rerun()

    with col_genera:
        if st.button("Genera PDF BEO", key=f"beo_gen_{ev['id']}", use_container_width=True):
            # Salva prima i dati aggiornati
            aggiorna_evento_catering(ev["id"], {
                "numero_coperti": coperti,
                "referente_cliente_nome": referente_nome,
                "referente_cliente_telefono": referente_tel,
                "setup_sala": setup_sala,
                "note_allergeni": note_allergeni,
                "note_cucina": note_cucina,
                "note_servizio": note_servizio,
                "timeline": st.session_state[state_key_tl],
            })
            # Ricarica evento aggiornato
            from db import get_evento_catering
            ev_aggiornato = get_evento_catering(ev["id"]) or ev
            ev_aggiornato["timeline"] = st.session_state[state_key_tl]

            with st.spinner("Generazione BEO in corso..."):
                from beo_generator import genera_beo
                pdf_bytes = genera_beo(ev_aggiornato, cliente, offerta)

            if pdf_bytes:
                nome_file = f"BEO-{ev['id'][:8].upper()}.pdf"
                st.download_button(
                    label="Scarica BEO",
                    data=pdf_bytes,
                    file_name=nome_file,
                    mime="application/pdf",
                    key=f"beo_dl_{ev['id']}"
                )
                st.success("BEO generato.")


def _gestione_collaboratori(ev, utente, ):
    collaboratori = lista_collaboratori_evento(ev["id"])

    if collaboratori:
        st.markdown("**Collaboratori assegnati**")
        for c in collaboratori:
            u = c.get("utente") or {}
            nome = f"{u.get('nome','')} {u.get('cognome','')}".strip() if u else c.get("nome_esterno","—")
            email = u.get("email","") if u else c.get("email_esterno","")
            avvisato = "Avvisato" if c.get("avvisato") else "Non avvisato"
            ruolo = c.get("ruolo") or "—"

            col1, col2, col3 = st.columns([3, 2, 1])
            col1.markdown(f"**{nome}** — {ruolo}")
            col2.markdown(f"{email}   ·   {avvisato}")
            if is_event_manager(utente):
                if col3.button("Rimuovi", key=f"rem_collab_{c['id']}"):
                    rimuovi_collaboratore(c["id"])
                    st.rerun()

    st.markdown("---")

    if is_event_manager(utente):
        st.markdown("**Aggiungi collaboratore**")
        tab_interno, tab_esterno = st.tabs(["Utente interno", "Personale esterno"])

        with tab_interno:
            utenti = lista_utenti()
            ids_già = [c.get("utente_id") for c in collaboratori if c.get("utente_id")]
            disponibili = [u for u in utenti if u["id"] not in ids_già]
            if disponibili:
                with st.form(f"form_add_collab_int_{ev['id']}"):
                    opzioni = {f"{u['nome']} {u['cognome']}": u["id"] for u in disponibili}
                    sel = st.selectbox("Seleziona utente", list(opzioni.keys()))
                    ruolo = st.text_input("Ruolo/mansione")
                    if st.form_submit_button("Aggiungi", use_container_width=True):
                        aggiungi_collaboratore(ev["id"], utente_id=opzioni[sel], ruolo=ruolo)
                        st.rerun()
            else:
                st.info("Tutti gli utenti sono già assegnati.")

        with tab_esterno:
            with st.form(f"form_add_collab_ext_{ev['id']}"):
                nome_ext = st.text_input("Nome e cognome *")
                email_ext = st.text_input("Email")
                ruolo_ext = st.text_input("Ruolo/mansione")
                if st.form_submit_button("Aggiungi", use_container_width=True):
                    if not nome_ext:
                        st.error("Il nome è obbligatorio.")
                    else:
                        aggiungi_collaboratore(
                            ev["id"],
                            nome_esterno=nome_ext,
                            email_esterno=email_ext,
                            ruolo=ruolo_ext
                        )
                        st.rerun()

        # Avvisa tutti
        if collaboratori:
            st.markdown("---")
            non_avvisati = [c for c in collaboratori if not c.get("avvisato")]
            if non_avvisati:
                if st.button("Avvisa tutti i collaboratori", key=f"avvisa_{ev['id']}"):
                    for c in non_avvisati:
                        segna_collaboratore_avvisato(c["id"])
                        # Crea avviso interno nel session state
                        if c.get("utente_id"):
                            from db import invia_messaggio
                            invia_messaggio(
                                utente["id"],
                                c["utente_id"],
                                f"Sei stato assegnato all'evento: {ev['titolo']}",
                                f"Sei stato assegnato come collaboratore per l'evento '{ev['titolo']}' "
                                f"in programma il {(ev.get('data_inizio') or '')[:10]} "
                                f"presso {ev.get('luogo','—')}. "
                                f"Ricordati di inserire le ore prestate entro 15 giorni dalla fine dell'evento."
                            )
                    st.success("Collaboratori avvisati.")
                    st.rerun()


def _gestione_ore(ev, utente):
    ore = lista_ore_evento(ev["id"])

    if ore:
        st.markdown("**Ore inserite**")
        totale = 0.0
        for o in ore:
            u = o.get("utente") or {}
            nome = f"{u.get('nome','')} {u.get('cognome','')}".strip() if u else o.get("nome_esterno","—")
            ore_tot = float(o.get("ore_totali") or 0)
            totale += ore_tot
            st.markdown(
                f"**{nome}** — dal {o['data_dal']} al {o['data_al']} "
                f"· {o['orario_da']}–{o['orario_a']} · **{ore_tot}h**"
                + (f" · {o['note']}" if o.get("note") else "")
            )
        st.markdown(f"**Totale ore: {totale:.1f}h**")
        st.markdown("---")

    # Form inserimento ore — visibile ai collaboratori assegnati
    collaboratori = lista_collaboratori_evento(ev["id"])
    ids_collab = [c.get("utente_id") for c in collaboratori if c.get("utente_id")]
    può_inserire = (
        utente["id"] in ids_collab or
        is_event_manager(utente)
    )

    if può_inserire:
        st.markdown("**Inserisci le tue ore**")
        with st.form(f"form_ore_{ev['id']}"):
            col1, col2 = st.columns(2)
            with col1:
                data_dal = st.date_input("Dal *", value=date.today())
                orario_da = st.text_input("Orario inizio (es. 08:00)", placeholder="08:00")
            with col2:
                data_al = st.date_input("Al *", value=date.today())
                orario_a = st.text_input("Orario fine (es. 18:00)", placeholder="18:00")
            note = st.text_input("Note (opzionale)")
            if st.form_submit_button("Salva ore", use_container_width=True):
                if not orario_da or not orario_a:
                    st.error("Inserisci orario inizio e fine.")
                else:
                    try:
                        from datetime import datetime as dt
                        giorni = (data_al - data_dal).days + 1
                        h_inizio = dt.strptime(orario_da, "%H:%M")
                        h_fine = dt.strptime(orario_a, "%H:%M")
                        ore_giorno = (h_fine - h_inizio).seconds / 3600
                        ore_tot = round(giorni * ore_giorno, 2)
                    except:
                        ore_tot = 0

                    inserisci_ore({
                        "evento_id": ev["id"],
                        "utente_id": utente["id"],
                        "data_dal": data_dal.isoformat(),
                        "data_al": data_al.isoformat(),
                        "orario_da": orario_da,
                        "orario_a": orario_a,
                        "ore_totali": ore_tot,
                        "note": note
                    })
                    st.success(f"Ore salvate: {ore_tot}h")
                    st.rerun()
    else:
        st.info("Solo i collaboratori assegnati possono inserire le ore.")


def _gestione_allegati(ev, utente):
    allegati = lista_allegati_evento(ev["id"])

    if allegati:
        for a in allegati:
            dim_kb = round((a.get("dimensione") or 0) / 1024, 1)
            col1, col2 = st.columns([4, 1])
            col1.markdown(f"**{a['nome_file']}** — {dim_kb} KB")
            with col2:
                if st.button("Scarica", key=f"sc_all_{a['id']}"):
                    contenuto = scarica_allegato_evento(a["storage_path"])
                    if contenuto:
                        st.download_button(
                            label="Clicca per scaricare",
                            data=contenuto,
                            file_name=a["nome_file"],
                            mime=a.get("tipo_file","application/octet-stream"),
                            key=f"dl_all_{a['id']}"
                        )
    else:
        st.info("Nessun allegato.")

    if can_edit(utente):
        st.markdown("---")
        file = st.file_uploader(
            "Carica allegato",
            type=["pdf","jpg","jpeg","png","doc","docx","xls","xlsx","txt"],
            key=f"upload_ev_{ev['id']}"
        )
        if file and st.button("Carica", key=f"btn_upload_ev_{ev['id']}"):
            err = carica_allegato_evento(
                ev["id"], file.read(), file.name,
                file.type or "application/octet-stream",
                file.size, utente["id"]
            )
            if err:
                st.error(f"Errore: {err}")
            else:
                st.success("Allegato caricato.")
                st.rerun()


def _form_nuovo_evento(utente):
    st.subheader("Nuovo evento")

    from db import lista_clienti, lista_offerte as db_lista_offerte
    clienti = lista_clienti()
    managers = utenti_event_manager()

    opzioni_clienti = {"— Seleziona cliente —": None}
    for c in clienti:
        nome = c.get("ragione_sociale") or f"{c.get('nome','')} {c.get('cognome','')}".strip()
        opzioni_clienti[nome] = c["id"]

    opzioni_managers = {"— Nessun event manager —": None}
    for m in managers:
        opzioni_managers[f"{m['nome']} {m['cognome']}"] = m["id"]

    with st.form("form_nuovo_evento_catering"):
        titolo = st.text_input("Titolo evento *")
        col1, col2 = st.columns(2)
        with col1:
            cliente_sel = st.selectbox("Cliente", list(opzioni_clienti.keys()))
            luogo = st.text_input("Luogo")
            data_inizio = st.date_input("Data inizio *", value=date.today())
            orario_inizio = st.text_input("Orario inizio (es. 10:00)", placeholder="10:00")
        with col2:
            manager_sel = st.selectbox("Event Manager", list(opzioni_managers.keys()))
            data_fine = st.date_input("Data fine *", value=date.today())
            orario_fine = st.text_input("Orario fine (es. 22:00)", placeholder="22:00")
        note = st.text_area("Note")
        submitted = st.form_submit_button("Crea evento", use_container_width=True)

    if submitted:
        if not titolo:
            st.error("Il titolo è obbligatorio.")
        else:
            nuovo = crea_evento_catering({
                "titolo": titolo,
                "cliente_id": opzioni_clienti[cliente_sel],
                "luogo": luogo,
                "data_inizio": datetime.combine(data_inizio, datetime.strptime(orario_inizio or "00:00", "%H:%M").time()).isoformat() if orario_inizio else data_inizio.isoformat(),
                "data_fine": datetime.combine(data_fine, datetime.strptime(orario_fine or "23:59", "%H:%M").time()).isoformat() if orario_fine else data_fine.isoformat(),
                "orario_inizio": orario_inizio,
                "orario_fine": orario_fine,
                "note": note,
                "stato": "nuovo",
                "event_manager_id": opzioni_managers[manager_sel],
            }, utente["id"])
            if nuovo:
                st.success("Evento creato.")
                # Avvisa event manager
                if opzioni_managers[manager_sel]:
                    from db import invia_messaggio
                    invia_messaggio(
                        utente["id"],
                        opzioni_managers[manager_sel],
                        f"Nuovo evento da gestire: {titolo}",
                        f"È stato creato un nuovo evento '{titolo}' che richiede la tua gestione. "
                        f"Accedi alla sezione Eventi per assegnare i collaboratori."
                    )
                st.rerun()


def _form_modifica_evento(ev, utente):
    managers = utenti_event_manager()
    opzioni_managers = {"— Nessun event manager —": None}
    for m in managers:
        opzioni_managers[f"{m['nome']} {m['cognome']}"] = m["id"]

    default_manager = 0
    if ev.get("event_manager_id"):
        ids_m = list(opzioni_managers.values())
        if ev["event_manager_id"] in ids_m:
            default_manager = ids_m.index(ev["event_manager_id"])

    with st.form(f"form_edit_ev_cat_{ev['id']}"):
        titolo = st.text_input("Titolo *", value=ev["titolo"])
        col1, col2 = st.columns(2)
        with col1:
            luogo = st.text_input("Luogo", value=ev.get("luogo",""))
            try:
                di = datetime.fromisoformat(ev["data_inizio"].replace("Z","")).date() if ev.get("data_inizio") else date.today()
            except:
                di = date.today()
            data_inizio = st.date_input("Data inizio", value=di)
            orario_inizio = st.text_input("Orario inizio", value=ev.get("orario_inizio",""))
        with col2:
            stato = st.selectbox("Stato", STATI,
                index=STATI.index(ev.get("stato","nuovo")) if ev.get("stato") in STATI else 0)
            try:
                df = datetime.fromisoformat(ev["data_fine"].replace("Z","")).date() if ev.get("data_fine") else date.today()
            except:
                df = date.today()
            data_fine = st.date_input("Data fine", value=df)
            orario_fine = st.text_input("Orario fine", value=ev.get("orario_fine",""))
        manager_sel = st.selectbox("Event Manager", list(opzioni_managers.keys()), index=default_manager)
        note = st.text_area("Note", value=ev.get("note",""))
        col1, col2 = st.columns(2)
        with col1:
            salva = st.form_submit_button("Salva", use_container_width=True)
        with col2:
            annulla = st.form_submit_button("Annulla", use_container_width=True)

    if salva:
        aggiorna_evento_catering(ev["id"], {
            "titolo": titolo,
            "luogo": luogo,
            "data_inizio": data_inizio.isoformat(),
            "data_fine": data_fine.isoformat(),
            "orario_inizio": orario_inizio,
            "orario_fine": orario_fine,
            "stato": stato,
            "note": note,
            "event_manager_id": opzioni_managers[manager_sel],
        })
        st.success("Evento aggiornato.")
        st.rerun()


def widget_avvisi_eventi(utente):
    """Widget da mostrare in dashboard per collaboratori."""
    from db import eventi_assegnati_a_utente
    assegnazioni = eventi_assegnati_a_utente(utente["id"])
    if not assegnazioni:
        return

    oggi = date.today()
    da_completare = []
    for a in assegnazioni:
        ev = a.get("evento") or {}
        if not ev:
            continue
        data_fine_str = ev.get("data_fine","")
        try:
            data_fine = datetime.fromisoformat(data_fine_str.replace("Z","")).date()
            scadenza = data_fine + timedelta(days=15)
            if oggi <= scadenza and ev.get("stato") not in ("completato","annullato"):
                da_completare.append((a, ev, scadenza))
        except:
            pass

    if not da_completare:
        return

    st.markdown("**Promemoria ore eventi**")
    for a, ev, scadenza in da_completare:
        giorni_rimasti = (scadenza - oggi).days
        colore = "#e94560" if giorni_rimasti <= 3 else "#ffc107"
        st.markdown(
            "<div style='background:white;border:1px solid #eaeaf0;"
            "border-left:4px solid " + colore + ";border-radius:8px;"
            "padding:10px 14px;margin-bottom:8px;'>"
            "<div style='font-size:13px;font-weight:600;'>" + ev.get("titolo","—") + "</div>"
            "<div style='font-size:11px;color:#888;margin-top:3px;'>"
            "Inserisci le ore entro il " + scadenza.isoformat() +
            " (" + str(giorni_rimasti) + " giorni)</div>"
            "</div>",
            unsafe_allow_html=True
        )
        if st.button("Vai all'evento", key=f"goto_ev_{ev.get('id','')}"):
            st.session_state.pagina = "eventi"
            st.rerun()
