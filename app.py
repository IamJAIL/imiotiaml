```python
import streamlit as st
import pandas as pd
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

# -----------------------------
# CONFIGURACIÓN GENERAL
# -----------------------------

st.set_page_config(
    page_title="Monitor Inteligente de Agua",
    layout="wide"
)

st.title("🚰 Monitor Inteligente de Consumo de Agua")

# URL del Google Sheet en formato CSV
URL = "https://docs.google.com/spreadsheets/d/1K7ITGY2xAKidO52i8VPNpkZKbpMi9CvME5pfZSuLsQM/export?format=csv&gid=0"

# correo destino
EMAIL_DESTINO = "joshinanlo@gmail.com"

# correo emisor (configurar)
EMAIL_ORIGEN = "sistemaagua@gmail.com"
EMAIL_PASSWORD = "APP_PASSWORD"

# límite mensual
LIMITE_CONSUMO = 15


# -----------------------------
# FUNCIONES
# -----------------------------

def enviar_alerta(mensaje_texto):

    mensaje = MIMEText(mensaje_texto)

    mensaje['Subject'] = "ALERTA CONSUMO DE AGUA"
    mensaje['From'] = EMAIL_ORIGEN
    mensaje['To'] = EMAIL_DESTINO

    servidor = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    servidor.login(EMAIL_ORIGEN, EMAIL_PASSWORD)

    servidor.send_message(mensaje)

    servidor.quit()


def cargar_datos():

    df = pd.read_csv(URL)

    # convertir timestamp
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    return df


# -----------------------------
# CARGAR DATOS
# -----------------------------

df = cargar_datos()

st.success("Datos cargados correctamente")

# -----------------------------
# DASHBOARD TIEMPO REAL
# -----------------------------

st.subheader("📈 Consumo en tiempo real")

st.line_chart(
    df.set_index("timestamp")["consumo_m3"]
)

# -----------------------------
# CONSUMO DEL MES ACTUAL
# -----------------------------

df["mes"] = df["timestamp"].dt.month
df["anio"] = df["timestamp"].dt.year

mes_actual = datetime.now().month
anio_actual = datetime.now().year

df_mes = df[
    (df["mes"] == mes_actual) &
    (df["anio"] == anio_actual)
]

consumo_mes = df_mes["consumo_m3"].sum()

col1, col2 = st.columns(2)

col1.metric("Consumo del mes (m³)", round(consumo_mes, 3))
col2.metric("Número de registros", len(df_mes))

# -----------------------------
# ALERTA POR CONSUMO EXCESIVO
# -----------------------------

if consumo_mes > LIMITE_CONSUMO:

    st.error("⚠ Consumo mensual excesivo detectado")

    mensaje = f"""
    ALERTA DE CONSUMO DE AGUA

    El consumo del mes actual ha superado el límite permitido.

    Consumo actual: {consumo_mes} m3
    Límite permitido: {LIMITE_CONSUMO} m3

    Fecha: {datetime.now()}
    """

    enviar_alerta(mensaje)


# -----------------------------
# DETECCIÓN SIMPLE DE FUGAS
# -----------------------------

st.subheader("🔎 Detección de posibles fugas")

df["flujo_promedio"] = df["consumo_m3"].rolling(30).mean()

flujo_reciente = df["flujo_promedio"].iloc[-1]

if flujo_reciente > 0.02:

    st.warning("⚠ Posible fuga detectada (flujo constante)")

    mensaje = f"""
    POSIBLE FUGA DE AGUA DETECTADA

    Flujo promedio reciente: {flujo_reciente}

    Se detectó un consumo constante que podría indicar
    una fuga en el sistema de distribución de agua.
    """

    enviar_alerta(mensaje)

else:

    st.success("No se detectan fugas en este momento")


# -----------------------------
# CONSUMO DIARIO
# -----------------------------

st.subheader("📊 Consumo diario")

df["dia"] = df["timestamp"].dt.date

consumo_diario = df.groupby("dia")["consumo_m3"].sum()

st.bar_chart(consumo_diario)


# -----------------------------
# TABLA DE DATOS
# -----------------------------

st.subheader("📋 Datos recientes")

st.dataframe(df.tail(50))


# -----------------------------
# ACTUALIZACIÓN AUTOMÁTICA
# -----------------------------

st.caption("Actualización automática cada 60 segundos")

st.experimental_rerun()
```
