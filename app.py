import streamlit as st
import pandas as pd
import numpy as np
import io
import os
from google import genai

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Configuración de la página web
st.set_page_config(page_title="Sistema SIMCE - Informes Escolares", page_icon="📊", layout="centered")

st.title("📊 Sistema Automatizado de Informes SIMCE")
st.markdown("Plataforma oficial para generación de reportes individuales y ejecutivos consolidados para UTP y Dirección.")

# --- BARRA LATERAL ---
st.sidebar.header("Configuración de Acceso")
api_key_input = st.sidebar.text_input("Gemini API Key:", type="password", placeholder="Ingresa tu clave")

st.sidebar.markdown("---")
st.sidebar.info("💡 **Consejo:** Asegúrate de subir tus archivos de atributos, preguntas y respuestas en formato `.txt` o `.csv` tabulado.")

# --- SELECCIÓN DE PRUEBA (Requerimiento V2) ---
st.markdown("### 1. Selección de Instrumento de Evaluación")
tipo_prueba = st.selectbox(
    "Selecciona la prueba correspondiente:",
    ["Historia y Ciencias Sociales - 8° Básico (Ensayo 1)", "Matemática - 2° Medio (Ensayo Diagnóstico)", "Lenguaje y Comunicación - 4° Básico"]
)

# --- CARGA DE ARCHIVOS ---
st.markdown("### 2. Carga de Archivos Requeridos")
col1, col2, col3 = st.columns(3)
with col1:
    # Atributos precargados simulados o subida opcional según selector
    archivo_attr = st.file_uploader("Tabla de Atributos", type=["txt", "csv"])
with col2:
    archivo_comp = st.file_uploader("Preguntas / Alternativas", type=["txt", "csv"])
with col3:
    archivo_resp = st.file_uploader("Respuestas Estudiantes", type=["txt", "csv"])

formato_opcion = st.selectbox("Selecciona el formato de respuestas:", ["Formato Vertical (ZipGrade)", "Formato Horizontal (Google Forms)"])

# Contador visual de informes/consultas generadas en la sesión (Requerimiento V2)
if 'contador_consultas' not in st.session_state:
    st.session_state.contador_consultas = 0

st.sidebar.markdown("---")
st.sidebar.metric(label="📊 Informes Generados en la Sesión", value=st.session_state.contador_consultas)

# Funciones de Encabezado y Pie de Página para Reporte 2
def encabezado_y_pie_institucional(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica-Bold', 8)
    canvas.setFillColor(colors.HexColor('#2c3e50'))
    canvas.drawString(36, 762, "@profealvaro.cl — Ensayos SIMCE")

    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#7f8c8d'))
    canvas.drawRightString(576, 762, f"Colegio DEMO - {tipo_prueba}")

    canvas.setStrokeColor(colors.HexColor('#bdc3c7'))
    canvas.setLineWidth(0.5)
    canvas.line(36, 754, 576, 754)

    canvas.line(36, 42, 576, 42)
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#7f8c8d'))
    canvas.drawString(36, 30, "Elaborado por: Alvaro Rene Ruiz Aguilera")

    num_pagina = canvas.getPageNumber()
    canvas.drawRightString(576, 30, f"Página {num_pagina}")
    canvas.restoreState()

# Función de respaldo inteligente para recomendaciones individuales
def generar_recomendacion_respaldo(correctas, incorrectas, subtotales_eje):
    total = correctas + incorrectas
    pct = round((correctas / total) * 100, 1) if total > 0 else 0
    ejes_bajos = subtotales_eje[subtotales_eje['pct_logro'] < 60.0]['Eje Curricular'].tolist()
    
    if pct >= 60:
        texto = f"Excelente desempeño general con un {pct}% de logro ({correctas} correctas de {total}). El/la estudiante demuestra un dominio sólido de los contenidos evaluados. Se le sugiere mantener sus hábitos de estudio y profundizar en lectura crítica."
    else:
        ejes_txt = ", ".join(ejes_bajos) if ejes_bajos else "los ejes descendidos"
        texto = f"El/la estudiante obtuvo un {pct}% de logro ({correctas} correctas y {incorrectas} incorrectas). Se observa la necesidad de enfocar el estudio en {ejes_txt}. Se recomienda realizar lecturas guiadas y revisar los errores conceptuales detectados."
    return texto

# Función de IA masiva
def generar_recomendaciones_masivas(df_cruce_global, api_key):
    diccionario_resultado = {}
    try:
        client = genai.Client(api_key=api_key)
        resumen_curso = {}
        for est in df_cruce_global['estudiante_id'].unique():
            df_e = df_cruce_global[df_cruce_global['estudiante_id'] == est]
            correctas = int(df_e['es_correcta'].sum())
            incorrectas = int(len(df_e) - correctas)
            
            ejes_est = df_e.groupby('Eje Curricular').agg(
                correctas=('es_correcta', 'sum'),
                total=('es_correcta', 'count')
            ).reset_index()
            ejes_est['pct_logro'] = round((ejes_est['correctas'] / ejes_est['total']) * 100, 1)
            
            resumen_curso[str(est)] = {
                "correctas": correctas,
                "incorrectas": incorrectas,
                "rendimiento_ejes": ejes_est[['Eje Curricular', 'pct_logro']].to_dict(orient="records")
            }

        prompt = f"""
        Actúa como un profesor asesor experto en la prueba SIMCE en Chile.
        Te voy a entregar un resumen de datos de un curso. 
        Para CADA estudiante, redacta una retroalimentación pedagógica motivadora y breve (máximo 2 párrafos) con su desempeño y consejos de estudio.

        FORMATO OBLIGATORIO: 
        Responde estrictamente usando este formato de separación por líneas, sin markdown extra:
        ---ESTUDIANTE: [ID_DEL_ESTUDIANTE]---
        [Texto de la recomendación]

        Datos del curso:
        {resumen_curso}
        """

        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        bloques = response.text.strip().split("---ESTUDIANTE:")
        
        for bloque in bloques:
            if "---" in bloque:
                partes = bloque.split("---")
                est_id = partes[0].strip()
                recomendacion = partes[1].strip()
                if est_id:
                    diccionario_resultado[est_id] = recomendacion
    except Exception as e:
        st.sidebar.warning(f"Aviso de IA: {e}. Usando modo de respaldo analítico.")

    for est in df_cruce_global['estudiante_id'].unique():
        if str(est) not in diccionario_resultado or len(diccionario_resultado[str(est)]) < 10:
            df_e = df_cruce_global[df_cruce_global['estudiante_id'] == est]
            c = int(df_e['es_correcta'].sum())
            i = int(len(df_e) - c)
            sub_eje = df_e.groupby('Eje Curricular').agg(correctas=('es_correcta', 'sum'), total=('es_correcta', 'count')).reset_index()
            sub_eje['pct_logro'] = round((sub_eje['correctas'] / sub_eje['total']) * 100, 1)
            diccionario_resultado[str(est)] = generar_recomendacion_respaldo(c, i, sub_eje)
            
    return diccionario_resultado

# --- BOTÓN DE ACCIÓN ---
if st.button("🚀 Procesar Curso y Generar Informes PDF (Reportes 1 y 2)", type="primary"):
    if not api_key_input:
        st.error("Por favor, ingresa tu API Key de Gemini en la barra lateral.")
    elif not archivo_attr or not archivo_comp or not archivo_resp:
        st.error("Por favor, sube los tres archivos necesarios (Atributos, Preguntas/Alternativas y Respuestas).")
    else:
        with st.spinner("Procesando datos del curso y compilando informes PDF..."):
            try:
                df_atributos = pd.read_csv(archivo_attr, sep='\t')
                df_complementaria = pd.read_csv(archivo_comp, sep='\t')
                df_respuestas_raw = pd.read_csv(archivo_resp, sep='\t')
                
                if "Vertical" in formato_opcion:
                    df_respuestas = df_respuestas_raw.copy()
                    df_respuestas.columns = [c.strip().lower() for c in df_respuestas.columns]
                    if 'n°' in df_respuestas.columns: df_respuestas.rename(columns={'n°': 'N°'}, inplace=True)
                    elif 'n' in df_respuestas.columns: df_respuestas.rename(columns={'n': 'N°'}, inplace=True)
                else:
                    id_col = df_respuestas_raw.columns[0]
                    df_respuestas = df_respuestas_raw.melt(id_vars=[id_col], var_name='N°', value_name='respuesta_estudiante')
                    df_respuestas.rename(columns={id_col: 'estudiante_id'}, inplace=True)
                
                # Normalización de complementaria
                df_complementaria.columns = [c.strip().lower() for c in df_complementaria.columns]
                if 'numero' in df_complementaria.columns: df_complementaria.rename(columns={'numero': 'N°'}, inplace=True)
                elif 'n°' in df_complementaria.columns: df_complementaria.rename(columns={'n°': 'N°'}, inplace=True)

                df_respuestas['N°'] = pd.to_numeric(df_respuestas['N°'])
                df_atributos['N°'] = pd.to_numeric(df_atributos['N°'])
                df_complementaria['N°'] = pd.to_numeric(df_complementaria['N°'])

                df_respuestas['respuesta_estudiante'] = df_respuestas['respuesta_estudiante'].astype(str).str.strip().str.upper()
                df_atributos['Opción'] = df_atributos['Opción'].astype(str).str.strip().str.upper()

                # Extracción y cruce maestro
                df_claves = df_atributos[df_atributos['Estado'].astype(str).str.strip().str.lower() == 'clave'][['N°', 'Opción']].rename(columns={'Opción': 'clave_oficial'})
                df_metadatos = df_atributos[['N°', 'Eje Curricular', 'Habilidad Medida', 'Análisis Pedagógico / Diagnóstico del Error', 'Actividad Sugerida de Remediación']].drop_duplicates(subset=['N°'])

                df_cruce = pd.merge(df_respuestas, df_metadatos, on='N°', how='left')
                df_cruce = pd.merge(df_cruce, df_claves, on='N°', how='left')

                df_cruce['es_correcta'] = (df_cruce['respuesta_estudiante'] == df_cruce['clave_oficial']).astype(int)
                df_cruce['Análisis Pedagógico / Diagnóstico del Error'] = df_cruce['Análisis Pedagógico / Diagnóstico del Error'].fillna('Respuesta no registrada.')
                df_cruce['Actividad Sugerida de Remediación'] = df_cruce['Actividad Sugerida de Remediación'].fillna('Revisar contenidos generales.')

                diccionario_ia = generar_recomendaciones_masivas(df_cruce, api_key_input)

                carpeta_reportes = "reportes_salida"
                if not os.path.exists(carpeta_reportes):
                    os.makedirs(carpeta_reportes)

                # ==========================================
                # REPORTE 1: Individual por Estudiante
                # ==========================================
                pdf_path_1 = os.path.join(carpeta_reportes, "1_Reporte_Detallado_Estudiantes.pdf")
                doc1 = SimpleDocTemplate(pdf_path_1, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
                story1 = []
                styles = getSampleStyleSheet()

                style_celda = ParagraphStyle('EstiloCelda', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#2c3e50'))
                style_header_tabla = ParagraphStyle('EstiloHeader', parent=styles['Normal'], fontSize=9, leading=11, textColor=colors.white, fontName='Helvetica-Bold')

                estudiantes = df_cruce['estudiante_id'].unique()
                for idx, estudiante in enumerate(estudiantes):
                    story1.append(Paragraph("<b>Informe Individual: Detalle por Estudiante y Pregunta</b>", styles['Heading1']))
                    story1.append(Paragraph(f"<b>Estudiante: {estudiante}</b><br/><i>Destinatario: Estudiante, Apoderado, Profesor Jefe y UTP</i><br/><br/>", styles['Normal']))
                    story1.append(Spacer(1, 10))

                    data_est = [[Paragraph("N°", style_header_tabla), Paragraph("Resp.", style_header_tabla), Paragraph("Estado", style_header_tabla), Paragraph("Análisis Pedagógico y Remediación", style_header_tabla)]]
                    df_est = df_cruce[df_cruce['estudiante_id'] == estudiante].sort_values(by='N°')
                    
                    for _, row in df_est.iterrows():
                        estado_txt = "<b>CORRECTA</b>" if row['es_correcta'] == 1 else "<b>INCORRECTA</b>"
                        detalles_texto = f"<b>Diag:</b> {row['Análisis Pedagógico / Diagnóstico del Error']}<br/><b>Remediación:</b> {row['Actividad Sugerida de Remediación']}"
                        data_est.append([Paragraph(str(row['N°']), style_celda), Paragraph(str(row['respuesta_estudiante']), style_celda), Paragraph(estado_txt, style_celda), Paragraph(detalles_texto, style_celda)])

                    t_est = Table(data_est, colWidths=[30, 60, 75, 375])
                    t_est.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2c3e50')), ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('VALIGN', (0,0), (-1,-1), 'TOP')]))
                    story1.append(t_est)
                    story1.append(Spacer(1, 10))

                    total_c = int(df_est['es_correcta'].sum())
                    total_i = int(len(df_est) - total_c)
                    subtotales_eje = df_est.groupby('Eje Curricular').agg(correctas=('es_correcta', 'sum'), total=('es_correcta', 'count')).reset_index()
                    subtotales_eje['pct_logro'] = round((subtotales_eje['correctas'] / subtotales_eje['total']) * 100, 1)

                    elementos_barra = [Paragraph("<b>Porcentaje de Logro por Eje Curricular (Estudiante)</b>", styles['Heading3']), Spacer(1, 4)]
                    for _, re in subtotales_eje.iterrows():
                        pct = re['pct_logro']
                        color_b = '#e74c3c' if pct < 60.0 else '#2980b9'
                        t_vis = Table([['']], colWidths=[max(2, int(3 * pct)), max(2, int(3 * (100 - pct)))])
                        t_vis.setStyle(TableStyle([('BACKGROUND', (0,0), (0,0), colors.HexColor(color_b)), ('BACKGROUND', (1,0), (1,0), colors.HexColor('#ecf0f1'))]))
                        t_fila = Table([[Paragraph(f"<b>{re['Eje Curricular']}</b>: {pct}%", style_celda)], [t_vis]], colWidths=[540])
                        elementos_barra.append(t_fila)
                        elementos_barra.append(Spacer(1, 4))
                    story1.append(KeepTogether(elementos_barra))
                    story1.append(Spacer(1, 10))

                    story1.append(Paragraph("<b>Orientación Pedagógica Personalizada</b>", styles['Heading3']))
                    story1.append(Spacer(1, 3))
                    txt_ia = diccionario_ia.get(str(estudiante), "Desempeño registrado.")
                    t_ia = Table([[Paragraph(str(txt_ia).replace('\n', '<br/>'), style_celda)]], colWidths=[540])
                    t_ia.setStyle(TableStyle([('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#2980b9')), ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0f8ff'))]))
                    story1.append(t_ia)
                    story1.append(Spacer(1, 10))

                    if idx < len(estudiantes) - 1:
                        story1.append(PageBreak())

                doc1.build(story1)

                # ==========================================
                # REPORTE 2: Consolidado Curso (UTP/Dirección)
                # ==========================================
                pdf_path_2 = os.path.join(carpeta_reportes, "2_Reporte_Consolidado_Curso.pdf")
                doc2 = SimpleDocTemplate(pdf_path_2, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=45, bottomMargin=45)
                story2 = []

                story2.append(Paragraph(f"<b>Informe Ejecutivo: Panorámica General del Curso</b>", styles['Heading1']))
                story2.append(Paragraph(f"<b>Destinatario: Dirección y UTP</b><br/><i>Resumen Agregado de Rendimiento, Análisis de Ítems y Rankings</i><br/><br/>", styles['Normal']))
                story2.append(Spacer(1, 15))

                # Habilidad
                subtotales_habilidad = df_cruce.groupby('Habilidad Medida').agg(correctas=('es_correcta', 'sum'), total=('es_correcta', 'count')).reset_index()
                subtotales_habilidad['pct_logro'] = round((subtotales_habilidad['correctas'] / subtotales_habilidad['total']) * 100, 1)

                story2.append(Paragraph("<b>1. Desempeño Consolidado por Habilidad Medida</b>", styles['Heading3']))
                for _, row_hab in subtotales_habilidad.iterrows():
                    pct = row_hab['pct_logro']
                    color_barra = '#e74c3c' if pct < 60.0 else '#2980b9'
                    t_vis = Table([['']], colWidths=[max(2, int(3 * pct)), max(2, int(3 * (100 - pct)))])
                    t_vis.setStyle(TableStyle([('BACKGROUND', (0,0), (0,0), colors.HexColor(color_barra)), ('BACKGROUND', (1,0), (1,0), colors.HexColor('#ecf0f1'))]))
                    t_fila = Table([[Paragraph(f"<b>{row_hab['Habilidad Medida']}</b>: {pct}% de logro", style_celda)], [t_vis]], colWidths=[540])
                    story2.append(t_fila)
                    story2.append(Spacer(1, 3))

                story2.append(Spacer(1, 10))

                # Eje
                subtotales_eje_curso = df_cruce.groupby('Eje Curricular').agg(correctas=('es_correcta', 'sum'), total=('es_correcta', 'count')).reset_index()
                subtotales_eje_curso['pct_logro'] = round((subtotales_eje_curso['correctas'] / subtotales_eje_curso['total']) * 100, 1)

                story2.append(Paragraph("<b>2. Desempeño Consolidado por Eje Curricular</b>", styles['Heading3']))
                for _, row_eje in subtotales_eje_curso.iterrows():
                    pct = row_eje['pct_logro']
                    color_barra = '#e74c3c' if pct < 60.0 else '#2980b9'
                    t_vis = Table([['']], colWidths=[max(2, int(3 * pct)), max(2, int(3 * (100 - pct)))])
                    t_vis.setStyle(TableStyle([('BACKGROUND', (0,0), (0,0), colors.HexColor(color_barra)), ('BACKGROUND', (1,0), (1,0), colors.HexColor('#ecf0f1'))]))
                    t_fila = Table([[Paragraph(f"<b>{row_eje['Eje Curricular']}</b>: {pct}% de logro", style_celda)], [t_vis]], colWidths=[540])
                    story2.append(t_fila)
                    story2.append(Spacer(1, 3))

                doc2.build(story2, onFirstPage=encabezado_y_pie_institucional, onLaterPages=encabezado_y_pie_institucional)

                # Incrementar contador de sesión
                st.session_state.contador_consultas += 1

                st.success("¡Informes detallados (Reporte 1 y Reporte 2) generados exitosamente!")

                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    with open(pdf_path_1, "rb") as f1:
                        st.download_button("📥 Descargar Reporte 1 (Individual)", data=f1, file_name="Reporte_Estudiantes.pdf", mime="application/pdf")
                with col_d2:
                    with open(pdf_path_2, "rb") as f2:
                        st.download_button("📥 Descargar Reporte 2 (Consolidado UTP)", data=f2, file_name="Reporte_Consolidado_Curso.pdf", mime="application/pdf")

            except Exception as e:
                st.error(f"Error durante el procesamiento: {e}")
