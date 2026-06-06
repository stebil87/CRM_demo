from supabase import create_client
import streamlit as st

@st.cache_resource
def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# ── AUTH ──────────────────────────────────────────────

def login_utente(email, password):
    sb = get_supabase()
    try:
        res = sb.auth.sign_in_with_password({"email": email, "password": password})
        return res.user, None
    except Exception as e:
        return None, str(e)

def logout_utente():
    sb = get_supabase()
    try:
        sb.auth.sign_out()
    except:
        pass

def get_profilo_utente(user_id):
    sb = get_supabase()
    try:
        res = sb.table("utenti").select("*").eq("id", user_id).single().execute()
        return res.data
    except:
        return None

def crea_utente_profilo(user_id, nome, cognome, email, ruolo):
    sb = get_supabase()
    try:
        sb.table("utenti").insert({
            "id": user_id, "nome": nome, "cognome": cognome,
            "email": email, "ruolo": ruolo
        }).execute()
        return None
    except Exception as e:
        return str(e)

def lista_utenti():
    sb = get_supabase()
    res = sb.table("utenti").select("*").order("cognome").execute()
    return res.data or []

def aggiorna_ruolo_utente(user_id, ruolo):
    sb = get_supabase()
    sb.table("utenti").update({"ruolo": ruolo}).eq("id", user_id).execute()

def disattiva_utente(user_id):
    sb = get_supabase()
    sb.table("utenti").update({"attivo": False}).eq("id", user_id).execute()

# ── CLIENTI ──────────────────────────────────────────

def lista_clienti(filtro_stato=None, filtro_testo=None):
    sb = get_supabase()
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

def get_cliente(cliente_id):
    sb = get_supabase()
    res = sb.table("clienti").select("*").eq("id", cliente_id).single().execute()
    return res.data

def crea_cliente(dati, user_id):
    sb = get_supabase()
    dati["created_by"] = user_id
    res = sb.table("clienti").insert(dati).execute()
    return res.data[0] if res.data else None

def aggiorna_cliente(cliente_id, dati):
    sb = get_supabase()
    from datetime import datetime
    dati["updated_at"] = datetime.utcnow().isoformat()
    sb.table("clienti").update(dati).eq("id", cliente_id).execute()

def elimina_cliente(cliente_id):
    sb = get_supabase()
    sb.table("clienti").delete().eq("id", cliente_id).execute()

# ── DIARIO ────────────────────────────────────────────

def lista_diario(cliente_id):
    sb = get_supabase()
    res = sb.table("diario").select(
        "*, utenti!diario_created_by_fkey(nome, cognome)"
    ).eq("cliente_id", cliente_id).order("data_contatto", desc=True).execute()
    return res.data or []

def crea_voce_diario(dati, user_id):
    sb = get_supabase()
    dati["created_by"] = user_id
    res = sb.table("diario").insert(dati).execute()
    return res.data[0] if res.data else None

def aggiorna_voce_diario(voce_id, dati):
    sb = get_supabase()
    sb.table("diario").update(dati).eq("id", voce_id).execute()

def elimina_voce_diario(voce_id):
    sb = get_supabase()
    sb.table("diario").delete().eq("id", voce_id).execute()

def followup_in_scadenza(user_id=None):
    sb = get_supabase()
    from datetime import date, timedelta
    oggi = date.today().isoformat()
    tra7 = (date.today() + timedelta(days=7)).isoformat()
    q = sb.table("diario").select(
        "*, clienti(nome, cognome, ragione_sociale, tipo)"
    ).eq("followup_fatto", False).gte("followup_data", oggi).lte("followup_data", tra7)
    res = q.execute()
    return res.data or []

# ── OFFERTE ───────────────────────────────────────────

def lista_offerte(cliente_id=None):
    sb = get_supabase()
    q = sb.table("offerte").select(
        "*, clienti(nome, cognome, ragione_sociale, tipo), utenti!offerte_created_by_fkey(nome, cognome)"
    ).order("created_at", desc=True)
    if cliente_id:
        q = q.eq("cliente_id", cliente_id)
    res = q.execute()
    return res.data or []

def get_offerta(offerta_id):
    sb = get_supabase()
    res = sb.table("offerte").select("*").eq("id", offerta_id).single().execute()
    return res.data

def crea_offerta(dati, user_id):
    sb = get_supabase()
    dati["created_by"] = user_id
    # genera numero offerta
    anno = __import__('datetime').date.today().year
    count_res = sb.table("offerte").select("id", count="exact").execute()
    n = (count_res.count or 0) + 1
    dati["numero"] = f"OFF-{anno}-{n:04d}"
    res = sb.table("offerte").insert(dati).execute()
    return res.data[0] if res.data else None

def aggiorna_offerta(offerta_id, dati):
    sb = get_supabase()
    from datetime import datetime
    dati["updated_at"] = datetime.utcnow().isoformat()
    sb.table("offerte").update(dati).eq("id", offerta_id).execute()

def nuova_versione_offerta(offerta_id, user_id):
    """Crea una nuova versione dell'offerta, mantiene la vecchia."""
    sb = get_supabase()
    orig = get_offerta(offerta_id)
    if not orig:
        return None
    nuova = {k: v for k, v in orig.items() if k not in ("id", "created_at", "updated_at")}
    nuova["versione"] = orig["versione"] + 1
    nuova["offerta_padre"] = offerta_id
    nuova["stato"] = "bozza"
    nuova["created_by"] = user_id
    res = sb.table("offerte").insert(nuova).execute()
    return res.data[0] if res.data else None

# ── DOCUMENTI ─────────────────────────────────────────

def lista_documenti(cliente_id):
    sb = get_supabase()
    res = sb.table("documenti").select(
        "*, utenti!documenti_created_by_fkey(nome, cognome)"
    ).eq("cliente_id", cliente_id).order("created_at", desc=True).execute()
    return res.data or []

def carica_documento(cliente_id, file_bytes, nome_file, tipo_file, dimensione, categoria, note, user_id):
    sb = get_supabase()
    import uuid
    path = f"{cliente_id}/{uuid.uuid4()}_{nome_file}"
    try:
        sb.storage.from_("documenti-clienti").upload(path, file_bytes, {"content-type": tipo_file})
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
    sb = get_supabase()
    try:
        res = sb.storage.from_("documenti-clienti").download(storage_path)
        return res
    except:
        return None

def elimina_documento(doc_id, storage_path):
    sb = get_supabase()
    try:
        sb.storage.from_("documenti-clienti").remove([storage_path])
        sb.table("documenti").delete().eq("id", doc_id).execute()
        return None
    except Exception as e:
        return str(e)

# ── DASHBOARD ─────────────────────────────────────────

def stats_dashboard():
    sb = get_supabase()
    clienti = sb.table("clienti").select("stato", count="exact").execute()
    offerte = sb.table("offerte").select("stato, importo").execute()
    diario_oggi = sb.table("diario").select("id", count="exact").gte(
        "created_at", __import__('datetime').date.today().isoformat()
    ).execute()
    return {
        "tot_clienti": clienti.count or 0,
        "clienti_data": clienti.data or [],
        "offerte_data": offerte.data or [],
        "diario_oggi": diario_oggi.count or 0,
    }