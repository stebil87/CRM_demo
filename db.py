from supabase import create_client
import streamlit as st

@st.cache_resource
def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def get_sb():
    """Usa service role key per le query."""
    url = st.secrets["SUPABASE_URL"]
    service_key = st.secrets["SUPABASE_SERVICE_KEY"]
    return create_client(url, service_key)
# ── NOTE DASHBOARD ────────────────────────────────────

def lista_note(utente_id):
    sb = get_sb()
    try:
        res = sb.table("note_dashboard").select("*").eq(
            "utente_id", utente_id
        ).order("updated_at", desc=True).execute()
        return res.data or []
    except:
        return []

def crea_nota(utente_id, testo, colore="#fff9c4"):
    sb = get_sb()
    try:
        res = sb.table("note_dashboard").insert({
            "utente_id": utente_id,
            "testo": testo,
            "colore": colore
        }).execute()
        return res.data[0] if res.data else None
    except:
        return None

def aggiorna_nota(nota_id, testo, colore):
    sb = get_sb()
    try:
        from datetime import datetime
        sb.table("note_dashboard").update({
            "testo": testo,
            "colore": colore,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", nota_id).execute()
    except:
        pass

def elimina_nota(nota_id):
    sb = get_sb()
    try:
        sb.table("note_dashboard").delete().eq("id", nota_id).execute()
    except:
        pass

# ── EVENTI CATERING ───────────────────────────────────

def lista_eventi_catering(solo_nuovo=False):
    sb = get_sb()
    try:
        q = sb.table("eventi_catering").select(
            "*, cliente:clienti(nome, cognome, ragione_sociale, tipo, email),"
            "offerta:offerte(numero, titolo, importo, valuta),"
            "creatore:utenti!eventi_catering_creato_da_fkey(nome, cognome),"
            "manager:utenti!eventi_catering_event_manager_id_fkey(nome, cognome)"
        ).order("data_inizio")
        if solo_nuovo:
            q = q.eq("stato", "nuovo")
        res = q.execute()
        return res.data or []
    except:
        return []

def get_evento_catering(evento_id):
    sb = get_sb()
    try:
        res = sb.table("eventi_catering").select(
            "*, cliente:clienti(nome, cognome, ragione_sociale, tipo, email, telefono, indirizzo, citta),"
            "offerta:offerte(numero, titolo, importo, valuta, righe, descrizione),"
            "creatore:utenti!eventi_catering_creato_da_fkey(nome, cognome),"
            "manager:utenti!eventi_catering_event_manager_id_fkey(nome, cognome)"
        ).eq("id", evento_id).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except:
        return None

def crea_evento_catering(dati, user_id):
    sb = get_sb()
    try:
        dati["creato_da"] = user_id
        res = sb.table("eventi_catering").insert(dati).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        return None

def aggiorna_evento_catering(evento_id, dati):
    sb = get_sb()
    try:
        from datetime import datetime
        dati["updated_at"] = datetime.utcnow().isoformat()
        sb.table("eventi_catering").update(dati).eq("id", evento_id).execute()
    except:
        pass

def lista_collaboratori_evento(evento_id):
    sb = get_sb()
    try:
        res = sb.table("eventi_collaboratori").select(
            "*, utente:utenti(nome, cognome, email)"
        ).eq("evento_id", evento_id).execute()
        return res.data or []
    except:
        return []

def aggiungi_collaboratore(evento_id, utente_id=None, nome_esterno=None, email_esterno=None, ruolo=None):
    sb = get_sb()
    try:
        res = sb.table("eventi_collaboratori").insert({
            "evento_id": evento_id,
            "utente_id": utente_id,
            "nome_esterno": nome_esterno,
            "email_esterno": email_esterno,
            "ruolo": ruolo,
            "avvisato": False
        }).execute()
        return res.data[0] if res.data else None
    except:
        return None

def rimuovi_collaboratore(collab_id):
    sb = get_sb()
    try:
        sb.table("eventi_collaboratori").delete().eq("id", collab_id).execute()
    except:
        pass

def segna_collaboratore_avvisato(collab_id):
    sb = get_sb()
    try:
        sb.table("eventi_collaboratori").update(
            {"avvisato": True}
        ).eq("id", collab_id).execute()
    except:
        pass

def lista_allegati_evento(evento_id):
    sb = get_sb()
    try:
        res = sb.table("eventi_allegati").select("*").eq(
            "evento_id", evento_id
        ).execute()
        return res.data or []
    except:
        return []

def carica_allegato_evento(evento_id, file_bytes, nome_file, tipo_file, dimensione, user_id):
    sb = get_sb()
    import uuid
    path = f"{evento_id}/{uuid.uuid4()}_{nome_file}"
    try:
        sb.storage.from_("eventi-allegati").upload(
            path, file_bytes, {"content-type": tipo_file})
        sb.table("eventi_allegati").insert({
            "evento_id": evento_id,
            "nome_file": nome_file,
            "storage_path": path,
            "tipo_file": tipo_file,
            "dimensione": dimensione,
            "created_by": user_id
        }).execute()
        return None
    except Exception as e:
        return str(e)

def scarica_allegato_evento(storage_path):
    sb = get_sb()
    try:
        return sb.storage.from_("eventi-allegati").download(storage_path)
    except:
        return None

def lista_ore_evento(evento_id):
    sb = get_sb()
    try:
        res = sb.table("ore_evento").select(
            "*, utente:utenti(nome, cognome)"
        ).eq("evento_id", evento_id).execute()
        return res.data or []
    except:
        return []

def inserisci_ore(dati):
    sb = get_sb()
    try:
        res = sb.table("ore_evento").insert(dati).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        return None

def eventi_assegnati_a_utente(utente_id):
    """Eventi in cui l'utente è collaboratore e non ha ancora inserito le ore."""
    sb = get_sb()
    try:
        res = sb.table("eventi_collaboratori").select(
            "*, evento:eventi_catering(id, titolo, data_fine, stato)"
        ).eq("utente_id", utente_id).execute()
        return res.data or []
    except:
        return []

def utenti_event_manager():
    sb = get_sb()
    try:
        res = sb.table("utenti").select("*").in_(
            "ruolo", ["event_manager", "admin"]
        ).execute()
        return res.data or []
    except:
        return []
# ── TEMPLATE OFFERTE ──────────────────────────────────

def lista_template(user_id):
    """Restituisce i template dell'utente + quelli condivisi da altri."""
    sb = get_sb()
    try:
        res = sb.table("template_offerte").select(
            "*, creatore:utenti!template_offerte_created_by_fkey(nome, cognome)"
        ).or_(
            f"created_by.eq.{user_id},condiviso.eq.true"
        ).order("created_at", desc=True).execute()
        return res.data or []
    except:
        return []

def get_template(template_id):
    sb = get_sb()
    try:
        res = sb.table("template_offerte").select("*").eq("id", template_id).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except:
        return None

def crea_template(dati, user_id):
    sb = get_sb()
    try:
        dati["created_by"] = user_id
        res = sb.table("template_offerte").insert(dati).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        return None

def aggiorna_template(template_id, dati):
    sb = get_sb()
    try:
        from datetime import datetime
        dati["updated_at"] = datetime.utcnow().isoformat()
        sb.table("template_offerte").update(dati).eq("id", template_id).execute()
    except:
        pass

def elimina_template(template_id):
    sb = get_sb()
    try:
        sb.table("template_offerte").delete().eq("id", template_id).execute()
    except:
        pass

# ── AUTH ──────────────────────────────────────────────

def get_profilo_utente(user_id):
    sb = get_sb()
    try:
        res = sb.table("utenti").select("*").eq("id", user_id).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except:
        return None

def crea_utente_profilo(user_id, nome, cognome, email, ruolo):
    sb = get_sb()
    try:
        sb.table("utenti").insert({
            "id": user_id, "nome": nome, "cognome": cognome,
            "email": email, "ruolo": ruolo
        }).execute()
        return None
    except Exception as e:
        return str(e)

def lista_utenti():
    sb = get_sb()
    try:
        res = sb.table("utenti").select("*").order("cognome").execute()
        return res.data or []
    except:
        return []

def aggiorna_ruolo_utente(user_id, ruolo):
    sb = get_sb()
    sb.table("utenti").update({"ruolo": ruolo}).eq("id", user_id).execute()

def disattiva_utente(user_id):
    sb = get_sb()
    sb.table("utenti").update({"attivo": False}).eq("id", user_id).execute()

# ── CLIENTI ──────────────────────────────────────────

def lista_clienti(filtro_stato=None, filtro_testo=None):
    sb = get_sb()
    try:
        q = sb.table("clienti").select(
            "*, utenti!clienti_assegnato_a_fkey(nome, cognome)"
        ).order("created_at", desc=True)
        if filtro_stato:
            q = q.eq("stato", filtro_stato)
        if filtro_testo:
            q = q.or_(
                f"nome.ilike.%{filtro_testo}%,"
                f"cognome.ilike.%{filtro_testo}%,"
                f"ragione_sociale.ilike.%{filtro_testo}%,"
                f"email.ilike.%{filtro_testo}%"
            )
        res = q.execute()
        return res.data or []
    except:
        return []

def get_cliente(cliente_id):
    sb = get_sb()
    try:
        res = sb.table("clienti").select("*").eq("id", cliente_id).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except:
        return None

def crea_cliente(dati, user_id):
    sb = get_sb()
    try:
        dati["created_by"] = user_id
        res = sb.table("clienti").insert(dati).execute()
        return res.data[0] if res.data else None
    except:
        return None

def aggiorna_cliente(cliente_id, dati):
    sb = get_sb()
    try:
        from datetime import datetime
        dati["updated_at"] = datetime.utcnow().isoformat()
        sb.table("clienti").update(dati).eq("id", cliente_id).execute()
    except:
        pass

def elimina_cliente(cliente_id):
    sb = get_sb()
    try:
        sb.table("clienti").delete().eq("id", cliente_id).execute()
    except:
        pass

# ── DIARIO ────────────────────────────────────────────

def lista_diario(cliente_id):
    sb = get_sb()
    try:
        res = sb.table("diario").select(
            "*, utenti!diario_created_by_fkey(nome, cognome)"
        ).eq("cliente_id", cliente_id).order("data_contatto", desc=True).execute()
        return res.data or []
    except:
        return []

def crea_voce_diario(dati, user_id):
    sb = get_sb()
    try:
        dati["created_by"] = user_id
        res = sb.table("diario").insert(dati).execute()
        return res.data[0] if res.data else None
    except:
        return None

def aggiorna_voce_diario(voce_id, dati):
    sb = get_sb()
    try:
        sb.table("diario").update(dati).eq("id", voce_id).execute()
    except:
        pass

def elimina_voce_diario(voce_id):
    sb = get_sb()
    try:
        sb.table("diario").delete().eq("id", voce_id).execute()
    except:
        pass

def followup_oggi():
    sb = get_sb()
    try:
        from datetime import date
        oggi = date.today().isoformat()
        res = sb.table("diario").select(
            "*, clienti(nome, cognome, ragione_sociale, tipo)"
        ).eq("followup_fatto", False).eq("followup_data", oggi).execute()
        return res.data or []
    except:
        return []

def followup_prossimi7():
    sb = get_sb()
    try:
        from datetime import date, timedelta
        domani = (date.today() + timedelta(days=1)).isoformat()
        tra7 = (date.today() + timedelta(days=7)).isoformat()
        res = sb.table("diario").select(
            "*, clienti(nome, cognome, ragione_sociale, tipo)"
        ).eq("followup_fatto", False).gte(
            "followup_data", domani
        ).lte("followup_data", tra7).execute()
        return res.data or []
    except:
        return []

# ── OFFERTE ───────────────────────────────────────────

def lista_offerte(cliente_id=None):
    sb = get_sb()
    try:
        q = sb.table("offerte").select(
            "*, clienti(nome, cognome, ragione_sociale, tipo), "
            "utenti!offerte_created_by_fkey(nome, cognome)"
        ).order("created_at", desc=True)
        if cliente_id:
            q = q.eq("cliente_id", cliente_id)
        res = q.execute()
        return res.data or []
    except:
        return []

def get_offerta(offerta_id):
    sb = get_sb()
    try:
        res = sb.table("offerte").select("*").eq("id", offerta_id).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except:
        return None

def crea_offerta(dati, user_id):
    sb = get_sb()
    try:
        dati["created_by"] = user_id
        import datetime
        anno = datetime.date.today().year
        count_res = sb.table("offerte").select("id", count="exact").execute()
        n = (count_res.count or 0) + 1
        dati["numero"] = f"OFF-{anno}-{n:04d}"
        res = sb.table("offerte").insert(dati).execute()
        return res.data[0] if res.data else None
    except:
        return None

def aggiorna_offerta(offerta_id, dati):
    sb = get_sb()
    try:
        from datetime import datetime
        dati["updated_at"] = datetime.utcnow().isoformat()
        sb.table("offerte").update(dati).eq("id", offerta_id).execute()
    except:
        pass

def nuova_versione_offerta(offerta_id, user_id):
    sb = get_sb()
    try:
        orig = get_offerta(offerta_id)
        if not orig:
            return None
        nuova = {k: v for k, v in orig.items()
                 if k not in ("id", "created_at", "updated_at")}
        nuova["versione"] = orig["versione"] + 1
        nuova["offerta_padre"] = offerta_id
        nuova["stato"] = "bozza"
        nuova["created_by"] = user_id
        res = sb.table("offerte").insert(nuova).execute()
        return res.data[0] if res.data else None
    except:
        return None

# ── DOCUMENTI ─────────────────────────────────────────

def lista_documenti(cliente_id):
    sb = get_sb()
    try:
        res = sb.table("documenti").select(
            "*, utenti!documenti_created_by_fkey(nome, cognome)"
        ).eq("cliente_id", cliente_id).order("created_at", desc=True).execute()
        return res.data or []
    except:
        return []

def carica_documento(cliente_id, file_bytes, nome_file, tipo_file,
                     dimensione, categoria, note, user_id):
    sb = get_sb()
    import uuid
    path = f"{cliente_id}/{uuid.uuid4()}_{nome_file}"
    try:
        sb.storage.from_("documenti-clienti").upload(
            path, file_bytes, {"content-type": tipo_file})
        sb.table("documenti").insert({
            "cliente_id": cliente_id,
            "nome_file": nome_file,
            "storage_path": path,
            "tipo_file": tipo_file,
            "dimensione": dimensione,
            "categoria": categoria,
            "note": note,
            "created_by": user_id
        }).execute()
        return None
    except Exception as e:
        return str(e)

def scarica_documento(storage_path):
    sb = get_sb()
    try:
        return sb.storage.from_("documenti-clienti").download(storage_path)
    except:
        return None

def elimina_documento(doc_id, storage_path):
    sb = get_sb()
    try:
        sb.storage.from_("documenti-clienti").remove([storage_path])
        sb.table("documenti").delete().eq("id", doc_id).execute()
        return None
    except Exception as e:
        return str(e)

# ── DASHBOARD ─────────────────────────────────────────

def stats_dashboard():
    sb = get_sb()
    try:
        clienti = sb.table("clienti").select("stato, paese").execute()
        offerte = sb.table("offerte").select("stato, importo").execute()
        return {
            "tot_clienti": len(clienti.data) if clienti.data else 0,
            "clienti_data": clienti.data or [],
            "offerte_data": offerte.data or [],
        }
    except:
        return {
            "tot_clienti": 0,
            "clienti_data": [],
            "offerte_data": [],
        }

# ── MESSAGGI ──────────────────────────────────────────

def lista_messaggi_ricevuti(user_id):
    sb = get_sb()
    try:
        res = sb.table("messaggi").select(
            "*, mittente:utenti!messaggi_mittente_id_fkey(id, nome, cognome, email)"
        ).eq("destinatario_id", user_id).order("created_at", desc=True).execute()
        return res.data or []
    except:
        return []

def lista_messaggi_inviati(user_id):
    sb = get_sb()
    try:
        res = sb.table("messaggi").select(
            "*, destinatario:utenti!messaggi_destinatario_id_fkey(id, nome, cognome, email)"
        ).eq("mittente_id", user_id).order("created_at", desc=True).execute()
        return res.data or []
    except:
        return []

def lista_messaggi_non_letti(user_id):
    sb = get_sb()
    try:
        res = sb.table("messaggi").select(
            "*, mittente:utenti!messaggi_mittente_id_fkey(nome, cognome)"
        ).eq("destinatario_id", user_id).eq("letto", False).execute()
        return res.data or []
    except:
        return []

def invia_messaggio(mittente_id, destinatario_id, oggetto, corpo):
    sb = get_sb()
    try:
        sb.table("messaggi").insert({
            "mittente_id": mittente_id,
            "destinatario_id": destinatario_id,
            "oggetto": oggetto,
            "corpo": corpo,
            "letto": False
        }).execute()
        return None
    except Exception as e:
        return str(e)

def segna_come_letto(messaggio_id):
    sb = get_sb()
    try:
        sb.table("messaggi").update(
            {"letto": True}
        ).eq("id", messaggio_id).execute()
    except:
        pass

# ── CALENDARIO ────────────────────────────────────────

def get_autorizzazioni_calendario(utente_id):
    sb = get_sb()
    try:
        res = sb.table("calendario_autorizzazioni").select(
            "*, proprietario:utenti!calendario_autorizzazioni_calendario_di_fkey"
            "(id, nome, cognome)"
        ).eq("utente_id", utente_id).execute()
        return res.data or []
    except:
        return []

def get_calendari_visibili(utente_id):
    sb = get_sb()
    try:
        res = sb.table("calendario_autorizzazioni").select(
            "calendario_di"
        ).eq("utente_id", utente_id).eq("puo_vedere", True).execute()
        ids = [r["calendario_di"] for r in (res.data or [])]
        if utente_id not in ids:
            ids.append(utente_id)
        return ids
    except:
        return [utente_id]

def get_calendari_modificabili(utente_id):
    sb = get_sb()
    try:
        res = sb.table("calendario_autorizzazioni").select(
            "calendario_di"
        ).eq("utente_id", utente_id).eq("puo_modificare", True).execute()
        ids = [r["calendario_di"] for r in (res.data or [])]
        if utente_id not in ids:
            ids.append(utente_id)
        return ids
    except:
        return [utente_id]

def salva_autorizzazione_calendario(utente_id, calendario_di, puo_vedere, puo_modificare):
    sb = get_sb()
    try:
        sb.table("calendario_autorizzazioni").upsert({
            "utente_id": utente_id,
            "calendario_di": calendario_di,
            "puo_vedere": puo_vedere,
            "puo_modificare": puo_modificare,
        }, on_conflict="utente_id,calendario_di").execute()
        return None
    except Exception as e:
        return str(e)

def elimina_autorizzazione_calendario(utente_id, calendario_di):
    sb = get_sb()
    try:
        sb.table("calendario_autorizzazioni").delete().eq(
            "utente_id", utente_id
        ).eq("calendario_di", calendario_di).execute()
        return None
    except Exception as e:
        return str(e)

def eventi_del_mese_multi(anno, mese, utenti_ids):
    sb = get_sb()
    try:
        import calendar as cal_lib
        primo = f"{anno}-{mese:02d}-01"
        ultimo_giorno = cal_lib.monthrange(anno, mese)[1]
        ultimo = f"{anno}-{mese:02d}-{ultimo_giorno}T23:59:59"
        res = sb.table("calendario").select(
            "*, proprietario:utenti!calendario_proprietario_id_fkey(id, nome, cognome)"
        ).in_("proprietario_id", utenti_ids).gte(
            "data_inizio", primo
        ).lte("data_inizio", ultimo).execute()
        return res.data or []
    except:
        return []

def eventi_oggi_multi(utenti_ids):
    sb = get_sb()
    try:
        from datetime import date
        oggi = date.today().isoformat()
        res = sb.table("calendario").select(
            "*, proprietario:utenti!calendario_proprietario_id_fkey(id, nome, cognome)"
        ).in_("proprietario_id", utenti_ids).gte(
            "data_inizio", f"{oggi}T00:00:00"
        ).lte(
            "data_inizio", f"{oggi}T23:59:59"
        ).order("data_inizio").execute()
        return res.data or []
    except:
        return []

def crea_evento(dati, user_id):
    sb = get_sb()
    try:
        dati["creato_da"] = user_id
        res = sb.table("calendario").insert(dati).execute()
        return res.data[0] if res.data else None
    except:
        return None

def aggiorna_evento(evento_id, dati):
    sb = get_sb()
    try:
        from datetime import datetime
        dati["updated_at"] = datetime.utcnow().isoformat()
        sb.table("calendario").update(dati).eq("id", evento_id).execute()
    except:
        pass

def elimina_evento(evento_id):
    sb = get_sb()
    try:
        sb.table("calendario").delete().eq("id", evento_id).execute()
    except:
        pass
