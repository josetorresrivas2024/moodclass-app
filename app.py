import streamlit as st
from pymongo import MongoClient
from datetime import datetime, date
import pandas as pd
import plotly.express as px

# --- CONEXIÓN SEGURA USANDO SECRETS ---
# Aquí Streamlit busca automáticamente la clave que guardaste en el paso anterior
MONGO_URI = st.secrets["MONGO_URI"]

@st.cache_resource
def get_database():
    client = MongoClient(MONGO_URI)
    return client['moodclass_db']

db = get_database()
col_moods = db['moods']

# --- CONFIGURACIÓN DE BASE DE DATOS ---
MONGO_URI = "mongodb+srv://joseycarito75_db_user:5jfbQjoh5B84RE4R@cluster0.hzl7cg0.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

@st.cache_resource
def get_database():
    client = MongoClient(MONGO_URI)
    return client['moodclass_db']

db_mongo = get_database()
col_moods = db_mongo['moods']

# --- DISEÑO ---
st.set_page_config(page_title="MoodClass", page_icon="🎒", layout="centered")
st.markdown("<style>.stApp { background-color: #0E1117 !important; color: white !important; }</style>", unsafe_allow_html=True)

st.title("🎒 MoodClass")

tab1, tab2 = st.tabs(["👦 Estudiante", "🧑‍🏫 Docente"])

with tab1:
    with st.form("registro_emocion"):
        momento = st.selectbox("Momento", ["Entrada", "Salida"])
        emocion = st.selectbox("¿Cómo te sientes?", ["😊 Feliz", "😐 Normal", "😢 Triste", "😡 Molesto", "😴 Cansado"])
        if st.form_submit_button("Guardar Estado"):
            col_moods.insert_one({
                "day": str(date.today()), 
                "moment": momento, 
                "emotion": emocion,
                "timestamp": datetime.now()
            })
            st.success("¡Estado guardado!")

with tab2:
    pin = st.text_input("PIN Docente", type="password")
    if pin == "1234":
        cursor = col_moods.find({"day": str(date.today())})
        datos = list(cursor)
        if datos:
            df = pd.DataFrame(datos)
            
            # --- LA SOLUCIÓN DEFINITIVA ---
            # En lugar de reset_index() genérico, creamos el conteo manual
            conteo = df['emotion'].value_counts().reset_index()
            # Forzamos los nombres de las columnas a 'emocion' y 'count'
            conteo.columns = ['emocion', 'count']
            
            fig = px.bar(
                conteo, 
                x="emocion", 
                y="count", 
                color="emocion",
                labels={'emocion': 'Estado de Ánimo', 'count': 'Cantidad'},
                template="plotly_dark"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay registros hoy.")
            # Actualizado el 4 de Abril - version 2
