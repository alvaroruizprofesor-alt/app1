import streamlit as st
import pandas as pd
import os
from procesador_simce import generar_pdf_reporte_curso

st.set_page_config(page_title="Reporte Consolidado SIMCE - Liceo EPS", page_icon="📊", layout="wide")

# --- CONTADOR DE CONSULTAS DIARIAS ---
if 'contador_consultas' not in st.session_state:
    st.session_state.contador_consultas = 0

# --- BARRA LATERAL: CONFIGURACIÓN E INSTITUCIONALIDAD ---
st.sidebar.title("🏫 Panel Institucional")
st.sidebar.info("Liceo Eugenio Pereira Salas\n\nMódulo Consolidado por Curso (UTP/Dirección)")

st.sidebar.markdown("---")
st.sidebar.subheader("📈 Control de Procesamiento")
st.sidebar.metric(label="Informes generados hoy", value=st.session_state.contador_consultas)

# --- CUERPO PRINCIPAL ---
st.title("📊 Generador de Reporte Ejecutivo Consolidado por Curso")
st.markdown("Herramienta orientada a la toma de decisiones de UTP y Dirección mediante el análisis panorámico del ensayo.")

# Selector de Pruebas Precargadas
st.subheader("1. Selección de Instrumento Evaluativo")
prueba_seleccionada = st.selectbox(
    "Seleccione la prueba SIMCE correspondiente:",
    ["Historia y Ciencias Sociales - 8° Básico", "Lenguaje y Comunicación - 8° Básico", "Matemática - 8° Básico"]
)

st.markdown("---")
st.subheader("2. Carga de Archivos del Ensayo")

col1, col2 = st.columns(2)

with col1:
    archivo_respuestas = st.file_uploader("Sube el archivo de respuestas de los estudiantes (.txt o .csv)", type=["txt", "csv"])
with col2:
    archivo_complementaria = st.file_uploader("Sube la Tabla Complementaria de Preguntas (.txt o .csv)", type=["txt", "csv"])

formato_opcion = st.radio(
    "Selecciona el formato de respuestas de los estudiantes:",
    options=["1. Formato Vertical (ZipGrade)", "2. Formato Horizontal (Google Forms)"],
    index=0
)
formato_val = '1' if formato_opcion.startswith("1") else '2'

if st.button("🚀 Generar Informe Consolidado del Curso", type="primary"):
    if archivo_respuestas and archivo_complementaria:
        try:
            with st.spinner("Procesando datos y generando el reporte ejecutivo PDF..."):
                df_resp_raw = pd.read_csv(archivo_respuestas, sep=None, engine='python')
                df_comp = pd.read_csv(archivo_complementaria, sep=None, engine='python')
                
                # Archivo de atributos precargado por defecto
                if os.path.exists("Tabla_Atributos_Historia_8vo_1.txt"):
                    df_attr = pd.read_csv("Tabla_Atributos_Historia_8vo_1.txt", sep='\t')
                else:
                    df_attr = df_comp.copy()
                    if 'Estado' not in df_attr.columns:
                        df_attr['Estado'] = 'Clave'
                    if 'Opción' not in df_attr.columns:
                        df_attr['Opción'] = 'A'

                pdf_salida = "Reporte_Consolidado_Curso.pdf"
                generar_pdf_reporte_curso(df_attr, df_comp, df_resp_raw, formato_val, pdf_salida)
                
                # Incrementar contador diario
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
        st.warning("Por favor, sube tanto el archivo de respuestas como la tabla complementaria para continuar.")
