# app.py
import streamlit as st
import pandas as pd
import numpy as np
import threading
import time
from datetime import datetime
import plotly.graph_objects as go
from tensorflow.keras.models import load_model
from tensorflow.keras.losses import MeanSquaredError
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# ────────────────────────────────────────────────────────────────
# CONFIGURACIÓN (variables seguras desde secrets o env)
# ────────────────────────────────────────────────────────────────
EMAIL_FROM = 'joshinanlo@gmail.com'
EMAIL_TO = 'joshinanlo@gmail.com'
APP_PASSWORD = os.environ.get("APP_PASSWORD") or st.secrets.get("APP_PASSWORD", "lvchktwnenwvgdje")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1K7ITGY2xAKidO52i8VPNpkZKbpMi9CvME5pfZSuLsQM/export?format=csv&gid=0"
LIMITE_MENSUAL_M3 = 15.0  # 5 personas × 3 m³

# Cargar modelo (debe estar en el repositorio)
@st.cache_resource
def cargar_modelo():
    try:
        model = load_model('modelo_anomalias_agua.h5', compile=False)
        model.compile(optimizer='adam', loss=MeanSquaredError())
        return model
    except Exception as e:
        st.error(f"Error cargando modelo: {e}")
        return None

model = cargar_modelo()

# Variables de estado para dashboard
if 'consumo_actual' not in st.session_state:
    st.session_state.update({
        'consumo_actual': 0.0,
        'porcentaje': 0.0,
        'mse_actual': 0.0,
        'estado': "Normal",
        'hist_mse': [],
        'hist_consumo': [],
        'ultima_actualizacion': datetime.now()
    })

# ────────────────────────────────────────────────────────────────
# FUNCIÓN DE ALERTA POR EMAIL
# ────────────────────────────────────────────────────────────────
def enviar_alerta_email(mse, consumo):
    try:
        subject = f"🚨 ALERTA - Posible Fuga o Sobreconsumo ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
        body = f"""¡Atención!

MSE detectado: {mse:.6f}
Consumo acumulado: {consumo:.2f} m³ ({st.session_state.porcentaje:.1f}% del límite de 15 m³)
Estado: {st.session_state.estado}

Revisa el consumo de agua urgentemente.
Sensor: Google Sheet ID 1K7ITGY2xAKidO52i8VPNpkZKbpMi9CvME5pfZSuLsQM
"""
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(EMAIL_FROM, APP_PASSWORD)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        server.quit()
        st.success("Alerta enviada por email")
    except Exception as e:
        st.error(f"Error enviando email: {e}")

# ────────────────────────────────────────────────────────────────
# HILO DE MONITOREO EN BACKGROUND
# ────────────────────────────────────────────────────────────────
def monitoreo_background():
    while True:
        try:
            df = pd.read_csv(SHEET_URL)
            df['timestamp'] = pd.to_datetime(df['date_id'].astype(str) + ' ' + df['start_time'].astype(str), errors='coerce')
            df = df.dropna(subset=['timestamp'])
            df = df[['timestamp', 'total_liters']].sort_values('timestamp').drop_duplicates(subset=['timestamp'])
            df.set_index('timestamp', inplace=True)
            series = df['total_liters'].resample('5T').last().ffill()
            consumption = series.diff().fillna(0)

            if len(consumption) >= 288 and model is not None:
                last_seq = consumption[-288:].values.reshape(1, 288, 1)
                last_scaled = scaler.transform(last_seq.reshape(-1, 1)).reshape(1, 288, 1)  # Asume scaler cargado o ajusta

                pred = model.predict(last_scaled, verbose=0)
                mse = np.mean(np.power(last_scaled - pred, 2))

                # Actualizar estado
                consumo_m3 = series.iloc[-1] / 1000  # litros a m³
                porcentaje = (consumo_m3 / LIMITE_MENSUAL_M3) * 100

                st.session_state.consumo_actual = consumo_m3
                st.session_state.porcentaje = porcentaje
                st.session_state.mse_actual = mse
                st.session_state.hist_mse.append(mse)
                st.session_state.hist_consumo.append(consumo_m3)
                st.session_state.ultima_actualizacion = datetime.now()

                if len(st.session_state.hist_mse) > 200:
                    st.session_state.hist_mse.pop(0)
                    st.session_state.hist_consumo.pop(0)

                # Alertas
                if mse > threshold or porcentaje > 90:
                    estado = "¡ALERTA!" if mse > threshold else "Cerca del límite"
                    enviar_alerta_email(mse, consumo_m3)
                else:
                    st.session_state.estado = "Normal"

        except Exception as e:
            print(f"Error en monitoreo: {e}")
        time.sleep(60)

# Iniciar hilo solo una vez
if 'hilo_iniciado' not in st.session_state:
    threading.Thread(target=monitoreo_background, daemon=True).start()
    st.session_state.hilo_iniciado = True

# ────────────────────────────────────────────────────────────────
# INTERFAZ DASHBOARD
# ────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
col1.metric("Consumo acumulado", f"{st.session_state.consumo_actual:.2f} m³", f"{st.session_state.porcentaje:.1f}% del límite")
col2.metric("Estado del sistema", st.session_state.estado)
col3.metric("Última actualización", st.session_state.ultima_actualizacion.strftime("%H:%M:%S"))

st.subheader("Consumo acumulado vs Límite mensual")
fig_consumo = go.Figure()
fig_consumo.add_trace(go.Scatter(y=st.session_state.hist_consumo, mode='lines', name='Consumo (m³)'))
fig_consumo.add_hline(y=LIMITE_MENSUAL_M3, line_dash="dash", line_color="red", annotation_text="Límite 15 m³")
fig_consumo.update_layout(height=400)
st.plotly_chart(fig_consumo, use_container_width=True)

st.subheader("Error MSE en vivo")
fig_mse = go.Figure()
fig_mse.add_trace(go.Scatter(y=st.session_state.hist_mse, mode='lines', name='MSE', line=dict(color='red')))
st.plotly_chart(fig_mse, use_container_width=True)

st.caption(f"App corriendo 24/7 en Render • Datos desde Google Sheets • Actualizado cada 60 segundos")