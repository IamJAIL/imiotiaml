import streamlit as st
import pandas as pd
import numpy as np
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from sklearn.ensemble import IsolationForest

# -------------------------
# CONFIGURACIÓN
# -------------------------

st.set_page_config(page_title="Monitor Inteligente de Agua", layout="wide")

URL = "https://docs.google.com/spreadsheets/d/1K7ITGY2xAKidO52i8VPNpkZKbpMi9CvME5pfZSuLsQM/export?format=csv&gid=0"

EMAIL_FROM = "joshinanlo@gmail.com"
EMAIL_TO = "joshinanlo@gmail.com"
APP_PASSWORD = os.environ.get("APP_PASSWORD")

LIMITE_MENSUAL = 15

st.title("🚰 Sistema Inteligente de Monitoreo de Agua")

# -------------------------
# FUNCIÓN DE ALERTA
# -------------------------

def enviar_alerta(asunto, mensaje):

    if APP_PASSWORD is None:
        return

    msg = MIMEText(mensaje)

    msg["Subject"] = asunto
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(EMAIL_FROM, APP_PASSWORD)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        server.quit()
    except:
        pass


# -------------------------
# CARGAR DATOS
# -------------------------

try:
    df = pd.read_csv(URL)
except:
    st.error("No se pudo leer el Google Sheet")
    st.stop()

# detectar columnas
timestamp_col = None
flow_col = None

for c in df.columns:
    if "time" in c.lower() or "fecha" in c.lower():
        timestamp_col = c
    if "m3" in c.lower() or "flow" in c.lower() or "consumo" in c.lower():
        flow_col = c

if timestamp_col is None or flow_col is None:
    st.error("No se detectaron columnas correctas")
    st.stop()

# limpiar datos
df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors="coerce")
df = df.dropna()

# -------------------------
# FEATURE ENGINEERING
# -------------------------

df["hour"] = df[timestamp_col].dt.hour
df["dayofweek"] = df[timestamp_col].dt.dayofweek

df["rolling_mean"] = df[flow_col].rolling(20).mean()
df["rolling_std"] = df[flow_col].rolling(20).std()

df["diff_flow"] = df[flow_col].diff()

df = df.dropna()

features = df[
    [
        flow_col,
        "hour",
        "dayofweek",
        "rolling_mean",
        "rolling_std",
        "diff_flow"
    ]
]

# -------------------------
# MODELO DE IA
# -------------------------

model = IsolationForest(
    contamination=0.01,
    n_estimators=200,
    random_state=42
)

model.fit(features)

df["anomaly"] = model.predict(features)

anomalies = df[df["anomaly"] == -1]

# -------------------------
# DASHBOARD
# -------------------------

st.subheader("Consumo en tiempo real")

st.line_chart(
    df.set_index(timestamp_col)[flow_col]
)

# -------------------------
# CONSUMO MENSUAL
# -------------------------

df["month"] = df[timestamp_col].dt.month
df["year"] = df[timestamp_col].dt.year

now = datetime.now()

df_month = df[
    (df["month"] == now.month) &
    (df["year"] == now.year)
]

monthly_consumption = df_month[flow_col].sum()

col1, col2 = st.columns(2)

col1.metric("Consumo del mes (m³)", round(monthly_consumption,2))
col2.metric("Registros analizados", len(df))

# -------------------------
# ALERTA DE CONSUMO
# -------------------------

if monthly_consumption > LIMITE_MENSUAL:

    st.error("⚠ Consumo mensual excedido")

    enviar_alerta(
        "Alerta consumo de agua",
        f"El consumo mensual ha excedido {LIMITE_MENSUAL} m3.\nConsumo actual: {monthly_consumption}"
    )

# -------------------------
# ANOMALÍAS IA
# -------------------------

st.subheader("Detección de anomalías por IA")

if len(anomalies) > 0:

    st.warning("Se detectaron anomalías en el consumo")

    st.dataframe(
        anomalies[[timestamp_col, flow_col]].tail(20)
    )

    enviar_alerta(
        "Anomalía detectada",
        "El sistema de IA detectó un comportamiento anormal en el consumo de agua."
    )

else:

    st.success("No se detectaron anomalías")

# -------------------------
# DETECCIÓN DE FUGA NOCTURNA
# -------------------------

st.subheader("Análisis de fugas nocturnas")

night_data = df[
    (df["hour"] >= 0) &
    (df["hour"] <= 5)
]

night_mean = night_data[flow_col].mean()

if night_mean > 0.02:

    st.error("⚠ Posible fuga nocturna detectada")

    enviar_alerta(
        "Posible fuga de agua",
        f"Se detectó consumo nocturno anormal.\nFlujo promedio: {night_mean}"
    )

else:

    st.success("Consumo nocturno normal")

# -------------------------
# PERFIL DE CONSUMO
# -------------------------

st.subheader("Perfil de consumo por hora")

hourly = df.groupby("hour")[flow_col].mean()

st.bar_chart(hourly)

# -------------------------
# CONSUMO DIARIO
# -------------------------

st.subheader("Consumo diario")

df["day"] = df[timestamp_col].dt.date

daily = df.groupby("day")[flow_col].sum()

st.bar_chart(daily)

# -------------------------
# DATOS RECIENTES
# -------------------------

st.subheader("Datos recientes")

st.dataframe(df.tail(50))

# -------------------------
# REFRESCO AUTOMÁTICO
# -------------------------

st.caption("Actualiza automáticamente al recargar la página")

