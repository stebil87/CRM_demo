import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from db import stats_dashboard, followup_in_scadenza, lista_messaggi_non_letti
from auth import can_edit

def pagina_dashboard(utente):
    st.title("Dashboard")

    stats = stats_dashboard()
    followups = followup_in_scadenza()
    non_letti = lista_messaggi_non_letti(utente["id"])

    offerte_df = pd.DataFrame(stats["offerte_data"]) if stats["offerte_data"] else pd.DataFrame()
    clienti_df = pd.DataFrame(stats["clienti_data"]) if stats["clienti_data"] else pd.DataFrame()

    valore_pipeline = offerte_df[offerte_df["stato"].isin(["bozza","inviata"])]["importo"].sum() if not offerte_df.empty and "importo" in offerte_df.columns else 0
    valore_chiuso = offerte_df[offerte_df["stato"] == "accettata"]["importo"].sum() if not offerte_df.empty and "importo" in offerte_df.columns else 0
    tasso_chiusura = 0
    if not offerte_df.empty and "stato" in offerte_df.columns:
        tot = len(offerte_df)
        chiuse = len(offerte_df[offerte_df["stato"] == "accettata"])
        tasso_chiusura = round((chiuse / tot) * 100) if tot > 0 else 0

    # KPI
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Clienti totali", stats["tot_clienti"])
    col2.metric("Attivita oggi", stats["diario_oggi"])
    col3.metric("Pipeline", f"CHF {valore_pipeline:,.0f}")
    col4.metric("Chiuso", f"CHF {valore_chiuso:,.0f}")
    col5.metric("Tasso chiusura", f"{tasso_chiusura}%")

    if non_letti:
        st.markdown(f"<div style='background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:10px 16px;font-size:13px;margin-top:8px;'>Hai <b>{len(non_letti)}</b> messaggio/i non letto/i. <a href='#' onclick='void(0)' style='color:#1a1a2e;font-weight:600;'>Vai alla posta</a></div>", unsafe_allow_html=True)
        if st.button("Apri messaggi", key="btn_msg_dash"):
            st.session_state.pagina = "messaggi"
            st.rerun()

    st.markdown("---")

    # Grafici compatti
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        if not clienti_df.empty and "stato" in clienti_df.columns:
            conteggio = clienti_df["stato"].value_counts().reset_index()
            conteggio.columns = ["Stato", "Numero"]
            fig = px.pie(conteggio, values="Numero", names="Stato",
                        title="Clienti per stato",
                        color_discrete_sequence=["#1a1a2e","#3a3a6e","#6a6aae","#aaaacc","#e0e0f0"],
                        hole=0.5)
            fig.update_layout(
                height=260, margin=dict(t=36, b=0, l=0, r=0),
                showlegend=True,
                legend=dict(font=dict(size=10)),
                title_font_size=12
            )
            fig.update_traces(textfont_size=10)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nessun cliente.")

    with col_b:
        if not offerte_df.empty and "stato" in offerte_df.columns:
            off_count = offerte_df["stato"].value_counts().reset_index()
            off_count.columns = ["Stato", "Numero"]
            fig2 = px.bar(off_count, x="Stato", y="Numero",
                         title="Offerte per stato",
                         color="Stato",
                         color_discrete_sequence=["#1a1a2e","#3a3a6e","#6a6aae","#aaaacc","#e94560"])
            fig2.update_layout(
                height=260, showlegend=False,
                margin=dict(t=36, b=0, l=0, r=0),
                title_font_size=12,
                xaxis=dict(tickfont=dict(size=10)),
                yaxis=dict(tickfont=dict(size=10))
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Nessuna offerta.")

    with col_c:
        if not offerte_df.empty and "importo" in offerte_df.columns and "stato" in offerte_df.columns:
            valore_per_stato = offerte_df.groupby("stato")["importo"].sum().reset_index()
            valore_per_stato.columns = ["Stato", "Valore"]
            fig3 = px.bar(valore_per_stato, x="Stato", y="Valore",
                         title="Valore per stato (CHF)",
                         color="Stato",
                         color_discrete_sequence=["#1a1a2e","#3a3a6e","#6a6aae","#aaaacc","#e94560"])
            fig3.update_layout(
                height=260, showlegend=False,
                margin=dict(t=36, b=0, l=0, r=0),
                title_font_size=12,
                xaxis=dict(tickfont=dict(size=10)),
                yaxis=dict(tickfont=dict(size=10))
            )
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Nessun dato valore.")

    # Insights espandibili
    st.markdown("---")
    with st.expander("Insights e analisi avanzata"):
        if offerte_df.empty or clienti_df.empty:
            st.info("Inserisci clienti e offerte per vedere gli insights.")
        else:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Conversione pipeline**")
                if not offerte_df.empty and "stato" in offerte_df.columns and "importo" in offerte_df.columns:
                    stati_ord = ["bozza", "inviata", "accettata"]
                    funnel_data = []
                    for s in stati_ord:
                        n = len(offerte_df[offerte_df["stato"] == s])
                        v = offerte_df[offerte_df["stato"] == s]["importo"].sum()
                        funnel_data.append({"Fase": s.upper(), "Numero": n, "Valore": v})
                    funnel_df = pd.DataFrame(funnel_data)
                    fig_f = go.Figure(go.Funnel(
                        y=funnel_df["Fase"],
                        x=funnel_df["Numero"],
                        textinfo="value+percent initial",
                        marker=dict(color=["#1a1a2e","#3a3a6e","#6a6aae"])
                    ))
                    fig_f.update_layout(height=220, margin=dict(t=10, b=0, l=0, r=0))
                    st.plotly_chart(fig_f, use_container_width=True)

            with col2:
                st.markdown("**Valore medio offerta per stato**")
                if not offerte_df.empty:
                    media = offerte_df.groupby("stato")["importo"].mean().reset_index()
                    media.columns = ["Stato", "Media CHF"]
                    media["Media CHF"] = media["Media CHF"].round(0)
                    st.dataframe(
                        media.sort_values("Media CHF", ascending=False),
                        use_container_width=True,
                        hide_index=True
                    )

            st.markdown("---")
            col3, col4 = st.columns(2)

            with col3:
                st.markdown("**Clienti per paese**")
                if not clienti_df.empty and "paese" in clienti_df.columns:
                    paesi = clienti_df["paese"].value_counts().reset_index()
                    paesi.columns = ["Paese", "Clienti"]
                    fig_p = px.bar(paesi.head(8), x="Clienti", y="Paese",
                                  orientation="h",
                                  color_discrete_sequence=["#1a1a2e"])
                    fig_p.update_layout(height=220, margin=dict(t=10, b=0, l=0, r=0),
                                       yaxis=dict(tickfont=dict(size=10)))
                    st.plotly_chart(fig_p, use_container_width=True)

            with col4:
                st.markdown("**Riepilogo numerico**")
                riepilogo = {
                    "Clienti prospect": len(clienti_df[clienti_df["stato"] == "prospect"]) if "stato" in clienti_df.columns else 0,
                    "Clienti attivi": len(clienti_df[clienti_df["stato"] == "attivo"]) if "stato" in clienti_df.columns else 0,
                    "Offerte aperte": len(offerte_df[offerte_df["stato"].isin(["bozza","inviata"])]) if "stato" in offerte_df.columns else 0,
                    "Offerte vinte": len(offerte_df[offerte_df["stato"] == "accettata"]) if "stato" in offerte_df.columns else 0,
                    "Offerte perse": len(offerte_df[offerte_df["stato"] == "rifiutata"]) if "stato" in offerte_df.columns else 0,
                    "Valore pipeline (CHF)": f"{valore_pipeline:,.0f}",
                    "Valore chiuso (CHF)": f"{valore_chiuso:,.0f}",
                    "Tasso chiusura": f"{tasso_chiusura}%",
                }
                for k, v in riepilogo.items():
                    col_k, col_v = st.columns([3, 2])
                    col_k.markdown(f"<span style='font-size:12px;color:#888;'>{k}</span>", unsafe_allow_html=True)
                    col_v.markdown(f"<span style='font-size:13px;font-weight:600;color:#1a1a2e;'>{v}</span>", unsafe_allow_html=True)

    # Follow-up
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
