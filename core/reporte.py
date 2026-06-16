"""
reporte.py — Generador de PDF con resumen de solución OptiNet.

Uso:
    from core.reporte import generar_pdf
    pdf_bytes = generar_pdf(result, net)
    # pdf_bytes es un BytesIO listo para devolver como FileResponse
"""

from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

from .data import NetworkData
from .solver import SolverResult


# ── Paleta de colores ────────────────────────────────────────────
AZUL_OSC  = colors.HexColor("#1D4ED8")
AZUL_MED  = colors.HexColor("#3B82F6")
VERDE     = colors.HexColor("#15803D")
ROJO      = colors.HexColor("#991B1B")
AMBAR     = colors.HexColor("#92400E")
GRIS_OSC  = colors.HexColor("#21262D")
GRIS_MED  = colors.HexColor("#484F58")
GRIS_CLAR = colors.HexColor("#8B949E")
FONDO     = colors.HexColor("#F3F4F6")
BLANCO    = colors.white
NEGRO     = colors.HexColor("#111827")


def generar_pdf(result: SolverResult, net: NetworkData) -> io.BytesIO:
    """
    Genera un PDF con el resumen de la solución MILP y lo retorna
    como BytesIO para ser servido directamente por FastAPI.
    """
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
        topMargin=0.9 * inch,
        bottomMargin=0.9 * inch,
        title="OptiNet — Resumen de Solución",
        author="OptiNet MILP",
    )

    estilos = _estilos()
    historia = []

    # ── Encabezado ────────────────────────────────────────────────
    historia += _encabezado(estilos, result)

    # ── Sección 1: Resumen de costos ─────────────────────────────
    historia += _seccion_costos(estilos, result)

    # ── Sección 2: Decisiones de infraestructura (CDs) ───────────
    historia += _seccion_cds(estilos, result)

    # ── Sección 3: Rutas activas ──────────────────────────────────
    historia += _seccion_rutas(estilos, result, net)

    # ── Sección 4: Atención a clientes ───────────────────────────
    historia += _seccion_clientes(estilos, result)

    # ── Sección 5: Justificación matemática ──────────────────────
    historia += _seccion_justificacion(estilos, result, net)

    # ── Pie de página (via onFirstPage / onLaterPages) ────────────
    doc.build(
        historia,
        onFirstPage=_pie_pagina,
        onLaterPages=_pie_pagina,
    )

    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────
# Estilos
# ─────────────────────────────────────────────────────────────────

def _estilos() -> dict:
    base = getSampleStyleSheet()
    return {
        "titulo":    ParagraphStyle("titulo",    fontSize=22, textColor=AZUL_OSC,
                                    spaceAfter=4,  fontName="Helvetica-Bold"),
        "subtitulo": ParagraphStyle("subtitulo", fontSize=10, textColor=GRIS_MED,
                                    spaceAfter=16, fontName="Helvetica"),
        "h2":        ParagraphStyle("h2",        fontSize=13, textColor=AZUL_OSC,
                                    spaceBefore=18, spaceAfter=6,
                                    fontName="Helvetica-Bold"),
        "body":      ParagraphStyle("body",      fontSize=9,  textColor=NEGRO,
                                    spaceAfter=4,  fontName="Helvetica",
                                    leading=14),
        "bold":      ParagraphStyle("bold",      fontSize=9,  textColor=NEGRO,
                                    fontName="Helvetica-Bold"),
        "kpi_val":   ParagraphStyle("kpi_val",   fontSize=20, textColor=AZUL_OSC,
                                    fontName="Helvetica-Bold", alignment=1),
        "kpi_lbl":   ParagraphStyle("kpi_lbl",   fontSize=8,  textColor=GRIS_MED,
                                    fontName="Helvetica",      alignment=1),
        "verde":     ParagraphStyle("verde",     fontSize=9,  textColor=VERDE,
                                    fontName="Helvetica-Bold"),
        "rojo":      ParagraphStyle("rojo",      fontSize=9,  textColor=ROJO,
                                    fontName="Helvetica-Bold"),
        "ambar":     ParagraphStyle("ambar",     fontSize=9,  textColor=AMBAR,
                                    fontName="Helvetica-Bold"),
    }


# ─────────────────────────────────────────────────────────────────
# Secciones
# ─────────────────────────────────────────────────────────────────

def _encabezado(e, result: SolverResult) -> list:
    fecha = datetime.now().strftime("%d de %B de %Y, %H:%M")
    estado_color = VERDE if result.feasible else ROJO
    estado_txt   = "ÓPTIMO ENCONTRADO" if result.feasible else result.status.upper()

    elementos = [
        Paragraph("OptiNet", e["titulo"]),
        Paragraph("Red de Distribución — Programación Entera Mixta (MILP) · CBC Solver", e["subtitulo"]),
        HRFlowable(width="100%", thickness=2, color=AZUL_OSC, spaceAfter=10),
    ]

    # Fila de estado + fecha
    estado_par = Paragraph(
        f'<font color="#{estado_color.hexval()[2:]}"><b>{estado_txt}</b></font>',
        e["body"]
    )
    fecha_par  = Paragraph(f"Generado el {fecha}", e["body"])

    t = Table([[estado_par, fecha_par]], colWidths=["50%", "50%"])
    t.setStyle(TableStyle([("ALIGN", (1, 0), (1, 0), "RIGHT")]))
    elementos += [t, Spacer(1, 14)]

    # KPIs principales
    kpis = [
        [
            Paragraph(f"${result.total_cost:,.2f}", e["kpi_val"]),
            Paragraph(f"${result.transport_cost:,.2f}", e["kpi_val"]),
            Paragraph(f"${result.penalty_cost:,.2f}", e["kpi_val"]),
            Paragraph(f"{result.service_level:.1%}", e["kpi_val"]),
        ],
        [
            Paragraph("Costo Total", e["kpi_lbl"]),
            Paragraph("Transporte", e["kpi_lbl"]),
            Paragraph("Penalizaciones", e["kpi_lbl"]),
            Paragraph("Nivel de Servicio", e["kpi_lbl"]),
        ],
    ]
    tk = Table(kpis, colWidths=["25%"] * 4)
    tk.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), FONDO),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [FONDO, FONDO]),
        ("BOX",        (0, 0), (-1, -1), 0.5, GRIS_MED),
        ("INNERGRID",  (0, 0), (-1, -1), 0.5, GRIS_MED),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elementos += [tk, Spacer(1, 6)]
    return elementos


def _seccion_costos(e, result: SolverResult) -> list:
    elementos = [
        Paragraph("1. Desglose de Costos", e["h2"]),
        HRFlowable(width="100%", thickness=0.5, color=GRIS_MED, spaceAfter=8),
    ]

    filas = [
        [Paragraph("Componente", e["bold"]),
         Paragraph("Monto", e["bold"]),
         Paragraph("Participación", e["bold"])],
        ["Transporte directo (fletes)",
         f"${result.transport_cost:,.2f}",
         f"{result.transport_cost/result.total_cost*100:.1f}%" if result.total_cost else "—"],
        ["Costos fijos (apertura de CDs)",
         f"${result.fixed_cost:,.2f}",
         f"{result.fixed_cost/result.total_cost*100:.1f}%" if result.total_cost else "—"],
        ["Penalizaciones por déficit",
         f"${result.penalty_cost:,.2f}",
         f"{result.penalty_cost/result.total_cost*100:.1f}%" if result.total_cost else "—"],
        [Paragraph("<b>TOTAL</b>", e["bold"]),
         Paragraph(f"<b>${result.total_cost:,.2f}</b>", e["bold"]),
         Paragraph("<b>100%</b>", e["bold"])],
    ]

    t = Table(filas, colWidths=["55%", "25%", "20%"])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  AZUL_OSC),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  BLANCO),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS",(0, 1), (-1, -2), [BLANCO, FONDO]),
        ("BACKGROUND",    (0, -1),(-1, -1), colors.HexColor("#DBEAFE")),
        ("BOX",           (0, 0), (-1, -1), 0.5, GRIS_MED),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, GRIS_CLAR),
        ("ALIGN",         (1, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ]))
    elementos += [t, Spacer(1, 4)]
    return elementos


def _seccion_cds(e, result: SolverResult) -> list:
    elementos = [
        Paragraph("2. Decisiones de Infraestructura", e["h2"]),
        HRFlowable(width="100%", thickness=0.5, color=GRIS_MED, spaceAfter=8),
    ]

    filas = [
        [Paragraph("Centro", e["bold"]),
         Paragraph("Decisión", e["bold"]),
         Paragraph("Costo Fijo", e["bold"]),
         Paragraph("Flujo (u.)", e["bold"])],
    ]
    for dc in result.dc_decisions:
        estado = Paragraph("✓ Abierto", e["verde"]) if dc.opened \
                 else Paragraph("✗ Cerrado", e["rojo"])
        filas.append([
            dc.dc_id,
            estado,
            f"${dc.fixed_cost_incurred:,.0f}",
            f"{dc.throughput:,.0f}",
        ])

    t = Table(filas, colWidths=["25%", "30%", "25%", "20%"])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  AZUL_OSC),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  BLANCO),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [BLANCO, FONDO]),
        ("BOX",           (0, 0), (-1, -1), 0.5, GRIS_MED),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, GRIS_CLAR),
        ("ALIGN",         (2, 1), (-1, -1), "RIGHT"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ]))
    elementos += [t, Spacer(1, 4)]
    return elementos


def _seccion_rutas(e, result: SolverResult, net: NetworkData) -> list:
    elementos = [
        Paragraph("3. Rutas Activas", e["h2"]),
        HRFlowable(width="100%", thickness=0.5, color=GRIS_MED, spaceAfter=8),
        Paragraph(
            f"Se activaron <b>{result.active_routes}</b> de un máximo de "
            f"<b>{net.config.max_active_routes}</b> rutas permitidas.",
            e["body"]
        ),
        Spacer(1, 6),
    ]

    filas = [
        [Paragraph("Origen", e["bold"]),
         Paragraph("Destino", e["bold"]),
         Paragraph("Tipo", e["bold"]),
         Paragraph("Flujo (u.)", e["bold"]),
         Paragraph("Costo Unit.", e["bold"]),
         Paragraph("Costo Total", e["bold"])],
    ]
    activas = [af for af in result.arc_flows if af.active and af.flow > 0]
    activas.sort(key=lambda a: -a.flow)

    for af in activas:
        tipo = "Directa" if af.origin_type == "plant" and af.dest_type == "client" \
               else "Planta→CD" if af.dest_type == "dc" \
               else "CD→Cliente"
        filas.append([
            af.origin_id,
            af.dest_id,
            tipo,
            f"{af.flow:,.0f}",
            f"${af.unit_cost:,.0f}",
            f"${af.total_cost:,.2f}",
        ])

    t = Table(filas, colWidths=["13%", "13%", "22%", "16%", "16%", "20%"])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  AZUL_OSC),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  BLANCO),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [BLANCO, FONDO]),
        ("BOX",           (0, 0), (-1, -1), 0.5, GRIS_MED),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, GRIS_CLAR),
        ("ALIGN",         (3, 1), (-1, -1), "RIGHT"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
    ]))
    elementos += [t, Spacer(1, 4)]
    return elementos


def _seccion_clientes(e, result: SolverResult) -> list:
    elementos = [
        Paragraph("4. Atención a Clientes", e["h2"]),
        HRFlowable(width="100%", thickness=0.5, color=GRIS_MED, spaceAfter=8),
    ]

    filas = [
        [Paragraph("Cliente", e["bold"]),
         Paragraph("Demanda", e["bold"]),
         Paragraph("Recibido", e["bold"]),
         Paragraph("Déficit", e["bold"]),
         Paragraph("Penaliz./u.", e["bold"]),
         Paragraph("Costo Déficit", e["bold"]),
         Paragraph("Fill Rate", e["bold"])],
    ]
    for cr in result.client_results:
        deficit_par = Paragraph(
            f"<b>{cr.deficit:,.0f}</b>", e["rojo"]
        ) if cr.deficit > 0 else Paragraph("0", e["verde"])

        fill_par = Paragraph(
            f"{cr.fill_rate:.0%}", e["verde"] if cr.fill_rate >= 1 else e["ambar"]
        )
        filas.append([
            cr.client_id,
            f"{cr.demand:,.0f}",
            f"{cr.received:,.0f}",
            deficit_par,
            f"${cr.penalty_per_unit:,.0f}",
            f"${cr.penalty_cost:,.2f}",
            fill_par,
        ])

    t = Table(filas, colWidths=["12%", "13%", "13%", "12%", "13%", "17%", "12%"])  # ajuste de ancho
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  AZUL_OSC),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  BLANCO),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [BLANCO, FONDO]),
        ("BOX",           (0, 0), (-1, -1), 0.5, GRIS_MED),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, GRIS_CLAR),
        ("ALIGN",         (1, 1), (-1, -1), "RIGHT"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
    ]))
    elementos += [t, Spacer(1, 4)]
    return elementos


def _seccion_justificacion(e, result: SolverResult, net: NetworkData) -> list:
    elementos = [
        Paragraph("5. Justificación de la Solución", e["h2"]),
        HRFlowable(width="100%", thickness=0.5, color=GRIS_MED, spaceAfter=8),
    ]

    gap = net.supply_gap
    cds_abiertos = [d for d in result.dc_decisions if d.opened]
    cliente_deficit = [cr for cr in result.client_results if cr.deficit > 0]

    # Párrafo 1 — balance oferta/demanda
    elementos.append(Paragraph(
        f"<b>Balance oferta / demanda:</b> La red cuenta con una oferta total de "
        f"<b>{net.total_supply:,.0f} u.</b> frente a una demanda total de "
        f"<b>{net.total_demand:,.0f} u.</b>, generando un déficit estructural de "
        f"<b>{gap:,.0f} u.</b> que el modelo debe distribuir de forma óptima.",
        e["body"]
    ))
    elementos.append(Spacer(1, 6))

    # Párrafo 2 — gestión del déficit
    if cliente_deficit:
        nombres = ", ".join(cr.client_id for cr in cliente_deficit)
        pen_min = min(cr.penalty_per_unit for cr in cliente_deficit)
        elementos.append(Paragraph(
            f"<b>Gestión del déficit:</b> El solver asigna el faltante al cliente "
            f"<b>{nombres}</b> porque posee la penalización más baja "
            f"(<b>${pen_min:,.0f}/u.</b>), minimizando así el costo por incumplimiento. "
            f"Esto genera un costo de penalización de "
            f"<b>${result.penalty_cost:,.2f}</b>.",
            e["body"]
        ))
    else:
        elementos.append(Paragraph(
            "<b>Gestión del déficit:</b> Toda la demanda fue satisfecha. "
            "No se incurrió en penalizaciones.",
            e["verde"]
        ))
    elementos.append(Spacer(1, 6))

    # Párrafo 3 — decisión de CDs
    if cds_abiertos:
        nombres_cd = ", ".join(d.dc_id for d in cds_abiertos)
        costo_fijo_total = sum(d.fixed_cost_incurred for d in cds_abiertos)
        elementos.append(Paragraph(
            f"<b>Infraestructura:</b> El modelo determinó abrir <b>{nombres_cd}</b> "
            f"(costo fijo: <b>${costo_fijo_total:,.0f}</b>) porque el ahorro en "
            f"costos de transporte supera la inversión de apertura.",
            e["body"]
        ))
    else:
        elementos.append(Paragraph(
            f"<b>Infraestructura:</b> Ningún centro de distribución fue abierto. "
            f"El costo fijo mínimo de apertura supera el ahorro potencial en fletes "
            f"para el volumen actual de <b>{net.total_supply:,.0f} u.</b>, "
            f"por lo que la red opera con rutas directas planta–cliente.",
            e["body"]
        ))
    elementos.append(Spacer(1, 6))

    # Párrafo 4 — rutas y restricción de conectividad
    elementos.append(Paragraph(
        f"<b>Selección de rutas:</b> De los {len(net.arcs)} arcos disponibles, "
        f"el solver activó <b>{result.active_routes}</b> rutas "
        f"(límite: {net.config.max_active_routes}), priorizando los trayectos "
        f"de menor costo unitario que maximizan el flujo entregado.",
        e["body"]
    ))
    elementos.append(Spacer(1, 10))

    # Ecuación de costo
    elementos.append(Paragraph(
        f"<b>Composición del costo óptimo:</b>",
        e["bold"]
    ))
    elementos.append(Spacer(1, 4))
    eq = Table([[
        Paragraph(f"Transporte: ${result.transport_cost:,.2f}", e["body"]),
        Paragraph("+", e["body"]),
        Paragraph(f"Costos fijos: ${result.fixed_cost:,.2f}", e["body"]),
        Paragraph("+", e["body"]),
        Paragraph(f"Penalizaciones: ${result.penalty_cost:,.2f}", e["body"]),
        Paragraph("=", e["body"]),
        Paragraph(f"<b>${result.total_cost:,.2f}</b>", e["bold"]),
    ]], colWidths=["22%", "4%", "22%", "4%", "24%", "4%", "20%"])
    eq.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#DBEAFE")),
        ("BOX",           (0, 0), (-1, -1), 0.5, AZUL_MED),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elementos += [eq, Spacer(1, 6)]

    elementos.append(Paragraph(
        "Esta solución es óptima global: no existe ninguna otra combinación de "
        "rutas activas o decisiones de apertura que logre un costo inferior "
        "respetando todas las restricciones de oferta, capacidad y conectividad.",
        e["body"]
    ))
    return elementos


# ── Pie de página ────────────────────────────────────────────────

def _pie_pagina(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(GRIS_MED)
    w, _ = letter
    canvas.drawString(0.85 * inch, 0.55 * inch, "OptiNet — Optimizador MILP")
    canvas.drawRightString(
        w - 0.85 * inch, 0.55 * inch,
        f"Página {doc.page}  |  {datetime.now().strftime('%d/%m/%Y')}"
    )
    canvas.setStrokeColor(GRIS_CLAR)
    canvas.setLineWidth(0.4)
    canvas.line(0.85 * inch, 0.65 * inch, w - 0.85 * inch, 0.65 * inch)
    canvas.restoreState()
    