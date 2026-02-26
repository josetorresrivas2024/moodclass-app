import sqlite3
from datetime import datetime, date
from pathlib import Path
from io import BytesIO
import calendar

import pandas as pd
import streamlit as st
import plotly.express as px

import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage


# =========================
# CONFIG BÁSICA (PILOTO)
# =========================
APP_TITLE = "MoodClass - Aula Emocional (Piloto)"

DATA_DIR = Path.home() / "Documents" / "MoodClass"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = str(DATA_DIR / "moodclass.db")

TEACHER_PIN = "1234"

EMOTIONS = [
    ("😊", "Tranquilo"),
    ("😃", "Feliz"),
    ("😐", "Normal"),
    ("😟", "Preocupado"),
    ("😡", "Molesto"),
    ("😢", "Triste"),
    ("😴", "Cansado"),
    ("😰", "Ansioso"),
]

REASONS = ["Casa", "Amigos", "Clases", "Salud", "No sé / prefiero no decir"]

TOOLKIT = {
    "Molesto": [
        "Respiración del semáforo (1 min): Inhala 3s, retén 2s, exhala 4s (x3).",
        "Descarga rápida: aprieta puños 5s y suelta (x5).",
        "Escribe qué te molestó y rompe el papel (guiado).",
    ],
    "Ansioso": [
        "Respiración 4–4–6: Inhala 4s, retén 4s, exhala 6s (x5).",
        "Visualización corta (1–2 min): imagina un lugar seguro con detalles.",
        "5-4-3-2-1: 5 cosas que ves, 4 que sientes, 3 que oyes, 2 que hueles, 1 que saboreas.",
    ],
    "Cansado": [
        "Activación 60s: saltitos suaves + estiramiento de brazos.",
        "Música + movimiento guiado (1–2 min).",
        "Postura: espalda recta 10s (x5) + agua.",
    ],
    "Triste": [
        "Validación: 'Lo que sientes importa. Respira conmigo 3 veces.'",
        "Rueda: ¿Qué necesito ahora? (descanso / hablar / agua / espacio).",
        "Escribe 1 cosa pequeña que te ayudaría hoy.",
    ],
    "Preocupado": [
        "Lista rápida: 1 cosa que controlo hoy + 1 acción pequeña.",
        "Respiración cuadrada: 4s inhala, 4s retén, 4s exhala, 4s retén (x4).",
        "Frase ancla: 'Haré lo mejor con lo que tengo hoy.'",
    ],
    "Normal": ["Mini check: 3 respiraciones profundas y define tu prioridad del día."],
    "Feliz": ["Reto: comparte una cosa buena del día con alguien (30s)."],
    "Tranquilo": ["Mantén: 30s de respiración lenta para sostener el estado."],
}


# =========================
# DB
# =========================
def db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    con = db()
    cur = con.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS moods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            day TEXT NOT NULL,
            moment TEXT NOT NULL,
            is_anonymous INTEGER NOT NULL,
            student_id INTEGER,
            emotion TEXT NOT NULL,
            reason TEXT DEFAULT '',
            note TEXT DEFAULT '',
            FOREIGN KEY(student_id) REFERENCES students(id)
        );
        """
    )

    con.commit()
    con.close()


def normalize_fullname(s: str) -> str:
    return " ".join(s.strip().split()).lower()


def add_student(fullname: str):
    con = db()
    cur = con.cursor()
    name_clean = " ".join(fullname.strip().split())
    cur.execute("INSERT INTO students(name) VALUES (?)", (name_clean,))
    con.commit()
    con.close()


def student_exists_fullname(fullname: str) -> bool:
    con = db()
    cur = con.cursor()
    cur.execute(
        "SELECT 1 FROM students WHERE lower(trim(name)) = ? LIMIT 1",
        (normalize_fullname(fullname),),
    )
    exists = cur.fetchone() is not None
    con.close()
    return exists


def get_students() -> pd.DataFrame:
    con = db()
    df = pd.read_sql_query("SELECT id, name FROM students ORDER BY name", con)
    con.close()
    return df


def delete_student(student_id: int, delete_moods: bool = True):
    con = db()
    cur = con.cursor()

    if delete_moods:
        cur.execute("DELETE FROM moods WHERE student_id = ?", (int(student_id),))
    else:
        cur.execute(
            """
            UPDATE moods
            SET student_id = NULL,
                is_anonymous = 1
            WHERE student_id = ?
            """,
            (int(student_id),),
        )

    cur.execute("DELETE FROM students WHERE id = ?", (int(student_id),))
    con.commit()
    con.close()


def save_mood(day, moment, is_anonymous, student_id, emotion, reason, note):
    con = db()
    cur = con.cursor()
    cur.execute(
        """
        INSERT INTO moods(created_at, day, moment, is_anonymous, student_id, emotion, reason, note)
        VALUES (?,?,?,?,?,?,?,?)
        """,
        (
            datetime.now().isoformat(timespec="seconds"),
            str(day),
            moment,
            1 if is_anonymous else 0,
            None if is_anonymous else int(student_id),
            emotion,
            reason or "",
            note or "",
        ),
    )
    con.commit()
    con.close()


def load_moods(day=None) -> pd.DataFrame:
    con = db()

    if day:
        df = pd.read_sql_query(
            """
            SELECT m.id, m.created_at, m.day, m.moment, m.is_anonymous,
                   s.name as student_name,
                   m.emotion, m.reason, m.note
            FROM moods m
            LEFT JOIN students s ON s.id = m.student_id
            WHERE m.day = ?
            ORDER BY m.created_at DESC
            """,
            con,
            params=(str(day),),
        )
    else:
        df = pd.read_sql_query(
            """
            SELECT m.id, m.created_at, m.day, m.moment, m.is_anonymous,
                   s.name as student_name,
                   m.emotion, m.reason, m.note
            FROM moods m
            LEFT JOIN students s ON s.id = m.student_id
            ORDER BY m.created_at DESC
            """,
            con,
        )

    con.close()
    return df


def load_moods_range(start_day: str, end_day: str) -> pd.DataFrame:
    con = db()
    df = pd.read_sql_query(
        """
        SELECT m.id, m.created_at, m.day, m.moment, m.is_anonymous,
               s.name as student_name,
               m.emotion, m.reason, m.note
        FROM moods m
        LEFT JOIN students s ON s.id = m.student_id
        WHERE m.day >= ? AND m.day <= ?
        ORDER BY m.created_at ASC
        """,
        con,
        params=(start_day, end_day),
    )
    con.close()
    return df


# =========================
# LÓGICA
# =========================
def emotion_label(emotion_text: str) -> str:
    return emotion_text.split(" ", 1)[1] if " " in emotion_text else emotion_text


def traffic_light(df_day_entrada: pd.DataFrame):
    if df_day_entrada.empty:
        return "🟡 Aula sin datos (aún)", 0.0

    cargadas = {"Molesto", "Triste", "Ansioso", "Preocupado", "Cansado"}
    labels = df_day_entrada["emotion"].apply(emotion_label)
    pct_cargada = (labels.isin(cargadas).sum() / len(labels)) * 100

    if pct_cargada >= 55:
        return "🔴 Aula en riesgo emocional", float(pct_cargada)
    if pct_cargada >= 35:
        return "🟡 Aula cargada", float(pct_cargada)
    return "🟢 Aula equilibrada", float(pct_cargada)


def recommended_tool(df_day_entrada: pd.DataFrame):
    if df_day_entrada.empty:
        return "Sin datos suficientes para recomendar.", []

    labels = df_day_entrada["emotion"].apply(emotion_label)
    top = labels.value_counts().idxmax()
    tools = TOOLKIT.get(top, ["Respira 3 veces lento (30s)."])
    msg = f"Hoy la emoción más frecuente al entrar es **{top}** → herramienta sugerida:"
    return msg, tools


def top3_table(df_moment: pd.DataFrame) -> pd.DataFrame:
    if df_moment.empty:
        return pd.DataFrame(columns=["Emoción", "Cantidad"])
    vc = df_moment["emotion"].value_counts().head(3).reset_index()
    vc.columns = ["Emoción", "Cantidad"]
    return vc


def compare_entrada_salida(df_entrada: pd.DataFrame, df_salida: pd.DataFrame) -> pd.DataFrame:
    ve = df_entrada["emotion"].value_counts()
    vs = df_salida["emotion"].value_counts()
    all_emotions = sorted(set(ve.index.tolist() + vs.index.tolist()))
    rows = []
    for emo in all_emotions:
        rows.append(
            {
                "Emoción": emo,
                "Entrada": int(ve.get(emo, 0)),
                "Salida": int(vs.get(emo, 0)),
                "Δ (Salida-Entrada)": int(vs.get(emo, 0) - ve.get(emo, 0)),
            }
        )
    return pd.DataFrame(rows)


# =========================
# PDF mensual
# =========================
def month_range(year: int, month: int):
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    return first_day, last_day


def generate_monthly_pdf(year: int, month: int) -> bytes:
    first_day, last_day = month_range(year, month)
    df = load_moods_range(str(first_day), str(last_day))

    df_entrada = df[df["moment"] == "entrada"].copy()
    df_salida = df[df["moment"] == "salida"].copy()

    total_registros = len(df)
    total_entrada = len(df_entrada)
    total_salida = len(df_salida)

    cargadas = {"Molesto", "Triste", "Ansioso", "Preocupado", "Cansado"}

    if not df_entrada.empty:
        df_entrada["label"] = df_entrada["emotion"].apply(emotion_label)
        daily = (
            df_entrada.groupby("day")["label"]
            .apply(lambda s: (s.isin(cargadas).sum() / len(s)) * 100)
            .reset_index()
        )
        daily.columns = ["Día", "% Cargadas (Entrada)"]
    else:
        daily = pd.DataFrame(columns=["Día", "% Cargadas (Entrada)"])

    if not df_entrada.empty:
        top_emotions = df_entrada["emotion"].value_counts().head(8).reset_index()
        top_emotions.columns = ["Emoción", "Cantidad"]
    else:
        top_emotions = pd.DataFrame(columns=["Emoción", "Cantidad"])

    img1 = BytesIO()
    plt.figure()
    if not top_emotions.empty:
        plt.bar(top_emotions["Emoción"], top_emotions["Cantidad"])
        plt.xticks(rotation=45, ha="right")
        plt.title("Top emociones del mes (Entrada)")
        plt.tight_layout()
    else:
        plt.text(0.5, 0.5, "Sin datos", ha="center")
        plt.axis("off")
    plt.savefig(img1, format="png", dpi=150, bbox_inches="tight")
    plt.close()
    img1.seek(0)

    img2 = BytesIO()
    plt.figure()
    if not daily.empty:
        plt.plot(daily["Día"], daily["% Cargadas (Entrada)"], marker="o")
        plt.xticks(rotation=45, ha="right")
        plt.title("% de estados cargados por día (Entrada)")
        plt.ylim(0, 100)
        plt.tight_layout()
    else:
        plt.text(0.5, 0.5, "Sin datos", ha="center")
        plt.axis("off")
    plt.savefig(img2, format="png", dpi=150, bbox_inches="tight")
    plt.close()
    img2.seek(0)

    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        rightMargin=28,
        leftMargin=28,
        topMargin=28,
        bottomMargin=28,
    )
    styles = getSampleStyleSheet()
    story = []

    month_name = calendar.month_name[month]
    story.append(Paragraph(f"Reporte Mensual - MoodClass ({month_name} {year})", styles["Title"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"<b>Rango:</b> {first_day} a {last_day}", styles["Normal"]))
    story.append(Spacer(1, 10))

    kpi_table = [
        ["Indicador", "Valor"],
        ["Total registros", str(total_registros)],
        ["Entradas registradas", str(total_entrada)],
        ["Salidas registradas", str(total_salida)],
    ]
    t = Table(kpi_table, colWidths=[260, 120])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F5F7FB")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 14))

    story.append(Paragraph("<b>Gráfico 1:</b> Top emociones del mes (Entrada)", styles["Heading3"]))
    story.append(RLImage(img1, width=500, height=260))
    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>Gráfico 2:</b> % estados cargados por día (Entrada)", styles["Heading3"]))
    story.append(RLImage(img2, width=500, height=260))
    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>Tabla:</b> Top emociones (Entrada)", styles["Heading3"]))
    if not top_emotions.empty:
        top_table = [["Emoción", "Cantidad"]] + top_emotions.values.tolist()
        tt = Table(top_table, colWidths=[380, 80])
        tt.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F5F7FB")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                    ("PADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(tt)
    else:
        story.append(Paragraph("Sin datos de entrada para este mes.", styles["Normal"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("<i>Nota: Este reporte es informativo. No etiqueta ni diagnostica.</i>", styles["Normal"]))

    doc.build(story)
    pdf_buffer.seek(0)
    return pdf_buffer.read()


# =========================
# UI: CSS (PRO + MOBILE)
# =========================
def inject_css():
    st.markdown(
        """
<style>
/* ---------- Design tokens ---------- */
:root{
  --bg: #F7F9FC;
  --surface: #FFFFFF;
  --text: #0B1220;
  --muted: rgba(11,18,32,.70);
  --muted2: rgba(11,18,32,.55);
  --border: rgba(11,18,32,.12);
  --shadow: 0 12px 28px rgba(11,18,32,.08);
  --shadow2: 0 8px 16px rgba(11,18,32,.07);
  --radius: 18px;
  --radius2: 14px;
  --focus: rgba(37, 99, 235, .35);
}

/* Dark mode support */
@media (prefers-color-scheme: dark){
  :root{
    --bg: #070B12;
    --surface: #0B1220;
    --text: #F3F6FF;
    --muted: rgba(243,246,255,.72);
    --muted2: rgba(243,246,255,.56);
    --border: rgba(243,246,255,.14);
    --shadow: 0 14px 32px rgba(0,0,0,.45);
    --shadow2: 0 10px 18px rgba(0,0,0,.35);
    --focus: rgba(96,165,250,.35);
  }
}

html, body, [data-testid="stAppViewContainer"]{
  background: var(--bg) !important;
  color: var(--text) !important;
}

/* App container */
.block-container{
  padding-top: 1.15rem;
  padding-bottom: 2.2rem;
  max-width: 980px;
}

/* Typography */
h1, h2, h3 {
  letter-spacing: -0.02em;
}
h1{
  font-size: 1.8rem;
}
p, li, label {
  color: var(--text);
}

/* Sidebar */
section[data-testid="stSidebar"]{
  border-right: 1px solid var(--border);
  background: var(--surface);
}

/* Inputs */
div[data-baseweb="input"] input, textarea, div[data-baseweb="select"] > div{
  border-radius: 12px !important;
}
input:focus, textarea:focus{
  outline: none !important;
  box-shadow: 0 0 0 4px var(--focus) !important;
}

/* Buttons */
.stButton>button, .stDownloadButton>button{
  border-radius: var(--radius2) !important;
  padding: 12px 14px !important;
  font-weight: 900 !important;
  border: 1px solid var(--border) !important;
}
.stButton>button:focus{
  box-shadow: 0 0 0 4px var(--focus) !important;
}
.stButton>button:hover, .stDownloadButton>button:hover{
  transform: translateY(-1px);
}

/* Cards */
.mcard{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px 16px;
  box-shadow: var(--shadow2);
}
.mcard-title{
  font-weight: 900;
  font-size: 1.02rem;
  margin-bottom: 6px;
}
.mmuted{ color: var(--muted); font-size: .95rem; }

/* KPI cards */
.kpi{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px 16px;
  box-shadow: var(--shadow2);
}
.kpi-title{ font-size: .85rem; color: var(--muted); font-weight: 900; text-transform: uppercase; letter-spacing: .06em; }
.kpi-value{ font-size: 1.7rem; font-weight: 900; margin-top: 2px; }
.kpi-sub{ font-size: .92rem; color: var(--muted2); margin-top: 4px; }

/* Badges */
.badge{
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 999px;
  font-weight: 900;
  border: 1px solid var(--border);
  margin-top: 10px;
  background: var(--surface);
}
.badge-green { background: rgba(16,185,129,.14); }
.badge-yellow { background: rgba(245,158,11,.16); }
.badge-red { background: rgba(239,68,68,.14); }

/* ---------- Mobile-first improvements ---------- */
@media (max-width: 640px){
  .block-container{
    padding-top: .8rem;
    padding-left: .9rem;
    padding-right: .9rem;
  }
  h1{ font-size: 1.45rem; }
  .stButton>button, .stDownloadButton>button{
    padding: 14px 14px !important;
    font-size: 1.02rem !important;
  }
  /* Make Streamlit columns behave like 2 per row on mobile */
  div[data-testid="column"]{
    flex: 0 0 50% !important;
    width: 50% !important;
  }
  /* Reduce chart height a bit on mobile */
  .js-plotly-plot, .plotly{
    min-height: 320px !important;
  }
}
</style>
        """,
        unsafe_allow_html=True,
    )


# =========================
# UI Helper: tarjetas de emoción (mejoradas)
# =========================
def emotion_cards(title: str, options, columns: int = 4, state_key: str = "chosen_emotion"):
    st.markdown(f"### {title}")

    # Colores con mejor contraste (y agradables en dark por transparencia)
    emotion_colors = {
        "Tranquilo": "rgba(16,185,129,.14)",
        "Feliz": "rgba(245,158,11,.16)",
        "Normal": "rgba(99,102,241,.14)",
        "Preocupado": "rgba(249,115,22,.16)",
        "Molesto": "rgba(239,68,68,.14)",
        "Triste": "rgba(59,130,246,.14)",
        "Cansado": "rgba(148,163,184,.18)",
        "Ansioso": "rgba(168,85,247,.16)",
    }

    chosen = st.session_state.get(state_key, "")
    cols = st.columns(columns)

    for i, (emoji, label) in enumerate(options):
        with cols[i % columns]:
            bg = emotion_colors.get(label, "rgba(2,6,23,.04)")
            is_selected = chosen == f"{emoji} {label}"

            st.markdown(
                f"""
                <style>
                /* target just this button via key attr */
                div[data-testid="stButton"] button[key="{state_key}_{i}"] {{
                    background: {bg} !important;
                    border-radius: 16px !important;
                    font-weight: 900 !important;
                    border: 2px solid {"rgba(37,99,235,.90)" if is_selected else "rgba(2,6,23,.18)"} !important;
                    color: inherit !important;
                }}
                div[data-testid="stButton"] button[key="{state_key}_{i}"]:hover {{
                    filter: brightness(0.98);
                    transform: translateY(-1px);
                }}
                </style>
                """,
                unsafe_allow_html=True,
            )

            txt = f"{emoji}  {label}" + (" ✅" if is_selected else "")
            if st.button(txt, key=f"{state_key}_{i}", use_container_width=True):
                st.session_state[state_key] = f"{emoji} {label}"
                chosen = st.session_state[state_key]

    if chosen:
        st.markdown(
            f"<div class='mcard'><div class='mcard-title'>Seleccionado</div>"
            f"<div style='font-size:1.25rem; font-weight:900;'>{chosen}</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='mcard'><div class='mmuted'>Elige una emoción para continuar.</div></div>",
            unsafe_allow_html=True,
        )

    return chosen


# =========================
# Plotly helper (más limpio)
# =========================
def polish_plotly(fig):
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=10, r=10, t=40, b=10),
        font=dict(size=14),
        title_font=dict(size=16),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="left", x=0),
    )
    return fig


# =========================
# APP
# =========================
st.set_page_config(page_title=APP_TITLE, page_icon="🎒", layout="centered")
inject_css()
init_db()

st.markdown(f"# 🎒 {APP_TITLE}")
st.caption("Registro emocional + panel docente + botiquín emocional. (Piloto local en tu PC)")


# Navegación (más cómoda en móvil que sidebar)
page = st.radio(
    "Navegación",
    ["👦 Estudiante", "🧑‍🏫 Docente (Panel)", "⚙️ Configuración (piloto)"],
    horizontal=True,
)

st.divider()


# =========================
# PÁGINA: ESTUDIANTE
# =========================
if page == "👦 Estudiante":
    st.markdown("## Registro emocional (2 minutos)")
    st.markdown("<div class='mcard'><div class='mcard-title'>Paso 1 · Datos</div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        moment = st.selectbox("¿Qué vas a registrar?", ["entrada", "salida"])
    with c2:
        day_sel = st.date_input("Fecha", value=date.today())

    mode = st.radio("Modo de registro:", ["Con mi nombre", "Anónimo"], horizontal=True)
    is_anon = mode == "Anónimo"

    students_df = get_students()
    student_id = None

    if not is_anon:
        if students_df.empty:
            st.warning("El docente aún no registró estudiantes. Pídele que agregue la lista.")
        else:
            chosen_name = st.selectbox("Selecciona tu nombre (Nombre y Apellido)", students_df["name"].tolist())
            student_id = int(students_df.loc[students_df["name"] == chosen_name, "id"].iloc[0])

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # Form para evitar “saltos” y mejorar UX en móvil
    with st.form("student_form", clear_on_submit=False):
        emotion = emotion_cards("Paso 2 · Elige tu emoción", EMOTIONS, columns=4, state_key="emo_student")

        st.markdown("### Paso 3 · (Opcional) ¿Por qué te sientes así?")
        reason = st.selectbox("Motivo", ["(opcional)"] + REASONS)
        reason = "" if reason == "(opcional)" else reason

        note = st.text_area("Nota opcional (máx 180 caracteres)", max_chars=180)

        submitted = st.form_submit_button("✅ Guardar registro", use_container_width=True)

    if submitted:
        if not emotion:
            st.error("Selecciona una emoción antes de guardar.")
        elif (not is_anon) and (student_id is None):
            st.error("Selecciona tu nombre o usa modo anónimo.")
        else:
            save_mood(day_sel, moment, is_anon, student_id, emotion, reason, note)
            st.success("Registro guardado. Gracias 🙌")

    st.info("📌 Tip: En primaria puedes reducir emociones a 4–5 y dejar botones aún más grandes.")


# =========================
# PÁGINA: DOCENTE
# =========================
elif page == "🧑‍🏫 Docente (Panel)":
    st.markdown("## Panel Docente")
    st.markdown("<div class='mcard'><div class='mcard-title'>Acceso</div>", unsafe_allow_html=True)
    pin = st.text_input("PIN docente", type="password", placeholder="Ejemplo: 1234")
    st.markdown("</div>", unsafe_allow_html=True)

    if pin != TEACHER_PIN:
        st.warning("Ingresa el PIN para ver el panel.")
    else:
        st.success("Acceso concedido ✅")

        tab1, tab2, tab3 = st.tabs(["📊 Vista general", "👦 Vista individual", "➕ Gestión de estudiantes"])

        # -------- tab1: vista general --------
        with tab1:
            day_sel = st.date_input("Fecha a analizar", value=date.today(), key="teacher_day")

            # Reporte mensual PDF
            st.markdown("### 📄 Reporte mensual (PDF)")
            cmy1, cmy2 = st.columns(2)
            with cmy1:
                rep_year = st.number_input("Año", min_value=2020, max_value=2100, value=date.today().year, step=1)
            with cmy2:
                rep_month = st.selectbox("Mes", list(range(1, 13)), index=date.today().month - 1)

            if st.button("📄 Generar PDF mensual", use_container_width=True):
                pdf_bytes = generate_monthly_pdf(int(rep_year), int(rep_month))
                file_name = f"moodclass_reporte_{int(rep_year)}_{int(rep_month):02d}.pdf"
                st.download_button(
                    "⬇️ Descargar PDF",
                    data=pdf_bytes,
                    file_name=file_name,
                    mime="application/pdf",
                    use_container_width=True,
                )

            st.divider()

            df = load_moods(day=str(day_sel))
            df_entrada = df[df["moment"] == "entrada"].copy()
            df_salida = df[df["moment"] == "salida"].copy()

            total_registros = len(df)
            total_entrada = len(df_entrada)

            if not df_entrada.empty:
                labels = df_entrada["emotion"].apply(emotion_label)
                emocion_top = labels.value_counts().idxmax()
            else:
                emocion_top = "—"

            status, pct = traffic_light(df_entrada)
            badge_class = "badge badge-green" if status.startswith("🟢") else "badge badge-yellow" if status.startswith("🟡") else "badge badge-red"

            st.markdown("### 📊 Resumen del día")
            k1, k2 = st.columns(2)
            k3, k4 = st.columns(2)

            with k1:
                st.markdown(
                    f"<div class='kpi'><div class='kpi-title'>Registros hoy</div>"
                    f"<div class='kpi-value'>{total_registros}</div>"
                    f"<div class='kpi-sub'>Entrada + salida</div></div>",
                    unsafe_allow_html=True,
                )
            with k2:
                st.markdown(
                    f"<div class='kpi'><div class='kpi-title'>Entradas registradas</div>"
                    f"<div class='kpi-value'>{total_entrada}</div>"
                    f"<div class='kpi-sub'>inicio de jornada</div></div>",
                    unsafe_allow_html=True,
                )
            with k3:
                st.markdown(
                    f"<div class='kpi'><div class='kpi-title'>Emoción más frecuente</div>"
                    f"<div class='kpi-value'>{emocion_top}</div>"
                    f"<div class='kpi-sub'>al ingresar</div></div>",
                    unsafe_allow_html=True,
                )
            with k4:
                st.markdown(
                    f"<div class='kpi'><div class='kpi-title'>Estados cargados</div>"
                    f"<div class='kpi-value'>{pct:.1f}%</div>"
                    f"<div class='kpi-sub'>Molesto/Triste/Ansioso/Preocupado/Cansado</div></div>",
                    unsafe_allow_html=True,
                )

            st.markdown(f"<div class='{badge_class}'>🚦 {status} · {pct:.1f}% cargado</div>", unsafe_allow_html=True)

            st.divider()

            a, b = st.columns(2)
            with a:
                st.markdown("<div class='mcard'><div class='mcard-title'>🏁 Top 3 al entrar</div>", unsafe_allow_html=True)
                st.dataframe(top3_table(df_entrada), use_container_width=True, hide_index=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with b:
                st.markdown("<div class='mcard'><div class='mcard-title'>🏁 Top 3 al salir</div>", unsafe_allow_html=True)
                st.dataframe(top3_table(df_salida), use_container_width=True, hide_index=True)
                st.markdown("</div>", unsafe_allow_html=True)

            comp = compare_entrada_salida(df_entrada, df_salida)
            st.markdown("<div class='mcard'><div class='mcard-title'>🔁 Comparación Entrada vs Salida</div>", unsafe_allow_html=True)
            if comp.empty:
                st.info("Sin datos suficientes para comparar.")
            else:
                st.dataframe(comp, use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)

            st.divider()

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("<div class='mcard'><div class='mcard-title'>📊 Emociones al entrar</div>", unsafe_allow_html=True)
                if df_entrada.empty:
                    st.info("Sin registros de entrada.")
                else:
                    vc = df_entrada["emotion"].value_counts().reset_index()
                    vc.columns = ["emotion", "count"]
                    fig = px.bar(vc, x="emotion", y="count", title="Entrada")
                    fig = polish_plotly(fig)
                    st.plotly_chart(fig, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            with c2:
                st.markdown("<div class='mcard'><div class='mcard-title'>🟠 Emociones al salir</div>", unsafe_allow_html=True)
                if df_salida.empty:
                    st.info("Sin registros de salida.")
                else:
                    vc = df_salida["emotion"].value_counts().reset_index()
                    vc.columns = ["emotion", "count"]
                    fig = px.pie(vc, names="emotion", values="count", title="Salida")
                    fig = polish_plotly(fig)
                    st.plotly_chart(fig, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            st.divider()

            st.markdown("<div class='mcard'><div class='mcard-title'>🧰 Botiquín emocional sugerido</div>", unsafe_allow_html=True)
            msg, tools = recommended_tool(df_entrada)
            st.write(msg)
            for t in tools:
                st.write("• " + t)
            st.markdown("</div>", unsafe_allow_html=True)

            st.divider()

            st.markdown("<div class='mcard'><div class='mcard-title'>🧾 Registros del día (detalle)</div>", unsafe_allow_html=True)
            if df.empty:
                st.info("Sin datos en esta fecha.")
            else:
                show = df.copy()
                show["estudiante"] = show.apply(
                    lambda r: "Anónimo" if r["is_anonymous"] == 1 else (r["student_name"] or "—"),
                    axis=1,
                )
                show = show[["created_at", "moment", "estudiante", "emotion", "reason", "note"]]
                st.dataframe(show, use_container_width=True, hide_index=True)

                csv = show.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    "⬇️ Descargar CSV (piloto)",
                    data=csv,
                    file_name=f"moodclass_{day_sel}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

        # -------- tab2: vista individual --------
        with tab2:
            st.markdown("### Historial por estudiante (no diagnóstico, solo tendencias)")
            students_df = get_students()

            if students_df.empty:
                st.info("Aún no hay estudiantes registrados.")
            else:
                student_name = st.selectbox("Selecciona estudiante", students_df["name"].tolist())
                df_all = load_moods()
                df_student = df_all[(df_all["student_name"] == student_name) & (df_all["is_anonymous"] == 0)].copy()

                if df_student.empty:
                    st.info("No hay registros para este estudiante.")
                else:
                    df_student = df_student.sort_values("created_at")
                    st.dataframe(
                        df_student[["created_at", "day", "moment", "emotion", "reason", "note"]],
                        use_container_width=True,
                        hide_index=True,
                    )

                    labels = df_student["emotion"].apply(emotion_label)
                    last3 = labels.tail(3).tolist()

                    st.markdown("#### Alertas suaves")
                    if len(last3) >= 3 and len(set(last3)) == 1 and last3[0] in {"Ansioso", "Triste", "Molesto"}:
                        st.warning(
                            f"Atención: **{student_name}** lleva **3 registros seguidos** con **{last3[0]}**. "
                            "(No diagnostica, solo alerta suave)."
                        )
                    else:
                        st.info("Sin alertas fuertes. Revisa tendencias y contexto.")

        # -------- tab3: gestión estudiantes --------
        with tab3:
            st.markdown("### Agregar estudiantes (Nombre y Apellido)")
            new_name = st.text_input("Nombre completo (Nombre y Apellido)", placeholder="Ej: Juan Pérez")

            if st.button("➕ Agregar estudiante", use_container_width=True):
                name_clean = " ".join(new_name.strip().split())

                if not name_clean:
                    st.error("Escribe el nombre completo.")
                elif len(name_clean.split()) < 2:
                    st.error("Debe ser Nombre y Apellido (mínimo 2 palabras).")
                else:
                    if student_exists_fullname(name_clean):
                        st.warning("⚠️ Ya existe un estudiante con ese Nombre y Apellido.")
                        st.session_state["pending_duplicate_name"] = name_clean
                    else:
                        add_student(name_clean)
                        st.success("Estudiante agregado ✅")
                        st.rerun()

            if "pending_duplicate_name" in st.session_state:
                st.info("Si lo agregaste por error, luego puedes eliminar el duplicado abajo.")
                confirm_dup = st.checkbox("Agregar de todos modos (duplicado)")
                if st.button("✅ Confirmar agregar duplicado", use_container_width=True):
                    if confirm_dup:
                        add_student(st.session_state["pending_duplicate_name"])
                        st.success("Duplicado agregado (a propósito) ✅")
                        del st.session_state["pending_duplicate_name"]
                        st.rerun()
                    else:
                        st.error("Marca 'Agregar de todos modos' para confirmar.")

            st.divider()
            st.markdown("### Lista actual")
            st.dataframe(get_students(), use_container_width=True, hide_index=True)

            st.divider()
            st.markdown("### 🗑️ Eliminar estudiante (si lo creaste duplicado)")
            students_df = get_students()

            if students_df.empty:
                st.info("No hay estudiantes para eliminar.")
            else:
                chosen_del = st.selectbox("Selecciona el estudiante a eliminar", students_df["name"].tolist(), key="del_student")
                del_id = int(students_df.loc[students_df["name"] == chosen_del, "id"].iloc[0])

                delete_moods = st.checkbox("¿Eliminar también sus registros emocionales?", value=True)
                confirm = st.text_input("Escribe ELIMINAR para confirmar")

                if st.button("🗑️ Eliminar definitivamente", use_container_width=True):
                    if confirm.strip().upper() != "ELIMINAR":
                        st.error("Para eliminar, escribe ELIMINAR.")
                    else:
                        delete_student(del_id, delete_moods=delete_moods)
                        st.success("Estudiante eliminado ✅")
                        st.rerun()


# =========================
# CONFIG
# =========================
else:
    st.markdown("## Configuración (piloto)")
    st.info(
        "✅ Cambia el PIN docente en el código (TEACHER_PIN). "
        "✅ Este piloto corre en tu PC y guarda datos en SQLite en Documentos\\MoodClass. "
        "✅ Luego lo podemos poner en red o agregar portada con logo al PDF."
    )
    st.markdown("### Ubicación de la base de datos")
    st.code(f"{DB_PATH}")