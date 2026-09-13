import streamlit as st
import pandas as pd
import os
from procesador_simce import generar_pdf_reporte_curso

st.set_page_config(page_title="Reporte Consolidado SIMCE - COLEGIO DEMO", page_icon="📊", layout="wide")

# --- CONTADOR DE CONSULTAS DIARIAS ---
if 'contador_consultas' not in st.session_state:
    st.session_state.contador_consultas = 0

# --- BARRA LATERAL: CONFIGURACIÓN E INSTITUCIONALIDAD ---
st.sidebar.title("🏫 Panel Institucional")
st.sidebar.info("COLEGIO DEMO \n\nMódulo Consolidado por Curso (UTP/Dirección)")

st.sidebar.markdown("---")
st.sidebar.subheader("📈 Control de Procesamiento")
st.sidebar.metric(label="Informes generados hoy", value=st.session_state.contador_consultas)

# --- CUERPO PRINCIPAL ---
st.title("📊 Generador de Reporte Ejecutivo Consolidado por Curso")
st.markdown("Herramienta orientada a la toma de decisiones de UTP y Dirección mediante el análisis panorámico del ensayo.")

st.markdown("---")
st.subheader("1. Carga de Archivos Requeridos")

col1, col2, col3 = st.columns(3)

with col1:
    archivo_attr = st.file_uploader("1. Tabla de Atributos (.txt o .csv)", type=["txt", "csv"])
with col2:
    archivo_complementaria = st.file_uploader("2. Tabla Complementaria (.txt o .csv)", type=["txt", "csv"])
with col3:
    archivo_respuestas = st.file_uploader("3. Respuestas Estudiantes (.txt o .csv)", type=["txt", "csv"])

formato_opcion = st.radio(
    "Selecciona el formato de respuestas de los estudiantes:",
    options=["1. Formato Vertical (ZipGrade)", "2. Formato Horizontal (Google Forms)"],
    index=0
)
formato_val = '1' if formato_opcion.startswith("1") else '2'

if st.button("🚀 Generar Informe Consolidado del Curso", type="primary"):
    if archivo_attr and archivo_complementaria and archivo_respuestas:
        try:
            with st.spinner("Procesando datos y generando el reporte ejecutivo PDF..."):
                df_attr = pd.read_csv(archivo_attr, sep=None, engine='python')
                df_comp = pd.read_csv(archivo_complementaria, sep=None, engine='python')
                df_resp_raw = pd.read_csv(archivo_respuestas, sep=None, engine='python')
                
                pdf_salida = "Reporte_Consolidado_Curso.pdf"
                generar_pdf_reporte_curso(df_attr, df_comp, df_resp_raw, formato_val, pdf_salida)
                
                st.session_state.contador_consultas += 1

            st.success("¡Informe consolidado generado con éxito!")
            
            with open(pdf_salida, "rb") as f:
                pdf_bytes = f.read()
                
            st.download_button(
                label="📥 Descargar Informe Consolidado en PDF",
                data=pdf_bytes,
                file_name="Reporte_Consolidado_Curso.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"Ocurrió un error durante el procesamiento: {e}")
    else:
        st.warning("Por favor, sube los tres archivos requeridos (Atributos, Complementaria y Respuestas) para continuar.")
