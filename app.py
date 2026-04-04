import streamlit as st
from pymongo import MongoClient
from datetime import datetime, date
import pandas as pd
import plotly.express as px
from bson.objectid import ObjectId

# --- CONFIGURACIÓN BASE DE DATOS ---
MONGO_URI = "mongodb+srv://joseycarito75_db_user:5jfbQjoh5B84RE4R@cluster0.hzl7cg0.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

@st.cache_resource
def get_database():
    client = MongoClient(MONGO_URI)
    return client['moodclass_db']

db_mongo = get_database()
col_estudiantes = db_mongo['students']
col_moods = db_mongo['moods']

TEACHER_PIN = "1234"

EMOTIONS = [
    ("😊", "Tranquilo"), ("😃", "Feliz"), ("😐", "Normal"), ("😟", "Preocupado"),
    ("😡", "Molesto"), ("😢", "Triste"), ("😴", "Cansado"), ("😰", "Ansioso"),
]

# --- ESTILO VISUAL ---
st.set_page_config(page_title="MoodClass", page_icon="🎒", layout="centered")
st.markdown("""<style>.stApp { background-color: #0E1117 !important; color: white !important; }</style>""", unsafe_allow_html=True)

# --- FUNCIONES ---
def get_students():
    lista = list(col_estudiantes.find().sort("name", 1))
    if not lista: return pd.DataFrame(columns=["id", "name"])
    df = pd.DataFrame(lista)
    df['id'] = df['_id'].astype(str)
    return df[["id", "name"]]

# --- INTERFAZ ---
st.title("🎒 MoodClass")
t1, t2, t3 = st.tabs(["👦 Estudiante", "🧑‍🏫 Docente", "⚙️ Configuración"])

with t1:
    with st.form("registro_mood"):
        momento = st.selectbox("Momento", ["Entrada", "Salida"])
        fecha = st.date_input("Fecha", value=date.today())
        modo = st.radio("Identificación", ["Anónimo", "Con mi nombre"], horizontal=True)
        id_sel = None
        if modo == "Con mi nombre":
            alumnos = get_students()
            if not alumnos.empty:
                nombre = st.selectbox("Tu nombre", alumnos["name"].tolist())
                id_sel = alumnos[alumnos["name"] == nombre]["id"].values[0]
        
        st.write("¿Cómo estás?")
        emo_sel = st.selectbox("Elige tu emoción", [f"{e[0]} {e[1]}" for e in EMOTIONS])
        
        if st.form_submit_button("Guardar Estado"):
            col_moods.insert_one({
                "day": str(fecha), "moment": momento, "emotion": emo_sel,
                "student_id": id_sel, "created_at": datetime.now()
            })
            st.success("¡Guardado!")

with t2:
    pin = st.text_input("PIN Docente", type="password")
    if pin == TEACHER_PIN:
        f_ver = st.date_input("Ver día", value=date.today())
        datos = list(col_moods.find({"day": str(f_ver)}))
        if datos:
            df = pd.DataFrame(datos)
            # SOLUCIÓN AL ERROR DE PLOTLY:
            conteo = df["emotion"].value_counts().reset_index()
            conteo.columns = ["Emoción", "Cantidad"] # Forzamos nombres claros
            
            fig = px.bar(conteo, x="Emoción", y="Cantidad", color="Emoción", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos hoy.")

with t3:
    pin_c = st.text_input("PIN Configuración", type="password", key="conf")
    if pin_c == TEACHER_PIN:
        with st.form("add_alumno"):
            nuevo = st.text_input("Nombre del alumno")
            if st.form_submit_button("Añadir"):
                if nuevo:
                    col_estudiantes.insert_one({"name": nuevo.strip()})
                    st.rerun()
        
        lista = get_students()
        for _, r in lista.iterrows():
            c_a, c_b = st.columns([0.8, 0.2])
            c_a.write(r["name"])
            if c_b.button("Borrar", key=r["id"]):
                col_estudiantes.delete_one({"_id": ObjectId(r["id"])})
                st.rerun()
