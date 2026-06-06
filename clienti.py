import streamlit as st
from db import lista_clienti, get_cliente, crea_cliente, aggiorna_cliente, elimina_cliente, lista_utenti
from auth import can_edit, is_admin

STATI = ["prospect", "attivo", "inattivo", "perso"]
PAESI = ["Italia", "Svizzera", "Germania", "Francia", "Austria", "Altro"]
SETTORI = ["Consulenza", "Tecnologia", "Commercio", "Industria", "Servizi", "Sanità", "Altro"]

def nome_display(c):
    if c["tipo"] == "giuridica":
        return c.get("ragione_sociale") or "—"
    return f"{c.get('nome','')} {c.get('cognome','')}".strip() or "—"

def pagina_clienti(utente):
    st.title("👥 Clienti")

    tab_lista, tab_nuovo = st.tabs(["Lista clienti", "➕ Nuovo cliente"])

    with tab_lista:
        col1, col2 = st.columns([3, 1])
        with col1:
            cerca = st.text_input("🔍 Cerca per nome, email...", key="cerca_clienti")
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
                with st.expander(f"{'🏢' if c['tipo']=='giuridica' else '👤'} {nome_display(c)} — {c.get('stato','').upper()}"):
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
            st.markdown(f"**P.IVA:** {c.get('partita_iva','—')}")
            st.markdown(f"**Settore:** {c.get('settore','—')}")
        else:
            st.markdown(f"**Nome:** {c.get('nome','')} {c.get('cognome','')}")
            st.markdown(f"**C.F.:** {c.get('codice_fiscale','—')}")
            st.markdown(f"**Nato il:** {c.get('data_nascita','—')}")
        st.markdown(f"**Email:** {c.get('email','—')}")
        st.markdown(f"**Telefono:** {c.get('telefono','—')}")
    with col2:
        st.markdown(f"**Indirizzo:** {c.get('indirizzo','—')}, {c.get('citta','—')}")
        if c["tipo"] == "giuridica":
            st.markdown(f"**Referente:** {c.get('contatto_nome','')} {c.get('contatto_cognome','')} ({c.get('contatto_ruolo','—')})")
            st.markdown(f"**Email referente:** {c.get('contatto_email','—')}")
            st.markdown(f"**Tel referente:** {c.get('contatto_telefono','—')}")
        st.markdown(f"**Note:** {c.get('note','—')}")

    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        if st.button("✏️ Modifica", key=f"mod_{c['id']}", disabled=not can_edit(utente)):
            st.session_state[f"edit_{c['id']}"] = True
    with col_b:
        if st.button("📔 Diario", key=f"dir_{c['id']}"):
            st.session_state.pagina = "diario"
            st.session_state.cliente_id = c["id"]
            st.session_state.cliente_nome = nome_display(c)
            st.rerun()
    with col_c:
        if st.button("📄 Offerte", key=f"off_{c['id']}"):
            st.session_state.pagina = "offerte"
            st.session_state.cliente_id = c["id"]
            st.session_state.cliente_nome = nome_display(c)
            st.rerun()
    with col_d:
        if st.button("📁 Documenti", key=f"doc_{c['id']}"):
            st.session_state.pagina = "documenti"
            st.session_state.cliente_id = c["id"]
            st.session_state.cliente_nome = nome_display(c)
            st.rerun()

    # Form modifica inline
    if st.session_state.get(f"edit_{c['id']}"):
        st.markdown("---")
        _form_modifica_cliente(c, utente)

def _form_cliente(dati_default=None, key_prefix="new"):
    d = dati_default or {}
    tipo = st.radio("Tipo cliente", ["fisica", "giuridica"],
                    index=0 if d.get("tipo","fisica") == "fisica" else 1,
                    key=f"{key_prefix}_tipo",
                    horizontal=True)
    st.markdown("---")
    risultato = {"tipo": tipo}

    if tipo == "giuridica":
        col1, col2 = st.columns(2)
        with col1:
            risultato["ragione_sociale"] = st.text_input("Ragione sociale *", value=d.get("ragione_sociale",""), key=f"{key_prefix}_rs")
            risultato["partita_iva"] = st.text_input("Partita IVA", value=d.get("partita_iva",""), key=f"{key_prefix}_piva")
        with col2:
            risultato["settore"] = st.selectbox("Settore", SETTORI, index=SETTORI.index(d.get("settore","Altro")) if d.get("settore") in SETTORI else len(SETTORI)-1, key=f"{key_prefix}_sett")
        st.markdown("**Persona di contatto**")
        col1, col2 = st.columns(2)
        with col1:
            risultato["contatto_nome"] = st.text_input("Nome referente", value=d.get("contatto_nome",""), key=f"{key_prefix}_cnome")
            risultato["contatto_email"] = st.text_input("Email referente", value=d.get("contatto_email",""), key=f"{key_prefix}_cemail")
        with col2:
            risultato["contatto_cognome"] = st.text_input("Cognome referente", value=d.get("contatto_cognome",""), key=f"{key_prefix}_ccogn")
            risultato["contatto_telefono"] = st.text_input("Tel referente", value=d.get("contatto_telefono",""), key=f"{key_prefix}_ctel")
        risultato["contatto_ruolo"] = st.text_input("Ruolo referente", value=d.get("contatto_ruolo",""), key=f"{key_prefix}_cruolo")
    else:
        col1, col2 = st.columns(2)
        with col1:
            risultato["nome"] = st.text_input("Nome *", value=d.get("nome",""), key=f"{key_prefix}_nome")
            risultato["codice_fiscale"] = st.text_input("Codice fiscale", value=d.get("codice_fiscale",""), key=f"{key_prefix}_cf")
        with col2:
            risultato["cognome"] = st.text_input("Cognome *", value=d.get("cognome",""), key=f"{key_prefix}_cognome")
            risultato["data_nascita"] = str(st.date_input("Data nascita", value=None, key=f"{key_prefix}_dn"))

    st.markdown("**Recapiti**")
    col1, col2 = st.columns(2)
    with col1:
        risultato["email"] = st.text_input("Email", value=d.get("email",""), key=f"{key_prefix}_email")
        risultato["indirizzo"] = st.text_input("Indirizzo", value=d.get("indirizzo",""), key=f"{key_prefix}_ind")
        risultato["cap"] = st.text_input("CAP", value=d.get("cap",""), key=f"{key_prefix}_cap")
    with col2:
        risultato["telefono"] = st.text_input("Telefono", value=d.get("telefono",""), key=f"{key_prefix}_tel")
        risultato["citta"] = st.text_input("Città", value=d.get("citta",""), key=f"{key_prefix}_citta")
        risultato["paese"] = st.selectbox("Paese", PAESI, index=PAESI.index(d.get("paese","Italia")) if d.get("paese") in PAESI else 0, key=f"{key_prefix}_paese")

    risultato["stato"] = st.selectbox("Stato cliente", STATI, index=STATI.index(d.get("stato","prospect")) if d.get("stato") in STATI else 0, key=f"{key_prefix}_stato")
    risultato["note"] = st.text_area("Note", value=d.get("note",""), key=f"{key_prefix}_note")

    utenti = lista_utenti()
    if utenti:
        opzioni = {f"{u['nome']} {u['cognome']}": u["id"] for u in utenti}
        default_idx = 0
        if d.get("assegnato_a"):
            ids = list(opzioni.values())
            if d["assegnato_a"] in ids:
                default_idx = ids.index(d["assegnato_a"])
        sel = st.selectbox("Assegnato a", list(opzioni.keys()), index=default_idx, key=f"{key_prefix}_ass")
        risultato["assegnato_a"] = opzioni[sel]

    return risultato

def _form_nuovo_cliente(utente):
    st.subheader("Nuovo cliente")
    with st.form("form_nuovo_cliente"):
        dati = _form_cliente(key_prefix="new")
        submitted = st.form_submit_button("Crea cliente", use_container_width=True)
    if submitted:
        errori = []
        if dati["tipo"] == "giuridica" and not dati.get("ragione_sociale"):
            errori.append("Ragione sociale")
        if dati["tipo"] == "fisica" and not dati.get("nome"):
            errori.append("Nome")
        if dati["tipo"] == "fisica" and not dati.get("cognome"):
            errori.append("Cognome")
        if errori:
            st.error(f"Campi obbligatori: {', '.join(errori)}")
        else:
            crea_cliente(dati, utente["id"])
            st.success("Cliente creato!")
            st.rerun()

def _form_modifica_cliente(c, utente):
    st.subheader("Modifica cliente")
    with st.form(f"form_edit_{c['id']}"):
        dati = _form_cliente(dati_default=c, key_prefix=f"edit_{c['id']}")
        col1, col2 = st.columns(2)
        with col1:
            salva = st.form_submit_button("💾 Salva", use_container_width=True)
        with col2:
            annulla = st.form_submit_button("Annulla", use_container_width=True)
    if salva:
        aggiorna_cliente(c["id"], dati)
        st.session_state[f"edit_{c['id']}"] = False
        st.success("Cliente aggiornato!")
        st.rerun()
    if annulla:
        st.session_state[f"edit_{c['id']}"] = False
        st.rerun()