import streamlit as st
from pymongo import MongoClient
from datetime import datetime, date
import pandas as pd
import plotly.express as px
from bson.objectid import ObjectId

# ==========================================
# 1. CONFIGURACIÓN DE BASE DE DATOS (MONGODB)
# ==========================================
MONGO_URI = "mongodb+srv://joseycarito75_db_user:5jfbQjoh5B84RE4R@cluster0.hzl7cg0.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

@st.cache_resource
def get_database():
    client = MongoClient(MONGO_URI)
    return client['moodclass_db']

db_mongo = get_database()
coleccion_estudiantes = db_mongo['students']
coleccion_moods = db_mongo['moods']

TEACHER_PIN = "1234"

EMOTIONS = [
    ("😊", "Tranquilo"), ("😃", "Feliz"), ("😐", "Normal"), ("😟", "Preocupado"),
    ("😡", "Molesto"), ("😢", "Triste"), ("😴", "Cansado"), ("😰", "Ansioso"),
]

# ==========================================
# 2. DISEÑO Y ESTILO (DARK MODE FORZADO)
# ==========================================
st.set_page_config(page_title="MoodClass", page_icon="🎒", layout="centered")

st.markdown("""
<style>
    .stApp { background-color: #0E1117 !important; color: #FFFFFF !important; }
    .mcard {
        background: #1A1C24 !important;
        border-radius: 15px;
        padding: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        margin-bottom: 20px;
        border: 1px solid #30363D;
    }
    .stButton>button {
        border-radius: 12px !important;
        background-color: #21262D !important;
        color: white !important;
        border: 1px solid #30363D !important;
        height: 70px;
    }
    h1, h2, h3, label, p { color: #FFFFFF !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. FUNCIONES DE DATOS
# ==========================================

def get_students():
    lista = list(coleccion_estudiantes.find().sort("name", 1))
    if not lista: return pd.DataFrame(columns=["id", "name"])
    df = pd.DataFrame(lista)
    df['id'] = df['_id'].astype(str)
    return df[["id", "name"]]

def save_mood(day, moment, is_anonymous, student_id, emotion):
    coleccion_moods.insert_one({
        "day": str(day),
        "moment": moment,
        "is_anonymous": is_anonymous,
        "student_id": student_id if not is_anonymous else None,
        "emotion": emotion,
        "created_at": datetime.now()
    })

def load_moods(day):
    lista = list(coleccion_moods.find({"day": str(day)}))
    if not lista: return pd.DataFrame()
    df = pd.DataFrame(lista)
    
    # Unir con nombres
    est_df = get_students()
    def get_name(sid):
        if not sid: return "Anónimo"
        match = est_df[est_df['id'] == str(sid)]
        return match['name'].values[0] if not match.empty else "—"
    
    df['Alumno'] = df['student_id'].apply(get_name) if 'student_id' in df.columns else "Anónimo"
    return df

# ==========================================
# 4. INTERFAZ
# ==========================================
st.title("🎒 MoodClass")

t1, t2, t3 = st.tabs(["👦 Estudiante", "🧑‍🏫 Docente", "⚙️ Configuración"])

with t1:
    st.markdown("<div class='mcard'>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    momento = c1.selectbox("Momento", ["Entrada", "Salida"])
    fecha = c2.date_input("Fecha", value=date.today())
    modo = st.radio("Identificación", ["Con mi nombre", "Anónimo"], horizontal=True)
    
    id_est = None
    if modo == "Con mi nombre":
        alumnos = get_students()
        if not alumnos.empty:
            sel = st.selectbox("Tu nombre", alumnos["name"].tolist())
            id_est = alumnos[alumnos["name"] == sel]["id"].values[0]
    st.markdown("</div>", unsafe_allow_html=True)

    st.subheader("¿Cómo te sientes?")
    cols = st.columns(4)
    for i, (emoji, texto) in enumerate(EMOTIONS):
        if cols[i % 4].button(f"{emoji}\n{texto}", use_container_width=True, key=f"e_{i}"):
            save_mood(fecha, momento, (modo=="Anónimo"), id_est, f"{emoji} {texto}")
            st.success("¡Guardado!")

with t2:
    pin = st.text_input("PIN Docente", type="password")
    if pin == TEACHER_PIN:
        f_ver = st.date_input("Ver día", value=date.today(), key="ver_dia")
        datos = load_moods(f_ver)
        
        if not datos.empty:
            # --- SOLUCIÓN AL ERROR DE PLOTLY ---
            # 1. Contamos las emociones
            conteo = datos["emotion"].value_counts().reset_index()
            # 2. Renombramos las columnas manualmente para que Plotly no se pierda
            conteo.columns = ["Sentimiento", "Cantidad"]
            
            # 3. Creamos el gráfico usando los nuevos nombres
            fig = px.bar(
                resumen, 
                x="Sentimiento",  # <--- Ahora usamos el nombre nuevo
                y="Cantidad",     # <--- Y este también
                color="Sentimiento",
                template="plotly_dark"
            )
            st.plotly_chart(fig, use_container_width=True)
            st.table(datos[["moment", "Alumno", "emotion"]])
        else:
            st.info("Sin registros hoy.")

with t3:
    pin_c = st.text_input("PIN Config", type="password", key="pc")
    if pin_c == TEACHER_PIN:
        with st.form("nuevo"):
            nombre = st.text_input("Nombre del alumno")
            if st.form_submit_button("Añadir"):
                if nombre:
                    coleccion_estudiantes.insert_one({"name": nombre.strip()})
                    st.rerun()
        
        lista = get_students()
        for _, fila in lista.iterrows():
            col_n, col_b = st.columns([0.8, 0.2])
            col_n.write(fila["name"])
            if col_b.button("Borrar", key=fila["id"]):
                coleccion_estudiantes.delete_one({"_id": ObjectId(fila["id"])})
                st.rerun()
