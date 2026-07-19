import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st
from db import get_sb

def invia_email(destinatario, oggetto, corpo_html, tipo=None, riferimento_id=None,
                cc=None, bcc=None, allegati=None):
    """Invia email dall'indirizzo centralizzato aziendale.
    cc / bcc : liste di indirizzi (facoltative).
    allegati : lista di tuple (nome_file, bytes) di qualsiasi formato."""
    from email.mime.application import MIMEApplication
    try:
        mittente = st.secrets["EMAIL_MITTENTE"]
        password = st.secrets["EMAIL_PASSWORD"]
        smtp_server = st.secrets["EMAIL_SMTP_SERVER"]
        smtp_port = int(st.secrets["EMAIL_SMTP_PORT"])

        cc = [x for x in (cc or []) if x]
        bcc = [x for x in (bcc or []) if x]

        msg = MIMEMultipart("mixed")
        msg["Subject"] = oggetto
        msg["From"] = mittente
        msg["To"] = destinatario
        if cc:
            msg["Cc"] = ", ".join(cc)

        corpo = MIMEMultipart("alternative")
        corpo.attach(MIMEText(corpo_html, "html"))
        msg.attach(corpo)

        for nome_file, dati in (allegati or []):
            parte = MIMEApplication(dati, Name=nome_file)
            parte["Content-Disposition"] = f'attachment; filename="{nome_file}"'
            msg.attach(parte)

        destinatari = [destinatario] + cc + bcc

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(mittente, password)
            server.sendmail(mittente, destinatari, msg.as_string())

        _log_email(destinatario, oggetto, corpo_html, tipo, riferimento_id, True, None)
        return None

    except Exception as e:
        _log_email(destinatario, oggetto, corpo_html, tipo, riferimento_id, False, str(e))
        return str(e)

def _log_email(destinatario, oggetto, corpo, tipo, riferimento_id, inviata, errore):
    sb = get_sb()
    try:
        sb.table("email_log").insert({
            "destinatario": destinatario,
            "oggetto": oggetto,
            "corpo": corpo,
            "tipo": tipo,
            "riferimento_id": str(riferimento_id) if riferimento_id else None,
            "inviata": inviata,
            "errore": errore
        }).execute()
    except:
        pass

def corpo_conferma_ordine(cliente, offerta):
    """Genera il corpo HTML della conferma d'ordine."""
    if cliente.get("tipo") == "giuridica":
        nome_dest = cliente.get("ragione_sociale", "")
        referente = f"{cliente.get('contatto_nome','')} {cliente.get('contatto_cognome','')}".strip()
        saluto = f"Gentile {referente}," if referente else f"Gentile {nome_dest},"
    else:
        nome_dest = f"{cliente.get('nome','')} {cliente.get('cognome','')}".strip()
        saluto = f"Gentile {nome_dest},"

    righe_html = ""
    righe = offerta.get("righe") or []
    import json
    if isinstance(righe, str):
        try:
            righe = json.loads(righe)
        except:
            righe = []

    for r in righe:
        righe_html += f"""
        <tr>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;">{r.get('descrizione','—')}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:center;">{r.get('qta',1)}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:right;">{float(r.get('prezzo',0)):,.2f}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:right;font-weight:600;">{float(r.get('totale',0)):,.2f}</td>
        </tr>"""

    importo = float(offerta.get("importo") or 0)
    valuta = offerta.get("valuta", "CHF")
    numero = offerta.get("numero", "—")

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:'Helvetica Neue',Arial,sans-serif;color:#1a1a2e;max-width:600px;margin:0 auto;padding:20px;">

  <div style="border-bottom:3px solid #1a1a2e;padding-bottom:20px;margin-bottom:30px;">
    <h1 style="font-size:22px;font-weight:700;margin:0;color:#1a1a2e;">RickCars</h1>
    <p style="font-size:12px;color:#888;margin:4px 0 0 0;">Conferma d'ordine</p>
  </div>

  <p style="font-size:15px;margin-bottom:24px;">{saluto}</p>

  <p style="font-size:14px;line-height:1.7;">
    Siamo lieti di confermare la ricezione e l'accettazione della Vs. offerta 
    <strong>n. {numero}</strong>. Di seguito il riepilogo di quanto concordato.
  </p>

  <table style="width:100%;border-collapse:collapse;margin:24px 0;font-size:13px;">
    <thead>
      <tr style="background:#1a1a2e;color:white;">
        <th style="padding:10px 12px;text-align:left;">Descrizione</th>
        <th style="padding:10px 12px;text-align:center;">Qta</th>
        <th style="padding:10px 12px;text-align:right;">Prezzo</th>
        <th style="padding:10px 12px;text-align:right;">Totale</th>
      </tr>
    </thead>
    <tbody>
      {righe_html}
    </tbody>
    <tfoot>
      <tr style="background:#f4f4f8;">
        <td colspan="3" style="padding:12px;font-weight:700;text-align:right;font-size:14px;">
          TOTALE {valuta}
        </td>
        <td style="padding:12px;font-weight:700;text-align:right;font-size:16px;color:#1a1a2e;">
          {importo:,.2f}
        </td>
      </tr>
    </tfoot>
  </table>

  <p style="font-size:14px;line-height:1.7;">
    Restiamo a Vostra disposizione per qualsiasi necessità e non vediamo l'ora 
    di lavorare insieme.
  </p>

  <div style="margin-top:40px;padding-top:20px;border-top:1px solid #eee;">
    <p style="font-size:12px;color:#888;margin:0;">
      RickCars &nbsp;·&nbsp; {st.secrets.get('EMAIL_MITTENTE','')}
    </p>
    <p style="font-size:11px;color:#bbb;margin:4px 0 0 0;">
      Questo messaggio è stato generato automaticamente dalla piattaforma CRM.
    </p>
  </div>

</body>
</html>"""
