import streamlit as st
from pymongo import MongoClient
from datetime import datetime, date
import pandas as pd
import plotly.express as px
from bson.objectid import ObjectId

# ==========================================
# 1. CONFIGURACIÓN DE BASE DE DATOS (MONGODB)
# ==========================================
# Tu URI de conexión (Asegúrate de que no tenga espacios al final)
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
# 2. CONFIGURACIÓN VISUAL Y CSS (DARK MODE)
# ==========================================
st.set_page_config(page_title="MoodClass - Aula Emocional", page_icon="🎒", layout="centered")

st.markdown("""
<style>
    /* Forzar fondo oscuro profundo */
    .stApp {
        background-color: #0E1117 !important;
        color: #FFFFFF !important;
    }
    /* Estilo de tarjetas para los formularios */
    .mcard {
        background: #1A1C24 !important;
        border-radius: 15px;
        padding: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        margin-bottom: 20px;
        border: 1px solid #30363D;
    }
    /* Botones de Emociones */
    .stButton>button {
        border-radius: 12px !important;
        background-color: #21262D !important;
        color: white !important;
        border: 1px solid #30363D !important;
        transition: 0.3s;
        height: 70px;
        font-size: 16px;
    }
    .stButton>button:hover {
        border-color: #58A6FF !important;
        background-color: #30363D !important;
        transform: scale(1.02);
    }
    /* Ajuste de textos */
    h1, h2, h3, label, .stMarkdown p { 
        color: #FFFFFF !important; 
    }
    .stSelectbox div[data-baseweb="select"] {
        background-color: #0D1117 !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. FUNCIONES DE LÓGICA DE DATOS
# ==========================================

def get_students():
    lista = list(coleccion_estudiantes.find().sort("name", 1))
    if not lista: 
        return pd.DataFrame(columns=["id", "name"])
    df = pd.DataFrame(lista)
    df['id'] = df['_id'].astype(str)
    return df[["id", "name"]]

def save_mood(day, moment, is_anonymous, student_id, emotion):
    doc = {
        "day": str(day),
        "moment": moment,
        "is_anonymous": is_anonymous,
        "student_id": student_id if not is_anonymous else None,
        "emotion": emotion,
        "created_at": datetime.now()
    }
    coleccion_moods.insert_one(doc)

def load_moods(day):
    lista = list(coleccion_moods.find({"day": str(day)}))
    if not lista: 
        return pd.DataFrame()
    df = pd.DataFrame(lista)
    
    # Obtener nombres para la visualización
    est_df = get_students()
    def get_name(sid):
        if not sid: return "Anónimo"
        match = est_df[est_df['id'] == str(sid)]
        return match['name'].values[0] if not match.empty else "—"
    
    if 'student_id' in df.columns:
        df['Alumno'] = df['student_id'].apply(get_name)
    else:
        df['Alumno'] = "Anónimo"
        
    return df

# ==========================================
# 4. INTERFAZ DE USUARIO (TABS)
# ==========================================
st.title("🎒 MoodClass")
st.write("Registro de bienestar emocional para el aula.")

tab_est, tab_doc, tab_conf = st.tabs(["👦 Estudiante", "🧑‍🏫 Docente", "⚙️ Configuración"])

# --- PESTAÑA ESTUDIANTE ---
with tab_est:
    st.markdown("<div class='mcard'>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    momento = c1.selectbox("Momento del día", ["Entrada", "Salida"])
    fecha = c2.date_input("Fecha", value=date.today())
    
    modo = st.radio("Identificación", ["Con mi nombre", "Anónimo"], horizontal=True)
    id_estudiante = None
    
    if modo == "Con mi nombre":
        alumnos = get_students()
        if alumnos.empty:
            st.warning("⚠️ No hay alumnos en la lista. Avisa a tu profe.")
        else:
            nombre_sel = st.selectbox("Selecciona tu nombre", alumnos["name"].tolist())
            id_estudiante = alumnos[alumnos["name"] == nombre_sel]["id"].values[0]
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### ¿Cómo te sientes ahora?")
    columnas_emo = st.columns(4)
    for i, (emoji, texto) in enumerate(EMOTIONS):
        if columnas_emo[i % 4].button(f"{emoji}\n{texto}", use_container_width=True, key=f"btn_{i}"):
            save_mood(fecha, momento, (modo == "Anónimo"), id_estudiante, f"{emoji} {texto}")
            st.balloons()
            st.success(f"¡Listo! Se guardó: {texto}")

# --- PESTAÑA DOCENTE ---
with tab_doc:
    clave = st.text_input("PIN de Docente", type="password")
    if clave == TEACHER_PIN:
        st.subheader("Análisis del Día")
        fecha_ver = st.date_input("Ver datos de:", value=date.today())
        datos = load_moods(fecha_ver)
        
        if not datos.empty:
            # --- SOLUCIÓN AL ERROR DE PLOTLY ---
            resumen = datos["emotion"].value_counts().reset_index()
            resumen.columns = ["Emoción", "Cantidad"] # Forzamos nombres de columnas
            
            fig = px.bar(
                resumen, 
                x="Emoción", 
                y="Cantidad", 
                color="Emoción",
                template="plotly_dark",
                title="Estado Emocional del Grupo"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("### Registros individuales")
            st.dataframe(datos[["moment", "Alumno", "emotion"]], use_container_width=True)
        else:
            st.info("No hay registros para este día todavía.")
    elif clave:
        st.error("PIN incorrecto.")

# --- PESTAÑA CONFIGURACIÓN ---
with tab_conf:
    clave_c = st.text_input("PIN de Configuración", type="password", key="c_pin")
    if clave_c == TEACHER_PIN:
        st.markdown("### Administrar Estudiantes")
        with st.form("add_form", clear_on_submit=True):
            n_nombre = st.text_input("Nombre del nuevo alumno")
            if st.form_submit_button("Registrar Alumno"):
                if n_nombre:
                    coleccion_estudiantes.insert_one({"name": n_nombre.strip()})
                    st.success("Alumno añadido.")
                    st.rerun()
        
        st.divider()
        lista_al = get_students()
        for _, fila in lista_al.iterrows():
            col_a, col_b = st.columns([0.8, 0.2])
            col_a.write(fila["name"])
            if col_b.button("Borrar", key=f"del_{fila['id']}"):
                coleccion_estudiantes.delete_one({"_id": ObjectId(fila['id'])})
                st.rerun()
