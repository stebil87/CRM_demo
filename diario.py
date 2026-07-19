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
                        col1, col2, col3 = st.columns([2, 2, 2])
                        with col1:
                            if st.button("✏️ Modifica", key=f"em_{v['id']}"):
                                st.session_state[f"edit_diario_{v['id']}"] = True
                        with col2:
                            if v.get("followup_data") and not v.get("followup_fatto"):
                                if st.button("✓ Follow-up fatto", key=f"fuf_{v['id']}"):
                                    aggiorna_voce_diario(v["id"], {"followup_fatto": True})
                                    st.rerun()
                        with col3:
                            _bottone_scarica_allegati(v, cliente_id)

                    if st.session_state.get(f"edit_diario_{v['id']}"):
                        _form_modifica_voce(v, utente)

def _bottone_scarica_allegati(v, cliente_id):
    """Se la voce arriva dal sito, offre lo zip dei documenti
    caricati dal cliente col modulo online."""
    if not str(v.get("titolo", "")).startswith("[Sito]"):
        return
    docs = [d for d in (lista_documenti(cliente_id) or [])
            if str(d.get("note", "")).startswith("Richiesta dal sito")]
    if not docs:
        return
    if st.button(f"📎 Scarica allegati ({len(docs)})", key=f"za_{v['id']}"):
        import io, zipfile
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for d in docs:
                dati = scarica_documento(d["storage_path"])
                if dati:
                    z.writestr(d["nome_file"], dati)
        st.session_state[f"zip_{v['id']}"] = buf.getvalue()
    if st.session_state.get(f"zip_{v['id']}"):
        st.download_button(
            "⬇️ Scarica ZIP",
            data=st.session_state[f"zip_{v['id']}"],
            file_name="allegati_richiesta_sito.zip",
            mime="application/zip",
            key=f"zdl_{v['id']}",
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

def _form_modifica_voce(v, utente):
    st.markdown("---")
    with st.form(f"form_edit_voce_{v['id']}"):
        col1, col2 = st.columns(2)
        with col1:
            tipo = st.selectbox("Tipo", TIPI, index=TIPI.index(v["tipo"]) if v["tipo"] in TIPI else 0)
            titolo = st.text_input("Titolo *", value=v["titolo"])
        with col2:
            data_contatto = st.date_input("Data", value=date.fromisoformat(v["data_contatto"][:10]))
            fu_val = date.fromisoformat(v["followup_data"]) if v.get("followup_data") else None
            followup_data = st.date_input("Follow-up", value=fu_val)
        contenuto = st.text_area("Dettaglio", value=v.get("contenuto",""), height=120)
        followup_fatto = st.checkbox("Follow-up completato", value=v.get("followup_fatto", False))
        col1, col2 = st.columns(2)
        with col1:
            salva = st.form_submit_button("💾 Salva", use_container_width=True)
        with col2:
            annulla = st.form_submit_button("Annulla", use_container_width=True)
    if salva:
        aggiorna_voce_diario(v["id"], {
            "tipo": tipo, "titolo": titolo, "contenuto": contenuto,
            "data_contatto": data_contatto.isoformat(),
            "followup_data": followup_data.isoformat() if followup_data else None,
            "followup_fatto": followup_fatto,
        })
        st.session_state[f"edit_diario_{v['id']}"] = False
        st.rerun()
    if annulla:
        st.session_state[f"edit_diario_{v['id']}"] = False
        st.rerun()
