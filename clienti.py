import streamlit as st
from db import lista_clienti, get_cliente, crea_cliente, aggiorna_cliente, elimina_cliente, lista_utenti
from auth import can_edit, is_admin

STATI = ["prospect", "attivo", "inattivo", "perso"]
SETTORI = [
    "Consulenza", "Tecnologia", "Commercio", "Industria", "Servizi",
    "Sanità", "Finanza", "Immobiliare", "Logistica", "Turismo", "Alimentare", "Altro"
]
FORME_GIURIDICHE = [
    "SA", "Sagl", "Ditta individuale", "Associazione",
    "Fondazione", "Cooperativa", "Società semplice", "Altro"
]
PAESI = [
    "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Arabia Saudita", "Argentina",
    "Armenia", "Australia", "Austria", "Azerbaigian", "Bahrain", "Bangladesh", "Belgio",
    "Bielorussia", "Bolivia", "Bosnia ed Erzegovina", "Brasile", "Bulgaria", "Cambogia",
    "Camerun", "Canada", "Cile", "Cina", "Cipro", "Colombia", "Corea del Nord", "Corea del Sud",
    "Costa Rica", "Croazia", "Cuba", "Danimarca", "Ecuador", "Egitto", "Emirati Arabi Uniti",
    "Estonia", "Etiopia", "Filippine", "Finlandia", "Francia", "Georgia", "Germania", "Ghana",
    "Giappone", "Giordania", "Grecia", "Guatemala", "Hong Kong", "India", "Indonesia", "Iran",
    "Iraq", "Irlanda", "Islanda", "Israele", "Italia", "Kazakhstan", "Kenya", "Kuwait",
    "Laos", "Lettonia", "Libano", "Libia", "Liechtenstein", "Lituania", "Lussemburgo",
    "Macedonia del Nord", "Malaysia", "Malta", "Marocco", "Messico", "Moldova", "Monaco",
    "Mongolia", "Montenegro", "Mozambico", "Myanmar", "Nepal", "Nicaragua", "Nigeria",
    "Norvegia", "Nuova Zelanda", "Oman", "Paesi Bassi", "Pakistan", "Panama", "Paraguay",
    "Peru", "Polonia", "Portogallo", "Qatar", "Regno Unito", "Repubblica Ceca",
    "Repubblica Dominicana", "Romania", "Russia", "Rwanda", "San Marino", "Senegal",
    "Serbia", "Singapore", "Siria", "Slovacchia", "Slovenia", "Somalia", "Spagna",
    "Sri Lanka", "Sudafrica", "Sudan", "Svezia", "Svizzera", "Taiwan", "Tanzania",
    "Thailandia", "Tunisia", "Turchia", "Ucraina", "Uganda", "Ungheria", "Uruguay",
    "Uzbekistan", "Venezuela", "Vietnam", "Yemen", "Zambia", "Zimbabwe"
]


def nome_display(c):
    if c["tipo"] == "giuridica":
        return c.get("ragione_sociale") or "—"
    return f"{c.get('nome','')} {c.get('cognome','')}".strip() or "—"


def pagina_clienti(utente):
    st.title("Clienti")

    tab_lista, tab_nuovo = st.tabs(["Lista clienti", "Nuovo cliente"])

    with tab_lista:
        col1, col2 = st.columns([3, 1])
        with col1:
            cerca = st.text_input("Cerca per nome, email...", key="cerca_clienti")
        with col2:
            stato_filtro = st.selectbox("Stato", ["tutti"] + STATI, key="filtro_stato")

        clienti = lista_clienti(
            filtro_stato=None if stato_filtro == "tutti" else stato_filtro,
            filtro_testo=cerca if cerca else None
        )

        if not clienti:
            st.info("Nessun cliente trovato.")
        else:
            for c in clienti:
                tipo_label = "Azienda" if c["tipo"] == "giuridica" else "Persona fisica"
                with st.expander(
                    f"{nome_display(c)}   |   {tipo_label}   |   {c.get('stato','').upper()}"
                ):
                    _scheda_cliente(c, utente)

    with tab_nuovo:
        if not can_edit(utente):
            st.warning("Non hai i permessi per creare clienti.")
        else:
            _form_nuovo_cliente(utente)


def _scheda_cliente(c, utente):
    col1, col2 = st.columns(2)
    with col1:
        if c["tipo"] == "giuridica":
            st.markdown(f"**Ragione sociale:** {c.get('ragione_sociale','—')}")
            st.markdown(f"**Forma giuridica:** {c.get('forma_giuridica','—')}")
            st.markdown(f"**Codice IDI:** {c.get('codice_idi','—')}")
            st.markdown(f"**Settore:** {c.get('settore','—')}")
            st.markdown(
                f"**Referente:** {c.get('contatto_nome','')} "
                f"{c.get('contatto_cognome','')} — {c.get('contatto_ruolo','—')}"
            )
            st.markdown(f"**Email referente:** {c.get('contatto_email','—')}")
            st.markdown(f"**Tel referente:** {c.get('contatto_telefono','—')}")
            st.markdown(f"**Sito web:** {c.get('sito_web','—')}")
        else:
            st.markdown(f"**Nome:** {c.get('nome','')} {c.get('cognome','')}")
            st.markdown(f"**Data di nascita:** {c.get('data_nascita','—')}")
        st.markdown(f"**Email:** {c.get('email','—')}")
        st.markdown(f"**Telefono:** {c.get('telefono','—')}")
    with col2:
        st.markdown(f"**Indirizzo:** {c.get('indirizzo','—')}")
        st.markdown(f"**Citta:** {c.get('citta','—')} {c.get('cap','')}")
        st.markdown(f"**Paese:** {c.get('paese','—')}")
        st.markdown(f"**Stato:** {c.get('stato','—').upper()}")
        st.markdown(f"**Note:** {c.get('note','—')}")

    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        if st.button("Modifica", key=f"mod_{c['id']}", disabled=not can_edit(utente)):
            st.session_state[f"edit_{c['id']}"] = True
    with col_b:
        if st.button("Diario", key=f"dir_{c['id']}"):
            st.session_state.pagina = "diario"
            st.session_state.cliente_id = c["id"]
            st.session_state.cliente_nome = nome_display(c)
            st.rerun()
    with col_c:
        if st.button("Offerte", key=f"off_{c['id']}"):
            st.session_state.pagina = "offerte"
            st.session_state.cliente_id = c["id"]
            st.session_state.cliente_nome = nome_display(c)
            st.rerun()
    with col_d:
        if st.button("Documenti", key=f"doc_{c['id']}"):
            st.session_state.pagina = "documenti"
            st.session_state.cliente_id = c["id"]
            st.session_state.cliente_nome = nome_display(c)
            st.rerun()

    if st.session_state.get(f"edit_{c['id']}"):
        st.markdown("---")
        _form_modifica_cliente(c, utente)


def _form_nuovo_cliente(utente):
    st.subheader("Nuovo cliente")

    if "new_cliente_tipo" not in st.session_state:
        st.session_state.new_cliente_tipo = "fisica"

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Persona fisica" + (" ✓" if st.session_state.new_cliente_tipo == "fisica" else ""),
            key="btn_tipo_fisica",
            use_container_width=True
        ):
            st.session_state.new_cliente_tipo = "fisica"
            st.rerun()
    with col2:
        if st.button(
            "Persona giuridica" + ("" if st.session_state.new_cliente_tipo == "giuridica" else ""),
            key="btn_tipo_giuridica",
            use_container_width=True
        ):
            st.session_state.new_cliente_tipo = "giuridica"
            st.rerun()

    tipo = st.session_state.new_cliente_tipo
   
    st.markdown("---")

    with st.form("form_nuovo_cliente"):
        dati = _form_campi(tipo=tipo, d={}, key_prefix="new")
        submitted = st.form_submit_button("Crea cliente", use_container_width=True)

    if submitted:
        tipo_finale = st.session_state.new_cliente_tipo
        errori = []
        if tipo_finale == "giuridica" and not dati.get("ragione_sociale"):
            errori.append("Ragione sociale obbligatoria")
        if tipo_finale == "fisica" and not dati.get("nome"):
            errori.append("Nome obbligatorio")
        if tipo_finale == "fisica" and not dati.get("cognome"):
            errori.append("Cognome obbligatorio")
        if errori:
            st.error(" · ".join(errori))
        else:
            dati["tipo"] = tipo_finale
            risultato = crea_cliente(dati, utente["id"])
            if risultato:
                st.success("Cliente creato.")
                st.session_state.new_cliente_tipo = "fisica"
                st.rerun()
            else:
                st.error("Errore nel salvataggio — riprova.")


def _form_modifica_cliente(c, utente):
    st.subheader("Modifica cliente")

    tipo = c.get("tipo", "fisica")
    st.markdown(
        f"<span style='background:#eaeaf0;color:#1a1a2e;font-size:11px;"
        f"font-weight:600;padding:3px 10px;border-radius:4px;'>"
        f"{'Persona giuridica' if tipo == 'giuridica' else 'Persona fisica'}</span>",
        unsafe_allow_html=True
    )
    st.caption("Il tipo cliente non può essere modificato dopo la creazione.")
    st.markdown("---")

    with st.form(f"form_edit_{c['id']}"):
        dati = _form_campi(tipo=tipo, d=c, key_prefix=f"edit_{c['id']}")
        col1, col2 = st.columns(2)
        with col1:
            salva = st.form_submit_button("Salva", use_container_width=True)
        with col2:
            annulla = st.form_submit_button("Annulla", use_container_width=True)

    if salva:
        dati["tipo"] = tipo
        aggiorna_cliente(c["id"], dati)
        st.session_state[f"edit_{c['id']}"] = False
        st.success("Cliente aggiornato.")
        st.rerun()
    if annulla:
        st.session_state[f"edit_{c['id']}"] = False
        st.rerun()


def _form_campi(tipo, d, key_prefix):
    risultato = {}

    if tipo == "giuridica":
        st.markdown("**Dati aziendali**")
        col1, col2 = st.columns(2)
        with col1:
            risultato["ragione_sociale"] = st.text_input(
                "Ragione sociale *",
                value=d.get("ragione_sociale", ""),
                key=f"{key_prefix}_rs"
            )
            risultato["codice_idi"] = st.text_input(
                "Codice IDI",
                value=d.get("codice_idi", ""),
                placeholder="CHE-000.000.000",
                key=f"{key_prefix}_idi"
            )
            risultato["sito_web"] = st.text_input(
                "Sito web",
                value=d.get("sito_web", ""),
                placeholder="https://www.esempio.ch",
                key=f"{key_prefix}_web"
            )
        with col2:
            idx_fg = FORME_GIURIDICHE.index(d.get("forma_giuridica", "SA")) \
                if d.get("forma_giuridica") in FORME_GIURIDICHE else 0
            risultato["forma_giuridica"] = st.selectbox(
                "Forma giuridica",
                FORME_GIURIDICHE,
                index=idx_fg,
                key=f"{key_prefix}_fg"
            )
            idx_sett = SETTORI.index(d.get("settore", "Altro")) \
                if d.get("settore") in SETTORI else len(SETTORI) - 1
            risultato["settore"] = st.selectbox(
                "Settore",
                SETTORI,
                index=idx_sett,
                key=f"{key_prefix}_sett"
            )

        st.markdown("---")
        st.markdown("**Referente principale**")
        col1, col2 = st.columns(2)
        with col1:
            risultato["contatto_nome"] = st.text_input(
                "Nome referente",
                value=d.get("contatto_nome", ""),
                key=f"{key_prefix}_cnome"
            )
            risultato["contatto_email"] = st.text_input(
                "Email referente",
                value=d.get("contatto_email", ""),
                key=f"{key_prefix}_cemail"
            )
        with col2:
            risultato["contatto_cognome"] = st.text_input(
                "Cognome referente",
                value=d.get("contatto_cognome", ""),
                key=f"{key_prefix}_ccogn"
            )
            risultato["contatto_telefono"] = st.text_input(
                "Telefono referente",
                value=d.get("contatto_telefono", ""),
                key=f"{key_prefix}_ctel"
            )
        risultato["contatto_ruolo"] = st.text_input(
            "Ruolo referente",
            value=d.get("contatto_ruolo", ""),
            placeholder="es. Direttore, Responsabile acquisti...",
            key=f"{key_prefix}_cruolo"
        )

    else:
        st.markdown("**Dati personali**")
        col1, col2 = st.columns(2)
        with col1:
            risultato["nome"] = st.text_input(
                "Nome *",
                value=d.get("nome", ""),
                key=f"{key_prefix}_nome"
            )
        with col2:
            risultato["cognome"] = st.text_input(
                "Cognome *",
                value=d.get("cognome", ""),
                key=f"{key_prefix}_cognome"
            )
        risultato["data_nascita"] = st.text_input(
            "Data di nascita (DD/MM/YYYY)",
            value=d.get("data_nascita", ""),
            placeholder="01/01/1980",
            key=f"{key_prefix}_dn"
        )

    st.markdown("---")
    st.markdown("**Recapiti**")
    col1, col2 = st.columns(2)
    with col1:
        risultato["email"] = st.text_input(
            "Email",
            value=d.get("email", ""),
            key=f"{key_prefix}_email"
        )
        risultato["indirizzo"] = st.text_input(
            "Indirizzo",
            value=d.get("indirizzo", ""),
            key=f"{key_prefix}_ind"
        )
        risultato["cap"] = st.text_input(
            "CAP",
            value=d.get("cap", ""),
            key=f"{key_prefix}_cap"
        )
    with col2:
        risultato["telefono"] = st.text_input(
            "Telefono",
            value=d.get("telefono", ""),
            key=f"{key_prefix}_tel"
        )
        risultato["citta"] = st.text_input(
            "Citta",
            value=d.get("citta", ""),
            key=f"{key_prefix}_citta"
        )
        idx_paese = PAESI.index(d.get("paese", "Svizzera")) \
            if d.get("paese") in PAESI else PAESI.index("Svizzera")
        risultato["paese"] = st.selectbox(
            "Paese",
            PAESI,
            index=idx_paese,
            key=f"{key_prefix}_paese"
        )

    st.markdown("---")
    risultato["stato"] = st.selectbox(
        "Stato cliente",
        STATI,
        index=STATI.index(d.get("stato", "prospect"))
        if d.get("stato") in STATI else 0,
        key=f"{key_prefix}_stato"
    )
    risultato["note"] = st.text_area(
        "Note",
        value=d.get("note", ""),
        key=f"{key_prefix}_note"
    )

    utenti = lista_utenti()
    if utenti:
        opzioni = {f"{u['nome']} {u['cognome']}": u["id"] for u in utenti}
        default_idx = 0
        if d.get("assegnato_a"):
            ids = list(opzioni.values())
            if d["assegnato_a"] in ids:
                default_idx = ids.index(d["assegnato_a"])
        sel = st.selectbox(
            "Assegnato a",
            list(opzioni.keys()),
            index=default_idx,
            key=f"{key_prefix}_ass"
        )
        risultato["assegnato_a"] = opzioni[sel]

    return risultato
