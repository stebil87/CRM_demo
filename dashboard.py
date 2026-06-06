import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from db import stats_dashboard, followup_in_scadenza
from auth import can_edit

def pagina_dashboard(utente):
    st.title("Dashboard")

    stats = stats_dashboard()
    followups = followup_in_scadenza()

    offerte_df = pd.DataFrame(stats["offerte_data"]) if stats["offerte_data"] else pd.DataFrame()
    clienti_df = pd.DataFrame(stats["clienti_data"]) if stats["clienti_data"] else pd.DataFrame()

    valore_pipeline = offerte_df[
        offerte_df["stato"].isin(["bozza", "inviata"])
    ]["importo"].sum() if not offerte_df.empty and "importo" in offerte_df.columns else 0

    valore_chiuso = offerte_df[
        offerte_df["stato"] == "accettata"
    ]["importo"].sum() if not offerte_df.empty and "importo" in offerte_df.columns else 0

    tasso_chiusura = 0
    if not offerte_df.empty and "stato" in offerte_df.columns:
        tot = len(offerte_df)
        chiuse = len(offerte_df[offerte_df["stato"] == "accettata"])
        tasso_chiusura = round((chiuse / tot) * 100) if tot > 0 else 0

    # ── KPI ──
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Clienti totali", stats["tot_clienti"])
    col2.metric("Pipeline", f"CHF {valore_pipeline:,.0f}")
    col3.metric("Chiuso", f"CHF {valore_chiuso:,.0f}")
    col4.metric("Tasso chiusura", f"{tasso_chiusura}%")

    st.markdown("---")

    # ── GRAFICI COMPATTI ──
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        if not clienti_df.empty and "stato" in clienti_df.columns:
            conteggio = clienti_df["stato"].value_counts().reset_index()
            conteggio.columns = ["Stato", "Numero"]
            fig = px.pie(
                conteggio, values="Numero", names="Stato",
                title="Clienti per stato",
                color_discrete_sequence=["#1a1a2e","#3a3a6e","#6a6aae","#aaaacc","#e0e0f0"],
                hole=0.5
            )
            fig.update_layout(
                height=240, margin=dict(t=36, b=0, l=0, r=0),
                showlegend=True,
                legend=dict(font=dict(size=10)),
                title_font_size=12
            )
            fig.update_traces(textfont_size=10)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nessun cliente ancora.")

    with col_b:
        if not offerte_df.empty and "stato" in offerte_df.columns:
            off_count = offerte_df["stato"].value_counts().reset_index()
            off_count.columns = ["Stato", "Numero"]
            fig2 = px.bar(
                off_count, x="Stato", y="Numero",
                title="Offerte per stato",
                color="Stato",
                color_discrete_sequence=["#1a1a2e","#3a3a6e","#6a6aae","#aaaacc","#e94560"]
            )
            fig2.update_layout(
                height=240, showlegend=False,
                margin=dict(t=36, b=0, l=0, r=0),
                title_font_size=12,
                xaxis=dict(tickfont=dict(size=10)),
                yaxis=dict(tickfont=dict(size=10))
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Nessuna offerta ancora.")

    with col_c:
        if not offerte_df.empty and "importo" in offerte_df.columns:
            valore_per_stato = offerte_df.groupby(
                "stato")["importo"].sum().reset_index()
            valore_per_stato.columns = ["Stato", "Valore"]
            fig3 = px.bar(
                valore_per_stato, x="Stato", y="Valore",
                title="Valore per stato (CHF)",
                color="Stato",
                color_discrete_sequence=["#1a1a2e","#3a3a6e","#6a6aae","#aaaacc","#e94560"]
            )
            fig3.update_layout(
                height=240, showlegend=False,
                margin=dict(t=36, b=0, l=0, r=0),
                title_font_size=12,
                xaxis=dict(tickfont=dict(size=10)),
                yaxis=dict(tickfont=dict(size=10))
            )
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Nessun dato valore.")

    # ── INSIGHTS ──
    st.markdown("---")
    with st.expander("Analisi avanzata"):
        if offerte_df.empty and clienti_df.empty:
            st.info("Inserisci clienti e offerte per vedere gli insights.")
        else:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Funnel di conversione**")
                if not offerte_df.empty and "stato" in offerte_df.columns:
                    stati_ord = ["bozza", "inviata", "accettata"]
                    funnel_data = []
                    for s in stati_ord:
                        n = len(offerte_df[offerte_df["stato"] == s])
                        funnel_data.append({"Fase": s.upper(), "Numero": n})
                    funnel_df = pd.DataFrame(funnel_data)
                    fig_f = go.Figure(go.Funnel(
                        y=funnel_df["Fase"],
                        x=funnel_df["Numero"],
                        textinfo="value+percent initial",
                        marker=dict(color=["#1a1a2e","#3a3a6e","#6a6aae"])
                    ))
                    fig_f.update_layout(
                        height=220, margin=dict(t=10, b=0, l=0, r=0))
                    st.plotly_chart(fig_f, use_container_width=True)

            with col2:
                st.markdown("**Valore medio offerta per stato**")
                if not offerte_df.empty and "importo" in offerte_df.columns:
                    media = offerte_df.groupby(
                        "stato")["importo"].mean().reset_index()
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
                    fig_p = px.bar(
                        paesi.head(8), x="Clienti", y="Paese",
                        orientation="h",
                        color_discrete_sequence=["#1a1a2e"]
                    )
                    fig_p.update_layout(
                        height=220, margin=dict(t=10, b=0, l=0, r=0),
                        yaxis=dict(tickfont=dict(size=10))
                    )
                    st.plotly_chart(fig_p, use_container_width=True)

            with col4:
                st.markdown("**Riepilogo**")
                riepilogo = {
                    "Clienti prospect": len(clienti_df[clienti_df["stato"] == "prospect"]) if not clienti_df.empty and "stato" in clienti_df.columns else 0,
                    "Clienti attivi": len(clienti_df[clienti_df["stato"] == "attivo"]) if not clienti_df.empty and "stato" in clienti_df.columns else 0,
                    "Offerte aperte": len(offerte_df[offerte_df["stato"].isin(["bozza","inviata"])]) if not offerte_df.empty and "stato" in offerte_df.columns else 0,
                    "Offerte vinte": len(offerte_df[offerte_df["stato"] == "accettata"]) if not offerte_df.empty and "stato" in offerte_df.columns else 0,
                    "Offerte perse": len(offerte_df[offerte_df["stato"] == "rifiutata"]) if not offerte_df.empty and "stato" in offerte_df.columns else 0,
                    "Valore pipeline": f"CHF {valore_pipeline:,.0f}",
                    "Valore chiuso": f"CHF {valore_chiuso:,.0f}",
                    "Tasso chiusura": f"{tasso_chiusura}%",
                }
                for k, v in riepilogo.items():
                    c1, c2 = st.columns([3, 2])
                    c1.markdown(f"<span style='font-size:12px;color:#888;'>{k}</span>", unsafe_allow_html=True)
                    c2.markdown(f"<span style='font-size:13px;font-weight:600;color:#1a1a2e;'>{v}</span>", unsafe_allow_html=True)

    # ── FOLLOW-UP ──
    st.markdown("---")
    st.subheader("Follow-up nei prossimi 7 giorni")
    if followups:
        for f in followups:
            cliente = f.get("clienti", {})
            nome_cliente = cliente.get("ragione_sociale") or \
                f"{cliente.get('nome','')} {cliente.get('cognome','')}".strip()
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

    # ── NOTIFICHE MESSAGGI ──
    _mostra_notifica_messaggi(utente)

def _mostra_notifica_messaggi(utente):
    from db import lista_messaggi_non_letti

    # Controlla se le notifiche sono disattivate
    if st.session_state.get("notifiche_disattivate", False):
        return

    non_letti = lista_messaggi_non_letti(utente["id"])
    if not non_letti:
        return

    # Mostra solo messaggi che non abbiamo già notificato
    già_notificati = st.session_state.get("msg_notificati", set())
    nuovi = [m for m in non_letti if m["id"] not in già_notificati]
    if not nuovi:
        return

    for m in nuovi:
        mitt = m.get("mittente") or {}
        nome_mitt = f"{mitt.get('nome','')} {mitt.get('cognome','')}".strip() or "Utente"
        oggetto = m.get("oggetto", "")
        st.toast(f"Nuovo messaggio da {nome_mitt}: {oggetto}", icon=None)
        già_notificati.add(m["id"])

    st.session_state.msg_notificati = già_notificati
