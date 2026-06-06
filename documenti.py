import streamlit as st
from db import lista_documenti, carica_documento, scarica_documento, elimina_documento
from auth import can_edit

CATEGORIE = ["contratto", "offerta", "identita", "fiscale", "altro"]
ICONE_CAT = {"contratto": "📜", "offerta": "💼", "identita": "🪪", "fiscale": "🧾", "altro": "📎"}
MAX_SIZE_MB = 20

def pagina_documenti(utente, cliente_id, cliente_nome):
    col1, col2 = st.columns([1, 8])
    with col1:
        if st.button("← Indietro"):
            st.session_state.pagina = "clienti"
            st.rerun()
    st.title(f"📁 Documenti — {cliente_nome}")
    st.markdown("---")

    tab_lista, tab_upload = st.tabs(["Documenti salvati", "⬆️ Carica documento"])

    with tab_upload:
        if not can_edit(utente):
            st.warning("Non hai i permessi per caricare documenti.")
        else:
            _form_upload(utente, cliente_id)

    with tab_lista:
        docs = lista_documenti(cliente_id)
        if not docs:
            st.info("Nessun documento caricato.")
        else:
            # Filtro categoria
            cat_presenti = list({d["categoria"] for d in docs})
            filtro = st.multiselect("Filtra categoria", CATEGORIE, default=cat_presenti)
            docs_filtrati = [d for d in docs if d["categoria"] in filtro]

            for d in docs_filtrati:
                icona = ICONE_CAT.get(d["categoria"], "📎")
                autore = d.get("utenti") or {}
                autore_str = f"{autore.get('nome','')} {autore.get('cognome','')}".strip()
                dim_kb = round((d.get("dimensione") or 0) / 1024, 1)
                data_str = (d.get("created_at") or "")[:10]
                label = f"{icona} **{d['nome_file']}** — {d['categoria']} | {dim_kb} KB | {data_str} | {autore_str}"

                with st.expander(label):
                    if d.get("note"):
                        st.markdown(f"**Note:** {d['note']}")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("⬇️ Scarica", key=f"dl_{d['id']}"):
                            contenuto = scarica_documento(d["storage_path"])
                            if contenuto:
                                st.download_button(
                                    label="Clicca per scaricare",
                                    data=contenuto,
                                    file_name=d["nome_file"],
                                    mime=d.get("tipo_file", "application/octet-stream"),
                                    key=f"dlbtn_{d['id']}"
                                )
                            else:
                                st.error("Impossibile scaricare il file.")
                    with col2:
                        if can_edit(utente):
                            if st.button("🗑️ Elimina", key=f"ddel_{d['id']}"):
                                st.session_state[f"del_doc_{d['id']}"] = True

                    if st.session_state.get(f"del_doc_{d['id']}"):
                        st.warning("Confermi l'eliminazione del documento? L'azione è irreversibile.")
                        c1, c2 = st.columns(2)
                        if c1.button("Sì, elimina", key=f"ddok_{d['id']}"):
                            err = elimina_documento(d["id"], d["storage_path"])
                            if err:
                                st.error(f"Errore: {err}")
                            else:
                                st.rerun()
                        if c2.button("Annulla", key=f"ddno_{d['id']}"):
                            st.session_state[f"del_doc_{d['id']}"] = False
                            st.rerun()

def _form_upload(utente, cliente_id):
    st.subheader("Carica un documento")
    file = st.file_uploader(
        "Seleziona file (PDF, immagini, Word, Excel...)",
        type=["pdf","jpg","jpeg","png","heic","doc","docx","xls","xlsx","txt","zip"],
        key="upload_doc"
    )
    col1, col2 = st.columns(2)
    with col1:
        categoria = st.selectbox("Categoria", CATEGORIE)
    with col2:
        note = st.text_input("Note (opzionale)")

    if st.button("⬆️ Carica", disabled=file is None):
        if file is None:
            st.error("Seleziona un file prima.")
        elif file.size > MAX_SIZE_MB * 1024 * 1024:
            st.error(f"File troppo grande. Massimo {MAX_SIZE_MB} MB.")
        else:
            with st.spinner("Caricamento in corso..."):
                err = carica_documento(
                    cliente_id=cliente_id,
                    file_bytes=file.read(),
                    nome_file=file.name,
                    tipo_file=file.type or "application/octet-stream",
                    dimensione=file.size,
                    categoria=categoria,
                    note=note,
                    user_id=utente["id"]
                )
            if err:
                st.error(f"Errore durante il caricamento: {err}")
            else:
                st.success(f"'{file.name}' caricato con successo!")
                st.rerun()