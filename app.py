import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import plotly.express as px
from pathlib import Path

# =========================
# CONFIGURACIÓN GENERAL
# =========================
st.set_page_config(
    page_title="MoodClass",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================
# ESTILOS RESPONSIVE PRO
# =========================
st.markdown("""
<style>

/* Fondo general */
.main {
    background-color: #f5f7fa;
}

/* Cards modernas */
.mcard {
    background: white;
    padding: 1.2rem;
    border-radius: 14px;
    box-shadow: 0 4px 18px rgba(0,0,0,0.06);
    margin-bottom: 1rem;
}

/* Título de card */
.mcard-title {
    font-weight: 700;
    font-size: 1.1rem;
    margin-bottom: 0.8rem;
    color: #1f2937;
}

/* KPIs */
.kpi-box {
    background: linear-gradient(135deg,#4f46e5,#6366f1);
    color: white;
    padding: 1rem;
    border-radius: 12px;
    text-align: center;
    font-weight: 600;
}

/* Responsive móvil */
@media (max-width: 768px) {
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    .mcard {
        padding: 0.8rem;
    }
}

</style>
""", unsafe_allow_html=True)

# =========================
# BASE DE DATOS
# =========================
DB_PATH = "moodclass.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS moods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT,
            emotion TEXT,
            reason TEXT,
            note TEXT,
            moment TEXT,
            is_anonymous INTEGER,
            created_at TEXT,
            day TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# =========================
# FUNCIONES
# =========================

def load_moods():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM moods", conn)
    conn.close()
    return df

def get_students():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM students", conn)
    conn.close()
    return df

def add_student(name):
    conn = get_connection()
    conn.execute("INSERT INTO students (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

def emotion_label(e):
    mapping = {
        "happy": "Feliz",
        "sad": "Triste",
        "angry": "Molesto",
        "anxious": "Ansioso",
        "calm": "Calmado"
    }
    return mapping.get(e, e)

# =========================
# INTERFAZ
# =========================

st.title("🎓 MoodClass - Panel Docente")

tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "👤 Vista individual", "⚙️ Gestión"])

# =========================
# TAB 1 - DASHBOARD
# =========================
with tab1:

    df = load_moods()

    if df.empty:
        st.info("Aún no hay registros.")
    else:
        day_sel = st.date_input("Selecciona fecha", datetime.now())
        day_sel = str(day_sel)

        df_day = df[df["day"] == day_sel]

        if df_day.empty:
            st.warning("No hay registros en esta fecha.")
        else:
            st.markdown("<div class='mcard'>", unsafe_allow_html=True)
            st.markdown("<div class='mcard-title'>Resumen del día</div>", unsafe_allow_html=True)

            total = len(df_day)
            positivos = len(df_day[df_day["emotion"] == "happy"])
            negativos = len(df_day[df_day["emotion"].isin(["sad","angry","anxious"])])

            col1, col2 = st.columns(2)
            col3, col4 = st.columns(2)

            col1.markdown(f"<div class='kpi-box'>Total<br>{total}</div>", unsafe_allow_html=True)
            col2.markdown(f"<div class='kpi-box'>Positivos<br>{positivos}</div>", unsafe_allow_html=True)
            col3.markdown(f"<div class='kpi-box'>Negativos<br>{negativos}</div>", unsafe_allow_html=True)
            col4.markdown(f"<div class='kpi-box'>Balance<br>{positivos - negativos}</div>", unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

            # Gráfico
            st.markdown("<div class='mcard'>", unsafe_allow_html=True)
            st.markdown("<div class='mcard-title'>Distribución emocional</div>", unsafe_allow_html=True)

            vc = df_day["emotion"].value_counts().reset_index()
            vc.columns = ["emotion", "count"]

            fig = px.pie(vc, names="emotion", values="count")
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("</div>", unsafe_allow_html=True)

# =========================
# TAB 2 - INDIVIDUAL
# =========================
with tab2:

    students_df = get_students()

    if students_df.empty:
        st.info("No hay estudiantes registrados.")
    else:
        student = st.selectbox("Selecciona estudiante", students_df["name"])

        df = load_moods()
        df_student = df[df["student_name"] == student]

        if df_student.empty:
            st.warning("Sin registros.")
        else:
            st.dataframe(
                df_student[["created_at","emotion","reason","note"]],
                use_container_width=True
            )

# =========================
# TAB 3 - GESTIÓN
# =========================
with tab3:

    st.subheader("Agregar estudiante")
    new_name = st.text_input("Nombre completo")

    if st.button("Agregar"):
        if new_name.strip():
            add_student(new_name.strip())
            st.success("Estudiante agregado")
            st.rerun()
        else:
            st.error("Escribe un nombre válido")

    st.divider()
    st.subheader("Lista actual")
    st.dataframe(get_students(), use_container_width=True)
