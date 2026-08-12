from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
import io
import json
import os
from datetime import date

COLORE_PRIMARIO   = colors.HexColor("#1a1a2e")
COLORE_SECONDARIO = colors.HexColor("#4a4a7a")
COLORE_CHIARO     = colors.HexColor("#f4f4f8")
COLORE_BORDO      = colors.HexColor("#dddde8")
COLORE_TESTO      = colors.HexColor("#1a1a2e")
COLORE_GRIGIO     = colors.HexColor("#888888")
COLORE_UPGRADE    = colors.HexColor("#856404")

# Nome mostrato nell'intestazione quando il logo non c'è
NOME_AZIENDA = "RickCars"

# Possibili nomi/percorsi del file logo, in ordine di preferenza.
FILE_LOGO = (
    "logo.jpeg",
    "logo.jpg",
    "logo.png",
    "assets/logo.jpeg",
)

# Larghezza del logo nel PDF; l'altezza è calcolata dalle proporzioni reali
# dell'immagine, così il logo non risulta schiacciato o stirato.
LOGO_LARGHEZZA_MM = 45


def _trova_logo():
    """Restituisce un'immagine ReportLab per il logo, o None se il file
    non esiste. Nota: ReportLab apre il file solo durante doc.build(),
    quindi il controllo va fatto qui e non con un try/except attorno a
    Image(), altrimenti l'errore esplode più tardi."""
    from reportlab.platypus import Image as RLImage
    base = os.path.dirname(os.path.abspath(__file__))
    for nome in FILE_LOGO:
        for percorso in (os.path.join(base, nome), nome):
            if os.path.isfile(percorso):
                try:
                    larg = LOGO_LARGHEZZA_MM * mm
                    try:
                        from reportlab.lib.utils import ImageReader
                        w_px, h_px = ImageReader(percorso).getSize()
                        alt = larg * h_px / w_px
                    except Exception:
                        alt = larg * 0.4
                    img = RLImage(percorso, width=larg, height=alt)
                    img.hAlign = "LEFT"
                    return img
                except Exception:
                    pass
    return None
COLORE_UPGRADE_BG = colors.HexColor("#fff8e1")


def genera_pdf_offerta(offerta, cliente):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=15 * mm,
        bottomMargin=20 * mm
    )

    larghezza = A4[0] - 40 * mm

    # ── STILI ─────────────────────────────────────────
    s_normale = ParagraphStyle(
        "normale", fontSize=9, leading=14, textColor=COLORE_TESTO)
    s_piccolo = ParagraphStyle(
        "piccolo", fontSize=8, leading=12, textColor=COLORE_GRIGIO)
    s_bold = ParagraphStyle(
        "bold", fontSize=9, leading=14, textColor=COLORE_TESTO,
        fontName="Helvetica-Bold")
    s_titolo_doc = ParagraphStyle(
        "titolo_doc", fontSize=22, leading=28, textColor=COLORE_PRIMARIO,
        fontName="Helvetica-Bold")
    s_numero = ParagraphStyle(
        "numero", fontSize=11, leading=16, textColor=COLORE_SECONDARIO,
        fontName="Helvetica-Bold")
    s_sezione = ParagraphStyle(
        "sezione", fontSize=8, leading=12, textColor=COLORE_GRIGIO,
        fontName="Helvetica-Bold", spaceAfter=4)
    s_footer = ParagraphStyle(
        "footer", fontSize=7.5, leading=11, textColor=COLORE_GRIGIO,
        alignment=TA_CENTER)
    s_td = ParagraphStyle(
        "td", fontSize=9, textColor=COLORE_TESTO)
    s_td_r = ParagraphStyle(
        "td_r", fontSize=9, textColor=COLORE_TESTO, alignment=TA_RIGHT)
    s_th = ParagraphStyle(
        "th", fontSize=8, fontName="Helvetica-Bold", textColor=colors.white)
    s_upgrade_td = ParagraphStyle(
        "upg_td", fontSize=9, textColor=COLORE_UPGRADE, leading=14)
    s_upgrade_td_r = ParagraphStyle(
        "upg_td_r", fontSize=9, textColor=COLORE_UPGRADE,
        leading=14, alignment=TA_RIGHT)

    elementi = []

    # ── INTESTAZIONE ──────────────────────────────────
    logo = _trova_logo()
    if logo is not None:
        t_int = Table(
            [[logo, Paragraph("OFFERTA COMMERCIALE", s_titolo_doc)]],
            colWidths=[60 * mm, larghezza - 60 * mm]
        )
        t_int.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ]))
        elementi.append(t_int)
    else:
        t_int = Table(
            [[Paragraph(NOME_AZIENDA, s_bold),
              Paragraph("OFFERTA COMMERCIALE", s_titolo_doc)]],
            colWidths=[60 * mm, larghezza - 60 * mm]
        )
        t_int.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ]))
        elementi.append(t_int)

    elementi.append(Spacer(1, 3 * mm))
    elementi.append(HRFlowable(
        width="100%", thickness=2, color=COLORE_PRIMARIO))
    elementi.append(Spacer(1, 5 * mm))

    # ── DATI OFFERTA + CLIENTE ────────────────────────
    numero = offerta.get("numero", "—")
    data_em = offerta.get("data_emissione", str(date.today()))
    data_sc = offerta.get("data_scadenza", "—") or "—"
    stato = offerta.get("stato", "—").upper()
    versione = offerta.get("versione", 1)
    valuta = offerta.get("valuta", "CHF")

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

    col_sx = [
        [Paragraph("DESTINATARIO", s_sezione)],
        [Paragraph(f"<b>{nome_cliente}</b>", s_bold)],
        [Paragraph(riga2_cliente, s_normale)],
    ]
    if riga3_cliente:
        col_sx.append([Paragraph(riga3_cliente, s_normale)])
    if indirizzo_cl.strip(", "):
        col_sx.append([Paragraph(indirizzo_cl, s_normale)])
    if paese_cl:
        col_sx.append([Paragraph(paese_cl, s_normale)])
    if email_cl:
        col_sx.append([Paragraph(email_cl, s_normale)])
    if tel_cl:
        col_sx.append([Paragraph(tel_cl, s_normale)])

    col_dx = [
        [Paragraph("DETTAGLI OFFERTA", s_sezione)],
        [Paragraph(f"<b>N. {numero}</b>", s_numero)],
        [Paragraph(f"Versione: {versione}", s_normale)],
        [Paragraph(f"Stato: <b>{stato}</b>", s_bold)],
        [Paragraph(f"Data emissione: {data_em}", s_normale)],
        [Paragraph(f"Valida fino al: {data_sc}", s_normale)],
    ]

    max_r = max(len(col_sx), len(col_dx))
    while len(col_sx) < max_r:
        col_sx.append([Paragraph("", s_normale)])
    while len(col_dx) < max_r:
        col_dx.append([Paragraph("", s_normale)])

    dati_header = [[col_sx[i][0], col_dx[i][0]] for i in range(max_r)]
    t_header = Table(
        dati_header,
        colWidths=[larghezza * 0.55, larghezza * 0.45]
    )
    t_header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("ROWPADDING", (0, 0), (-1, -1), 2),
    ]))
    elementi.append(t_header)
    elementi.append(Spacer(1, 6 * mm))

    # ── OGGETTO ───────────────────────────────────────
    titolo_offerta = offerta.get("titolo", "")
    descrizione = offerta.get("descrizione", "")

    elementi.append(HRFlowable(
        width="100%", thickness=0.5, color=COLORE_BORDO))
    elementi.append(Spacer(1, 3 * mm))
    elementi.append(Paragraph("OGGETTO", s_sezione))
    elementi.append(Paragraph(f"<b>{titolo_offerta}</b>", s_bold))
    if descrizione:
        elementi.append(Spacer(1, 2 * mm))
        elementi.append(Paragraph(descrizione, s_normale))
    elementi.append(Spacer(1, 5 * mm))

    # ── TABELLA VOCI ─────────────────────────────────
    righe = offerta.get("righe") or []
    if isinstance(righe, str):
        try:
            righe = json.loads(righe)
        except:
            righe = []

    righe_base = [r for r in righe if not r.get("upgrade")]
    righe_upgrade = [r for r in righe if r.get("upgrade")]

    elementi.append(HRFlowable(
        width="100%", thickness=0.5, color=COLORE_BORDO))
    elementi.append(Spacer(1, 3 * mm))
    elementi.append(Paragraph("VOCI", s_sezione))
    elementi.append(Spacer(1, 2 * mm))

    col_w = [
        larghezza * 0.50,
        larghezza * 0.12,
        larghezza * 0.18,
        larghezza * 0.20
    ]

    # Header tabella
    dati_tabella = [[
        Paragraph("DESCRIZIONE", s_th),
        Paragraph("QTA", s_th),
        Paragraph(f"PREZZO ({valuta})", s_th),
        Paragraph(f"TOTALE ({valuta})", s_th),
    ]]

    totale_base = 0.0
    totale_upgrade = 0.0

    # Righe base
    for i, r in enumerate(righe_base):
        qta = float(r.get("qta", 1))
        prezzo = float(r.get("prezzo", 0))
        tot_riga = float(r.get("totale", qta * prezzo))
        totale_base += tot_riga
        dati_tabella.append([
            Paragraph(r.get("descrizione", "—"), s_td),
            Paragraph(f"{qta:g}", ParagraphStyle(
                "td_c", fontSize=9, textColor=COLORE_TESTO,
                alignment=TA_CENTER)),
            Paragraph(f"{prezzo:,.2f}", s_td_r),
            Paragraph(f"{tot_riga:,.2f}", s_td_r),
        ])

    if not righe_base:
        dati_tabella.append([
            Paragraph("Nessuna voce base inserita", s_td),
            Paragraph("", s_td),
            Paragraph("", s_td),
            Paragraph("", s_td),
        ])

    # Riga totale base
    dati_tabella.append([
        Paragraph("", s_td),
        Paragraph("", s_td),
        Paragraph(f"TOTALE BASE {valuta}", ParagraphStyle(
            "tot_base_l", fontSize=10, fontName="Helvetica-Bold",
            textColor=COLORE_PRIMARIO, leading=14, alignment=TA_RIGHT)),
        Paragraph(f"{totale_base:,.2f}", ParagraphStyle(
            "tot_base_v", fontSize=12, fontName="Helvetica-Bold",
            textColor=COLORE_PRIMARIO, leading=16, alignment=TA_RIGHT)),
    ])

    # Sezione upgrade
    if righe_upgrade:
        elementi_upgrade_idx = len(dati_tabella)

        # Separatore upgrade
        dati_tabella.append([
            Paragraph("OPZIONI UPGRADE — opzionali", ParagraphStyle(
                "upg_sep", fontSize=8, fontName="Helvetica-Bold",
                textColor=colors.white, leading=12)),
            Paragraph("", s_th),
            Paragraph("", s_th),
            Paragraph("", s_th),
        ])

        for i, r in enumerate(righe_upgrade):
            qta = float(r.get("qta", 1))
            prezzo = float(r.get("prezzo", 0))
            tot_riga = float(r.get("totale", qta * prezzo))
            totale_upgrade += tot_riga
            dati_tabella.append([
                Paragraph(r.get("descrizione", "—"), s_upgrade_td),
                Paragraph(f"{qta:g}", ParagraphStyle(
                    "upg_c", fontSize=9, textColor=COLORE_UPGRADE,
                    alignment=TA_CENTER)),
                Paragraph(f"{prezzo:,.2f}", s_upgrade_td_r),
                Paragraph(f"{tot_riga:,.2f}", s_upgrade_td_r),
            ])

        # Totale upgrade
        dati_tabella.append([
            Paragraph("", s_td),
            Paragraph("", s_td),
            Paragraph(f"UPGRADE OPZIONALE {valuta}", ParagraphStyle(
                "tot_upg_l", fontSize=9, fontName="Helvetica-Bold",
                textColor=COLORE_UPGRADE, leading=13, alignment=TA_RIGHT)),
            Paragraph(f"{totale_upgrade:,.2f}", ParagraphStyle(
                "tot_upg_v", fontSize=11, fontName="Helvetica-Bold",
                textColor=COLORE_UPGRADE, leading=15, alignment=TA_RIGHT)),
        ])

        # Totale complessivo con upgrade
        dati_tabella.append([
            Paragraph("", s_td),
            Paragraph("", s_td),
            Paragraph(f"TOTALE CON UPGRADE {valuta}", ParagraphStyle(
                "tot_all_l", fontSize=10, fontName="Helvetica-Bold",
                textColor=COLORE_PRIMARIO, leading=14, alignment=TA_RIGHT)),
            Paragraph(f"{totale_base + totale_upgrade:,.2f}", ParagraphStyle(
                "tot_all_v", fontSize=13, fontName="Helvetica-Bold",
                textColor=COLORE_PRIMARIO, leading=17, alignment=TA_RIGHT)),
        ])

    n = len(dati_tabella)
    t_voci = Table(dati_tabella, colWidths=col_w, repeatRows=1)

    stile = [
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), COLORE_PRIMARIO),
        # Righe alternate base
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLORE_CHIARO]),
        # Griglia
        ("GRID", (0, 0), (-1, -1), 0.3, COLORE_BORDO),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
    ]

    # Stile riga totale base
    idx_tot_base = len(righe_base) + (1 if not righe_base else 0) + 1
    stile.append(("BACKGROUND", (0, idx_tot_base), (-1, idx_tot_base),
                  colors.HexColor("#eeeef8")))
    stile.append(("LINEABOVE", (0, idx_tot_base), (-1, idx_tot_base),
                  1.5, COLORE_PRIMARIO))

    # Stile sezione upgrade
    if righe_upgrade:
        sep_idx = idx_tot_base + 1
        stile.append(("BACKGROUND", (0, sep_idx), (-1, sep_idx),
                      COLORE_UPGRADE))
        # Sfondi righe upgrade
        for i in range(len(righe_upgrade)):
            row_idx = sep_idx + 1 + i
            bg = COLORE_UPGRADE_BG if i % 2 == 0 else colors.white
            stile.append(("BACKGROUND", (0, row_idx), (-1, row_idx), bg))
        # Totale upgrade
        tot_upg_idx = sep_idx + len(righe_upgrade) + 1
        stile.append(("BACKGROUND", (0, tot_upg_idx), (-1, tot_upg_idx),
                      colors.HexColor("#fff3cd")))
        stile.append(("LINEABOVE", (0, tot_upg_idx), (-1, tot_upg_idx),
                      1, COLORE_UPGRADE))
        # Totale con upgrade
        tot_all_idx = tot_upg_idx + 1
        stile.append(("BACKGROUND", (0, tot_all_idx), (-1, tot_all_idx),
                      colors.HexColor("#eeeef8")))
        stile.append(("LINEABOVE", (0, tot_all_idx), (-1, tot_all_idx),
                      1.5, COLORE_PRIMARIO))

    t_voci.setStyle(TableStyle(stile))
    elementi.append(t_voci)
    elementi.append(Spacer(1, 3 * mm))

    # ── NOTE ─────────────────────────────────────────
    note = offerta.get("note", "")
    if note:
        elementi.append(Spacer(1, 5 * mm))
        elementi.append(HRFlowable(
            width="100%", thickness=0.5, color=COLORE_BORDO))
        elementi.append(Spacer(1, 3 * mm))
        elementi.append(Paragraph("NOTE", s_sezione))
        elementi.append(Paragraph(note, s_normale))

    # ── FOOTER ────────────────────────────────────────
    elementi.append(Spacer(1, 10 * mm))
    elementi.append(HRFlowable(
        width="100%", thickness=1, color=COLORE_PRIMARIO))
    elementi.append(Spacer(1, 3 * mm))
    elementi.append(Paragraph(
        NOME_AZIENDA + "   |   Documento generato automaticamente dalla "
        "piattaforma CRM   |   Riservato e confidenziale",
        s_footer
    ))

    doc.build(elementi)
    buffer.seek(0)
    return buffer.read()
