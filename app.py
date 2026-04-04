import streamlit as st
from pymongo import MongoClient
from datetime import datetime, date
import pandas as pd
import plotly.express as px
from bson.objectid import ObjectId

# --- CONFIGURACIÓN DB ---
MONGO_URI = "mongodb+srv://joseycarito75_db_user:5jfbQjoh5B84RE4R@cluster0.hzl7cg0.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

@st.cache_resource
def get_db():
    client = MongoClient(MONGO_URI)
    return client['moodclass_db']

db = get_db()
col_est = db['students']
col_moods = db['moods']

# --- ESTILO DARK ---
st.set_page_config(page_title="MoodClass", page_icon="🎒")
st.markdown("<style>.stApp {background-color: #0E1117; color: white;}</style>", unsafe_allow_html=True)

st.title("🎒 MoodClass")

tab1, tab2 = st.tabs(["👦 Estudiante", "🧑‍🏫 Docente"])

with tab1:
    with st.form("registro"):
        momento = st.selectbox("Momento", ["Entrada", "Salida"])
        emo = st.selectbox("¿Cómo te sientes?", ["😊 Feliz", "😐 Normal", "😢 Triste", "😡 Molesto", "😴 Cansado"])
        if st.form_submit_button("Guardar"):
            col_moods.insert_one({"day": str(date.today()), "moment": momento, "emotion": emo})
            st.success("¡Guardado!")

with tab2:
    pin = st.text_input("PIN", type="password")
    if pin == "1234":
        df = pd.DataFrame(list(col_moods.find({"day": str(date.today())})))
        if not df.empty:
            # CORRECCIÓN DEFINITIVA PARA EL ERROR DE PLOTLY
            conteo = df["emotion"].value_counts().reset_index()
            conteo.columns = ["Emocion", "Cantidad"] # Esto arregla el error de la imagen 9
            fig = px.bar(conteo, x="Emocion", y="Cantidad", template="plotly_dark")
            st.plotly_chart(fig)
        else:
            st.write("No hay datos hoy.")
