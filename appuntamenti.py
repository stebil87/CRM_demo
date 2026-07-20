"""Richieste di appuntamento dal sito: canale separato.
Il consulente vede motivo, allegati e data/ora proposte; può accettare
(anche modificando data/ora) o rifiutare. All'accettazione il CRM crea il
cliente, salva allegati e diario, mette l'appuntamento in calendario e invia
la e-mail di conferma."""
import streamlit as st
from datetime import date, datetime, time as _time, timezone
from db import (get_sb, fmt_data, crea_cliente, crea_evento, crea_voce_diario,
                get_calendari_modificabili, lista_utenti)


UTENTE_SITO = "c55695c3-6ff1-495b-ad2a-f3189b99c5e3"


# ── dati ────────────────────────────────────────────────────────────────────
def lista_richieste(stato="in attesa"):
    sb = get_sb()
    try:
        q = sb.table("richieste_appuntamento").select("*").order(
            "created_at", desc=True)
        if stato:
            q = q.eq("stato", stato)
        return q.execute().data or []
    except Exception:
        return []


def _conta_in_attesa():
    sb = get_sb()
    try:
        r = sb.table("richieste_appuntamento").select(
            "id", count="exact").eq("stato", "in attesa").execute()
        return r.count or 0
    except Exception:
        return 0


def _normalizza_tel(t):
    import re
    t = re.sub(r"[^0-9+]", "", str(t or ""))
    if t.startswith("00"):
        t = "+" + t[2:]
    if t.startswith("0") and len(t) == 10:
        t = "+41" + t[1:]
    return t


def _trova_cliente(telefono, email):
    """Cerca un cliente per telefono o email; ritorna id o None."""
    sb = get_sb()
    tel = _normalizza_tel(telefono)
    try:
        cond = []
        if tel:
            cond.append(f"telefono.eq.{tel}")
        if email:
            cond.append(f"email.eq.{email}")
        if not cond:
            return None
        r = sb.table("clienti").select("id").or_(
            ",".join(cond)).limit(1).execute()
        if r.data:
            return r.data[0]["id"]
    except Exception:
        pass
    return None


# ── azioni ──────────────────────────────────────────────────────────────────
def accetta_richiesta(rich, utente, data_conf, ora_conf, calendario_id):
    """Crea cliente (o riusa), sposta allegati, crea diario + evento,
    invia e-mail di conferma, aggiorna la richiesta. Ritorna (ok, messaggio)."""
    sb = get_sb()
    try:
        # 1) cliente: riusa se esiste, altrimenti crea
        cid = _trova_cliente(rich.get("telefono"), rich.get("email"))
        if not cid:
            parti = (rich.get("nome") or "").split(" ", 1)
            nuovo = crea_cliente({
                "tipo": "fisica",
                "nome": parti[0] if parti else rich.get("nome"),
                "cognome": parti[1] if len(parti) > 1 else "",
                "telefono": _normalizza_tel(rich.get("telefono")),
                "email": rich.get("email"),
                "note": "Scheda creata da una richiesta di appuntamento dal sito.",
            }, UTENTE_SITO)
            cid = nuovo["id"] if nuovo else None
        if not cid:
            return False, "Impossibile creare o trovare il cliente."

        # 2) allegati: dalla cartella temporanea alla scheda documenti del cliente
        for a in (rich.get("allegati") or []):
            try:
                sb.table("documenti").insert({
                    "cliente_id": cid,
                    "nome_file": a.get("nome"),
                    "storage_path": a.get("storage_path"),
                    "tipo_file": a.get("mime"),
                    "dimensione": a.get("dim"),
                    "categoria": "altro",
                    "note": "Allegato alla richiesta di appuntamento dal sito",
                    "created_by": UTENTE_SITO,
                }).execute()
            except Exception:
                pass

        # 3) voce diario con il motivo della visita
        quando = f"{data_conf.isoformat()} {ora_conf.strftime('%H:%M')}"
        crea_voce_diario({
            "cliente_id": cid,
            "tipo": "riunione",
            "titolo": f"[Sito] Appuntamento del {data_conf.strftime('%d/%m/%Y')} {ora_conf.strftime('%H:%M')}",
            "contenuto": (rich.get("motivo") or "")
                         + f"\n\nVeicolo: {rich.get('veicolo') or '—'} · Targa: {rich.get('targa') or '—'}",
            "data_contatto": date.today().isoformat(),
        }, utente["id"])

        # 4) evento in calendario
        dt = datetime.combine(data_conf, ora_conf).isoformat()
        crea_evento({
            "titolo": f"Appuntamento — {rich.get('nome')}",
            "data_inizio": dt,
            "descrizione": (rich.get("motivo") or "")[:500],
            "proprietario_id": calendario_id,
            "cliente_id": cid,
        }, utente["id"])

        # 5) e-mail di conferma al cliente
        _invia_conferma(rich, data_conf, ora_conf)

        # 6) aggiorno la richiesta
        sb.table("richieste_appuntamento").update({
            "stato": "accettata",
            "data_confermata": data_conf.isoformat(),
            "ora_confermata": ora_conf.strftime("%H:%M"),
            "cliente_id": cid,
            "gestita_da": utente["id"],
            "gestita_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", rich["id"]).execute()

        return True, "Appuntamento confermato, cliente e calendario aggiornati."
    except Exception as e:
        return False, f"Errore: {e}"


def rifiuta_richiesta(rich, utente, invia_mail=False):
    sb = get_sb()
    try:
        if invia_mail and rich.get("email"):
            from email_service import invia_email
            invia_email(
                rich["email"],
                "La tua richiesta di appuntamento — RickCars",
                "<p>Buongiorno,</p><p>grazie per averci contattato. "
                "Purtroppo non possiamo confermare l'appuntamento nella data proposta. "
                "Ti invitiamo a chiamarci allo +41 91 683 00 00 per trovare insieme "
                "un momento adatto.</p><p>RickCars</p>",
                tipo="rifiuto_appuntamento",
            )
        sb.table("richieste_appuntamento").update({
            "stato": "rifiutata",
            "gestita_da": utente["id"],
            "gestita_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", rich["id"]).execute()
        return True
    except Exception:
        return False


def _invia_conferma(rich, data_conf, ora_conf):
    if not rich.get("email"):
        return
    from email_service import invia_email
    dstr = data_conf.strftime("%d/%m/%Y")
    ostr = ora_conf.strftime("%H:%M")
    corpo = (
        f"<p>Buongiorno {rich.get('nome','')},</p>"
        f"<p>confermiamo il tuo appuntamento da <b>RickCars</b>:</p>"
        f"<p style='font-size:16px'><b>{dstr} alle {ostr}</b><br>"
        f"Via Carlo Maderno 41 · 6850 Mendrisio</p>"
        f"<p>Motivo della visita: {rich.get('motivo','')}</p>"
        f"<p>Se hai bisogno di modificare l'orario, chiamaci allo "
        f"+41 91 683 00 00. A presto!</p><p>RickCars</p>"
    )
    invia_email(rich["email"], "Conferma appuntamento — RickCars",
                corpo, tipo="conferma_appuntamento")


# ── UI ──────────────────────────────────────────────────────────────────────
def _opzioni_calendari(utente):
    ids = get_calendari_modificabili(utente["id"])
    out = []
    for u in (lista_utenti() or []):
        if u["id"] in ids:
            et = f"{u.get('nome','')} {u.get('cognome','')}".strip()
            if u["id"] == utente["id"]:
                et += " (io)"
            out.append((u["id"], et))
    return out or [(utente["id"], "io")]


def widget_richieste_appuntamento(utente, compatta=True):
    """Widget dashboard: elenco richieste in attesa con azioni."""
    richieste = lista_richieste("in attesa")
    n = len(richieste)
    st.markdown(
        "<div style='display:flex;align-items:center;gap:8px;margin-bottom:8px;'>"
        "<span style='font-size:13px;font-weight:600;color:#1a1a2e;'>📅 Richieste appuntamento</span>"
        + (f"<span style='background:#F97316;color:white;font-size:10px;font-weight:700;"
           f"padding:2px 8px;border-radius:10px;'>{n} nuove</span>" if n else "")
        + "</div>", unsafe_allow_html=True)
    if not richieste:
        st.markdown(
            "<div style='background:#f6fff6;border:1px solid #d6ebd6;color:#3a7a3a;"
            "border-radius:8px;padding:10px 14px;font-size:12px;'>"
            "Nessuna richiesta in attesa.</div>", unsafe_allow_html=True)
        return
    for r in richieste:
        _scheda_richiesta(r, utente)


def _scheda_richiesta(r, utente):
    dstr = fmt_data(r.get("data_proposta"), "%d/%m/%Y") if r.get("data_proposta") else "—"
    testo_data = f"{r.get('data_proposta','')} {str(r.get('ora_proposta',''))[:5]}"
    with st.expander(f"📅 {r.get('nome')} · propone {testo_data}"):
        st.markdown(f"**Telefono:** {r.get('telefono') or '—'}  ·  "
                    f"**E-mail:** {r.get('email') or '—'}")
        st.markdown(f"**Veicolo:** {r.get('veicolo') or '—'}  ·  "
                    f"**Targa:** {r.get('targa') or '—'}")
        st.markdown(f"**Motivo della visita:**\n\n{r.get('motivo') or '—'}")

        allegati = r.get("allegati") or []
        if allegati:
            st.markdown(f"**Allegati:** {len(allegati)}")
            for a in allegati:
                url = _url_allegato(a.get("storage_path"))
                if url:
                    st.markdown(f"- [{a.get('nome')}]({url})")
                else:
                    st.markdown(f"- {a.get('nome')}")

        st.markdown("---")
        st.markdown("**Conferma o modifica data e ora:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            try:
                d_def = datetime.fromisoformat(str(r.get("data_proposta"))).date()
            except Exception:
                d_def = date.today()
            data_conf = st.date_input("Data", value=d_def, key=f"rd_{r['id']}")
        with col2:
            try:
                hh, mm = str(r.get("ora_proposta") or "09:00").split(":")[:2]
                o_def = _time(int(hh), int(mm))
            except Exception:
                o_def = _time(9, 0)
            ora_conf = st.time_input("Ora", value=o_def, key=f"ro_{r['id']}")
        with col3:
            cal = st.selectbox("Calendario", _opzioni_calendari(utente),
                               format_func=lambda x: x[1], key=f"rc_{r['id']}")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("✅ Accetta e conferma", key=f"acc_{r['id']}",
                         use_container_width=True, type="primary"):
                ok, msg = accetta_richiesta(r, utente, data_conf, ora_conf, cal[0])
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
        with col_b:
            if st.button("✖️ Rifiuta", key=f"rif_{r['id']}",
                         use_container_width=True):
                if rifiuta_richiesta(r, utente, invia_mail=True):
                    st.info("Richiesta rifiutata; e-mail inviata al cliente.")
                    st.rerun()


def _url_allegato(storage_path):
    if not storage_path:
        return None
    sb = get_sb()
    try:
        res = sb.storage.from_("documenti-clienti").create_signed_url(
            storage_path, 3600)
        return res.get("signedURL") or res.get("signedUrl")
    except Exception:
        return None


def pagina_appuntamenti(utente):
    st.title("📅 Richieste appuntamento")
    st.markdown("---")
    tab_att, tab_stor = st.tabs(["Da gestire", "Storico"])
    with tab_att:
        widget_richieste_appuntamento(utente, compatta=False)
    with tab_stor:
        for stato in ("accettata", "rifiutata"):
            righe = lista_richieste(stato)
            for r in righe:
                etichetta = "✅" if stato == "accettata" else "✖️"
                conf = ""
                if stato == "accettata" and r.get("data_confermata"):
                    conf = f" → confermato {r.get('data_confermata')} {str(r.get('ora_confermata',''))[:5]}"
                with st.expander(f"{etichetta} {r.get('nome')} · {r.get('data_proposta')}{conf}"):
                    st.markdown(f"**Motivo:** {r.get('motivo') or '—'}")
                    st.caption(f"Gestita da {r.get('gestita_da','—')} il "
                               f"{fmt_data(r.get('gestita_at'))}")
