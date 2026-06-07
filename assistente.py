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

# ── CARICA MODELLI ────────────────────────────────────

@st.cache_resource
def carica_modelli():
    """Carica i modelli una volta sola e li mantiene in cache."""
    try:
        from transformers import pipeline
        import torch

        device = 0 if torch.cuda.is_available() else -1

        # Intent classifier — zero-shot multilingue
        intent_clf = pipeline(
            "zero-shot-classification",
            model="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli",
            device=device
        )

        # NER per entità italiane
        try:
            ner = pipeline(
                "token-classification",
                model="osiria/deberta-italian-ner",
                aggregation_strategy="simple",
                device=device
            )
        except:
            ner = None

        return intent_clf, ner

    except Exception as e:
        print(f"Errore caricamento modelli: {e}")
        return None, None


# ── INTENT LABELS ─────────────────────────────────────

INTENT_LABELS = {
    "crea_appuntamento":   "creare un appuntamento o riunione nel calendario",
    "invia_messaggio":     "inviare un messaggio interno a un collega",
    "cerca_cliente":       "cercare o trovare informazioni su un cliente",
    "crea_cliente":        "aggiungere un nuovo cliente",
    "crea_offerta":        "creare una nuova offerta commerciale",
    "mostra_followup":     "vedere i follow-up di oggi o della settimana",
    "crea_evento":         "creare un evento catering",
    "mostra_eventi":       "vedere gli eventi in programma",
    "registra_contatto":   "registrare una chiamata email o riunione nel diario",
    "mostra_messaggi":     "vedere i messaggi non letti o ricevuti",
    "crea_nota":           "aggiungere una nota rapida",
    "domanda_generica":    "rispondere a una domanda generica sul CRM o sull'azienda",
    "saluto":              "salutare o chiedere aiuto",
}

INTENT_KEYS = list(INTENT_LABELS.keys())
INTENT_DESCRIPTIONS = list(INTENT_LABELS.values())


# ── CLASSIFICATORE INTENT ─────────────────────────────

def classifica_intent(testo: str, intent_clf) -> tuple[str, float]:
    """Classifica l'intent dell'input utente."""
    if intent_clf is None:
        return _classifica_regex(testo)

    try:
        result = intent_clf(
            testo,
            candidate_labels=INTENT_DESCRIPTIONS,
            hypothesis_template="L'utente vuole {}.",
        )
        idx = INTENT_DESCRIPTIONS.index(result["labels"][0])
        intent = INTENT_KEYS[idx]
        score = result["scores"][0]
        return intent, score
    except Exception as e:
        print(f"Errore classificazione: {e}")
        return _classifica_regex(testo)


def _classifica_regex(testo: str) -> tuple[str, float]:
    """Fallback regex con scoring — vince chi ha più match."""
    t = testo.lower()

    patterns = {
        "crea_appuntamento": [
            r"appuntamento", r"riunione", r"meeting", r"incontro",
            r"calendario", r"agenda", r"fissa", r"metti.*calendario",
            r"crea.*calendario", r"segna.*calendario"
        ],
        "invia_messaggio": [
            r"messaggio", r"scrivi a", r"manda", r"contatta",
            r"notifica", r"avvisa", r"di.*a\s+\w+"
        ],
        "cerca_cliente": [
            r"^cerca\b", r"^trova\b", r"chi è\b", r"info su\b",
            r"dettagli su\b", r"dammi info", r"dimmi di"
        ],
        "crea_cliente": [
            r"nuovo cliente", r"aggiungi cliente", r"crea cliente",
            r"inserisci cliente", r"registra cliente"
        ],
        "crea_offerta": [
            r"offerta", r"preventivo", r"proposta commerciale", r"quotazione"
        ],
        "mostra_followup": [
            r"follow.?up", r"cosa devo fare", r"promemoria",
            r"scadenze", r"da fare oggi", r"richiamare"
        ],
        "crea_evento": [
            r"evento catering", r"catering", r"banchetto",
            r"ricevimento", r"nuovo evento"
        ],
        "mostra_eventi": [
            r"eventi in programma", r"prossimi eventi",
            r"lista eventi", r"che eventi"
        ],
        "registra_contatto": [
            r"ho chiamato", r"ho parlato", r"ho incontrato",
            r"diario", r"registra contatto", r"ho sentito"
        ],
        "mostra_messaggi": [
            r"messaggi non letti", r"posta", r"inbox",
            r"ho messaggi", r"nuovi messaggi"
        ],
        "crea_nota": [
            r"nota:", r"appunto:", r"ricordami", r"segna questo",
            r"post.?it", r"nota rapida"
        ],
        "saluto": [
            r"^ciao\b", r"^buongiorno\b", r"^buonasera\b",
            r"cosa puoi fare", r"come funzioni", r"^help\b", r"^aiuto\b"
        ],
        "mostra_followup": [
            r"follow.?up", r"scadenze oggi", r"cosa devo fare oggi"
        ],
        "domanda_generica": [
            r"quanti clienti", r"quante offerte", r"statistiche",
            r"riepilogo", r"dashboard"
        ],
    }

    scores = {intent: 0 for intent in patterns}

    for intent, pats in patterns.items():
        for pat in pats:
            if re.search(pat, t):
                scores[intent] += 1

    # Vince chi ha più match
    best_intent = max(scores, key=lambda k: scores[k])
    best_score = scores[best_intent]

    if best_score == 0:
        return "domanda_generica", 0.4

    # Normalizza score
    confidence = min(0.5 + best_score * 0.15, 0.95)
    return best_intent, confidence


# ── ENTITY EXTRACTION ─────────────────────────────────

def estrai_entita(testo: str, ner_model) -> dict:
    """Estrae entità dal testo."""
    entita = {
        "persone": [],
        "luoghi": [],
        "organizzazioni": [],
        "data": None,
        "ora": None,
        "testo_originale": testo,
    }

    # Date con dateparser
    if DATEPARSER_OK:
        entita["data"], entita["ora"] = _estrai_data_ora(testo)

    # NER per persone e organizzazioni
    if ner_model:
        try:
            risultati = ner_model(testo)
            for r in risultati:
                entita_tipo = r.get("entity_group", "")
                parola = r.get("word", "").strip()
                if entita_tipo == "PER" and parola:
                    entita["persone"].append(parola)
                elif entita_tipo == "ORG" and parola:
                    entita["organizzazioni"].append(parola)
                elif entita_tipo == "LOC" and parola:
                    entita["luoghi"].append(parola)
        except:
            pass

    # Fallback regex per nomi comuni
    if not entita["persone"] and not entita["organizzazioni"]:
        entita = _estrai_entita_regex(testo, entita)

    return entita


def _estrai_data_ora(testo: str) -> tuple:
    """Estrae data e ora dal testo."""
    try:
        import dateparser
        settings = {
            "PREFER_DATES_FROM": "future",
            "RETURN_AS_TIMEZONE_AWARE": False,
        }

        # Prova a parsare la data
        parsed = dateparser.parse(
            testo,
            languages=["it"],
            settings=settings
        )

        if parsed:
            data = parsed.date()
            ora = parsed.time() if parsed.hour != 0 or parsed.minute != 0 else None
            return data, ora

    except:
        pass

    return None, None


def _estrai_entita_regex(testo: str, entita: dict) -> dict:
    """Fallback regex per estrarre nomi."""
    # Pattern per "a/con/per [Nome Cognome]"
    patterns = [
        r"(?:a|con|per|da|verso)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"(?:il signor|la signora|dott\.?|ing\.?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
    ]
    for pat in patterns:
        match = re.search(pat, testo)
        if match:
            entita["persone"].append(match.group(1))
    return entita


# ── RESOLVER — disambigua entità ──────────────────────

def resolve_cliente(nome: str, utente_corrente) -> tuple:
    """
    Cerca il cliente per nome.
    Ritorna (cliente, domanda) — se domanda è None, il cliente è univoco.
    """
    if not nome:
        return None, "Per quale cliente?"

    clienti = lista_clienti(filtro_testo=nome)

    if len(clienti) == 0:
        return None, f"Non ho trovato nessun cliente con '{nome}'. Vuoi che lo crei?"

    if len(clienti) == 1:
        return clienti[0], None

    # Più clienti — chiedi quale
    nomi = []
    for c in clienti[:5]:
        if c["tipo"] == "giuridica":
            nomi.append(c.get("ragione_sociale", "—"))
        else:
            nomi.append(f"{c.get('nome','')} {c.get('cognome','')}".strip())

    return None, f"Ho trovato più clienti: {', '.join(nomi)}. Quale intendi?"


def resolve_utente(nome: str, utente_corrente) -> tuple:
    """Cerca un utente interno per nome."""
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


# ── EXECUTOR — esegue le azioni ───────────────────────

def esegui_azione(intent: str, entita: dict, utente: dict,
                  dati_extra: dict = None) -> str:
    """Esegue l'azione corrispondente all'intent."""

    dati_extra = dati_extra or {}

    # ── SALUTO ──
    if intent == "saluto":
        nome = utente.get("nome", "")
        return (
            f"Ciao {nome}! Sono l'assistente del CRM 1908 Group. "
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
        oggi = followup_oggi()
        prossimi = followup_prossimi7()

        if not oggi and not prossimi:
            return "Nessun follow-up in programma per oggi o i prossimi 7 giorni."

        risposta = ""
        if oggi:
            risposta += f"**Follow-up di oggi ({len(oggi)}):**\n"
            for f in oggi[:5]:
                cliente = f.get("clienti", {})
                nome_cl = cliente.get("ragione_sociale") or \
                    f"{cliente.get('nome','')} {cliente.get('cognome','')}".strip()
                risposta += f"- {f['titolo']} — {nome_cl}\n"

        if prossimi:
            risposta += f"\n**Prossimi 7 giorni ({len(prossimi)}):**\n"
            for f in prossimi[:5]:
                cliente = f.get("clienti", {})
                nome_cl = cliente.get("ragione_sociale") or \
                    f"{cliente.get('nome','')} {cliente.get('cognome','')}".strip()
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
            data_str = (ev.get("data_inizio") or "")[:10]
            risposta += f"- {ev['titolo']} — {data_str} ({ev.get('stato','').upper()})\n"
        return risposta

    # ── CERCA CLIENTE ──
    if intent == "cerca_cliente":
        persone = entita.get("persone", []) + entita.get("organizzazioni", [])
        nome = dati_extra.get("nome_cliente") or (persone[0] if persone else None)

        if not nome:
            return "CHIEDI:nome_cliente:Chi stai cercando?"

        clienti = lista_clienti(filtro_testo=nome)
        if not clienti:
            return f"Nessun cliente trovato con '{nome}'."

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
        return (
            f"Ho trovato {len(clienti)} clienti: {', '.join(nomi)}. "
            f"Vuoi più dettagli su uno in particolare?"
        )

    # ── CREA NOTA ──
    if intent == "crea_nota":
        if not can_edit(utente):
            return "Non hai i permessi per creare note."

        testo = dati_extra.get("testo_nota")
        if not testo:
            t = entita["testo_originale"]
            for keyword in ["nota:", "appunto:", "segna:", "ricordami:"]:
                if keyword in t.lower():
                    testo = t[t.lower().index(keyword) + len(keyword):].strip()
                    break
            # Prova anche con virgolette
            if not testo:
                match_vir = re.findall(r'"([^"]+)"', t)
                if match_vir:
                    testo = match_vir[0]
            if not testo:
                return "CHIEDI:testo_nota:Cosa vuoi annotare?"

        crea_nota(utente["id"], testo)
        return f"Nota salvata: '{testo}'"

    # ── INVIA MESSAGGIO ──
    if intent == "invia_messaggio":
        if not can_edit(utente):
            return "Non hai i permessi per inviare messaggi."

        persone = entita.get("persone", [])
        nome_dest = dati_extra.get("nome_destinatario") or \
            (persone[0] if persone else None)

        if not nome_dest:
            return "CHIEDI:nome_destinatario:A chi vuoi mandare il messaggio?"

        destinatario, domanda = resolve_utente(nome_dest, utente)
        if domanda and not destinatario:
            return f"CHIEDI:nome_destinatario:{domanda}"

        corpo = dati_extra.get("corpo_messaggio")
        if not corpo:
            # Prova a estrarre corpo dal testo originale
            t = entita.get("testo_originale", "")
            match_vir = re.findall(r'"([^"]+)"', t)
            if match_vir:
                corpo = match_vir[-1]  # Ultimo testo tra virgolette
            if not corpo:
                return (
                    f"CHIEDI:corpo_messaggio:"
                    f"Cosa vuoi scrivere a {destinatario['nome']}?"
                )

        oggetto = dati_extra.get("oggetto_messaggio", "")
        invia_messaggio(utente["id"], destinatario["id"], oggetto, corpo)
        return f"Messaggio inviato a {destinatario['nome']} {destinatario['cognome']}."

    # ── CREA APPUNTAMENTO ──
    if intent == "crea_appuntamento":
        if not can_edit(utente):
            return "Non hai i permessi per creare appuntamenti."

        data_ev = dati_extra.get("data") or entita.get("data")
        ora_ev = dati_extra.get("ora") or entita.get("ora")
        ora_fine_ev = dati_extra.get("ora_fine")
        titolo = dati_extra.get("titolo")
        luogo = dati_extra.get("luogo") or \
            (entita["luoghi"][0] if entita.get("luoghi") else "")

        # Titolo automatico da persone estratte
        if not titolo:
            persone = entita.get("persone", [])
            if persone:
                titolo = f"Incontro con {persone[0]}"
            else:
                return "CHIEDI:titolo:Come vuoi chiamare questo appuntamento?"

        if not data_ev:
            return "CHIEDI:data:Quando vuoi fissare l'appuntamento? (es. domani, lunedì, 15/06)"

        # Costruisci datetime
        try:
            if isinstance(data_ev, str):
                if DATEPARSER_OK:
                    import dateparser
                    parsed = dateparser.parse(
                        data_ev,
                        languages=["it"],
                        settings={"PREFER_DATES_FROM": "future"}
                    )
                    if parsed:
                        data_ev = parsed.date()
                    else:
                        data_ev = date.fromisoformat(data_ev)
                else:
                    data_ev = date.fromisoformat(data_ev)

            if ora_ev and isinstance(ora_ev, str):
                from datetime import time
                parts = ora_ev.replace(".", ":").split(":")
                ora_ev = time(int(parts[0]), int(parts[1]))

            dt_inizio = datetime.combine(
                data_ev,
                ora_ev if ora_ev else datetime.strptime("09:00", "%H:%M").time()
            )

            # Usa ora_fine se presente, altrimenti +1 ora
            if ora_fine_ev:
                if isinstance(ora_fine_ev, str):
                    from datetime import time
                    parts = ora_fine_ev.replace(".", ":").split(":")
                    ora_fine_ev = time(int(parts[0]), int(parts[1]))
                dt_fine = datetime.combine(data_ev, ora_fine_ev)
            else:
                dt_fine = datetime(
                    dt_inizio.year, dt_inizio.month, dt_inizio.day,
                    min(dt_inizio.hour + 1, 23), dt_inizio.minute
                )

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

    # ── REGISTRA CONTATTO NEL DIARIO ──
    if intent == "registra_contatto":
        if not can_edit(utente):
            return "Non hai i permessi per registrare contatti."

        persone = entita.get("persone", []) + entita.get("organizzazioni", [])
        nome_cliente = dati_extra.get("nome_cliente") or \
            (persone[0] if persone else None)

        if not nome_cliente:
            return "CHIEDI:nome_cliente:Con quale cliente hai avuto questo contatto?"

        cliente, domanda = resolve_cliente(nome_cliente, utente)
        if domanda and not cliente:
            return f"CHIEDI:nome_cliente:{domanda}"

        tipo_contatto = dati_extra.get("tipo_contatto", "nota")
        descrizione = dati_extra.get("descrizione")

        if not descrizione:
            # Prova da virgolette
            t = entita.get("testo_originale", "")
            match_vir = re.findall(r'"([^"]+)"', t)
            if match_vir:
                descrizione = match_vir[-1]
            if not descrizione:
                return "CHIEDI:descrizione:Di cosa avete parlato?"

        crea_voce_diario({
            "cliente_id": cliente["id"],
            "tipo": tipo_contatto,
            "titolo": f"Contatto con {nome_cliente}",
            "descrizione": descrizione,
            "data_contatto": date.today().isoformat(),
        }, utente["id"])

        nome_cl = cliente.get("ragione_sociale") or \
            f"{cliente.get('nome','')} {cliente.get('cognome','')}".strip()
        return f"Contatto registrato nel diario di {nome_cl}."

    # ── DOMANDA GENERICA ──
    if intent == "domanda_generica":
        testo = entita.get("testo_originale", "").lower()

        if "quanti clienti" in testo or "numero clienti" in testo:
            clienti = lista_clienti()
            attivi = [c for c in clienti if c.get("stato") == "attivo"]
            prospect = [c for c in clienti if c.get("stato") == "prospect"]
            return (
                f"Hai **{len(clienti)} clienti** totali nel CRM.\n"
                f"- Attivi: {len(attivi)}\n"
                f"- Prospect: {len(prospect)}\n"
                f"- Altri: {len(clienti) - len(attivi) - len(prospect)}"
            )

        if "follow" in testo or "scadenz" in testo or "da fare" in testo:
            oggi = followup_oggi()
            prossimi = followup_prossimi7()
            return (
                f"Hai **{len(oggi)} follow-up oggi** e "
                f"**{len(prossimi)} nei prossimi 7 giorni**."
            )

        if "eventi" in testo or "catering" in testo:
            eventi = lista_eventi_catering()
            return f"Ci sono **{len(eventi)} eventi** nel sistema."

        if "messaggi" in testo or "non letti" in testo:
            non_letti = lista_messaggi_non_letti(utente["id"])
            return f"Hai **{len(non_letti)} messaggi non letti**."

        return (
            "Non sono sicuro di aver capito. Prova a dirmi cosa vuoi fare, "
            "ad esempio:\n"
            "- 'Crea un appuntamento con Rossi domani alle 10'\n"
            "- 'Manda un messaggio a Giorgio che dice di chiamarmi'\n"
            "- 'Mostrami i follow-up di oggi'\n"
            "- 'Cerca il cliente Bianchi'\n"
            "- 'Quanti clienti ho?'"
        )

    return "Non ho capito la richiesta. Puoi ripetere in modo diverso?"


# ── GESTORE STATO CONVERSAZIONE ───────────────────────

def processa_messaggio(testo: str, utente: dict,
                       intent_clf, ner_model) -> str:
    chat_state = st.session_state.get("assistente_state", {})
    pending_intent = chat_state.get("pending_intent")
    pending_entities = chat_state.get("pending_entities", {})
    pending_field = chat_state.get("pending_field")

    if pending_intent and pending_field:
        # L'utente sta rispondendo a una domanda specifica
        # Salva la risposta nel campo corretto
        pending_entities[pending_field] = testo.strip()
        st.session_state.assistente_state = {
            "pending_intent": pending_intent,
            "pending_entities": pending_entities,
            "pending_field": None,
        }
        risposta = esegui_azione(
            pending_intent,
            {"testo_originale": testo},
            utente,
            pending_entities
        )
    else:
        # Nuova richiesta — analizza tutto il testo
        intent, score = classifica_intent(testo, intent_clf)
        entita = estrai_entita(testo, ner_model)

        # Pre-popola le entities dal testo originale
        dati_extra = {}

        # Estrai titolo da virgolette se presente
        match_virgolette = re.findall(r'"([^"]+)"', testo)
        if match_virgolette:
            dati_extra["titolo"] = match_virgolette[0]

        # Estrai data e ora
        if entita.get("data"):
            dati_extra["data"] = entita["data"]
        if entita.get("ora"):
            dati_extra["ora"] = entita["ora"]

        # Estrai orario fine se presente nel testo (es "alle 11.30 alle 13.30")
        orari = re.findall(r'\b(\d{1,2})[:\.](\d{2})\b', testo)
        if len(orari) >= 2:
            try:
                from datetime import time
                dati_extra["ora"] = time(int(orari[0][0]), int(orari[0][1]))
                dati_extra["ora_fine"] = time(int(orari[1][0]), int(orari[1][1]))
            except:
                pass
        elif len(orari) == 1:
            try:
                from datetime import time
                dati_extra["ora"] = time(int(orari[0][0]), int(orari[0][1]))
            except:
                pass

        st.session_state.assistente_state = {
            "pending_intent": intent,
            "pending_entities": {
                **dati_extra,
                "data": entita.get("data"),
                "ora": dati_extra.get("ora") or entita.get("ora"),
                "luoghi": entita.get("luoghi", []),
            },
            "pending_field": None,
            "last_intent": intent,
            "last_score": score,
        }

        risposta = esegui_azione(intent, entita, utente, dati_extra)

    # Gestisci richieste di chiarimento
    if risposta.startswith("CHIEDI:"):
        parts = risposta.split(":", 2)
        field = parts[1]
        domanda = parts[2]
        state = st.session_state.get("assistente_state", {})
        state["pending_field"] = field
        st.session_state.assistente_state = state
        return domanda

    state = st.session_state.get("assistente_state", {})
    state["pending_field"] = None
    st.session_state.assistente_state = state

    return risposta


# ── UI WIDGET SIDEBAR ─────────────────────────────────

def widget_assistente_sidebar(utente):
    """Widget compatto per la sidebar."""
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

    # Mostra ultimo messaggio se esiste
    history = st.session_state.get("assistente_history", [])
    if history:
        ultimo = history[-1]
        if ultimo["role"] == "assistant":
            st.markdown(
                f"<div style='font-size:10px;color:#9999bb;"
                f"margin-top:4px;line-height:1.4;'>"
                f"{ultimo['content'][:80]}{'...' if len(ultimo['content']) > 80 else ''}"
                f"</div>",
                unsafe_allow_html=True
            )


# ── UI PAGINA COMPLETA ────────────────────────────────

def pagina_assistente(utente):
    """Pagina dedicata all'assistente."""
    st.title("Assistente AI")
    st.markdown("---")

    # Carica modelli
    with st.spinner("Carico i modelli AI..."):
        intent_clf, ner_model = carica_modelli()

    if intent_clf is None:
        st.warning(
            "Modelli AI non disponibili — uso modalità regole. "
            "Installa transformers e torch per le funzionalità complete."
        )

    # Info capacità basate sul ruolo
    ruolo = utente.get("ruolo", "visualizza")
    col_info, col_reset = st.columns([4, 1])
    with col_info:
        st.markdown(
            f"<div style='background:#f4f4f8;border-radius:8px;"
            f"padding:10px 14px;font-size:12px;color:#666;'>"
            f"Ruolo: <b>{ruolo}</b> · "
            f"{'Puoi creare e modificare' if can_edit(utente) else 'Sola lettura'} · "
            f"{'Admin: sì' if is_admin(utente) else ''}"
            f"</div>",
            unsafe_allow_html=True
        )
    with col_reset:
        if st.button("Reset", key="reset_chat"):
            st.session_state.assistente_history = []
            st.session_state.assistente_state = {}
            st.rerun()

    st.markdown("---")

    # Inizializza history
    if "assistente_history" not in st.session_state:
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
                f"<div style='background:#1a1a2e;color:white;border-radius:12px 12px 2px 12px;"
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
                f"line-height:1.6;'>"
                f"{msg['content'].replace(chr(10), '<br>')}"
                f"</div></div>",
                unsafe_allow_html=True
            )

    # Suggerimenti rapidi
    if len(st.session_state.assistente_history) <= 1:
        st.markdown(
            "<div style='font-size:11px;color:#aaa;margin:12px 0 6px 0;'>"
            "Suggerimenti:</div>",
            unsafe_allow_html=True
        )
        suggerimenti = [
            "Mostrami i follow-up di oggi",
            "Quanti clienti ho?",
            "Mostrami i messaggi non letti",
            "Cosa puoi fare?",
        ]
        cols = st.columns(2)
        for i, sug in enumerate(suggerimenti):
            with cols[i % 2]:
                if st.button(sug, key=f"sug_{i}", use_container_width=True):
                    _processa_e_aggiungi(sug, utente, intent_clf, ner_model)
                    st.rerun()

    # Input
    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

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
        _processa_e_aggiungi(user_input, utente, intent_clf, ner_model)
        st.rerun()


def _processa_e_aggiungi(testo: str, utente: dict,
                          intent_clf, ner_model):
    """Processa il messaggio e aggiorna la history."""
    # Aggiungi messaggio utente
    st.session_state.assistente_history.append({
        "role": "user",
        "content": testo
    })

    # Processa e ottieni risposta
    with st.spinner("..."):
        risposta = processa_messaggio(testo, utente, intent_clf, ner_model)

    # Aggiungi risposta assistente
    st.session_state.assistente_history.append({
        "role": "assistant",
        "content": risposta
    })

    # Limita history a 50 messaggi
    if len(st.session_state.assistente_history) > 50:
        st.session_state.assistente_history = \
            st.session_state.assistente_history[-50:]
