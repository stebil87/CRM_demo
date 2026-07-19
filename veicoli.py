import streamlit as st
from datetime import datetime
from db import get_sb, lista_clienti
from auth import can_edit


# ── accesso dati ────────────────────────────────────────────────────────────

def lista_veicoli(cliente_id=None, ricerca=""):
    sb = get_sb()
    try:
        q = sb.table("veicoli").select(
            "*, clienti(id, nome, cognome, ragione_sociale, tipo)"
        ).order("created_at", desc=True)
        if cliente_id:
            q = q.eq("cliente_id", cliente_id)
        res = q.execute()
        veicoli = res.data or []
    except Exception:
        return []
    if ricerca:
        r = ricerca.replace(" ", "").lower()
        def match(v):
            targa = (v.get("targa") or "").replace(" ", "").lower()
            testo = " ".join([
                v.get("marca") or "", v.get("modello") or "",
                _nome_cliente(v),
            ]).lower()
            return r in targa or ricerca.lower() in testo
        veicoli = [v for v in veicoli if match(v)]
    return veicoli


def crea_veicolo(dati, user_id):
    sb = get_sb()
    try:
        dati["created_by"] = user_id
        sb.table("veicoli").insert(dati).execute()
        return None
    except Exception as e:
        return str(e)


def aggiorna_veicolo(veicolo_id, dati):
    sb = get_sb()
    try:
        sb.table("veicoli").update(dati).eq("id", veicolo_id).execute()
        return None
    except Exception as e:
        return str(e)


def _nome_cliente(v):
    c = v.get("clienti") or {}
    if c.get("tipo") == "giuridica":
        return c.get("ragione_sociale") or "—"
    return f"{c.get('nome','')} {c.get('cognome','')}".strip() or "—"


def _opzioni_clienti():
    """[(id, etichetta)] per il menu a tendina."""
    out = []
    for c in (lista_clienti() or []):
        if c.get("tipo") == "giuridica":
            nome = c.get("ragione_sociale") or "—"
        else:
            nome = f"{c.get('nome','')} {c.get('cognome','')}".strip() or "—"
        out.append((c["id"], nome))
    return sorted(out, key=lambda x: x[1].lower())


# ── pagina ──────────────────────────────────────────────────────────────────

def pagina_veicoli(utente):
    st.title("🚗 Veicoli")
    st.markdown("---")

    tab_lista, tab_nuovo = st.tabs(["Parco veicoli", "➕ Nuovo veicolo"])

    with tab_lista:
        col_r, col_f = st.columns([3, 2])
        with col_r:
            ricerca = st.text_input(
                "Cerca", placeholder="Targa, marca, modello o cliente...",
                label_visibility="collapsed",
            )
        with col_f:
            opzioni = [("", "Tutti i clienti")] + _opzioni_clienti()
            pre = st.session_state.get("cliente_id")
            idx = next((i for i, o in enumerate(opzioni) if o[0] == pre), 0)
            scelta = st.selectbox(
                "Cliente", opzioni, index=idx, format_func=lambda x: x[1],
                label_visibility="collapsed",
            )
        veicoli = lista_veicoli(
            cliente_id=scelta[0] or None, ricerca=ricerca.strip()
        )
        if not veicoli:
            st.info("Nessun veicolo trovato. Aggiungine uno dalla tab «Nuovo veicolo».")
        for v in veicoli:
            _scheda_veicolo(v, utente)

    with tab_nuovo:
        _form_nuovo(utente)


def _scheda_veicolo(v, utente):
    targa = v.get("targa") or "senza targa"
    titolo = f"{targa}  ·  {v.get('marca','')} {v.get('modello','')}  ·  {_nome_cliente(v)}"
    with st.expander(titolo):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Targa:** {v.get('targa') or '—'}")
            st.markdown(f"**Marca / modello:** {v.get('marca') or '—'} {v.get('modello') or ''}")
            st.markdown(f"**Anno:** {v.get('anno') or '—'}")
            st.markdown(f"**Colore:** {v.get('colore') or '—'}")
        with col2:
            st.markdown(f"**Cliente:** {_nome_cliente(v)}")
            st.markdown(f"**Telaio:** {v.get('telaio') or '—'}")
            st.markdown(f"**Km:** {v.get('km') or '—'}")
            st.markdown(f"**Note:** {v.get('note') or '—'}")

        if can_edit(utente):
            if st.button("✏️ Modifica", key=f"vmod_{v['id']}"):
                st.session_state[f"vedit_{v['id']}"] = True
        if st.session_state.get(f"vedit_{v['id']}"):
            _form_modifica(v)


def _campi_veicolo(v=None):
    v = v or {}
    col1, col2 = st.columns(2)
    with col1:
        targa = st.text_input("Targa", value=v.get("targa") or "", placeholder="TI 123456")
        marca = st.text_input("Marca", value=v.get("marca") or "", placeholder="VW")
        modello = st.text_input("Modello", value=v.get("modello") or "", placeholder="Golf 1.5 TSI")
        anno = st.number_input(
            "Anno", min_value=1950, max_value=datetime.now().year + 1,
            value=v.get("anno") or datetime.now().year,
        )
    with col2:
        colore = st.text_input("Colore", value=v.get("colore") or "")
        telaio = st.text_input("Telaio (VIN)", value=v.get("telaio") or "")
        km = st.number_input("Chilometri", min_value=0, max_value=2_000_000,
                             value=v.get("km") or 0, step=1000)
        note = st.text_input("Note", value=v.get("note") or "")
    return {
        "targa": targa.strip().upper() or None,
        "marca": marca.strip() or None,
        "modello": modello.strip() or None,
        "anno": int(anno),
        "colore": colore.strip() or None,
        "telaio": telaio.strip() or None,
        "km": int(km),
        "note": note.strip() or None,
    }


def _form_nuovo(utente):
    if not can_edit(utente):
        st.warning("Non hai i permessi per aggiungere veicoli.")
        return
    opzioni = _opzioni_clienti()
    if not opzioni:
        st.info("Prima serve almeno un cliente in anagrafica.")
        return
    with st.form("form_nuovo_veicolo"):
        scelta = st.selectbox("Cliente *", opzioni, format_func=lambda x: x[1])
        dati = _campi_veicolo()
        ok = st.form_submit_button("Salva veicolo", use_container_width=True)
    if ok:
        if not dati["targa"] and not dati["telaio"]:
            st.error("Serve almeno la targa (o il telaio).")
            return
        dati["cliente_id"] = scelta[0]
        err = crea_veicolo(dati, utente["id"])
        if err:
            st.error("Veicolo non salvato.")
            st.caption(f"Dettaglio tecnico: {err}")
        else:
            st.success("Veicolo aggiunto!")
            st.rerun()


def _form_modifica(v):
    st.markdown("---")
    with st.form(f"form_edit_veicolo_{v['id']}"):
        dati = _campi_veicolo(v)
        col1, col2 = st.columns(2)
        salva = col1.form_submit_button("💾 Salva", use_container_width=True)
        annulla = col2.form_submit_button("Annulla", use_container_width=True)
    if salva:
        err = aggiorna_veicolo(v["id"], dati)
        if err:
            st.error("Modifica non salvata.")
            st.caption(f"Dettaglio tecnico: {err}")
        else:
            st.session_state[f"vedit_{v['id']}"] = False
            st.rerun()
    if annulla:
        st.session_state[f"vedit_{v['id']}"] = False
        st.rerun()
