import streamlit as st
from ui_stile import intestazione
from db import lista_note, crea_nota, aggiorna_nota, elimina_nota

COLORI_NOTE = {
    "Giallo":  "#fff9c4",
    "Verde":   "#c8f7c5",
    "Azzurro": "#c5e8f7",
    "Rosa":    "#f7c5e8",
    "Arancio": "#f7e0c5",
}

def widget_note(utente):
    note = lista_note(utente["id"])

    intestazione("Note rapide", "📝")

    # Bottone nuova nota
    if st.button("Nuova nota", key="btn_nuova_nota"):
        st.session_state.mostra_form_nota = True

    if st.session_state.get("mostra_form_nota"):
        with st.form("form_nuova_nota"):
            testo = st.text_area("Scrivi qui...", height=100, key="testo_nuova_nota")
            colore_label = st.selectbox("Colore", list(COLORI_NOTE.keys()))
            col1, col2 = st.columns(2)
            with col1:
                salva = st.form_submit_button("Salva", use_container_width=True)
            with col2:
                annulla = st.form_submit_button("Annulla", use_container_width=True)
        if salva and testo.strip():
            crea_nota(utente["id"], testo.strip(), COLORI_NOTE[colore_label])
            st.session_state.mostra_form_nota = False
            st.rerun()
        if annulla:
            st.session_state.mostra_form_nota = False
            st.rerun()

    if not note:
        st.markdown(
            "<div style='font-size:12px;color:#bbb;padding:8px 0;'>"
            "Nessuna nota. Aggiungine una.</div>",
            unsafe_allow_html=True
        )
        return

    for n in note:
        colore = n.get("colore", "#fff9c4")
        data_str = (n.get("updated_at") or "")[:10]

        st.markdown(
            "<div style='background:" + colore + ";border-radius:8px;"
            "padding:12px 14px;margin-bottom:8px;border:1px solid rgba(0,0,0,0.06);'>"
            "<div style='font-size:13px;white-space:pre-wrap;color:#1a1a2e;line-height:1.6;'>"
            + n["testo"] +
            "</div>"
            "<div style='font-size:10px;color:#aaa;margin-top:8px;'>" + data_str + "</div>"
            "</div>",
            unsafe_allow_html=True
        )

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Modifica", key=f"mod_nota_{n['id']}"):
                st.session_state[f"edit_nota_{n['id']}"] = True
        with col2:
            if st.button("Elimina", key=f"del_nota_{n['id']}"):
                elimina_nota(n["id"])
                st.rerun()

        if st.session_state.get(f"edit_nota_{n['id']}"):
            with st.form(f"form_edit_nota_{n['id']}"):
                nuovo_testo = st.text_area("Modifica", value=n["testo"], height=100)
                colori_lista = list(COLORI_NOTE.keys())
                colori_valori = list(COLORI_NOTE.values())
                idx = colori_valori.index(n.get("colore", "#fff9c4")) if n.get("colore") in colori_valori else 0
                nuovo_colore_label = st.selectbox("Colore", colori_lista, index=idx)
                c1, c2 = st.columns(2)
                with c1:
                    salva_mod = st.form_submit_button("Salva", use_container_width=True)
                with c2:
                    annulla_mod = st.form_submit_button("Annulla", use_container_width=True)
            if salva_mod:
                aggiorna_nota(n["id"], nuovo_testo, COLORI_NOTE[nuovo_colore_label])
                st.session_state[f"edit_nota_{n['id']}"] = False
                st.rerun()
            if annulla_mod:
                st.session_state[f"edit_nota_{n['id']}"] = False
                st.rerun()
