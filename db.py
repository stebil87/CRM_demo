from supabase import create_client
import streamlit as st
from datetime import datetime, date, timedelta
import calendar as cal_lib
import time
import functools

try:
    import pytz
    TIMEZONE = pytz.timezone("Europe/Zurich")
except:
    TIMEZONE = None

def ora_locale():
    if TIMEZONE:
        return datetime.now(TIMEZONE)
    return datetime.now()

# ── PROFILER ──────────────────────────────────────────

PROFILING = True

def profila(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not PROFILING:
            return func(*args, **kwargs)
        t0 = time.time()
        risultato = func(*args, **kwargs)
        ms = (time.time() - t0) * 1000
        livello = "🔴 LENTO" if ms > 500 else "🟡 OK" if ms > 100 else "🟢 veloce"
        print(f"[DB] {func.__name__:<40} {ms:>7.1f}ms  {livello}")
        return risultato
    return wrapper

@st.cache_data(ttl=60)
@profila
def kpi_operativi():
    sb = get_sb()
    try:
        from datetime import date, timedelta
        oggi = date.today().isoformat()
        tra30 = (date.today() + timedelta(days=30)).isoformat()

        # Offerte in attesa
        offerte = sb.table("offerte").select("stato, importo").execute()
        offerte_data = offerte.data or []
        in_attesa = [o for o in offerte_data if o.get("stato") == "inviata"]
        accettate = [o for o in offerte_data if o.get("stato") == "accettata"]
        chiuse_neg = [o for o in offerte_data if o.get("stato") in ("rifiutata", "scaduta")]

        n_attesa = len(in_attesa)
        valore_pipeline = sum(float(o.get("importo") or 0) for o in in_attesa)
        tot_chiuse = len(accettate) + len(chiuse_neg)
        tasso = round(len(accettate) / tot_chiuse * 100) if tot_chiuse > 0 else 0

        # Eventi prossimi 30 giorni
        ev = sb.table("eventi_catering").select(
            "id, titolo, data_inizio, stato"
        ).gte("data_inizio", oggi).lte(
            "data_inizio", tra30 + "T23:59:59"
        ).not_.in_("stato", ["annullato"]).order("data_inizio").execute()
        eventi_data = ev.data or []
        n_eventi = len(eventi_data)
        prossimo = eventi_data[0] if eventi_data else None

        return {
            "n_attesa": n_attesa,
            "valore_pipeline": valore_pipeline,
            "tasso_chiusura": tasso,
            "n_eventi_30gg": n_eventi,
            "prossimo_evento": prossimo,
        }
    except Exception as e:
        print(f"ERRORE kpi_operativi: {e}")
        return {
            "n_attesa": 0,
            "valore_pipeline": 0,
            "tasso_chiusura": 0,
            "n_eventi_30gg": 0,
            "prossimo_evento": None,
        }

# ── CLIENT ────────────────────────────────────────────

@st.cache_resource
def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def get_sb():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)

# ── LOG ───────────────────────────────────────────────

def log_attivita(utente_id, azione, entita, entita_id=None, dettagli=None):
    sb = get_sb()
    try:
        sb.table("activity_log").insert({
            "utente_id": utente_id,
            "azione": azione,
            "entita": entita,
            "entita_id": str(entita_id) if entita_id else None,
            "dettagli": dettagli or {}
        }).execute()
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
        _invalida_cache_utenti()
        return None
    except Exception as e:
        return str(e)

@st.cache_data(ttl=120)
@profila
def lista_utenti():
    sb = get_sb()
    try:
        res = sb.table("utenti").select("*").order("cognome").execute()
        return res.data or []
    except:
        return []

def _invalida_cache_utenti():
    lista_utenti.clear()

def aggiorna_ruolo_utente(user_id, ruolo):
    sb = get_sb()
    sb.table("utenti").update({"ruolo": ruolo}).eq("id", user_id).execute()
    _invalida_cache_utenti()

def disattiva_utente(user_id):
    sb = get_sb()
    sb.table("utenti").update({"attivo": False}).eq("id", user_id).execute()
    _invalida_cache_utenti()

@st.cache_data(ttl=120)
@profila
def utenti_event_manager():
    sb = get_sb()
    try:
        res = sb.table("utenti").select("*").in_(
            "ruolo", ["event_manager", "admin"]
        ).execute()
        return res.data or []
    except:
        return []

# ── CLIENTI ──────────────────────────────────────────

@st.cache_data(ttl=60)
@profila
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

@st.cache_data(ttl=60)
@profila
def get_cliente(cliente_id):
    sb = get_sb()
    try:
        res = sb.table("clienti").select("*").eq("id", cliente_id).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except:
        return None

@st.cache_data(ttl=120)
@profila
def compleanni_in_arrivo(giorni=30):
    sb = get_sb()
    try:
        oggi = date.today()
        risultati = []
        res = sb.table("clienti").select(
            "id, nome, cognome, data_nascita, email, telefono"
        ).eq("tipo", "fisica").execute()

        for c in (res.data or []):
            try:
                dn = c.get("data_nascita", "")
                if not dn:
                    continue
                if "/" in str(dn):
                    parts = str(dn).split("/")
                    giorno, mese = int(parts[0]), int(parts[1])
                else:
                    parts = str(dn).split("-")
                    giorno, mese = int(parts[2]), int(parts[1])
                try:
                    compleanno = date(oggi.year, mese, giorno)
                except:
                    continue
                if compleanno < oggi:
                    compleanno = date(oggi.year + 1, mese, giorno)
                giorni_mancanti = (compleanno - oggi).days
                if giorni_mancanti <= giorni:
                    c["compleanno"] = compleanno.isoformat()
                    c["giorni_mancanti"] = giorni_mancanti
                    risultati.append(c)
            except:
                continue
        return sorted(risultati, key=lambda x: x["giorni_mancanti"])
    except:
        return []

def _invalida_cache_clienti():
    lista_clienti.clear()
    get_cliente.clear()
    stats_dashboard.clear()
    try:
        compleanni_in_arrivo.clear()
    except:
        pass

def crea_cliente(dati, user_id):
    sb = get_sb()
    try:
        dati["created_by"] = user_id
        res = sb.table("clienti").insert(dati).execute()
        _invalida_cache_clienti()
        if res.data:
            log_attivita(user_id, "creato", "cliente", res.data[0]["id"], {
                "nome": dati.get("ragione_sociale") or
                        f"{dati.get('nome','')} {dati.get('cognome','')}".strip()
            })
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"ERRORE crea_cliente: {e}")
        return None

def aggiorna_cliente(cliente_id, dati, user_id=None):
    sb = get_sb()
    try:
        dati["updated_at"] = datetime.utcnow().isoformat()
        sb.table("clienti").update(dati).eq("id", cliente_id).execute()
        _invalida_cache_clienti()
        if user_id:
            log_attivita(user_id, "modificato", "cliente", cliente_id)
    except Exception as e:
        print(f"ERRORE aggiorna_cliente: {e}")

def elimina_cliente(cliente_id, user_id=None):
    sb = get_sb()
    try:
        sb.table("clienti").delete().eq("id", cliente_id).execute()
        _invalida_cache_clienti()
        if user_id:
            log_attivita(user_id, "eliminato", "cliente", cliente_id)
    except Exception as e:
        print(f"ERRORE elimina_cliente: {e}")

# ── DIARIO ────────────────────────────────────────────

@st.cache_data(ttl=30)
@profila
def lista_diario(cliente_id):
    sb = get_sb()
    try:
        res = sb.table("diario").select(
            "*, utenti!diario_created_by_fkey(nome, cognome)"
        ).eq("cliente_id", cliente_id).order("data_contatto", desc=True).execute()
        return res.data or []
    except:
        return []

def _invalida_cache_diario():
    lista_diario.clear()
    followup_oggi.clear()
    followup_prossimi7.clear()

def crea_voce_diario(dati, user_id):
    sb = get_sb()
    try:
        dati["created_by"] = user_id
        res = sb.table("diario").insert(dati).execute()
        _invalida_cache_diario()
        if res.data:
            log_attivita(user_id, "creato", "diario", res.data[0]["id"], {
                "tipo": dati.get("tipo", ""),
                "titolo": dati.get("titolo", "")
            })
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"ERRORE crea_voce_diario: {e}")
        return None

def aggiorna_voce_diario(voce_id, dati, user_id=None):
    sb = get_sb()
    try:
        sb.table("diario").update(dati).eq("id", voce_id).execute()
        _invalida_cache_diario()
        if user_id:
            log_attivita(user_id, "modificato", "diario", voce_id)
    except Exception as e:
        print(f"ERRORE aggiorna_voce_diario: {e}")

def elimina_voce_diario(voce_id, user_id=None):
    sb = get_sb()
    try:
        sb.table("diario").delete().eq("id", voce_id).execute()
        _invalida_cache_diario()
        if user_id:
            log_attivita(user_id, "eliminato", "diario", voce_id)
    except Exception as e:
        print(f"ERRORE elimina_voce_diario: {e}")

@st.cache_data(ttl=60)
@profila
def followup_oggi():
    sb = get_sb()
    try:
        oggi = date.today().isoformat()
        res = sb.table("diario").select(
            "*, clienti(nome, cognome, ragione_sociale, tipo)"
        ).eq("followup_fatto", False).eq("followup_data", oggi).execute()
        return res.data or []
    except:
        return []

@st.cache_data(ttl=60)
@profila
def followup_prossimi7():
    sb = get_sb()
    try:
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

@st.cache_data(ttl=30)
@profila
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

@st.cache_data(ttl=30)
@profila
def get_offerta(offerta_id):
    sb = get_sb()
    try:
        res = sb.table("offerte").select("*").eq("id", offerta_id).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except:
        return []

def _invalida_cache_offerte():
    lista_offerte.clear()
    get_offerta.clear()
    stats_dashboard.clear()

def crea_offerta(dati, user_id):
    sb = get_sb()
    try:
        dati["created_by"] = user_id
        anno = date.today().year
        count_res = sb.table("offerte").select("id", count="exact").execute()
        n = (count_res.count or 0) + 1
        dati["numero"] = f"OFF-{anno}-{n:04d}"
        res = sb.table("offerte").insert(dati).execute()
        _invalida_cache_offerte()
        if res.data:
            log_attivita(user_id, "creato", "offerta", res.data[0]["id"], {
                "numero": dati["numero"],
                "titolo": dati.get("titolo", "")
            })
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"ERRORE crea_offerta: {e}")
        return None

def aggiorna_offerta(offerta_id, dati, user_id=None):
    sb = get_sb()
    try:
        dati["updated_at"] = datetime.utcnow().isoformat()
        sb.table("offerte").update(dati).eq("id", offerta_id).execute()
        _invalida_cache_offerte()
        if user_id:
            log_attivita(user_id, "modificato", "offerta", offerta_id, {
                "stato": dati.get("stato", "")
            })
    except Exception as e:
        print(f"ERRORE aggiorna_offerta: {e}")

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
        _invalida_cache_offerte()
        if res.data:
            log_attivita(user_id, "creato", "offerta", res.data[0]["id"], {
                "numero": nuova.get("numero", ""),
                "versione": nuova["versione"]
            })
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"ERRORE nuova_versione_offerta: {e}")
        return None

# ── DOCUMENTI ─────────────────────────────────────────

@st.cache_data(ttl=60)
@profila
def lista_documenti(cliente_id):
    sb = get_sb()
    try:
        res = sb.table("documenti").select(
            "*, utenti!documenti_created_by_fkey(nome, cognome)"
        ).eq("cliente_id", cliente_id).order("created_at", desc=True).execute()
        return res.data or []
    except:
        return []

def _invalida_cache_documenti():
    lista_documenti.clear()

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
        _invalida_cache_documenti()
        log_attivita(user_id, "caricato", "documento", cliente_id, {
            "file": nome_file
        })
        return None
    except Exception as e:
        return str(e)

def scarica_documento(storage_path):
    sb = get_sb()
    try:
        return sb.storage.from_("documenti-clienti").download(storage_path)
    except:
        return None

def elimina_documento(doc_id, storage_path, user_id=None):
    sb = get_sb()
    try:
        sb.storage.from_("documenti-clienti").remove([storage_path])
        sb.table("documenti").delete().eq("id", doc_id).execute()
        _invalida_cache_documenti()
        if user_id:
            log_attivita(user_id, "eliminato", "documento", doc_id)
        return None
    except Exception as e:
        return str(e)

# ── DASHBOARD ─────────────────────────────────────────

@st.cache_data(ttl=60)
@profila
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
        return {"tot_clienti": 0, "clienti_data": [], "offerte_data": []}

# ── MESSAGGI ──────────────────────────────────────────

@st.cache_data(ttl=15)
@profila
def lista_messaggi_ricevuti(user_id):
    sb = get_sb()
    try:
        res = sb.table("messaggi").select(
            "*, mittente:utenti!messaggi_mittente_id_fkey(id, nome, cognome, email)"
        ).eq("destinatario_id", user_id).order("created_at", desc=True).execute()
        return res.data or []
    except:
        return []

@st.cache_data(ttl=15)
@profila
def lista_messaggi_inviati(user_id):
    sb = get_sb()
    try:
        res = sb.table("messaggi").select(
            "*, destinatario:utenti!messaggi_destinatario_id_fkey(id, nome, cognome, email)"
        ).eq("mittente_id", user_id).order("created_at", desc=True).execute()
        return res.data or []
    except:
        return []

@st.cache_data(ttl=15)
@profila
def lista_messaggi_non_letti(user_id):
    sb = get_sb()
    try:
        res = sb.table("messaggi").select(
            "*, mittente:utenti!messaggi_mittente_id_fkey(nome, cognome)"
        ).eq("destinatario_id", user_id).eq("letto", False).execute()
        return res.data or []
    except:
        return []

def _invalida_cache_messaggi():
    lista_messaggi_ricevuti.clear()
    lista_messaggi_inviati.clear()
    lista_messaggi_non_letti.clear()

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
        _invalida_cache_messaggi()
        log_attivita(mittente_id, "inviato", "messaggio", None, {
            "oggetto": oggetto
        })
        return None
    except Exception as e:
        return str(e)

def segna_come_letto(messaggio_id):
    sb = get_sb()
    try:
        sb.table("messaggi").update(
            {"letto": True}
        ).eq("id", messaggio_id).execute()
        _invalida_cache_messaggi()
    except:
        pass

# ── CALENDARIO ────────────────────────────────────────

@st.cache_data(ttl=30)
@profila
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

@st.cache_data(ttl=30)
@profila
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

@st.cache_data(ttl=30)
@profila
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

def _invalida_cache_calendario():
    get_autorizzazioni_calendario.clear()
    get_calendari_visibili.clear()
    get_calendari_modificabili.clear()
    eventi_del_mese_multi.clear()
    eventi_oggi_multi.clear()

def salva_autorizzazione_calendario(utente_id, calendario_di,
                                    puo_vedere, puo_modificare):
    sb = get_sb()
    try:
        sb.table("calendario_autorizzazioni").upsert({
            "utente_id": utente_id,
            "calendario_di": calendario_di,
            "puo_vedere": puo_vedere,
            "puo_modificare": puo_modificare,
        }, on_conflict="utente_id,calendario_di").execute()
        _invalida_cache_calendario()
        return None
    except Exception as e:
        return str(e)

def elimina_autorizzazione_calendario(utente_id, calendario_di):
    sb = get_sb()
    try:
        sb.table("calendario_autorizzazioni").delete().eq(
            "utente_id", utente_id
        ).eq("calendario_di", calendario_di).execute()
        _invalida_cache_calendario()
        return None
    except Exception as e:
        return str(e)

@st.cache_data(ttl=30)
@profila
def eventi_del_mese_multi(anno, mese, utenti_ids_tuple):
    sb = get_sb()
    utenti_ids = list(utenti_ids_tuple)
    try:
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

@st.cache_data(ttl=30)
@profila
def eventi_oggi_multi(utenti_ids_tuple):
    sb = get_sb()
    utenti_ids = list(utenti_ids_tuple)
    try:
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
        _invalida_cache_calendario()
        if res.data:
            log_attivita(user_id, "creato", "calendario", res.data[0]["id"], {
                "titolo": dati.get("titolo", "")
            })
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"ERRORE crea_evento: {e}")
        return None

def aggiorna_evento(evento_id, dati, user_id=None):
    sb = get_sb()
    try:
        dati["updated_at"] = datetime.utcnow().isoformat()
        sb.table("calendario").update(dati).eq("id", evento_id).execute()
        _invalida_cache_calendario()
        if user_id:
            log_attivita(user_id, "modificato", "calendario", evento_id)
    except Exception as e:
        print(f"ERRORE aggiorna_evento: {e}")

def elimina_evento(evento_id, user_id=None):
    sb = get_sb()
    try:
        sb.table("calendario").delete().eq("id", evento_id).execute()
        _invalida_cache_calendario()
        if user_id:
            log_attivita(user_id, "eliminato", "calendario", evento_id)
    except Exception as e:
        print(f"ERRORE elimina_evento: {e}")

# ── NOTE DASHBOARD ────────────────────────────────────

@st.cache_data(ttl=30)
@profila
def lista_note(utente_id):
    sb = get_sb()
    try:
        res = sb.table("note_dashboard").select("*").eq(
            "utente_id", utente_id
        ).order("updated_at", desc=True).execute()
        return res.data or []
    except:
        return []

def _invalida_cache_note():
    lista_note.clear()

def crea_nota(utente_id, testo, colore="#fff9c4"):
    sb = get_sb()
    try:
        res = sb.table("note_dashboard").insert({
            "utente_id": utente_id,
            "testo": testo,
            "colore": colore
        }).execute()
        _invalida_cache_note()
        return res.data[0] if res.data else None
    except:
        return None

def aggiorna_nota(nota_id, testo, colore):
    sb = get_sb()
    try:
        sb.table("note_dashboard").update({
            "testo": testo,
            "colore": colore,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", nota_id).execute()
        _invalida_cache_note()
    except:
        pass

def elimina_nota(nota_id):
    sb = get_sb()
    try:
        sb.table("note_dashboard").delete().eq("id", nota_id).execute()
        _invalida_cache_note()
    except:
        pass

# ── TEMPLATE OFFERTE ──────────────────────────────────

def lista_template(user_id):
    from supabase import create_client
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_SERVICE_KEY"]
    sb = create_client(url, key)
    try:
        res = sb.table("template_offerte").select("*").eq(
            "created_by", user_id
        ).order("created_at", desc=True).execute()
        miei = res.data or []

        res_cond = sb.table("template_condivisioni").select(
            "template_id"
        ).eq("utente_id", user_id).execute()
        ids_condivisi = [r["template_id"] for r in (res_cond.data or [])]

        condivisi = []
        if ids_condivisi:
            res_c = sb.table("template_offerte").select("*").in_(
                "id", ids_condivisi
            ).execute()
            condivisi = res_c.data or []

        return miei + condivisi
    except:
        return []

@st.cache_data(ttl=60)
@profila
def get_template(template_id):
    sb = get_sb()
    try:
        res = sb.table("template_offerte").select("*").eq(
            "id", template_id
        ).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except:
        return None

def _invalida_cache_template():
    get_template.clear()

def crea_template(dati, user_id):
    sb = get_sb()
    try:
        dati["created_by"] = user_id
        dati.pop("condiviso", None)
        res = sb.table("template_offerte").insert(dati).execute()
        _invalida_cache_template()
        if res.data:
            log_attivita(user_id, "creato", "template", res.data[0]["id"], {
                "titolo": dati.get("titolo", "")
            })
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"ERRORE crea_template: {e}")
        return None

def aggiorna_template(template_id, dati):
    sb = get_sb()
    try:
        dati["updated_at"] = datetime.utcnow().isoformat()
        sb.table("template_offerte").update(dati).eq(
            "id", template_id
        ).execute()
        _invalida_cache_template()
    except Exception as e:
        print(f"ERRORE aggiorna_template: {e}")

def elimina_template(template_id):
    sb = get_sb()
    try:
        sb.table("template_offerte").delete().eq("id", template_id).execute()
        _invalida_cache_template()
    except Exception as e:
        print(f"ERRORE elimina_template: {e}")

def get_condivisioni_template(template_id):
    sb = get_sb()
    try:
        res = sb.table("template_condivisioni").select(
            "*, utente:utenti(id, nome, cognome, email)"
        ).eq("template_id", template_id).execute()
        return res.data or []
    except:
        return []

def condividi_template(template_id, utente_id):
    sb = get_sb()
    try:
        sb.table("template_condivisioni").upsert({
            "template_id": template_id,
            "utente_id": utente_id,
        }, on_conflict="template_id,utente_id").execute()
        _invalida_cache_template()
        return None
    except Exception as e:
        return str(e)

def rimuovi_condivisione_template(template_id, utente_id):
    sb = get_sb()
    try:
        sb.table("template_condivisioni").delete().eq(
            "template_id", template_id
        ).eq("utente_id", utente_id).execute()
        _invalida_cache_template()
        return None
    except Exception as e:
        return str(e)

# ── EVENTI CATERING ───────────────────────────────────

@st.cache_data(ttl=30)
@profila
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

@st.cache_data(ttl=30)
@profila
def get_evento_catering(evento_id):
    sb = get_sb()
    try:
        res = sb.table("eventi_catering").select(
            "*, cliente:clienti(nome, cognome, ragione_sociale, tipo, "
            "email, telefono, indirizzo, citta),"
            "offerta:offerte(numero, titolo, importo, valuta, righe, descrizione),"
            "creatore:utenti!eventi_catering_creato_da_fkey(nome, cognome),"
            "manager:utenti!eventi_catering_event_manager_id_fkey(nome, cognome)"
        ).eq("id", evento_id).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except:
        return None

def _invalida_cache_eventi():
    lista_eventi_catering.clear()
    get_evento_catering.clear()

def crea_evento_catering(dati, user_id):
    sb = get_sb()
    try:
        dati["creato_da"] = user_id
        res = sb.table("eventi_catering").insert(dati).execute()
        _invalida_cache_eventi()
        if res.data:
            log_attivita(user_id, "creato", "evento", res.data[0]["id"], {
                "titolo": dati.get("titolo", "")
            })
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"ERRORE crea_evento_catering: {e}")
        return None

def aggiorna_evento_catering(evento_id, dati, user_id=None):
    sb = get_sb()
    try:
        dati["updated_at"] = datetime.utcnow().isoformat()
        sb.table("eventi_catering").update(dati).eq("id", evento_id).execute()
        _invalida_cache_eventi()
        if user_id:
            log_attivita(user_id, "modificato", "evento", evento_id, {
                "stato": dati.get("stato", "")
            })
    except Exception as e:
        print(f"ERRORE aggiorna_evento_catering: {e}")

@st.cache_data(ttl=30)
@profila
def lista_collaboratori_evento(evento_id):
    sb = get_sb()
    try:
        res = sb.table("eventi_collaboratori").select(
            "*, utente:utenti(nome, cognome, email)"
        ).eq("evento_id", evento_id).execute()
        return res.data or []
    except:
        return []

def _invalida_cache_collaboratori():
    lista_collaboratori_evento.clear()
    eventi_assegnati_a_utente.clear()

def aggiungi_collaboratore(evento_id, utente_id=None, nome_esterno=None,
                           email_esterno=None, ruolo=None):
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
        _invalida_cache_collaboratori()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"ERRORE aggiungi_collaboratore: {e}")
        return None

def rimuovi_collaboratore(collab_id):
    sb = get_sb()
    try:
        sb.table("eventi_collaboratori").delete().eq("id", collab_id).execute()
        _invalida_cache_collaboratori()
    except Exception as e:
        print(f"ERRORE rimuovi_collaboratore: {e}")

def segna_collaboratore_avvisato(collab_id):
    sb = get_sb()
    try:
        sb.table("eventi_collaboratori").update(
            {"avvisato": True}
        ).eq("id", collab_id).execute()
        _invalida_cache_collaboratori()
    except Exception as e:
        print(f"ERRORE segna_collaboratore_avvisato: {e}")

@st.cache_data(ttl=30)
@profila
def lista_allegati_evento(evento_id):
    sb = get_sb()
    try:
        res = sb.table("eventi_allegati").select("*").eq(
            "evento_id", evento_id
        ).execute()
        return res.data or []
    except:
        return []

def _invalida_cache_allegati_evento():
    lista_allegati_evento.clear()

def carica_allegato_evento(evento_id, file_bytes, nome_file,
                           tipo_file, dimensione, user_id):
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
        _invalida_cache_allegati_evento()
        log_attivita(user_id, "caricato", "allegato_evento", evento_id, {
            "file": nome_file
        })
        return None
    except Exception as e:
        return str(e)

def scarica_allegato_evento(storage_path):
    sb = get_sb()
    try:
        return sb.storage.from_("eventi-allegati").download(storage_path)
    except:
        return None

@st.cache_data(ttl=30)
@profila
def lista_ore_evento(evento_id):
    sb = get_sb()
    try:
        res = sb.table("ore_evento").select(
            "*, utente:utenti(nome, cognome)"
        ).eq("evento_id", evento_id).execute()
        return res.data or []
    except:
        return []

def _invalida_cache_ore():
    lista_ore_evento.clear()

def inserisci_ore(dati):
    sb = get_sb()
    try:
        res = sb.table("ore_evento").insert(dati).execute()
        _invalida_cache_ore()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"ERRORE inserisci_ore: {e}")
        return None

@st.cache_data(ttl=30)
@profila
def eventi_assegnati_a_utente(utente_id):
    sb = get_sb()
    try:
        res = sb.table("eventi_collaboratori").select(
            "*, evento:eventi_catering(id, titolo, data_fine, stato)"
        ).eq("utente_id", utente_id).execute()
        return res.data or []
    except:
        return []

# ── INBOX EMAIL CONDIVISA ─────────────────────────────

def lista_inbox_nuove():
    sb = get_sb()
    try:
        res = sb.table("inbox_email").select(
            "*, gestore:utenti!inbox_email_presa_in_carico_da_fkey(nome, cognome)"
        ).eq("presa_in_carico", False).order(
            "data_ricezione", desc=True
        ).execute()
        return res.data or []
    except:
        return []

def lista_inbox_storico():
    sb = get_sb()
    try:
        res = sb.table("inbox_email").select(
            "*, gestore:utenti!inbox_email_presa_in_carico_da_fkey(nome, cognome)"
        ).eq("presa_in_carico", True).order(
            "data_ricezione", desc=True
        ).execute()
        return res.data or []
    except:
        return []

def prendi_in_carico_email(email_id, utente_id):
    sb = get_sb()
    try:
        sb.table("inbox_email").update({
            "presa_in_carico": True,
            "presa_in_carico_da": utente_id,
            "presa_in_carico_at": datetime.utcnow().isoformat(),
            "letta": True
        }).eq("id", email_id).execute()
        log_attivita(utente_id, "preso_in_carico", "email", email_id)
        return None
    except Exception as e:
        return str(e)

def inserisci_email_inbox(mittente, oggetto, corpo):
    sb = get_sb()
    try:
        sb.table("inbox_email").insert({
            "mittente": mittente,
            "oggetto": oggetto,
            "corpo": corpo,
        }).execute()
        return None
    except Exception as e:
        return str(e)
