import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
from db import (
    stats_dashboard, followup_oggi, followup_prossimi7,
    eventi_oggi_multi, get_calendari_visibili,
    lista_eventi_catering
)
from auth import can_edit

def is_event_manager(utente):
    return utente and utente["ruolo"] in ("admin", "event_manager")

def pagina_dashboard(utente):
    st.title("Dashboard")

    stats = stats_dashboard()
    oggi_fu = followup_oggi()
    prossimi_fu = followup_prossimi7()
    ids_visibili = get_calendari_visibili(utente["id"])
    ev_oggi = eventi_oggi_multi(ids_visibili)

    offerte_df = pd.DataFrame(stats["offerte_data"]) if stats["offerte_data"] else pd.DataFrame()
    clienti_df = pd.DataFrame(stats["clienti_data"]) if stats["clienti_data"] else pd.DataFrame()

    valore_chiuso = offerte_df[
        offerte_df["stato"] == "accettata"
    ]["importo"].sum() if not offerte_df.empty and "importo" in offerte_df.columns else 0

    tasso_chiusura = 0
    if not offerte_df.empty and "stato" in offerte_df.columns:
        tot = len(offerte_df)
        chiuse = len(offerte_df[offerte_df["stato"] == "accettata"])
        tasso_chiusura = round((chiuse / tot) * 100) if tot > 0 else 0

    # ── KPI ──
    col1, col2, col3 = st.columns(3)
    col1.metric("Clienti totali", stats["tot_clienti"])
    col2.metric("Chiuso", f"CHF {valore_chiuso:,.0f}")
    col3.metric("Tasso chiusura", f"{tasso_chiusura}%")

    st.markdown("---")

    # ── NOTE RAPIDE + AVVISI EVENTI ──
    col_note, col_avvisi = st.columns(2)

    with col_note:
        from note_dashboard import widget_note
        widget_note(utente)

    with col_avvisi:
        from eventi_catering import widget_avvisi_eventi
        widget_avvisi_eventi(utente)

        if is_event_manager(utente):
            nuovi = lista_eventi_catering(solo_nuovo=True)
            if nuovi:
                st.markdown("**Nuovi eventi da gestire**")
                for ev in nuovi:
                    st.markdown(
                        "<div style='background:white;border:1px solid #eaeaf0;"
                        "border-left:4px solid #e94560;border-radius:8px;"
                        "padding:10px 14px;margin-bottom:8px;'>"
                        "<div style='font-size:13px;font-weight:600;'>"
                        + ev["titolo"] +
                        "</div>"
                        "<div style='font-size:11px;color:#888;margin-top:3px;'>"
                        + (ev.get("data_inizio") or "")[:10] +
                        "</div></div>",
                        unsafe_allow_html=True
                    )
                    if st.button("Gestisci", key=f"dash_ev_{ev['id']}"):
                        st.session_state.pagina = "eventi"
                        st.rerun()

    st.markdown("---")

    # ── AGENDA + FOLLOW-UP ──
    col_ev, col_fu_oggi, col_fu_prox = st.columns(3)

    with col_ev:
        st.markdown("**Agenda di oggi**")
        if ev_oggi:
            for e in ev_oggi:
                try:
                    ora = datetime.fromisoformat(
                        e["data_inizio"].replace("Z", "")
                    ).strftime("%H:%M")
                except:
                    ora = ""
                colore = {
                    "appuntamento": "#1a1a2e",
                    "riunione":     "#0f3460",
                    "chiamata":     "#533483",
                    "scadenza":     "#e94560",
                    "altro":        "#6a6aae",
                }.get(e.get("tipo", "altro"), "#1a1a2e")
                propr = e.get("proprietario") or {}
                nome_propr = f"{propr.get('nome','')} {propr.get('cognome','')}".strip()
                st.markdown(
                    "<div style='background:white;border:1px solid #eaeaf0;"
                    "border-left:3px solid " + colore + ";border-radius:8px;"
                    "padding:10px 14px;margin-bottom:8px;'>"
                    "<div style='font-size:13px;font-weight:600;color:#1a1a2e;'>"
                    + ora + "&nbsp;&nbsp;" + e["titolo"] +
                    "</div>"
                    "<div style='font-size:11px;color:#888;margin-top:3px;'>"
                    + e.get("tipo", "").upper()
                    + (" · " + e["luogo"] if e.get("luogo") else "")
                    + (" · " + nome_propr if nome_propr else "")
                    + "</div></div>",
                    unsafe_allow_html=True
                )
        else:
            st.markdown(
                "<div style='background:#f0faf4;border:1px solid #c3e6cb;"
                "border-radius:8px;padding:12px 16px;font-size:13px;color:#2d6a4f;'>"
                "Nessun evento oggi.</div>",
                unsafe_allow_html=True
            )

    with col_fu_oggi:
        st.markdown("**Follow-up di oggi**")
        if oggi_fu:
            for f in oggi_fu:
                cliente = f.get("clienti", {})
                nome_cliente = cliente.get("ragione_sociale") or \
                    f"{cliente.get('nome','')} {cliente.get('cognome','')}".strip()
                st.markdown(
                    "<div style='background:white;border:1px solid #eaeaf0;"
                    "border-left:3px solid #1a1a2e;border-radius:8px;"
                    "padding:10px 14px;margin-bottom:8px;'>"
                    "<div style='font-size:13px;font-weight:600;'>"
                    + f["titolo"] +
                    "</div>"
                    "<div style='font-size:11px;color:#888;margin-top:3px;'>"
                    + nome_cliente +
                    "</div></div>",
                    unsafe_allow_html=True
                )
                if can_edit(utente):
                    if st.button("Fatto", key=f"oggi_{f['id']}"):
                        from db import aggiorna_voce_diario
                        aggiorna_voce_diario(f["id"], {"followup_fatto": True})
                        st.rerun()
        else:
            st.markdown(
                "<div style='background:#f0faf4;border:1px solid #c3e6cb;"
                "border-radius:8px;padding:12px 16px;font-size:13px;color:#2d6a4f;'>"
                "Nessun follow-up oggi.</div>",
                unsafe_allow_html=True
            )

    with col_fu_prox:
        st.markdown("**Follow-up prossimi 7 giorni**")
        if prossimi_fu:
            for f in prossimi_fu:
                cliente = f.get("clienti", {})
                nome_cliente = cliente.get("ragione_sociale") or \
                    f"{cliente.get('nome','')} {cliente.get('cognome','')}".strip()
                st.markdown(
                    "<div style='background:white;border:1px solid #eaeaf0;"
                    "border-left:3px solid #6a6aae;border-radius:8px;"
                    "padding:10px 14px;margin-bottom:8px;'>"
                    "<div style='font-size:13px;font-weight:600;'>"
                    + f["titolo"] +
                    "</div>"
                    "<div style='font-size:11px;color:#888;margin-top:3px;'>"
                    + nome_cliente + " · " + f.get("followup_data", "") +
                    "</div></div>",
                    unsafe_allow_html=True
                )
                if can_edit(utente):
                    if st.button("Fatto", key=f"prox_{f['id']}"):
                        from db import aggiorna_voce_diario
                        aggiorna_voce_diario(f["id"], {"followup_fatto": True})
                        st.rerun()
        else:
            st.markdown(
                "<div style='background:#f0faf4;border:1px solid #c3e6cb;"
                "border-radius:8px;padding:12px 16px;font-size:13px;color:#2d6a4f;'>"
                "Nessun follow-up in arrivo.</div>",
                unsafe_allow_html=True
            )

    st.markdown("---")

    # ── GRAFICI ──
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
                    "Valore chiuso": f"CHF {valore_chiuso:,.0f}",
                    "Tasso chiusura": f"{tasso_chiusura}%",
                }
                for k, v in riepilogo.items():
                    c1, c2 = st.columns([3, 2])
                    c1.markdown(
                        "<span style='font-size:12px;color:#888;'>" + k + "</span>",
                        unsafe_allow_html=True
                    )
                    c2.markdown(
                        "<span style='font-size:13px;font-weight:600;color:#1a1a2e;'>"
                        + str(v) + "</span>",
                        unsafe_allow_html=True
                    )

    _mostra_notifica_messaggi(utente)


def _mostra_notifica_messaggi(utente):
    from db import lista_messaggi_non_letti
    if st.session_state.get("notifiche_disattivate", False):
        return
    non_letti = lista_messaggi_non_letti(utente["id"])
    if not non_letti:
        return
    gia_notificati = st.session_state.get("msg_notificati", set())
    nuovi = [m for m in non_letti if m["id"] not in gia_notificati]
    if not nuovi:
        return
    for m in nuovi:
        mitt = m.get("mittente") or {}
        nome_mitt = f"{mitt.get('nome','')} {mitt.get('cognome','')}".strip() or "Utente"
        st.toast(f"Nuovo messaggio da {nome_mitt}: {m.get('oggetto','')}")
        gia_notificati.add(m["id"])
    st.session_state.msg_notificati = gia_notificati
