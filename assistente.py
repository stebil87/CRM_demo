import streamlit as st
import json
import re
from datetime import datetime, date, timedelta
from typing import Optional

# ── IMPORT DB ─────────────────────────────────────────
from db import (
    lista_clienti, get_cliente, crea_cliente,
    lista_utenti, invia_messaggio,
    crea_voce_diario, lista_diario,
    lista_offerte, crea_offerta,
    followup_oggi, followup_prossimi7,
    lista_eventi_catering, crea_evento_catering,
    crea_evento, get_calendari_visibili,
    lista_messaggi_non_letti, lista_messaggi_ricevuti,
    lista_note, crea_nota,
)
from auth import can_edit, is_admin

try:
    import dateparser
    DATEPARSER_OK = True
except:
    DATEPARSER_OK = False

# ── GROQ CLIENT ───────────────────────────────────────

def get_groq_client():
    try:
        from groq import Groq
        api_key = st.secrets.get("GROQ_API_KEY", "")
        if not api_key:
            return None
        return Groq(api_key=api_key)
    except:
        return None


def chiama_groq(sistema: str, utente_msg: str, max_tokens: int = 500) -> Optional[str]:
    """Chiama Groq API e restituisce il testo della risposta."""
    client = get_groq_client()
    if not client:
        return None
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": sistema},
                {"role": "user", "content": utente_msg}
            ],
            max_tokens=max_tokens,
            temperature=0.1,  # bassa temperatura per output strutturato
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[GROQ] Errore: {e}")
        return None


# ── PROMPT SISTEMA PER ESTRAZIONE ─────────────────────

PROMPT_ESTRAZIONE = """Sei un assistente per un CRM di una società di catering chiamata 1908 Group SA.
Il tuo compito è analizzare il messaggio dell'utente ed estrarre informazioni strutturate.

Rispondi SOLO con un JSON valido, senza testo aggiuntivo, senza markdown, senza backtick.

Il JSON deve avere questa struttura:
{
  "intent": "uno tra: crea_appuntamento | invia_messaggio | cerca_cliente | crea_cliente | crea_offerta | mostra_followup | crea_evento | mostra_eventi | registra_contatto | mostra_messaggi | crea_nota | domanda_generica | saluto",
  "titolo": "titolo dell'appuntamento o null",
  "data": "data in formato YYYY-MM-DD o null. Oggi è %s. Interpreta 'domani', 'lunedì', ecc.",
  "ora_inizio": "orario inizio in formato HH:MM o null",
  "ora_fine": "orario fine in formato HH:MM o null",
  "nome_persona": "nome della persona menzionata (cliente, destinatario, ecc.) o null",
  "nome_destinatario": "nome del destinatario del messaggio o null",
  "corpo_messaggio": "testo del messaggio da inviare o null",
  "luogo": "luogo dell'appuntamento o null",
  "testo_nota": "testo della nota da creare o null",
  "descrizione": "descrizione del contatto o evento o null",
  "confidenza": 0.0
}

Esempi:
- "metti un appuntamento domani dalle 12 alle 13 con simone" → intent: crea_appuntamento, titolo: "Incontro con Simone", data: domani, ora_inizio: "12:00", ora_fine: "13:00", nome_persona: "Simone"
- "manda un messaggio a Giorgio che dice di chiamarmi" → intent: invia_messaggio, nome_destinatario: "Giorgio", corpo_messaggio: "Di chiamarmi"
- "cerca il cliente Rossi" → intent: cerca_cliente, nome_persona: "Rossi"
- "mostrami i follow-up di oggi" → intent: mostra_followup
- "quanti clienti ho" → intent: domanda_generica
- "ciao cosa puoi fare" → intent: saluto
"""


def estrai_con_groq(testo: str) -> Optional[dict]:
    """Usa Groq per estrarre intent ed entità dal testo."""
    oggi = date.today().strftime("%Y-%m-%d (%A %d %B %Y)")
    sistema = PROMPT_ESTRAZIONE % oggi

    risposta = chiama_groq(sistema, testo, max_tokens=300)
    if not risposta:
        return None

    try:
        # Pulisci eventuale markdown
        risposta = risposta.strip()
        risposta = re.sub(r'^```json\s*', '', risposta)
        risposta = re.sub(r'^```\s*', '', risposta)
        risposta = re.sub(r'\s*```$', '', risposta)
        return json.loads(risposta)
    except Exception as e:
        print(f"[GROQ] Errore parsing JSON: {e} — risposta: {risposta[:200]}")
        return None


# ── FALLBACK REGEX ─────────────────────────────────────

def estrai_con_regex(testo: str) -> dict:
    """Fallback regex quando Groq non è disponibile."""
    t = testo.lower()
    risultato = {
        "intent": "domanda_generica",
        "titolo": None,
        "data": None,
        "ora_inizio": None,
        "ora_fine": None,
        "nome_persona": None,
        "nome_destinatario": None,
        "corpo_messaggio": None,
        "luogo": None,
        "testo_nota": None,
        "descrizione": None,
        "confidenza": 0.5,
    }

    # Intent
    if any(p in t for p in ["appuntamento", "riunione", "meeting", "calendario", "agenda"]):
        risultato["intent"] = "crea_appuntamento"
    elif any(p in t for p in ["messaggio", "scrivi a", "manda a", "invia a"]):
        risultato["intent"] = "invia_messaggio"
    elif any(p in t for p in ["cerca cliente", "trova cliente", "info su", "chi è"]):
        risultato["intent"] = "cerca_cliente"
    elif any(p in t for p in ["follow-up", "followup", "scadenze", "da fare"]):
        risultato["intent"] = "mostra_followup"
    elif any(p in t for p in ["messaggi non letti", "inbox", "posta"]):
        risultato["intent"] = "mostra_messaggi"
    elif any(p in t for p in ["nota", "appunto", "ricordami"]):
        risultato["intent"] = "crea_nota"
    elif any(p in t for p in ["ciao", "buongiorno", "cosa puoi", "aiuto", "help"]):
        risultato["intent"] = "saluto"
    elif any(p in t for p in ["quanti clienti", "statistiche", "fatturato"]):
        risultato["intent"] = "domanda_generica"

    # Data
    if DATEPARSER_OK:
        try:
            testo_pulito = re.sub(r'\b\d{1,2}[:\.]?\d{0,2}\b', '', testo)
            parole_tempo = [
                "domani", "oggi", "lunedì", "martedì", "mercoledì",
                "giovedì", "venerdì", "sabato", "domenica", "prossimo"
            ]
            if any(p in t for p in parole_tempo):
                parsed = dateparser.parse(
                    testo_pulito, languages=["it"],
                    settings={"PREFER_DATES_FROM": "future"}
                )
                if parsed:
                    risultato["data"] = parsed.date().strftime("%Y-%m-%d")
        except:
            pass

    # Orari
    orari_raw = re.findall(r'\b(\d{1,2})[:\.](\d{2})\b', testo)
    orari_interi = re.findall(
        r'(?:alle|dalle|ore)\s+(\d{1,2})(?![:\.\d])', t)

    orari = []
    for h, m in orari_raw:
        orari.append(f"{int(h):02d}:{m}")
    for h in orari_interi:
        t_str = f"{int(h):02d}:00"
        if t_str not in orari:
            orari.append(t_str)
    orari.sort()

    if len(orari) >= 2:
        risultato["ora_inizio"] = orari[0]
        risultato["ora_fine"] = orari[1]
    elif len(orari) == 1:
        risultato["ora_inizio"] = orari[0]

    # Nome persona
    match = re.search(
        r'(?:con|a|per|da)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', testo)
    if match:
        risultato["nome_persona"] = match.group(1)

    # Titolo da virgolette
    match_vir = re.findall(r'"([^"]+)"', testo)
    if match_vir:
        risultato["titolo"] = match_vir[0]

    return risultato


# ── RESOLVER ──────────────────────────────────────────

def resolve_cliente(nome: str, utente_corrente) -> tuple:
    if not nome:
        return None, "Per quale cliente?"
    clienti = lista_clienti(filtro_testo=nome)
    if len(clienti) == 0:
        return None, f"Non ho trovato nessun cliente con '{nome}'. Vuoi che lo crei?"
    if len(clienti) == 1:
        return clienti[0], None
    nomi = []
    for c in clienti[:5]:
        nomi.append(
            c.get("ragione_sociale") or
            f"{c.get('nome','')} {c.get('cognome','')}".strip()
        )
    return None, f"Ho trovato più clienti: {', '.join(nomi)}. Quale intendi?"


def resolve_utente(nome: str, utente_corrente) -> tuple:
    if not nome:
        return None, "A chi vuoi mandare il messaggio?"
    utenti = lista_utenti()
    trovati = [
        u for u in utenti
        if nome.lower() in f"{u['nome']} {u['cognome']}".lower()
        and u["id"] != utente_corrente["id"]
    ]
    if len(trovati) == 0:
        return None, f"Non ho trovato nessun collega con '{nome}'."
    if len(trovati) == 1:
        return trovati[0], None
    nomi = [f"{u['nome']} {u['cognome']}" for u in trovati[:5]]
    return None, f"Ho trovato: {', '.join(nomi)}. Chi intendi?"


# ── EXECUTOR ──────────────────────────────────────────

def esegui_azione(estratto: dict, utente: dict,
                  dati_extra: dict = None) -> str:
    """Esegue l'azione basandosi sui dati estratti da Groq/regex."""
    dati_extra = dati_extra or {}
    intent = estratto.get("intent", "domanda_generica")

    # Merge estratto + dati_extra (dati_extra ha priorità — sono risposte dell'utente)
    titolo = dati_extra.get("titolo") or estratto.get("titolo")
    data_str = dati_extra.get("data") or estratto.get("data")
    ora_inizio_str = dati_extra.get("ora_inizio") or estratto.get("ora_inizio")
    ora_fine_str = dati_extra.get("ora_fine") or estratto.get("ora_fine")
    nome_persona = dati_extra.get("nome_persona") or estratto.get("nome_persona")
    nome_dest = dati_extra.get("nome_destinatario") or estratto.get("nome_destinatario")
    corpo_msg = dati_extra.get("corpo_messaggio") or estratto.get("corpo_messaggio")
    testo_nota = dati_extra.get("testo_nota") or estratto.get("testo_nota")
    descrizione = dati_extra.get("descrizione") or estratto.get("descrizione")
    luogo = dati_extra.get("luogo") or estratto.get("luogo") or ""
    nome_cliente = dati_extra.get("nome_cliente") or nome_persona

    # ── SALUTO ──
    if intent == "saluto":
        nome = utente.get("nome", "")
        return (
            f"Ciao {nome}! Sono l'assistente del CRM 1908 Group.\n"
            f"Posso aiutarti a:\n"
            f"- Creare appuntamenti nel calendario\n"
            f"- Mandare messaggi ai colleghi\n"
            f"- Cercare clienti\n"
            f"- Registrare conversazioni nel diario\n"
            f"- Creare offerte ed eventi\n"
            f"- Vedere follow-up e messaggi\n\n"
            f"Cosa posso fare per te?"
        )

    # ── MOSTRA FOLLOW-UP ──
    if intent == "mostra_followup":
        oggi_fu = followup_oggi()
        prossimi = followup_prossimi7()
        if not oggi_fu and not prossimi:
            return "Nessun follow-up in programma per oggi o i prossimi 7 giorni."
        risposta = ""
        if oggi_fu:
            risposta += f"**Follow-up di oggi ({len(oggi_fu)}):**\n"
            for f in oggi_fu[:5]:
                cl = f.get("clienti", {})
                nome_cl = cl.get("ragione_sociale") or \
                    f"{cl.get('nome','')} {cl.get('cognome','')}".strip()
                risposta += f"- {f['titolo']} — {nome_cl}\n"
        if prossimi:
            risposta += f"\n**Prossimi 7 giorni ({len(prossimi)}):**\n"
            for f in prossimi[:5]:
                cl = f.get("clienti", {})
                nome_cl = cl.get("ragione_sociale") or \
                    f"{cl.get('nome','')} {cl.get('cognome','')}".strip()
                risposta += f"- {f['titolo']} — {nome_cl} ({f.get('followup_data','')})\n"
        return risposta

    # ── MOSTRA MESSAGGI ──
    if intent == "mostra_messaggi":
        non_letti = lista_messaggi_non_letti(utente["id"])
        if not non_letti:
            return "Nessun messaggio non letto."
        risposta = f"**Hai {len(non_letti)} messaggi non letti:**\n"
        for m in non_letti[:5]:
            mitt = m.get("mittente") or {}
            nome_mitt = f"{mitt.get('nome','')} {mitt.get('cognome','')}".strip()
            risposta += f"- Da {nome_mitt}: {m.get('oggetto','(nessun oggetto)')}\n"
        return risposta

    # ── MOSTRA EVENTI ──
    if intent == "mostra_eventi":
        eventi = lista_eventi_catering()
        if not eventi:
            return "Nessun evento in programma."
        risposta = f"**Prossimi eventi ({len(eventi)}):**\n"
        for ev in eventi[:5]:
            data_ev = (ev.get("data_inizio") or "")[:10]
            risposta += f"- {ev['titolo']} — {data_ev} ({ev.get('stato','').upper()})\n"
        return risposta

    # ── CERCA CLIENTE ──
    if intent == "cerca_cliente":
        if not nome_cliente:
            return "CHIEDI:nome_cliente:Chi stai cercando?"
        clienti = lista_clienti(filtro_testo=nome_cliente)
        if not clienti:
            return f"Nessun cliente trovato con '{nome_cliente}'."
        if len(clienti) == 1:
            c = clienti[0]
            if c["tipo"] == "giuridica":
                return (
                    f"**{c.get('ragione_sociale','—')}** ({c.get('forma_giuridica','—')})\n"
                    f"Email: {c.get('email','—')}\n"
                    f"Tel: {c.get('telefono','—')}\n"
                    f"Referente: {c.get('contatto_nome','')} {c.get('contatto_cognome','')}\n"
                    f"Stato: {c.get('stato','—').upper()}"
                )
            else:
                return (
                    f"**{c.get('nome','')} {c.get('cognome','')}**\n"
                    f"Email: {c.get('email','—')}\n"
                    f"Tel: {c.get('telefono','—')}\n"
                    f"Stato: {c.get('stato','—').upper()}"
                )
        nomi = []
        for c in clienti[:5]:
            nomi.append(
                c.get("ragione_sociale") or
                f"{c.get('nome','')} {c.get('cognome','')}".strip()
            )
        return f"Ho trovato {len(clienti)} clienti: {', '.join(nomi)}. Quale?"

    # ── CREA NOTA ──
    if intent == "crea_nota":
        if not can_edit(utente):
            return "Non hai i permessi per creare note."
        if not testo_nota:
            return "CHIEDI:testo_nota:Cosa vuoi annotare?"
        crea_nota(utente["id"], testo_nota)
        return f"Nota salvata: '{testo_nota}'"

    # ── INVIA MESSAGGIO ──
    if intent == "invia_messaggio":
        if not can_edit(utente):
            return "Non hai i permessi per inviare messaggi."
        if not nome_dest:
            return "CHIEDI:nome_destinatario:A chi vuoi mandare il messaggio?"
        destinatario, domanda = resolve_utente(nome_dest, utente)
        if domanda and not destinatario:
            return f"CHIEDI:nome_destinatario:{domanda}"
        if not corpo_msg:
            return (
                f"CHIEDI:corpo_messaggio:"
                f"Cosa vuoi scrivere a {destinatario['nome']}?"
            )
        invia_messaggio(utente["id"], destinatario["id"], "", corpo_msg)
        return (
            f"Messaggio inviato a "
            f"{destinatario['nome']} {destinatario['cognome']}."
        )

    # ── CREA APPUNTAMENTO ──
    if intent == "crea_appuntamento":
        if not can_edit(utente):
            return "Non hai i permessi per creare appuntamenti."

        # Titolo automatico se non presente
        if not titolo:
            if nome_persona:
                titolo = f"Incontro con {nome_persona}"
            else:
                return "CHIEDI:titolo:Come vuoi chiamare questo appuntamento?"

        if not data_str:
            return "CHIEDI:data:Quando? (es. domani, lunedì, 15/06)"

        try:
            # Parsa data
            if DATEPARSER_OK:
                parsed_date = dateparser.parse(
                    data_str, languages=["it"],
                    settings={"PREFER_DATES_FROM": "future"}
                )
                data_ev = parsed_date.date() if parsed_date else date.fromisoformat(data_str)
            else:
                data_ev = date.fromisoformat(data_str)

            # Parsa orario inizio
            if ora_inizio_str:
                parts = ora_inizio_str.replace(".", ":").split(":")
                from datetime import time
                ora_inizio = time(int(parts[0]), int(parts[1]))
            else:
                from datetime import time
                ora_inizio = time(9, 0)

            # Parsa orario fine
            if ora_fine_str:
                parts = ora_fine_str.replace(".", ":").split(":")
                from datetime import time
                ora_fine = time(int(parts[0]), int(parts[1]))
            else:
                from datetime import time
                ora_fine = time(min(ora_inizio.hour + 1, 23), ora_inizio.minute)

            dt_inizio = datetime.combine(data_ev, ora_inizio)
            dt_fine = datetime.combine(data_ev, ora_fine)

        except Exception as e:
            return f"Non sono riuscito a interpretare la data/ora: {e}"

        risultato = crea_evento({
            "titolo": titolo,
            "tipo": "appuntamento",
            "data_inizio": dt_inizio.isoformat(),
            "data_fine": dt_fine.isoformat(),
            "luogo": luogo,
            "descrizione": "",
            "proprietario_id": utente["id"],
            "tutto_il_giorno": False,
            "colore": "#1a1a2e",
        }, utente["id"])

        if risultato:
            data_fmt = dt_inizio.strftime("%d/%m/%Y alle %H:%M")
            fine_fmt = dt_fine.strftime("%H:%M")
            return (
                f"Appuntamento '{titolo}' creato per {data_fmt} "
                f"fino alle {fine_fmt}."
            )
        return "Errore nella creazione dell'appuntamento."

    # ── REGISTRA CONTATTO ──
    if intent == "registra_contatto":
        if not can_edit(utente):
            return "Non hai i permessi per registrare contatti."
        if not nome_cliente:
            return "CHIEDI:nome_cliente:Con quale cliente hai avuto questo contatto?"
        cliente, domanda = resolve_cliente(nome_cliente, utente)
        if domanda and not cliente:
            return f"CHIEDI:nome_cliente:{domanda}"
        if not descrizione:
            return "CHIEDI:descrizione:Di cosa avete parlato?"
        crea_voce_diario({
            "cliente_id": cliente["id"],
            "tipo": "nota",
            "titolo": f"Contatto con {nome_cliente}",
            "descrizione": descrizione,
            "data_contatto": date.today().isoformat(),
        }, utente["id"])
        nome_cl = cliente.get("ragione_sociale") or \
            f"{cliente.get('nome','')} {cliente.get('cognome','')}".strip()
        return f"Contatto registrato nel diario di {nome_cl}."

    # ── DOMANDA GENERICA ──
    if intent == "domanda_generica":
        testo_orig = dati_extra.get("testo_originale", "").lower()
        if "quanti clienti" in testo_orig or "numero clienti" in testo_orig:
            clienti = lista_clienti()
            attivi = [c for c in clienti if c.get("stato") == "attivo"]
            prospect = [c for c in clienti if c.get("stato") == "prospect"]
            return (
                f"Hai **{len(clienti)} clienti** totali.\n"
                f"- Attivi: {len(attivi)}\n"
                f"- Prospect: {len(prospect)}\n"
                f"- Altri: {len(clienti) - len(attivi) - len(prospect)}"
            )
        if "follow" in testo_orig or "scadenz" in testo_orig:
            oggi_fu = followup_oggi()
            prossimi = followup_prossimi7()
            return (
                f"Hai **{len(oggi_fu)} follow-up oggi** e "
                f"**{len(prossimi)} nei prossimi 7 giorni**."
            )
        if "eventi" in testo_orig:
            eventi = lista_eventi_catering()
            return f"Ci sono **{len(eventi)} eventi** nel sistema."
        if "messaggi" in testo_orig:
            non_letti = lista_messaggi_non_letti(utente["id"])
            return f"Hai **{len(non_letti)} messaggi non letti**."
        return (
            "Non sono sicuro di aver capito. Prova a dirmi cosa vuoi fare,\n"
            "ad esempio:\n"
            "- 'Crea un appuntamento con Rossi domani alle 10'\n"
            "- 'Manda un messaggio a Giorgio che dice di chiamarmi'\n"
            "- 'Mostrami i follow-up di oggi'\n"
            "- 'Cerca il cliente Bianchi'\n"
            "- 'Quanti clienti ho?'"
        )

    return "Non ho capito la richiesta. Puoi ripetere in modo diverso?"


# ── PROCESSA MESSAGGIO ────────────────────────────────

def processa_messaggio(testo: str, utente: dict) -> str:
    """Processa un messaggio gestendo lo stato multi-turn."""
    chat_state = st.session_state.get("assistente_state", {})
    pending_intent = chat_state.get("pending_intent")
    pending_estratto = chat_state.get("pending_estratto", {})
    pending_dati = chat_state.get("pending_dati", {})
    pending_field = chat_state.get("pending_field")

    if pending_intent and pending_field:
        # L'utente sta rispondendo a una domanda specifica
        risposta_pulita = testo.strip()

        if pending_field == "data":
            if DATEPARSER_OK:
                try:
                    parsed = dateparser.parse(
                        risposta_pulita, languages=["it"],
                        settings={"PREFER_DATES_FROM": "future"}
                    )
                    if parsed:
                        pending_dati["data"] = parsed.date().strftime("%Y-%m-%d")
                        # Estrai anche orari dalla risposta
                        orari = re.findall(r'\b(\d{1,2})[:\.](\d{2})\b', risposta_pulita)
                        orari_interi = re.findall(
                            r'(?:alle|dalle|ore)\s+(\d{1,2})(?![:\.\d])',
                            risposta_pulita.lower()
                        )
                        tutti_orari = []
                        for h, m in orari:
                            tutti_orari.append(f"{int(h):02d}:{m}")
                        for h in orari_interi:
                            s = f"{int(h):02d}:00"
                            if s not in tutti_orari:
                                tutti_orari.append(s)
                        tutti_orari.sort()
                        if len(tutti_orari) >= 2:
                            pending_dati["ora_inizio"] = tutti_orari[0]
                            pending_dati["ora_fine"] = tutti_orari[1]
                        elif len(tutti_orari) == 1:
                            pending_dati["ora_inizio"] = tutti_orari[0]
                    else:
                        return (
                            "Non ho capito la data. "
                            "Puoi dirmi quando? (es. domani, lunedì, 15/06)"
                        )
                except:
                    return "Non ho capito la data. Prova con: domani, lunedì, 15/06"
            else:
                pending_dati["data"] = risposta_pulita

        elif pending_field == "titolo":
            pending_dati["titolo"] = risposta_pulita
        elif pending_field == "nome_destinatario":
            pending_dati["nome_destinatario"] = risposta_pulita
        elif pending_field == "nome_cliente":
            pending_dati["nome_cliente"] = risposta_pulita
        elif pending_field == "corpo_messaggio":
            pending_dati["corpo_messaggio"] = risposta_pulita
        elif pending_field == "descrizione":
            pending_dati["descrizione"] = risposta_pulita
        elif pending_field == "testo_nota":
            pending_dati["testo_nota"] = risposta_pulita
        else:
            pending_dati[pending_field] = risposta_pulita

        st.session_state.assistente_state = {
            "pending_intent": pending_intent,
            "pending_estratto": pending_estratto,
            "pending_dati": pending_dati,
            "pending_field": None,
        }

        # Ricostruisci estratto con intent corretto
        pending_estratto["intent"] = pending_intent
        pending_dati["testo_originale"] = chat_state.get("testo_originale", testo)
        risposta = esegui_azione(pending_estratto, utente, pending_dati)

    else:
        # Nuova richiesta — usa Groq o fallback regex
        estratto = estrai_con_groq(testo)

        if estratto is None:
            print("[ASSISTENTE] Groq non disponibile — uso regex")
            estratto = estrai_con_regex(testo)

        estratto["testo_originale"] = testo

        st.session_state.assistente_state = {
            "pending_intent": estratto.get("intent"),
            "pending_estratto": estratto,
            "pending_dati": {},
            "pending_field": None,
            "testo_originale": testo,
        }

        risposta = esegui_azione(estratto, utente, {"testo_originale": testo})

    # Gestisci chiarimenti
    if risposta.startswith("CHIEDI:"):
        parts = risposta.split(":", 2)
        field = parts[1]
        domanda = parts[2]
        state = st.session_state.get("assistente_state", {})
        state["pending_field"] = field
        st.session_state.assistente_state = state
        return domanda

    # Reset pending field dopo azione completata
    state = st.session_state.get("assistente_state", {})
    state["pending_field"] = None
    st.session_state.assistente_state = state
    return risposta


# ── UI WIDGET SIDEBAR ─────────────────────────────────

def widget_assistente_sidebar(utente):
    st.markdown(
        "<hr style='border-color:#2a2a4a;margin:12px 0;'>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<div style='font-size:10px;font-weight:700;text-transform:uppercase;"
        "letter-spacing:1.2px;color:#666888;padding:0 0 6px 0;'>"
        "Assistente AI</div>",
        unsafe_allow_html=True
    )
    if st.button("Apri assistente", key="btn_apri_assistente",
                 use_container_width=True):
        st.session_state.pagina = "assistente"
        st.rerun()

    history = st.session_state.get("assistente_history", [])
    if history:
        ultimo = history[-1]
        if ultimo["role"] == "assistant":
            st.markdown(
                f"<div style='font-size:10px;color:#9999bb;"
                f"margin-top:4px;line-height:1.4;'>"
                f"{ultimo['content'][:80]}"
                f"{'...' if len(ultimo['content']) > 80 else ''}"
                f"</div>",
                unsafe_allow_html=True
            )


# ── UI PAGINA COMPLETA ────────────────────────────────

def pagina_assistente(utente):
    st.title("Assistente AI")
    st.markdown("---")

    # Controlla se Groq è configurato
    groq_ok = bool(st.secrets.get("GROQ_API_KEY", ""))
    if not groq_ok:
        st.warning(
            "GROQ_API_KEY non configurata nei secrets. "
            "L'assistente funziona in modalità base (regex). "
            "Aggiungi la chiave per funzionalità complete."
        )

    col_sp, col_reset = st.columns([5, 1])
    with col_reset:
        if st.button("Reset", key="reset_chat"):
            st.session_state.assistente_history = []
            st.session_state.assistente_state = {}
            st.rerun()

    st.markdown("---")

    # Inizializza history
    if "assistente_history" not in st.session_state or \
            not st.session_state.assistente_history:
        st.session_state.assistente_history = []
        ora = datetime.now().hour
        if 5 <= ora < 12:
            benvenuto = f"Buongiorno {utente['nome']}! Come posso aiutarti?"
        elif 12 <= ora < 18:
            benvenuto = f"Buon pomeriggio {utente['nome']}! Cosa posso fare per te?"
        else:
            benvenuto = f"Buonasera {utente['nome']}! Come posso aiutarti?"
        st.session_state.assistente_history.append({
            "role": "assistant",
            "content": benvenuto
        })

    # Mostra history
    for msg in st.session_state.assistente_history:
        if msg["role"] == "user":
            st.markdown(
                f"<div style='display:flex;justify-content:flex-end;"
                f"margin:8px 0;'>"
                f"<div style='background:#1a1a2e;color:white;"
                f"border-radius:12px 12px 2px 12px;"
                f"padding:10px 16px;max-width:75%;font-size:13px;'>"
                f"{msg['content']}"
                f"</div></div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<div style='display:flex;justify-content:flex-start;"
                f"margin:8px 0;'>"
                f"<div style='background:#f4f4f8;color:#1a1a2e;"
                f"border-radius:12px 12px 12px 2px;"
                f"padding:10px 16px;max-width:75%;font-size:13px;"
                f"line-height:1.6;white-space:pre-wrap;'>"
                f"{msg['content']}"
                f"</div></div>",
                unsafe_allow_html=True
            )

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # Input
    with st.form("form_chat", clear_on_submit=True):
        col_input, col_btn = st.columns([5, 1])
        with col_input:
            user_input = st.text_input(
                "Scrivi un messaggio",
                placeholder="Es: crea appuntamento con Rossi domani alle 10...",
                label_visibility="collapsed"
            )
        with col_btn:
            invia = st.form_submit_button("Invia", use_container_width=True)

    if invia and user_input.strip():
        _processa_e_aggiungi(user_input, utente)
        st.rerun()


def _processa_e_aggiungi(testo: str, utente: dict):
    st.session_state.assistente_history.append({
        "role": "user",
        "content": testo
    })

    risposta = processa_messaggio(testo, utente)

    st.session_state.assistente_history.append({
        "role": "assistant",
        "content": risposta
    })

    if len(st.session_state.assistente_history) > 50:
        st.session_state.assistente_history = \
            st.session_state.assistente_history[-50:]
