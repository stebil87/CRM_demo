import streamlit as st
import plotly.express as px
import pandas as pd
from db import stats_dashboard, followup_in_scadenza
from auth import can_edit

def pagina_dashboard(utente):
    st.title("Dashboard")
    stats = stats_dashboard()
    followups = followup_in_scadenza()

    offerte_df = pd.DataFrame(stats["offerte_data"]) if stats["offerte_data"] else pd.DataFrame()
    valore_pipeline = offerte_df[offerte_df["stato"].isin(["bozza","inviata"])]["importo"].sum() if not offerte_df.empty else 0
    valore_chiuso = offerte_df[offerte_df["stato"] == "accettata"]["importo"].sum() if not offerte_df.empty else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Clienti totali", stats["tot_clienti"])
    col2.metric("Attivita oggi", stats["diario_oggi"])
    col3.metric("Pipeline", f"CHF {valore_pipeline:,.0f}")
    col4.metric("Chiuso", f"CHF {valore_chiuso:,.0f}")

    st.markdown("---")
    col_a, col_b = st.columns(2)

    with col_a:
        clienti_df = pd.DataFrame(stats["clienti_data"]) if stats["clienti_data"] else pd.DataFrame()
        if not clienti_df.empty and "stato" in clienti_df.columns:
            conteggio = clienti_df["stato"].value_counts().reset_index()
            conteggio.columns = ["Stato", "Numero"]
            fig = px.pie(conteggio, values="Numero", names="Stato",
                        title="Clienti per stato",
                        color_discrete_sequence=["#1a1a2e","#16213e","#0f3460","#533483"])
            fig.update_layout(margin=dict(t=40, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nessun cliente ancora.")

    with col_b:
        if not offerte_df.empty and "stato" in offerte_df.columns:
            off_count = offerte_df["stato"].value_counts().reset_index()
            off_count.columns = ["Stato", "Numero"]
            fig2 = px.bar(off_count, x="Stato", y="Numero",
                         title="Offerte per stato",
                         color="Stato",
                         color_discrete_sequence=["#1a1a2e","#16213e","#0f3460","#533483","#e94560"])
            fig2.update_layout(showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Nessuna offerta ancora.")

    st.markdown("---")
    st.subheader("Follow-up nei prossimi 7 giorni")
    if followups:
        for f in followups:
            cliente = f.get("clienti", {})
            nome_cliente = cliente.get("ragione_sociale") or f"{cliente.get('nome','')} {cliente.get('cognome','')}".strip()
            col1, col2, col3 = st.columns([3, 2, 1])
            col1.markdown(f"**{f['titolo']}** — {nome_cliente}")
            col2.markdown(f"{f['followup_data']}")
            if can_edit(utente):
                if col3.button("Fatto", key=f"fu_{f['id']}"):
                    from db import aggiorna_voce_diario
                    aggiorna_voce_diario(f["id"], {"followup_fatto": True})
                    st.rerun()
    else:
        st.success("Nessun follow-up in scadenza.")
