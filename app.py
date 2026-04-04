import streamlit as st
from pymongo import MongoClient
from datetime import datetime, date
import pandas as pd
import plotly.express as px
from bson.objectid import ObjectId

# --- CONFIGURACIÓN DE BASE DE DATOS ---
MONGO_URI = "mongodb+srv://joseycarito75_db_user:5jfbQjoh5B84RE4R@cluster0.hzl7cg0.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

@st.cache_resource
def get_database():
    # Conexión directa a MongoDB Atlas
    client = MongoClient(MONGO_URI)
    return client['moodclass_db']

db_mongo = get_database()
col_moods = db_mongo['moods']
col_estudiantes = db_mongo['students']

# --- DISEÑO OSCURO (DARK MODE) ---
st.set_page_config(page_title="MoodClass", page_icon="🎒", layout="centered")
st.markdown("""
<style>
    .stApp { background-color: #0E1117 !important; color: white !important; }
    .stMarkdown p, label, h1, h2, h3 { color: white !important; }
</style>
""", unsafe_allow_html=True)

st.title("🎒 MoodClass")

tab1, tab2 = st.tabs(["👦 Estudiante", "🧑‍🏫 Docente"])

with tab1:
    with st.form("registro_emocion"):
        momento = st.selectbox("Momento", ["Entrada", "Salida"])
        emocion = st.selectbox("¿Cómo te sientes?", ["😊 Feliz", "😐 Normal", "😢 Triste", "😡 Molesto", "😴 Cansado"])
        if st.form_submit_button("Guardar"):
            col_moods.insert_one({
                "day": str(date.today()), 
                "moment": momento, 
                "emotion": emocion,
                "timestamp": datetime.now()
            })
            st.success("¡Estado guardado correctamente!")

with tab2:
    pin = st.text_input("PIN Docente", type="password")
    if pin == "1234":
        # Cargar datos del día
        datos = list(col_moods.find({"day": str(date.today())}))
        if datos:
            df = pd.DataFrame(datos)
            
            # --- SOLUCIÓN AL ERROR DE PLOTLY ---
            # Forzamos los nombres de las columnas para evitar el error de 'index'
            conteo = df["emotion"].value_counts().reset_index()
            conteo.columns = ["Emoción", "Conteo"] 
            
            fig = px.bar(
                conteo, 
                x="Emoción", 
                y="Conteo", 
                color="Emoción",
                template="plotly_dark",
                title="Resumen Emocional de Hoy"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay registros hoy.")
