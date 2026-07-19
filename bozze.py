"""Motore bozze condivise: salva/recupera il lavoro in corso (email, note,
follow-up, schede cliente) così che, se la sessione scade, nulla vada perso.
Le bozze sono condivise: un collega autorizzato può riprenderle."""
import streamlit as st
from db import get_sb


def salva_bozza(contesto, chiave, contenuto, utente_id, titolo=""):
    """Crea o aggiorna la bozza per (contesto, chiave). contenuto = dict."""
    sb = get_sb()
    try:
        from datetime import datetime, timezone
        payload = {
            "contesto": contesto,
            "chiave": str(chiave),
            "titolo": titolo or "",
            "contenuto": contenuto,
            "updated_by": utente_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        # upsert sulla coppia unica (contesto, chiave)
        sb.table("bozze").upsert(
            {**payload, "created_by": utente_id},
            on_conflict="contesto,chiave",
        ).execute()
        return None
    except Exception as e:
        return str(e)


def carica_bozza(contesto, chiave):
    """Ritorna il dict 'contenuto' della bozza, o None se non esiste."""
    sb = get_sb()
    try:
        res = sb.table("bozze").select("*").eq(
            "contesto", contesto).eq("chiave", str(chiave)).limit(1).execute()
        if res.data:
            return res.data[0]
        return None
    except Exception:
        return None


def elimina_bozza(contesto, chiave):
    sb = get_sb()
    try:
        sb.table("bozze").delete().eq(
            "contesto", contesto).eq("chiave", str(chiave)).execute()
        return None
    except Exception as e:
        return str(e)


def lista_bozze(contesto=None):
    """Tutte le bozze (condivise), opzionalmente filtrate per contesto."""
    sb = get_sb()
    try:
        q = sb.table("bozze").select(
            "*, autore:utenti!bozze_updated_by_fkey(nome, cognome)"
        ).order("updated_at", desc=True)
        if contesto:
            q = q.eq("contesto", contesto)
        return q.execute().data or []
    except Exception:
        return []


def widget_bozze_in_sospeso(utente):
    """Pannello riassuntivo delle bozze aperte, da mettere in dashboard."""
    from db import fmt_data
    bozze = lista_bozze()
    if not bozze:
        return
    st.markdown(
        "<div style='font-size:13px;font-weight:600;color:#1a1a2e;"
        "margin-bottom:8px;'>✏️ Lavori in sospeso (bozze)</div>",
        unsafe_allow_html=True,
    )
    icone = {"email": "✉️", "nota": "📝", "followup": "🔔", "cliente": "👤"}
    for b in bozze[:8]:
        a = b.get("autore") or {}
        autore = f"{a.get('nome','')} {a.get('cognome','')}".strip() or "—"
        st.markdown(
            "<div style='background:#fffdf5;border:1px solid #f0e6c0;"
            "border-left:4px solid #d4a017;border-radius:8px;"
            "padding:8px 12px;margin-bottom:6px;font-size:12px;'>"
            f"{icone.get(b['contesto'],'📄')} <b>{b.get('titolo') or b['contesto']}</b>"
            f"<span style='color:#999;'> · {autore} · {fmt_data(b.get('updated_at'),'%d/%m %H:%M')}</span>"
            "</div>",
            unsafe_allow_html=True,
        )
