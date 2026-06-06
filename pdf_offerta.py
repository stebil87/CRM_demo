from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
import io
import json
from datetime import date

COLORE_PRIMARIO = colors.HexColor("#1a1a2e")
COLORE_SECONDARIO = colors.HexColor("#4a4a7a")
COLORE_CHIARO = colors.HexColor("#f4f4f8")
COLORE_BORDO = colors.HexColor("#dddde8")
COLORE_TESTO = colors.HexColor("#1a1a2e")
COLORE_TESTO_CHIARO = colors.HexColor("#888888")

def genera_pdf_offerta(offerta, cliente):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=15*mm,
        bottomMargin=20*mm
    )

    styles = getSampleStyleSheet()

    s_normale = ParagraphStyle("normale", fontSize=9, leading=14, textColor=COLORE_TESTO)
    s_piccolo = ParagraphStyle("piccolo", fontSize=8, leading=12, textColor=COLORE_TESTO_CHIARO)
    s_bold = ParagraphStyle("bold", fontSize=9, leading=14, textColor=COLORE_TESTO, fontName="Helvetica-Bold")
    s_titolo_doc = ParagraphStyle("titolo_doc", fontSize=22, leading=28, textColor=COLORE_PRIMARIO, fontName="Helvetica-Bold")
    s_numero = ParagraphStyle("numero", fontSize=11, leading=16, textColor=COLORE_SECONDARIO, fontName="Helvetica-Bold")
    s_sezione = ParagraphStyle("sezione", fontSize=8, leading=12, textColor=COLORE_TESTO_CHIARO, fontName="Helvetica-Bold", spaceAfter=4)
    s_footer = ParagraphStyle("footer", fontSize=7.5, leading=11, textColor=COLORE_TESTO_CHIARO, alignment=TA_CENTER)
    s_importo = ParagraphStyle("importo", fontSize=14, leading=18, textColor=COLORE_PRIMARIO, fontName="Helvetica-Bold", alignment=TA_RIGHT)

    elementi = []
    larghezza = A4[0] - 40*mm

    # ── INTESTAZIONE ──────────────────────────────────
    try:
        from reportlab.platypus import Image as RLImage
        logo = RLImage("1908_Group_Black.png", width=45*mm, height=18*mm)
        logo.hAlign = "LEFT"

        intestazione_dati = [
            [logo, Paragraph("OFFERTA COMMERCIALE", s_titolo_doc)]
        ]
        t_intestazione = Table(intestazione_dati, colWidths=[60*mm, larghezza - 60*mm])
        t_intestazione.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ]))
        elementi.append(t_intestazione)
    except:
        elementi.append(Paragraph("1908 Group SA", s_bold))
        elementi.append(Paragraph("OFFERTA COMMERCIALE", s_titolo_doc))

    elementi.append(Spacer(1, 3*mm))
    elementi.append(HRFlowable(width="100%", thickness=2, color=COLORE_PRIMARIO))
    elementi.append(Spacer(1, 5*mm))

    # ── DATI OFFERTA + DATI CLIENTE ───────────────────
    numero = offerta.get("numero", "—")
    data_em = offerta.get("data_emissione", str(date.today()))
    data_sc = offerta.get("data_scadenza", "—") or "—"
    stato = offerta.get("stato", "—").upper()
    versione = offerta.get("versione", 1)

    # Nome cliente
    if cliente.get("tipo") == "giuridica":
        nome_cliente = cliente.get("ragione_sociale") or "—"
        riga2_cliente = f"Cod. IDI: {cliente.get('codice_idi','—')}"
        referente = f"{cliente.get('contatto_nome','')} {cliente.get('contatto_cognome','')}".strip()
        riga3_cliente = f"Ref: {referente} — {cliente.get('contatto_ruolo','')}" if referente else ""
    else:
        nome_cliente = f"{cliente.get('nome','')} {cliente.get('cognome','')}".strip() or "—"
        riga2_cliente = f"Nato il: {cliente.get('data_nascita','—')}"
        riga3_cliente = ""

    indirizzo_cl = f"{cliente.get('indirizzo','')}, {cliente.get('cap','')} {cliente.get('citta','')}".strip(", ")
    paese_cl = cliente.get("paese", "")
    email_cl = cliente.get("email", "")
    tel_cl = cliente.get("telefono", "")

    col_sinistra = [
        [Paragraph("DESTINATARIO", s_sezione)],
        [Paragraph(f"<b>{nome_cliente}</b>", s_bold)],
        [Paragraph(riga2_cliente, s_normale)],
    ]
    if riga3_cliente:
        col_sinistra.append([Paragraph(riga3_cliente, s_normale)])
    if indirizzo_cl.strip(", "):
        col_sinistra.append([Paragraph(indirizzo_cl, s_normale)])
    if paese_cl:
        col_sinistra.append([Paragraph(paese_cl, s_normale)])
    if email_cl:
        col_sinistra.append([Paragraph(email_cl, s_normale)])
    if tel_cl:
        col_sinistra.append([Paragraph(tel_cl, s_normale)])

    col_destra = [
        [Paragraph("DETTAGLI OFFERTA", s_sezione)],
        [Paragraph(f"<b>N. {numero}</b>", s_numero)],
        [Paragraph(f"Versione: {versione}", s_normale)],
        [Paragraph(f"Stato: <b>{stato}</b>", s_bold)],
        [Paragraph(f"Data emissione: {data_em}", s_normale)],
        [Paragraph(f"Valida fino al: {data_sc}", s_normale)],
    ]

    # Padding righe per allineare altezze
    max_r = max(len(col_sinistra), len(col_destra))
    while len(col_sinistra) < max_r:
        col_sinistra.append([Paragraph("", s_normale)])
    while len(col_destra) < max_r:
        col_destra.append([Paragraph("", s_normale)])

    dati_header = [[col_sinistra[i][0], col_destra[i][0]] for i in range(max_r)]
    t_header = Table(dati_header, colWidths=[larghezza * 0.55, larghezza * 0.45])
    t_header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("ROWPADDING", (0, 0), (-1, -1), 2),
    ]))
    elementi.append(t_header)
    elementi.append(Spacer(1, 6*mm))

    # ── OGGETTO ───────────────────────────────────────
    titolo_offerta = offerta.get("titolo", "")
    descrizione = offerta.get("descrizione", "")

    elementi.append(HRFlowable(width="100%", thickness=0.5, color=COLORE_BORDO))
    elementi.append(Spacer(1, 3*mm))
    elementi.append(Paragraph("OGGETTO", s_sezione))
    elementi.append(Paragraph(f"<b>{titolo_offerta}</b>", s_bold))
    if descrizione:
        elementi.append(Spacer(1, 2*mm))
        elementi.append(Paragraph(descrizione, s_normale))
    elementi.append(Spacer(1, 5*mm))

    # ── TABELLA VOCI ─────────────────────────────────
    righe = offerta.get("righe") or []
    if isinstance(righe, str):
        try:
            righe = json.loads(righe)
        except:
            righe = []

    valuta = offerta.get("valuta", "CHF")

    elementi.append(HRFlowable(width="100%", thickness=0.5, color=COLORE_BORDO))
    elementi.append(Spacer(1, 3*mm))
    elementi.append(Paragraph("VOCI", s_sezione))
    elementi.append(Spacer(1, 2*mm))

    s_th = ParagraphStyle("th", fontSize=8, fontName="Helvetica-Bold", textColor=colors.white)
    s_td = ParagraphStyle("td", fontSize=9, textColor=COLORE_TESTO)
    s_td_r = ParagraphStyle("td_r", fontSize=9, textColor=COLORE_TESTO, alignment=TA_RIGHT)
    s_td_bold_r = ParagraphStyle("td_bold_r", fontSize=9, fontName="Helvetica-Bold", textColor=COLORE_TESTO, alignment=TA_RIGHT)

    col_w = [larghezza * 0.50, larghezza * 0.12, larghezza * 0.18, larghezza * 0.20]

    dati_tabella = [[
        Paragraph("DESCRIZIONE", s_th),
        Paragraph("QTA", s_th),
        Paragraph(f"PREZZO ({valuta})", s_th),
        Paragraph(f"TOTALE ({valuta})", s_th),
    ]]

    totale = 0.0
    for r in righe:
        qta = float(r.get("qta", 1))
        prezzo = float(r.get("prezzo", 0))
        tot_riga = float(r.get("totale", qta * prezzo))
        totale += tot_riga
        dati_tabella.append([
            Paragraph(r.get("descrizione", "—"), s_td),
            Paragraph(f"{qta:g}", s_td_r),
            Paragraph(f"{prezzo:,.2f}", s_td_r),
            Paragraph(f"{tot_riga:,.2f}", s_td_r),
        ])

    if not righe:
        dati_tabella.append([
            Paragraph("Nessuna voce inserita", s_td),
            Paragraph("", s_td), Paragraph("", s_td), Paragraph("", s_td)
        ])

    t_voci = Table(dati_tabella, colWidths=col_w, repeatRows=1)
    n_righe = len(dati_tabella)
    t_voci.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLORE_PRIMARIO),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLORE_CHIARO]),
        ("GRID", (0, 0), (-1, -1), 0.3, COLORE_BORDO),
        ("LINEBELOW", (0, 0), (-1, 0), 0, colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWPADDING", (0, 0), (-1, -1), 5),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
    ]))
    elementi.append(t_voci)
    elementi.append(Spacer(1, 3*mm))

    # ── TOTALE ────────────────────────────────────────
    dati_totale = [
        ["", Paragraph(f"TOTALE {valuta}", ParagraphStyle("tot_label", fontSize=10, fontName="Helvetica-Bold", textColor=COLORE_TESTO_CHIARO, alignment=TA_RIGHT)),
         Paragraph(f"{totale:,.2f}", ParagraphStyle("tot_val", fontSize=14, fontName="Helvetica-Bold", textColor=COLORE_PRIMARIO, alignment=TA_RIGHT))]
    ]
    t_totale = Table(dati_totale, colWidths=[larghezza * 0.50, larghezza * 0.28, larghezza * 0.22])
    t_totale.setStyle(TableStyle([
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEABOVE", (1, 0), (-1, 0), 1.5, COLORE_PRIMARIO),
        ("ROWPADDING", (0, 0), (-1, -1), 6),
    ]))
    elementi.append(t_totale)

    # ── NOTE ─────────────────────────────────────────
    note = offerta.get("note", "")
    if note:
        elementi.append(Spacer(1, 5*mm))
        elementi.append(HRFlowable(width="100%", thickness=0.5, color=COLORE_BORDO))
        elementi.append(Spacer(1, 3*mm))
        elementi.append(Paragraph("NOTE", s_sezione))
        elementi.append(Paragraph(note, s_normale))

    # ── FOOTER ────────────────────────────────────────
    elementi.append(Spacer(1, 10*mm))
    elementi.append(HRFlowable(width="100%", thickness=1, color=COLORE_PRIMARIO))
    elementi.append(Spacer(1, 3*mm))
    elementi.append(Paragraph(
        "1908 Group SA   |   Documento generato automaticamente dalla piattaforma CRM   |   Riservato e confidenziale",
        s_footer
    ))

    doc.build(elementi)
    buffer.seek(0)
    return buffer.read()
