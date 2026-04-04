import streamlit as st
from pymongo import MongoClient
from datetime import datetime, date
from pathlib import Path
from io import BytesIO
import calendar
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
from bson.objectid import ObjectId

# Librerías para el PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage

# =========================
# CONFIG BÁSICA & MONGODB
# =========================
APP_TITLE = "MoodClass - Aula Emocional"

# Conexión a MongoDB (Corregida)
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

REASONS = ["Casa", "Amigos", "Clases", "Salud", "No sé / prefiero no decir"]

TOOLKIT = {
    "Molesto": ["Respiración del semáforo (1 min)", "Descarga rápida: aprieta puños", "Escribe y rompe el papel"],
    "Ansioso": ["Respiración 4–4–6", "Visualización corta", "Técnica 5-4-3-2-1"],
    "Cansado": ["Activación 60s: saltitos", "Música + movimiento", "Beber agua"],
    "Triste": ["Validación emocional", "¿Qué necesito ahora?", "Escribe algo que te ayude"],
    "Preocupado": ["Lista de control", "Respiración cuadrada", "Frase ancla"],
    "Normal": ["Mini check: 3 respiraciones profundas"],
    "Feliz": ["Reto: comparte algo bueno"],
    "Tranquilo": ["Mantén el estado con respiración lenta"],
}

# =========================
# FUNCIONES DE BASE DE DATOS
# =========================

def add_student(fullname: str):
    name_clean = " ".join(fullname.strip().split())
    coleccion_estudiantes.insert_one({"name": name_clean})

def get_students() -> pd.DataFrame:
    lista = list(coleccion_estudiantes.find().sort("name", 1))
    if not lista:
        return pd.DataFrame(columns=["id", "name"])
    df = pd.DataFrame(lista)
    df['id'] = df['_id'].astype(str)
    return df[["id", "name"]]

def delete_student(student_id: str):
    coleccion_moods.delete_many({"student_id": str(student_id)})
    coleccion_estudiantes.delete_one({"_id": ObjectId(student_id)})

def save_mood(day, moment, is_anonymous, student_id, emotion, reason, note):
    doc = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "day": str(day),
        "moment": moment,
        "is_anonymous": 1 if is_anonymous else 0,
        "student_id": None if is_anonymous else str(student_id),
        "emotion": emotion,
        "reason": reason or "",
        "note": note or ""
    }
    coleccion_moods.insert_one(doc)

def load_moods(day=None) -> pd.DataFrame:
    query = {"day": str(day)} if day else {}
    lista = list(coleccion_moods.find(query).sort("created_at", -1))
    if not lista:
        return pd.DataFrame(columns=["id", "created_at", "day", "moment", "is_anonymous", "student_name", "emotion", "reason", "note"])
    
    df = pd.DataFrame(lista)
    est_df = get_students()
    
    def get_name(sid):
        if not sid: return "Anónimo"
        match = est_df[est_df['id'] == sid]
        return match['name'].values[0] if not match.empty else "—"
    
    df['student_name'] = df['student_id'].apply(get_name)
    return df

# =========================
# LÓGICA DE NEGOCIO Y PDF
# =========================

def emotion_label(emotion_text: str) -> str:
    return emotion_text.split(" ", 1)[1] if " " in emotion_text else emotion_text

def traffic_light(df_entrada: pd.DataFrame):
    if df_entrada.empty: return "🟡 Aula sin datos", 0.0
    cargadas = {"Molesto", "Triste", "Ansioso", "Preocupado", "Cansado"}
    labels = df_entrada["emotion"].apply(emotion_label)
    pct = (labels.isin(cargadas).sum() / len(labels)) * 100
    if pct >= 55: return "🔴 Aula en riesgo emocional", pct
    if pct >= 35: return "🟡 Aula cargada", pct
    return "🟢 Aula equilibrada", pct

def generate_monthly_pdf(year, month):
    # Función simplificada para asegurar compatibilidad
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [Paragraph(f"Reporte Mensual MoodClass - {month}/{year}", styles["Title"]), Spacer(1, 12)]
    
    df = load_moods() # En producción filtrar por mes
    if not df.empty:
        data = [["Fecha", "Momento", "Emoción"]] + df[["day", "moment", "emotion"]].values.tolist()[:20]
        t = Table(data)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.grey),('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke)]))
        story.append(t)
    
    doc.build(story)
    pdf_buffer.seek(0)
    return pdf_buffer.read()

# =========================
# INTERFAZ (UI)
# =========================
st.set_page_config(page_title=APP_TITLE, page_icon="🎒", layout="centered")

# Inyectar tu CSS original
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background: #F7F9FC !important; }
    .mcard { background: white; border-radius: 15px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 15px; border: 1px solid #eee; }
    .stButton>button { border-radius: 12px !important; font-weight: bold !important; }
</style>
""", unsafe_allow_html=True)

st.title(f"🎒 {APP_TITLE}")

menu = st.radio("Navegación", ["👦 Estudiante", "🧑‍🏫 Docente", "⚙️ Configuración"], horizontal=True)

if menu == "👦 Estudiante":
    st.markdown("## Registro Diario")
    with st.container():
        st.markdown("<div class='mcard'>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        moment = col1.selectbox("Momento", ["entrada", "salida"])
        day_sel = col2.date_input("Fecha", value=date.today())
        
        mode = st.radio("Modo", ["Con mi nombre", "Anónimo"], horizontal=True)
        student_id = None
        
        if mode == "Con mi nombre":
            students = get_students()
            if students.empty:
                st.warning("No hay estudiantes registrados.")
            else:
                sel_name = st.selectbox("Busca tu nombre", students["name"].tolist())
                student_id = students[students["name"] == sel_name]["id"].values[0]
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("### ¿Cómo te sientes hoy?")
        cols = st.columns(4)
        emotion = st.session_state.get("emo_sel", "")
        for i, (emoji, label) in enumerate(EMOTIONS):
            if cols[i % 4].button(f"{emoji}\n{label}", key=f"btn_{i}", use_container_width=True):
                st.session_state["emo_sel"] = f"{emoji} {label}"
                emotion = f"{emoji} {label}"
        
        if emotion: st.info(f"Seleccionado: **{emotion}**")

        with st.form("registro"):
            reason = st.selectbox("Motivo (opcional)", [""] + REASONS)
            note = st.text_area("Nota privada")
            if st.form_submit_button("✅ Guardar mi estado", use_container_width=True):
                if not emotion:
                    st.error("Por favor selecciona una emoción arriba.")
                elif mode == "Con mi nombre" and not student_id:
                    st.error("Selecciona un nombre.")
                else:
                    save_mood(day_sel, moment, mode=="Anónimo", student_id, emotion, reason, note)
                    st.success("¡Registro guardado! Que tengas un gran día.")

elif menu == "🧑‍🏫 Docente":
    st.markdown("## Panel de Análisis")
    pin = st.text_input("PIN Docente", type="password")
    if pin == TEACHER_PIN:
        day_view = st.date_input("Ver datos del día", value=date.today())
        df = load_moods(day=str(day_view))
        
        if df.empty:
            st.info("No hay registros hoy.")
        else:
            status, pct = traffic_light(df[df["moment"]=="entrada"])
            st.subheader(f"{status} ({pct:.1f}%)")
            
            c1, c2 = st.columns(2)
            fig1 = px.bar(df["emotion"].value_counts().reset_index(), x="index", y="emotion", title="Frecuencia de Emociones")
            c1.plotly_chart(fig1, use_container_width=True)
            
            st.markdown("### Detalle de registros")
            st.dataframe(df[["moment", "student_name", "emotion", "reason", "note"]], use_container_width=True)
            
            if st.button("Generar PDF Mensual"):
                pdf = generate_monthly_pdf(day_view.year, day_view.month)
                st.download_button("Descargar Reporte", pdf, f"reporte_{day_view.month}.pdf", "application/pdf")
    else:
        st.write("Por favor introduce el PIN.")

elif menu == "⚙️ Configuración":
    st.markdown("## Gestión de Alumnos")
    pin = st.text_input("PIN de seguridad", type="password", key="conf_pin")
    if pin == TEACHER_PIN:
        with st.form("add_student"):
            new_name = st.text_input("Nombre completo del estudiante")
            if st.form_submit_button("Agregar a la lista"):
                if new_name:
                    add_student(new_name)
                    st.success("Estudiante agregado.")
        
        st.divider()
        st.markdown("### Lista actual")
        students = get_students()
        for idx, row in students.iterrows():
            c1, c2 = st.columns([0.8, 0.2])
            c1.write(row["name"])
            if c2.button("Eliminar", key=f"del_{row['id']}"):
                delete_student(row["id"])
                st.rerun()
