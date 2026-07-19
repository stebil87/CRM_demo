import streamlit as st
from datetime import date
from db import lista_diario, crea_voce_diario, aggiorna_voce_diario, lista_documenti, scarica_documento
from auth import can_edit

TIPI = ["email", "telefono", "riunione", "nota", "followup", "accordo", "altro"]
ICONE = {"email": "📧", "telefono": "📞", "riunione": "🤝", "nota": "📝",
         "followup": "🔔", "accordo": "✅", "altro": "💬"}

def pagina_diario(utente, cliente_id, cliente_nome):
    col1, col2 = st.columns([1, 8])
    with col1:
        if st.button("← Indietro"):
            st.session_state.pagina = "clienti"
            st.rerun()
    st.title(f"📔 Diario — {cliente_nome}")
    st.markdown("---")

    tab_log, tab_nuovo = st.tabs(["Storico", "➕ Nuova voce"])

    with tab_nuovo:
        if not can_edit(utente):
            st.warning("Non hai i permessi per aggiungere voci.")
        else:
            _form_nuova_voce(utente, cliente_id)

    with tab_log:
        voci = lista_diario(cliente_id)
        if not voci:
            st.info("Nessuna voce nel diario. Inizia aggiungendo un'attività.")
        else:
            # Filtro tipo
            tipi_presenti = list({v["tipo"] for v in voci})
            filtro = st.multiselect("Filtra per tipo", TIPI,
                                     default=tipi_presenti, key="filtro_diario")
            voci_filtrate = [v for v in voci if v["tipo"] in filtro]

            for v in voci_filtrate:
                icona = ICONE.get(v["tipo"], "💬")
                autore = v.get("utenti") or {}
                autore_str = f"{autore.get('nome','')} {autore.get('cognome','')}".strip() or "—"
                data_str = (v.get("data_contatto") or "")[:10]
                label = f"{icona} **{v['titolo']}** — {data_str} ({autore_str})"
                if v.get("followup_data") and not v.get("followup_fatto"):
                    label += f" 🔔 follow-up: {v['followup_data']}"

                with st.expander(label):
                    st.markdown(v.get("contenuto") or "_nessun dettaglio_")
                    if v.get("followup_data"):
                        stato_fu = "✅ Fatto" if v.get("followup_fatto") else f"⏳ Previsto: {v['followup_data']}"
                        st.caption(f"Follow-up: {stato_fu}")

                    if can_edit(utente):
                        col1, col2 = st.columns([2, 2])
                        with col1:
                            if v.get("followup_data") and not v.get("followup_fatto"):
                                if st.button("✓ Follow-up fatto", key=f"fuf_{v['id']}"):
                                    aggiorna_voce_diario(v["id"], {"followup_fatto": True})
                                    st.rerun()
                        with col2:
                            _bottone_scarica_allegati(v, cliente_id, cliente_nome)

                    _sezione_note(v, utente)

def _sezione_note(v, utente):
    """Note/commenti sotto la voce: si aggiungono, non si toccano.
    Il messaggio originale resta immutabile."""
    import html as _html
    from db import get_sb
    sb = get_sb()
    try:
        res = sb.table("diario_commenti").select(
            "*, utenti(nome, cognome)"
        ).eq("voce_id", v["id"]).order("created_at").execute()
        note = res.data or []
    except Exception:
        note = []
    for n in note:
        a = n.get("utenti") or {}
        autore = f"{a.get('nome','')} {a.get('cognome','')}".strip() or "—"
        data = (n.get("created_at") or "")[:16].replace("T", " ")
        st.markdown(
            "<div style='background:#f7f7f9;border-left:3px solid #b9bdc9;"
            "border-radius:6px;padding:8px 12px;margin:6px 0;font-size:13px;'>"
            f"<span style='color:#888;font-size:11px;'>{_html.escape(autore)} — {data}</span><br>"
            f"{_html.escape(n.get('contenuto','')).replace(chr(10), '<br>')}</div>",
            unsafe_allow_html=True,
        )
    if can_edit(utente):
        with st.form(f"nota_{v['id']}", clear_on_submit=True):
            testo = st.text_area(
                "Aggiungi una nota", height=80,
                placeholder="Es. richiamato il cliente, appuntamento fissato...",
                label_visibility="collapsed",
            )
            invia = st.form_submit_button("💬 Aggiungi nota")
        if invia and testo.strip():
            try:
                sb.table("diario_commenti").insert({
                    "voce_id": v["id"],
                    "contenuto": testo.strip(),
                    "created_by": utente["id"],
                }).execute()
                st.rerun()
            except Exception:
                st.error("Nota non salvata: riprova.")


@st.cache_data(ttl=600, show_spinner=False)
def _zip_allegati_sito(cliente_id, firma_docs):
    """Prepara (e tiene in cache) lo zip dei documenti caricati
    dal cliente tramite il modulo del sito. firma_docs serve solo
    a invalidare la cache quando arrivano documenti nuovi."""
    import io, zipfile
    docs = [d for d in (lista_documenti(cliente_id) or [])
            if str(d.get("note", "")).startswith("Richiesta dal sito")]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for d in docs:
            dati = scarica_documento(d["storage_path"])
            if dati:
                z.writestr(d["nome_file"], dati)
    return buf.getvalue()


def _bottone_scarica_allegati(v, cliente_id, cliente_nome=""):
    """Sulle voci arrivate dal sito: download diretto, un solo click."""
    if not str(v.get("titolo", "")).startswith("[Sito]"):
        return
    docs = [d for d in (lista_documenti(cliente_id) or [])
            if str(d.get("note", "")).startswith("Richiesta dal sito")]
    if not docs:
        return
    firma = tuple(sorted(str(d.get("id", d.get("storage_path", ""))) for d in docs))
    dati_zip = _zip_allegati_sito(cliente_id, firma)
    import re as _re
    slug = _re.sub(r"[^A-Za-z0-9]+", "_", (cliente_nome or "cliente")).strip("_") or "cliente"
    st.download_button(
        f"📎 Scarica allegati ({len(docs)})",
        data=dati_zip,
        file_name=f"allegati_{slug}.zip",
        mime="application/zip",
        key=f"za_{v['id']}",
    )


def _form_nuova_voce(utente, cliente_id):
    st.subheader("Nuova voce")
    with st.form("form_nuova_voce"):
        col1, col2 = st.columns(2)
        with col1:
            tipo = st.selectbox("Tipo", TIPI)
            titolo = st.text_input("Titolo *")
        with col2:
            data_contatto = st.date_input("Data contatto", value=date.today())
            followup_data = st.date_input("Data follow-up (opzionale)", value=None)
        contenuto = st.text_area("Dettaglio / Note", height=150)
        submitted = st.form_submit_button("Aggiungi", use_container_width=True)
    if submitted:
        if not titolo:
            st.error("Il titolo è obbligatorio.")
        else:
            crea_voce_diario({
                "cliente_id": cliente_id,
                "tipo": tipo,
                "titolo": titolo,
                "contenuto": contenuto,
                "data_contatto": data_contatto.isoformat(),
                "followup_data": followup_data.isoformat() if followup_data else None,
            }, utente["id"])
            st.success("Voce aggiunta!")
            st.rerun()
