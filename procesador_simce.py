import os
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def encabezado_y_pie_institucional(canvas, doc):
    canvas.saveState()
    # --- ENCABEZADO ---
    canvas.setFont('Helvetica-Bold', 8)
    canvas.setFillColor(colors.HexColor('#2c3e50'))
    canvas.drawString(36, 762, "@profealvaro.cl — Ensayos SIMCE")

    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#7f8c8d'))
    canvas.drawRightString(576, 762, "Colegio DEMO - 8° Básico")

    canvas.setStrokeColor(colors.HexColor('#bdc3c7'))
    canvas.setLineWidth(0.5)
    canvas.line(36, 754, 576, 754)

    # --- PIE DE PÁGINA ---
    canvas.line(36, 42, 576, 42)
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#7f8c8d'))
    canvas.drawString(36, 30, "Elaborado por: Alvaro Rene Ruiz Aguilera")

    num_pagina = canvas.getPageNumber()
    canvas.drawRightString(576, 30, f"Página {num_pagina}")
    canvas.restoreState()

def generar_pdf_reporte_curso(df_atributos, df_complementaria, df_respuestas_raw, opcion_formato, ruta_salida):
    # Normalización de respuestas
    if opcion_formato == '1':
        df_respuestas = df_respuestas_raw.copy()
        df_respuestas.columns = [c.strip().lower() for c in df_respuestas.columns]
        if 'n°' in df_respuestas.columns:
            df_respuestas.rename(columns={'n°': 'N°'}, inplace=True)
        elif 'n' in df_respuestas.columns:
            df_respuestas.rename(columns={'n': 'N°'}, inplace=True)
    elif opcion_formato == '2':
        id_col = df_respuestas_raw.columns[0]
        df_respuestas = df_respuestas_raw.melt(
            id_vars=[id_col],
            var_name='N°',
            value_name='respuesta_estudiante'
        )
        df_respuestas.rename(columns={id_col: 'estudiante_id'}, inplace=True)
    else:
        raise ValueError("Formato inválido.")

    df_complementaria.columns = [c.strip().lower() for c in df_complementaria.columns]
    if 'numero' in df_complementaria.columns:
        df_complementaria.rename(columns={'numero': 'N°'}, inplace=True)
    elif 'n°' in df_complementaria.columns:
        df_complementaria.rename(columns={'n°': 'N°'}, inplace=True)

    df_respuestas['N°'] = pd.to_numeric(df_respuestas['N°'])
    df_atributos['N°'] = pd.to_numeric(df_atributos['N°'])
    df_complementaria['N°'] = pd.to_numeric(df_complementaria['N°'])

    df_respuestas['respuesta_estudiante'] = df_respuestas['respuesta_estudiante'].astype(str).str.strip().str.upper()
    df_atributos['Opción'] = df_atributos['Opción'].astype(str).str.strip().str.upper()

    df_claves = df_atributos[df_atributos['Estado'].astype(str).str.strip().str.lower() == 'clave'][['N°', 'Opción']].rename(columns={'Opción': 'clave_oficial'})
    df_metadatos = df_atributos[['N°', 'Eje Curricular', 'Habilidad Medida']].drop_duplicates(subset=['N°'])

    df_cruce = pd.merge(df_respuestas, df_metadatos, on='N°', how='left')
    df_cruce = pd.merge(df_cruce, df_claves, on='N°', how='left')
    df_cruce['es_correcta'] = (df_cruce['respuesta_estudiante'] == df_cruce['clave_oficial']).astype(int)

    styles = getSampleStyleSheet()
    style_celda = ParagraphStyle('EstiloCeldaTablaInf2', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#2c3e50'))
    style_header_tabla = ParagraphStyle('EstiloHeaderTablaInf2', parent=styles['Normal'], fontSize=9, leading=11, textColor=colors.white, fontName='Helvetica-Bold')

    texto_descripcion_inf2 = (
        "<b>Descripción del Informe Ejecutivo:</b> Este documento consolida la visión panorámica del curso para la "
        "Dirección y la Unidad Técnico-Pedagógica (UTP). Presenta el desempeño agregado mediante barras de progreso "
        "por Habilidad y Eje Curricular, el análisis crítico de ítems con texto de alternativas y los rankings "
        "de los estudiantes con mayor logro y atención prioritaria."
    )

    doc2 = SimpleDocTemplate(ruta_salida, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=45, bottomMargin=45)
    story2 = []

    story2.append(Paragraph("<b>Informe Ejecutivo: Panorámica General del Curso</b>", styles['Heading1']))
    story2.append(Paragraph("<b>Destinatario: Dirección y UTP</b><br/><i>Resumen Agregado de Rendimiento, Análisis de Ítems y Rankings</i><br/><br/>", styles['Normal']))
    story2.append(Paragraph(texto_descripcion_inf2, styles['Normal']))
    story2.append(Spacer(1, 15))

    # Agregación Habilidad
    subtotales_habilidad = df_cruce.groupby('Habilidad Medida').agg(correctas=('es_correcta', 'sum'), total=('es_correcta', 'count')).reset_index()
    subtotales_habilidad['pct_logro'] = round((subtotales_habilidad['correctas'] / subtotales_habilidad['total']) * 100, 1)

    story2.append(Paragraph("<b>1. Desempeño Consolidado por Habilidad Medida</b>", styles['Heading3']))
    story2.append(Spacer(1, 4))
    elementos_barra_hab = []
    for _, row_hab in subtotales_habilidad.iterrows():
        pct = row_hab['pct_logro']
        color_barra = '#e74c3c' if pct < 60.0 else '#2980b9'
        t_progreso = Table([['']], colWidths=[max(2, int(3 * pct)), max(2, int(3 * (100 - pct)))])
        t_progreso.setStyle(TableStyle([('BACKGROUND', (0,0), (0,0), colors.HexColor(color_barra)), ('BACKGROUND', (1,0), (1,0), colors.HexColor('#ecf0f1')), ('TOPPADDING', (0,0), (-1,-1), 3), ('BOTTOMPADDING', (0,0), (-1,-1), 3)]))
        t_fila = Table([[Paragraph(f"<b>{row_hab['Habilidad Medida']}</b>: {pct}% de logro (Correctas: {int(row_hab['correctas'])}/{int(row_hab['total'])})", style_celda)], [t_progreso]], colWidths=[540])
        t_fila.setStyle(TableStyle([('BOTTOMPADDING', (0,0), (-1,-1), 2), ('TOPPADDING', (0,0), (-1,-1), 2)]))
        elementos_barra_hab.extend([t_fila, Spacer(1, 3)])
    story2.append(KeepTogether(elementos_barra_hab))
    story2.append(Spacer(1, 12))

    # Agregación Eje
    subtotales_eje_curso = df_cruce.groupby('Eje Curricular').agg(correctas=('es_correcta', 'sum'), total=('es_correcta', 'count')).reset_index()
    subtotales_eje_curso['pct_logro'] = round((subtotales_eje_curso['correctas'] / subtotales_eje_curso['total']) * 100, 1)

    story2.append(Paragraph("<b>2. Desempeño Consolidado por Eje Curricular</b>", styles['Heading3']))
    story2.append(Spacer(1, 4))
    elementos_barra_eje = []
    for _, row_eje in subtotales_eje_curso.iterrows():
        pct = row_eje['pct_logro']
        color_barra = '#e74c3c' if pct < 60.0 else '#2980b9'
        t_progreso = Table([['']], colWidths=[max(2, int(3 * pct)), max(2, int(3 * (100 - pct)))])
        t_progreso.setStyle(TableStyle([('BACKGROUND', (0,0), (0,0), colors.HexColor(color_barra)), ('BACKGROUND', (1,0), (1,0), colors.HexColor('#ecf0f1')), ('TOPPADDING', (0,0), (-1,-1), 3), ('BOTTOMPADDING', (0,0), (-1,-1), 3)]))
        t_fila = Table([[Paragraph(f"<b>{row_eje['Eje Curricular']}</b>: {pct}% de logro (Correctas: {int(row_eje['correctas'])}/{int(row_eje['total'])})", style_celda)], [t_progreso]], colWidths=[540])
        t_fila.setStyle(TableStyle([('BOTTOMPADDING', (0,0), (-1,-1), 2), ('TOPPADDING', (0,0), (-1,-1), 2)]))
        elementos_barra_eje.extend([t_fila, Spacer(1, 3)])
    story2.append(KeepTogether(elementos_barra_eje))
    story2.append(PageBreak())

    doc2.build(story2, onFirstPage=encabezado_y_pie_institucional, onLaterPages=encabezado_y_pie_institucional)
    return ruta_salida