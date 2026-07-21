# ui_stile.py — stile condiviso della dashboard RickCars
import streamlit as st

_CSS = """
<style>
/* ---- Bottoni dell'area principale ---- */
.main .stButton > button {
    border: 1px solid #e4e4ee;
    border-radius: 9px;
    background: #ffffff;
    color: #1a1a2e;
    font-size: 12.5px;
    font-weight: 600;
    padding: 7px 14px;
    box-shadow: 0 1px 2px rgba(13,13,26,.05);
    transition: all .15s ease;
}
.main .stButton > button:hover {
    border-color: #1a1a2e;
    color: #0d0d1a;
    box-shadow: 0 3px 10px rgba(13,13,26,.10);
    transform: translateY(-1px);
}

/* ---- Bottoni che aprono i popover (compositore, moduli) ---- */
.main [data-testid="stPopover"] > div > button {
    border: 1px dashed #d8d8e6;
    border-radius: 9px;
    background: #fbfbfe;
    font-weight: 600;
    color: #3a3a5e;
}
.main [data-testid="stPopover"] > div > button:hover {
    border-color: #e94560;
    color: #e94560;
    background: #ffffff;
}

/* ---- Separatori tra le sezioni ---- */
.main hr {
    border: none !important;
    height: 1px !important;
    margin: 26px 0 !important;
    background: linear-gradient(90deg,
        rgba(233,69,96,.35), rgba(15,52,96,.25), rgba(26,26,46,.05)) !important;
}

/* ---- Expander (richieste appuntamento) ---- */
.main [data-testid="stExpander"] {
    border: 1px solid #eaeaf0;
    border-radius: 10px;
    background: #ffffff;
    box-shadow: 0 1px 3px rgba(13,13,26,.05);
}
</style>
"""


def stile_globale():
    """Da chiamare una volta all'inizio della dashboard."""
    st.markdown(_CSS, unsafe_allow_html=True)


def intestazione(titolo, icona="", badge=None, badge_bg="#e94560", destra=None):
    """Titolo di sezione uniforme: barretta colorata, titolo in maiuscolo,
    badge colorato (se badge non è None) oppure nota grigia a destra."""
    sin = (
        "<span style='display:inline-block;width:4px;height:15px;border-radius:2px;"
        "background:linear-gradient(180deg,#e94560,#0f3460);'></span>"
        + (f"<span style='font-size:13px;'>{icona}</span>" if icona else "")
        + "<span style='font-size:11.5px;font-weight:800;letter-spacing:1.1px;"
        + f"text-transform:uppercase;color:#1a1a2e;'>{titolo}</span>"
    )
    if badge is not None:
        des = (f"<span style='background:{badge_bg};color:#fff;font-size:10px;"
               f"font-weight:700;padding:2px 9px;border-radius:10px;"
               f"box-shadow:0 1px 3px rgba(0,0,0,.15);'>{badge}</span>")
    elif destra:
        des = f"<span style='font-size:10.5px;color:#b0b0c0;font-weight:600;'>{destra}</span>"
    else:
        des = ""
    st.markdown(
        "<div style='display:flex;align-items:center;justify-content:space-between;"
        "margin:2px 0 12px;'>"
        f"<div style='display:flex;align-items:center;gap:8px;'>{sin}</div>{des}</div>",
        unsafe_allow_html=True,
    )
