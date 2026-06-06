from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
import io
import json
from datetime import datetime

# ── COLORI ───────────────────────────────────────────
NERO        = colors.HexColor("#0d0d1a")
BLU_SCURO   = colors.HexColor("#1a1a2e")
BLU_MEDIO   = colors.HexColor("#0f3460")
BLU_CHIARO  = colors.HexColor("#16213e")
GRIGIO      = colors.HexColor("#f4f4f8")
GRIGIO_MED  = colors.HexColor("#dddde8")
GRIGIO_TESTO = colors.HexColor("#888888")
BIANCO      = colors.white
ACCENT      = colors.HexColor("#e94560")

def _stili():
    return {
        "titolo_doc": ParagraphStyle(
            "titolo_doc", fontSize=28, fontName="Helvetica-Bold",
            textColor=BIANCO, leading=32, spaceAfter=2
        ),
        "sottotitolo_doc": ParagraphStyle(
            "sottotitolo_doc", fontSize=10, fontName="Helvetica",
            textColor=colors.HexColor("#aaaacc"), leading=14
        ),
        "sezione": ParagraphStyle(
            "sezione", fontSize=8, fontName="Helvetica-Bold",
            textColor=GRIGIO_TESTO, leading=12,
            spaceBefore=4, spaceAfter=6,
            textTransform="uppercase", letterSpacing=1.2
        ),
        "normale": ParagraphStyle(
            "normale", fontSize=9, fontName="Helvetica",
            textColor=NERO, leading=14
        ),
        "bold": ParagraphStyle(
            "bold", fontSize=9, fontName="Helvetica-Bold",
            textColor=NERO, leading=14
        ),
        "grande": ParagraphStyle(
            "grande", fontSize=13, fontName="Helvetica-Bold",
            textColor=NERO, leading=18
        ),
        "piccolo": ParagraphStyle(
            "piccolo", fontSize=7.5, fontName="Helvetica",
            textColor=GRIGIO_TESTO, leading=11
        ),
        "bianco_bold": ParagraphStyle(
            "bianco_bold", fontSize=9, fontName="Helvetica-Bold",
            textColor=BIANCO, leading=13
        ),
        "bianco": ParagraphStyle(
            "bianco", fontSize=8, fontName="Helvetica",
            textColor=BIANCO, leading=12
        ),
        "centro": ParagraphStyle(
            "centro", fontSize=9, fontName="Helvetica",
            textColor=NERO, leading=14, alignment=TA_CENTER
        ),
        "destra": ParagraphStyle(
            "destra", fontSize=9, fontName="Helvetica",
            textColor=NERO, leading=14, alignment=TA_RIGHT
        ),
        "footer": ParagraphStyle(
            "footer", fontSize=7, fontName="Helvetica",
            textColor=GRIGIO_TESTO, leading=10, alignment=TA_CENTER
        ),
        "alert": ParagraphStyle(
            "alert", fontSize=9, fontName="Helvetica-Bold",
            textColor=ACCENT, leading=14
        ),
    }

def _riga_info(label, valore, s):
    return Table(
        [[Paragraph(label, s["piccolo"]), Paragraph(str(valore), s["bold"])]],
        colWidths=["35%", "65%"]
    )

def genera_beo(evento, cliente=None, offerta=None, allegati=None):
    buffer = io.BytesIO()
    larghezza, altezza = A4
    margine = 18 * mm

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=margine, leftMargin=margine,
        topMargin=margine, bottomMargin=20 * mm
    )

    s = _stili()
    w = larghezza - 2 * margine
    elementi = []

    # ════════════════════════════════════════════════
    # INTESTAZIONE
    # ════════════════════════════════════════════════
    data_evento = ""
    orario_str = ""
    try:
        if evento.get("data_inizio"):
            dt = datetime.fromisoformat(evento["data_inizio"].replace("Z", ""))
            data_evento = dt.strftime("%A %d %B %Y").capitalize()
        orario_str = (
            f"{evento.get('orario_inizio','—')} — {evento.get('orario_fine','—')}"
        )
    except:
        data_evento = evento.get("data_inizio", "")[:10]

    # Blocco header scuro
    header_data = [[
        [
            Paragraph("BANQUET EVENT ORDER", s["titolo_doc"]),
            Paragraph("1908 Group SA", s["sottotitolo_doc"]),
        ],
        [
            Paragraph(data_evento, ParagraphStyle(
                "data_h", fontSize=11, fontName="Helvetica-Bold",
                textColor=BIANCO, leading=15, alignment=TA_RIGHT
            )),
            Paragraph(orario_str, ParagraphStyle(
                "ora_h", fontSize=9, fontName="Helvetica",
                textColor=colors.HexColor("#aaaacc"), leading=13,
                alignment=TA_RIGHT
            )),
        ]
    ]]

    t_header = Table(header_data, colWidths=[w * 0.6, w * 0.4])
    t_header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLU_SCURO),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWPADDING", (0, 0), (-1, -1), 18),
        ("ROUNDEDCORNERS", [8, 8, 8, 8]),
    ]))

    # Aggiungi logo se disponibile
    try:
        from reportlab.platypus import Image as RLImage
        logo = RLImage("1908_Group_Black.png", width=35 * mm, height=14 * mm)
        logo_data = [[logo, t_header]]
        # Usa solo il t_header senza logo per semplicità
        elementi.append(t_header)
    except:
        elementi.append(t_header)

    elementi.append(Spacer(1, 6 * mm))

    # Striscia numero BEO + stato
    numero_beo = f"BEO-{evento.get('id','')[:8].upper()}"
    stato = evento.get("stato", "nuovo").upper()
    coperti = evento.get("numero_coperti", 0)

    badge_data = [[
        Paragraph(f"N. {numero_beo}", ParagraphStyle(
            "beo_num", fontSize=11, fontName="Helvetica-Bold",
            textColor=BLU_SCURO, leading=15
        )),
        Paragraph(stato, ParagraphStyle(
            "stato_b", fontSize=9, fontName="Helvetica-Bold",
            textColor=BIANCO, leading=13, alignment=TA_CENTER
        )),
        Paragraph(
            f"{coperti} coperti" if coperti else "Coperti da definire",
            ParagraphStyle(
                "cop_b", fontSize=9, fontName="Helvetica-Bold",
                textColor=BLU_SCURO, leading=13, alignment=TA_RIGHT
            )
        ),
    ]]
    t_badge = Table(badge_data, colWidths=[w * 0.45, w * 0.2, w * 0.35])
    t_badge.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), GRIGIO),
        ("BACKGROUND", (1, 0), (1, 0), BLU_MEDIO),
        ("BACKGROUND", (2, 0), (2, 0), GRIGIO),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWPADDING", (0, 0), (-1, -1), 10),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    elementi.append(t_badge)
    elementi.append(Spacer(1, 6 * mm))

    # ════════════════════════════════════════════════
    # SEZIONE 1 — EVENTO + CLIENTE
    # ════════════════════════════════════════════════
    elementi.append(Paragraph("Dettagli evento", s["sezione"]))
    elementi.append(HRFlowable(width="100%", thickness=0.5, color=GRIGIO_MED))
    elementi.append(Spacer(1, 3 * mm))

    # Nome cliente
    if cliente:
        if cliente.get("tipo") == "giuridica":
            nome_cliente = cliente.get("ragione_sociale", "—")
        else:
            nome_cliente = f"{cliente.get('nome','')} {cliente.get('cognome','')}".strip()
        email_cl = cliente.get("email", "—")
        tel_cl = cliente.get("telefono", "—")
        indirizzo_cl = f"{cliente.get('indirizzo','')}, {cliente.get('cap','')} {cliente.get('citta','')}".strip(", ")
    else:
        nome_cliente = "—"
        email_cl = tel_cl = indirizzo_cl = "—"

    ref_nome = evento.get("referente_cliente_nome", "")
    ref_tel = evento.get("referente_cliente_telefono", "")

    col_ev = [
        [Paragraph("Evento", s["piccolo"]),
         Paragraph(evento.get("titolo", "—"), s["grande"])],
        [Paragraph("Luogo", s["piccolo"]),
         Paragraph(evento.get("luogo", "—"), s["bold"])],
        [Paragraph("Data", s["piccolo"]),
         Paragraph(data_evento, s["normale"])],
        [Paragraph("Orario", s["piccolo"]),
         Paragraph(orario_str, s["normale"])],
        [Paragraph("Coperti", s["piccolo"]),
         Paragraph(str(coperti) if coperti else "Da definire", s["normale"])],
    ]
    col_cl = [
        [Paragraph("Cliente", s["piccolo"]),
         Paragraph(nome_cliente, s["grande"])],
        [Paragraph("Email", s["piccolo"]),
         Paragraph(email_cl, s["normale"])],
        [Paragraph("Telefono", s["piccolo"]),
         Paragraph(tel_cl, s["normale"])],
        [Paragraph("Indirizzo", s["piccolo"]),
         Paragraph(indirizzo_cl, s["normale"])],
        [Paragraph("Referente giorno", s["piccolo"]),
         Paragraph(
             f"{ref_nome} — {ref_tel}" if ref_nome else "—",
             s["normale"]
         )],
    ]

    def _blocco_info(righe, w_col):
        t = Table(righe, colWidths=[w_col * 0.32, w_col * 0.68])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWPADDING", (0, 0), (-1, -1), 3),
        ]))
        return t

    t_ev_cl = Table(
        [[_blocco_info(col_ev, w * 0.48), _blocco_info(col_cl, w * 0.48)]],
        colWidths=[w * 0.50, w * 0.50]
    )
    t_ev_cl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, 0), GRIGIO),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#f0f0f8")),
        ("ROWPADDING", (0, 0), (-1, -1), 12),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    elementi.append(t_ev_cl)
    elementi.append(Spacer(1, 5 * mm))

    # ════════════════════════════════════════════════
    # SEZIONE 2 — MENU
    # ════════════════════════════════════════════════
    elementi.append(Paragraph("Menu e servizi", s["sezione"]))
    elementi.append(HRFlowable(width="100%", thickness=0.5, color=GRIGIO_MED))
    elementi.append(Spacer(1, 3 * mm))

    righe_offerta = []
    if offerta:
        righe_raw = offerta.get("righe") or []
        if isinstance(righe_raw, str):
            try:
                righe_raw = json.loads(righe_raw)
            except:
                righe_raw = []
        righe_offerta = righe_raw

    if righe_offerta:
        # Header tabella
        header_menu = [
            Paragraph("VOCE / DESCRIZIONE", s["bianco_bold"]),
            Paragraph("QTÀ", ParagraphStyle(
                "qta_h", fontSize=9, fontName="Helvetica-Bold",
                textColor=BIANCO, leading=13, alignment=TA_CENTER
            )),
            Paragraph(f"PREZZO UNIT.\n({offerta.get('valuta','CHF')})", ParagraphStyle(
                "pr_h", fontSize=9, fontName="Helvetica-Bold",
                textColor=BIANCO, leading=13, alignment=TA_RIGHT
            )),
            Paragraph(f"TOTALE\n({offerta.get('valuta','CHF')})", ParagraphStyle(
                "tot_h", fontSize=9, fontName="Helvetica-Bold",
                textColor=BIANCO, leading=13, alignment=TA_RIGHT
            )),
        ]

        dati_menu = [header_menu]
        totale_gen = 0.0

        for i, r in enumerate(righe_offerta):
            qta = float(r.get("qta", 1))
            prezzo = float(r.get("prezzo", 0))
            tot = float(r.get("totale", qta * prezzo))
            totale_gen += tot
            bg = GRIGIO if i % 2 == 0 else BIANCO
            dati_menu.append([
                Paragraph(r.get("descrizione", "—"), s["normale"]),
                Paragraph(f"{qta:g}", s["centro"]),
                Paragraph(f"{prezzo:,.2f}", s["destra"]),
                Paragraph(f"{tot:,.2f}", s["destra"]),
            ])

        # Riga totale
        dati_menu.append([
            Paragraph("", s["normale"]),
            Paragraph("", s["normale"]),
            Paragraph("TOTALE", ParagraphStyle(
                "tot_l", fontSize=10, fontName="Helvetica-Bold",
                textColor=BLU_SCURO, leading=14, alignment=TA_RIGHT
            )),
            Paragraph(
                f"{offerta.get('valuta','CHF')} {totale_gen:,.2f}",
                ParagraphStyle(
                    "tot_v", fontSize=12, fontName="Helvetica-Bold",
                    textColor=BLU_SCURO, leading=16, alignment=TA_RIGHT
                )
            ),
        ])

        col_w_menu = [w * 0.52, w * 0.10, w * 0.19, w * 0.19]
        n = len(dati_menu)

        t_menu = Table(dati_menu, colWidths=col_w_menu, repeatRows=1)
        stile_menu = [
            ("BACKGROUND", (0, 0), (-1, 0), BLU_SCURO),
            ("ROWBACKGROUNDS", (0, 1), (-1, n - 2), [GRIGIO, BIANCO]),
            ("BACKGROUND", (0, n - 1), (-1, n - 1), colors.HexColor("#eeeef8")),
            ("LINEABOVE", (0, n - 1), (-1, n - 1), 1.5, BLU_SCURO),
            ("GRID", (0, 0), (-1, n - 2), 0.3, GRIGIO_MED),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWPADDING", (0, 0), (-1, -1), 7),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ]
        t_menu.setStyle(TableStyle(stile_menu))
        elementi.append(t_menu)
    else:
        elementi.append(Paragraph(
            "Nessuna voce di menu inserita — fare riferimento all'offerta allegata.",
            s["normale"]
        ))

    elementi.append(Spacer(1, 5 * mm))

    # ════════════════════════════════════════════════
    # SEZIONE 3 — TIMELINE
    # ════════════════════════════════════════════════
    timeline = evento.get("timeline") or []
    if isinstance(timeline, str):
        try:
            timeline = json.loads(timeline)
        except:
            timeline = []

    if timeline:
        elementi.append(Paragraph("Timeline operativa", s["sezione"]))
        elementi.append(HRFlowable(width="100%", thickness=0.5, color=GRIGIO_MED))
        elementi.append(Spacer(1, 3 * mm))

        header_tl = [
            Paragraph("ORARIO", s["bianco_bold"]),
            Paragraph("ATTIVITÀ", s["bianco_bold"]),
            Paragraph("RESPONSABILE", s["bianco_bold"]),
            Paragraph("NOTE", s["bianco_bold"]),
        ]
        dati_tl = [header_tl]
        for i, t_item in enumerate(timeline):
            dati_tl.append([
                Paragraph(t_item.get("orario", "—"), s["bold"]),
                Paragraph(t_item.get("attivita", "—"), s["normale"]),
                Paragraph(t_item.get("responsabile", "—"), s["normale"]),
                Paragraph(t_item.get("note", ""), s["piccolo"]),
            ])

        t_tl = Table(
            dati_tl,
            colWidths=[w * 0.13, w * 0.37, w * 0.25, w * 0.25],
            repeatRows=1
        )
        t_tl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BLU_MEDIO),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [GRIGIO, BIANCO]),
            ("GRID", (0, 0), (-1, -1), 0.3, GRIGIO_MED),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWPADDING", (0, 0), (-1, -1), 7),
        ]))
        elementi.append(t_tl)
        elementi.append(Spacer(1, 5 * mm))

    # ════════════════════════════════════════════════
    # SEZIONE 4 — NOTE OPERATIVE (3 colonne)
    # ════════════════════════════════════════════════
    note_setup = evento.get("setup_sala", "")
    note_allergeni = evento.get("note_allergeni", "")
    note_cucina = evento.get("note_cucina", "")
    note_servizio = evento.get("note_servizio", "")
    note_gen = evento.get("note", "")

    if any([note_setup, note_allergeni, note_cucina, note_servizio, note_gen]):
        elementi.append(Paragraph("Note operative", s["sezione"]))
        elementi.append(HRFlowable(width="100%", thickness=0.5, color=GRIGIO_MED))
        elementi.append(Spacer(1, 3 * mm))

        def _box_nota(titolo, testo, colore_header):
            contenuto = testo or "—"
            inner = Table(
                [
                    [Paragraph(titolo, s["bianco_bold"])],
                    [Paragraph(contenuto, s["normale"])],
                ],
                colWidths=["100%"]
            )
            inner.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colore_header),
                ("BACKGROUND", (0, 1), (-1, -1), GRIGIO),
                ("ROWPADDING", (0, 0), (-1, -1), 8),
                ("ROUNDEDCORNERS", [5, 5, 5, 5]),
            ]))
            return inner

        note_items = []
        if note_allergeni:
            note_items.append(_box_nota("ALLERGENI", note_allergeni, ACCENT))
        if note_cucina:
            note_items.append(_box_nota("CUCINA", note_cucina, BLU_SCURO))
        if note_servizio:
            note_items.append(_box_nota("SERVIZIO", note_servizio, BLU_MEDIO))
        if note_setup:
            note_items.append(_box_nota("SETUP SALA", note_setup, colors.HexColor("#533483")))
        if note_gen:
            note_items.append(_box_nota("NOTE GENERALI", note_gen, colors.HexColor("#2d6a4f")))

        # Distribuisci in colonne da 2
        for i in range(0, len(note_items), 2):
            riga = note_items[i:i+2]
            if len(riga) == 1:
                riga.append(Paragraph("", s["normale"]))
            t_note = Table([riga], colWidths=[w * 0.49, w * 0.49])
            t_note.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (1, 0), (1, 0), 8),
            ]))
            elementi.append(t_note)
            elementi.append(Spacer(1, 3 * mm))

    # ════════════════════════════════════════════════
    # SEZIONE 5 — COLLABORATORI
    # ════════════════════════════════════════════════
    from db import lista_collaboratori_evento
    collaboratori = lista_collaboratori_evento(evento["id"])

    if collaboratori:
        elementi.append(Spacer(1, 2 * mm))
        elementi.append(Paragraph("Team assegnato", s["sezione"]))
        elementi.append(HRFlowable(width="100%", thickness=0.5, color=GRIGIO_MED))
        elementi.append(Spacer(1, 3 * mm))

        header_team = [
            Paragraph("NOME", s["bianco_bold"]),
            Paragraph("RUOLO", s["bianco_bold"]),
            Paragraph("CONTATTO", s["bianco_bold"]),
        ]
        dati_team = [header_team]
        for c in collaboratori:
            u = c.get("utente") or {}
            nome = f"{u.get('nome','')} {u.get('cognome','')}".strip() if u else c.get("nome_esterno", "—")
            email = u.get("email", "") if u else c.get("email_esterno", "")
            ruolo = c.get("ruolo") or "—"
            dati_team.append([
                Paragraph(nome, s["normale"]),
                Paragraph(ruolo, s["normale"]),
                Paragraph(email, s["piccolo"]),
            ])

        t_team = Table(
            dati_team,
            colWidths=[w * 0.35, w * 0.30, w * 0.35],
            repeatRows=1
        )
        t_team.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BLU_SCURO),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [GRIGIO, BIANCO]),
            ("GRID", (0, 0), (-1, -1), 0.3, GRIGIO_MED),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWPADDING", (0, 0), (-1, -1), 7),
        ]))
        elementi.append(t_team)

    # ════════════════════════════════════════════════
    # FOOTER
    # ════════════════════════════════════════════════
    elementi.append(Spacer(1, 8 * mm))
    elementi.append(HRFlowable(width="100%", thickness=1.5, color=BLU_SCURO))
    elementi.append(Spacer(1, 3 * mm))

    numero_offerta = offerta.get("numero", "—") if offerta else "—"
    data_stampa = datetime.now().strftime("%d/%m/%Y %H:%M")

    elementi.append(Paragraph(
        f"1908 Group SA  &nbsp;·&nbsp;  BEO {numero_beo}  &nbsp;·&nbsp;  "
        f"Offerta rif. {numero_offerta}  &nbsp;·&nbsp;  "
        f"Documento generato il {data_stampa}  &nbsp;·&nbsp;  "
        f"Documento riservato — uso interno e operativo",
        s["footer"]
    ))

    doc.build(elementi)
    buffer.seek(0)
    return buffer.read()
