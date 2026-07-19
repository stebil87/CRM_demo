import streamlit as st
from db import get_sb
from auth import can_edit
from veicoli import _opzioni_clienti

STAGIONI = ["invernali", "estive", "4stagioni"]
ICONE_STAG = {"invernali": "❄️", "estive": "☀️", "4stagioni": "🍂"}


# ── accesso dati ────────────────────────────────────────────────────────────

def lista_gomme(stato="in deposito"):
    sb = get_sb()
    try:
        q = sb.table("deposito_gomme").select(
            "*, clienti(nome, cognome, ragione_sociale, tipo), veicoli(targa, marca, modello)"
        ).order("created_at", desc=True)
        if stato:
            q = q.eq("stato", stato)
        res = q.execute()
        return res.data or []
    except Exception:
        return []


def crea_set_gomme(dati):
    sb = get_sb()
    try:
        sb.table("deposito_gomme").insert(dati).execute()
        return None
    except Exception as e:
        return str(e)


def cambia_stato_gomme(set_id, stato):
    sb = get_sb()
    try:
        from datetime import datetime, timezone
        sb.table("deposito_gomme").update({
            "stato": stato,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", set_id).execute()
        return None
    except Exception as e:
        return str(e)


def _nome_cliente(g):
    c = g.get("clienti") or {}
    if c.get("tipo") == "giuridica":
        return c.get("ragione_sociale") or "—"
    return f"{c.get('nome','')} {c.get('cognome','')}".strip() or "—"


def _veicolo_txt(g):
    v = g.get("veicoli") or {}
    if not v:
        return "—"
    return f"{v.get('targa') or ''} {v.get('marca') or ''} {v.get('modello') or ''}".strip() or "—"


def _veicoli_del_cliente(cliente_id):
    sb = get_sb()
    try:
        res = sb.table("veicoli").select("id, targa, marca, modello").eq(
            "cliente_id", cliente_id
        ).execute()
        return res.data or []
    except Exception:
        return []


# ── pagina ──────────────────────────────────────────────────────────────────

def pagina_gomme(utente):
    st.title("🛞 Deposito gomme")
    st.markdown("---")

    tab_dep, tab_nuovo, tab_storico = st.tabs(
        ["In deposito", "➕ Nuovo set", "Storico"]
    )

    with tab_dep:
        gomme = lista_gomme("in deposito")
        if not gomme:
            st.info("Nessun set in deposito al momento.")
        else:
            st.markdown(f"**{len(gomme)} set in deposito**")
            for g in gomme:
                _scheda_set(g, utente, attivo=True)

    with tab_nuovo:
        _form_nuovo_set(utente)

    with tab_storico:
        finiti = lista_gomme("riconsegnate") + lista_gomme("smaltite")
        if not finiti:
            st.info("Storico vuoto.")
        for g in finiti:
            _scheda_set(g, utente, attivo=False)


def _scheda_set(g, utente, attivo):
    icona = ICONE_STAG.get(g.get("stagione"), "🛞")
    titolo = (
        f"{icona} {_nome_cliente(g)}  ·  {_veicolo_txt(g)}  ·  "
        f"{g.get('quantita', 4)}× {g.get('misura') or '—'}"
        + ("" if attivo else f"  ·  {g.get('stato','')}")
    )
    with st.expander(titolo):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Cliente:** {_nome_cliente(g)}")
            st.markdown(f"**Veicolo:** {_veicolo_txt(g)}")
            st.markdown(f"**Stagione:** {g.get('stagione') or '—'}")
            st.markdown(f"**Quantità:** {g.get('quantita') or '—'}")
        with col2:
            st.markdown(f"**Misura:** {g.get('misura') or '—'}")
            st.markdown(f"**Marca:** {g.get('marca') or '—'}")
            st.markdown(f"**DOT:** {g.get('dot') or '—'}")
            st.markdown(f"**Posizione:** {g.get('posizione') or '—'}")
        if g.get("note"):
            st.markdown(f"**Note:** {g['note']}")

        if attivo and can_edit(utente):
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("↩️ Riconsegnate al cliente", key=f"gr_{g['id']}",
                             use_container_width=True):
                    err = cambia_stato_gomme(g["id"], "riconsegnate")
                    if err:
                        st.error("Operazione non riuscita.")
                    else:
                        st.rerun()
            with col_b:
                if st.button("🗑️ Smaltite", key=f"gs_{g['id']}",
                             use_container_width=True):
                    err = cambia_stato_gomme(g["id"], "smaltite")
                    if err:
                        st.error("Operazione non riuscita.")
                    else:
                        st.rerun()


def _form_nuovo_set(utente):
    if not can_edit(utente):
        st.warning("Non hai i permessi per registrare set di gomme.")
        return
    opzioni = _opzioni_clienti()
    if not opzioni:
        st.info("Prima serve almeno un cliente in anagrafica.")
        return

    scelta = st.selectbox("Cliente *", opzioni, format_func=lambda x: x[1],
                          key="gomme_cliente")
    veicoli = _veicoli_del_cliente(scelta[0])
    opz_veicoli = [("", "Nessun veicolo specifico")] + [
        (v["id"], f"{v.get('targa') or ''} {v.get('marca') or ''} {v.get('modello') or ''}".strip())
        for v in veicoli
    ]

    with st.form("form_nuovo_set_gomme"):
        veic = st.selectbox("Veicolo", opz_veicoli, format_func=lambda x: x[1])
        col1, col2 = st.columns(2)
        with col1:
            stagione = st.selectbox("Stagione *", STAGIONI)
            quantita = st.number_input("Quantità", 1, 8, 4)
            misura = st.text_input("Misura", placeholder="205/55 R16")
        with col2:
            marca = st.text_input("Marca gomme", placeholder="Michelin")
            dot = st.text_input("DOT", placeholder="2325")
            posizione = st.text_input("Posizione in magazzino *", placeholder="Scaffale B3")
        note = st.text_input("Note")
        ok = st.form_submit_button("Registra il set", use_container_width=True)

    if ok:
        if not posizione.strip():
            st.error("La posizione in magazzino è obbligatoria: ritrovarle poi è il punto!")
            return
        err = crea_set_gomme({
            "cliente_id": scelta[0],
            "veicolo_id": veic[0] or None,
            "stagione": stagione,
            "quantita": int(quantita),
            "misura": misura.strip() or None,
            "marca": marca.strip() or None,
            "dot": dot.strip() or None,
            "posizione": posizione.strip(),
            "note": note.strip() or None,
        })
        if err:
            st.error("Set non registrato.")
            st.caption(f"Dettaglio tecnico: {err}")
        else:
            st.success("Set registrato in deposito!")
            st.rerun()
