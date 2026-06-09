import streamlit as st
import pandas as pd
import joblib
import requests
import json
import plotly.express as px
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timezone
import threading
import sys

DATA_PATH = Path("data/firms_brasil.csv")
MODEL_PATH = Path("src/python/modelo_risco.pkl")
IOT_DATA_PATH = Path("data/iot_readings.json")

OPENMETEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


@dataclass
class RiskLevel:
    name: str
    min_frp: float
    max_frp: float


RISK_LEVELS = {
    "Baixo": RiskLevel("Baixo", 0, 10),
    "Médio": RiskLevel("Médio", 10, 50),
    "Alto": RiskLevel("Alto", 50, float("inf")),
}


def get_risk_label(frp: float) -> str:
    if frp >= 50:
        return "Alto"
    if frp >= 10:
        return "Médio"
    return "Baixo"


@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df["risk_level"] = df["frp"].apply(get_risk_label)
    return df


def filter_data(
    df: pd.DataFrame,
    satellite: list[str] | None,
    risk_level: str,
) -> pd.DataFrame:
    if satellite:
        df = df[df["satellite"].isin(satellite)]
    if risk_level != "Todos":
        df = df[df["risk_level"] == risk_level]
    return df


def load_model():
    if not MODEL_PATH.exists():
        return None
    return joblib.load(MODEL_PATH)


def fetch_current_weather(lat: float, lon: float) -> dict | None:
    """Busca clima atual via OpenMeteo Forecast API (fallback)."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,temperature_2m_mean,"
                 "wind_speed_10m_max,precipitation_sum",
        "timezone": "auto",
    }
    try:
        resp = requests.get(OPENMETEO_FORECAST_URL, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException:
        return None


def read_iot_sensor() -> dict | None:
    """Lê dados do sensor IoT (ESP32) de um arquivo JSON.

    O formato esperado do JSON é:
    {
        "timestamp": "2026-06-08T14:30:00",
        "temperature": 28.3,
        "humidity": 62.0,
        "precipitation": 0.0,
        "soil_moisture": 45.2
    }

    Retorna None se o arquivo não existir ou estiver inválido.
    """
    if not IOT_DATA_PATH.exists():
        return None
    try:
        data = json.loads(IOT_DATA_PATH.read_text())
        return data
    except (json.JSONDecodeError, OSError):
        return None


def sensor_to_features(sensor_data: dict) -> dict:
    """Converte dados do sensor IoT nas features esperadas pelo modelo.

    O sensor fornece temperatura, umidade, precipitação e umidade do solo
    em tempo real. Para as features diárias (temp_max, temp_min, temp_mean)
    usamos o valor atual como estimativa. Ventos não são medidos pelo DHT22.
    """
    temp = sensor_data.get("temperature")
    humidity = sensor_data.get("humidity")
    precipitation = sensor_data.get("precipitation")
    soil_moisture = sensor_data.get("soil_moisture")

    return {
        "temp_max": temp,
        "temp_min": temp,
        "temp_mean": temp,
        "humidity": humidity,
        "wind_speed": None,       # não disponível no DHT22
        "precipitation": precipitation,
        "soil_moisture": soil_moisture,
    }


def openmeteo_to_features(weather_data: dict) -> dict:
    """Converte dados do OpenMeteo nas features esperadas pelo modelo."""
    current = weather_data.get("current", {})
    daily = weather_data.get("daily", {})

    return {
        "temp_max": (daily.get("temperature_2m_max") or [None])[0],
        "temp_min": (daily.get("temperature_2m_min") or [None])[0],
        "temp_mean": (daily.get("temperature_2m_mean") or [None])[0],
        "humidity": current.get("relative_humidity_2m"),
        "wind_speed": (daily.get("wind_speed_10m_max") or [None])[0],
        "precipitation": (daily.get("precipitation_sum") or [None])[0],
        "soil_moisture": None,
    }


def predict_risk(model, features: dict, source: str) -> dict | None:
    """Prevê risco de queimada a partir de features climáticas.

    Args:
        model: modelo treinado (RandomForestClassifier).
        features: dict com as features climáticas.
        source: fonte dos dados ("IoT" ou "OpenMeteo").
    """
    if model is None:
        return None

    # Verificar se temos features suficientes
    required = ["temp_max", "temp_min", "temp_mean", "humidity"]
    if any(features.get(f) is None for f in required):
        return None

    # Preencher features faltantes com 0
    try:
        model_features = list(model.feature_names_in_)
    except AttributeError:
        return None

    input_data = {f: features.get(f, 0) for f in model_features}
    X = pd.DataFrame([input_data])

    prediction = model.predict(X)[0]
    probabilities = model.predict_proba(X)[0]

    risk_map = {0: "Baixo", 1: "Médio", 2: "Alto"}

    return {
        "risk": risk_map[prediction],
        "probabilities": {
            "Baixo": probabilities[0],
            "Médio": probabilities[1],
            "Alto": probabilities[2],
        },
        "source": source,
        "weather": {
            "temperature": features.get("temp_mean"),
            "temp_max": features.get("temp_max"),
            "temp_min": features.get("temp_min"),
            "humidity": features.get("humidity"),
            "wind_speed": features.get("wind_speed"),
            "precipitation": features.get("precipitation"),
            "soil_moisture": features.get("soil_moisture"),
        },
    }


def display_prediction_result(result: dict) -> None:
    """Exibe o resultado de uma previsão de risco (usado por ambas as abas).
    Mostra apenas as métricas que existirem no contexto da fonte de dados.
    """
    risk = result["risk"]
    proba = result["probabilities"]
    w = result["weather"]

    risk_colors = {"Baixo": "green", "Médio": "orange", "Alto": "red"}
    risk_icons = {"Baixo": "🟢", "Médio": "🟡", "Alto": "🔴"}

    st.markdown(f"### {risk_icons[risk]} Risco Previsto: :{risk_colors[risk]}[{risk}]")
    st.caption(f"Fonte dos dados: {result['source']}")

    metrics = {}
    if w.get("temperature") is not None:
        metrics["Temperatura"] = f"{w['temperature']:.1f}°C"
    if w.get("humidity") is not None:
        metrics["Umidade"] = f"{w['humidity']:.0f}%"
    if w.get("soil_moisture") is not None:
        metrics["Umidade do Solo"] = f"{w['soil_moisture']:.1f}%"
    if w.get("wind_speed") is not None:
        metrics["Vento máx"] = f"{w['wind_speed']:.1f} km/h"
    if w.get("precipitation") is not None:
        metrics["Precipitação"] = f"{w['precipitation']:.1f} mm"

    if metrics:
        cols = st.columns(len(metrics))
        for col, (label, value) in zip(cols, metrics.items()):
            with col:
                st.metric(label, value)

    st.subheader("Probabilidades por classe")

    RISK_HEX = {"Baixo": "#008000", "Médio": "#FFA500", "Alto": "#FF0000"}
    proba_df = pd.DataFrame({
        "Classe": ["Baixo", "Médio", "Alto"],
        "Probabilidade": [proba["Baixo"], proba["Médio"], proba["Alto"]],
    })

    fig = px.bar(
        proba_df,
        x="Classe",
        y="Probabilidade",
        color="Classe",
        color_discrete_map=RISK_HEX,
        text_auto=".1%",
        range_y=[0, 1],
        template="plotly_dark",
    )
    fig.update_layout(
        showlegend=False,
        xaxis_title=None,
        yaxis_title="Probabilidade",
        margin=dict(l=0, r=0, t=30, b=0),
    )
    fig.update_traces(textposition="outside", textfont_size=13)
    st.plotly_chart(fig, use_container_width=True)


def start_iot_server_background() -> None:
    """Inicia o servidor IoT em background thread (porta 8001).

    O servidor recebe dados do ESP32 via HTTP POST e salva em
    data/iot_readings.json para uso pelo dashboard.
    """
    try:
        import uvicorn
        sys.path.insert(0, str(Path(__file__).parent))
        from iot_server import app

        def run_server():
            uvicorn.run(app, host="0.0.0.0", port=8001, log_level="warning")

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        print("[IoT] Servidor iniciado em http://0.0.0.0:8001")
    except ImportError:
        print("[IoT] FastAPI/uvicorn não instalado — servidor offline")
    except Exception as e:
        print(f"[IoT] Erro ao iniciar servidor: {e}")


def main() -> None:
    start_iot_server_background()
    st.set_page_config(layout="wide", page_title="Geo Fire - Monitoramento de Queimadas")

    st.title("🔥 Geo Fire: Monitoramento de queimadas")

    df = load_data()
    model = load_model()

    # ================================================================
    # SIDEBAR — Filtros e Status do Modelo
    # ================================================================
    st.sidebar.header("Filtros")

    satellites = sorted(df["satellite"].unique().tolist())
    selected_satellites = st.sidebar.multiselect(
        "Satélite",
        options=satellites,
        default=satellites,
    )

    selected_risk = st.sidebar.selectbox(
        "Nível de risco",
        options=["Todos", "Baixo", "Médio", "Alto"],
    )

    st.sidebar.date_input(
        "Período",
        value=pd.to_datetime("2026-06-08"),
        disabled=True,
    )

    st.sidebar.header("Modelo ML")
    if model is not None:
        st.sidebar.success(f"Modelo carregado: RandomForest ({model.n_estimators} árvores)")
        try:
            feature_imp = (
                pd.DataFrame(
                    {"feature": model.feature_names_in_, "importance": model.feature_importances_}
                )
                .sort_values("importance", ascending=False)
                .reset_index(drop=True)
            )
            st.sidebar.subheader("Importância das Features")
            st.sidebar.dataframe(feature_imp, hide_index=True, use_container_width=True)
        except AttributeError:
            pass
    else:
        st.sidebar.warning(
            "Modelo não encontrado. Execute o notebook analise_firms.ipynb primeiro."
        )

    # ================================================================
    # VISÃO GERAL — Métricas e Mapa
    # ================================================================
    filtered = filter_data(df, selected_satellites, selected_risk)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de focos", len(filtered))
    with col2:
        frp_mean = round(filtered["frp"].mean(), 2) if len(filtered) > 0 else 0
        st.metric("FRP médio", frp_mean)
    with col3:
        if len(filtered) > 0:
            top_region = (
                filtered.groupby(
                    [filtered["latitude"].round(2), filtered["longitude"].round(2)]
                )
                .size()
                .idxmax()
            )
            st.metric("Top região", f"{top_region[0]}, {top_region[1]}")
        else:
            st.metric("Top região", "N/A")

    if len(filtered) > 0:
        st.map(filtered, latitude="latitude", longitude="longitude")
    else:
        st.info("Nenhum foco encontrado com os filtros selecionados.")

    st.subheader("Top 10 focos mais intensos")
    if len(filtered) > 0:
        top10 = (
            filtered.nlargest(10, "frp")[
                ["latitude", "longitude", "frp", "satellite", "risk_level", "acq_time"]
            ]
            .reset_index(drop=True)
            .assign(acq_time=lambda x: x["acq_time"].apply(
                lambda t: f"{t // 100:02d}:{t % 100:02d}"
            ))
        )
        st.dataframe(top10, use_container_width=True)
    else:
        st.info("Nenhum dado disponível.")

    # ================================================================
    # SEÇÃO: Previsão de Risco em Tempo Real
    # ================================================================
    st.markdown("---")
    st.subheader("⚡ Previsão de Risco em Tempo Real")

    sensor_data = read_iot_sensor()

    tab_farm, tab_region = st.tabs(["Fazenda Fictícia", "Monitoramento Regional"])

    # ─── Aba 1: Fazenda Fictícia (IoT) ──────────────────────────────────────
    with tab_farm:
        if sensor_data is None:
            st.warning(
                "Sensores IoT offline — aguardando leituras do ESP32.\n\n"
                "Para utilizar esta aba, inicie o servidor Wokwi e certifique-se "
                "de que o ESP32 está enviando dados para `data/iot_readings.json`."
            )
        else:
            ts_raw = sensor_data.get("timestamp", "")
            try:
                ts_dt = datetime.fromisoformat(ts_raw).replace(tzinfo=timezone.utc).astimezone()
                ts_label = ts_dt.strftime("%d/%m/%Y às %H:%M:%S")
            except (ValueError, TypeError):
                ts_label = ts_raw

            st.caption(f"Última atualização: {ts_label}")

            features = sensor_to_features(sensor_data)
            result = predict_risk(model, features, "IoT")

            if result is None:
                st.error("Dados climáticos insuficientes para previsão.")
            else:
                display_prediction_result(result)

    # ─── Aba 2: Monitoramento Regional (OpenMeteo) ──────────────────────────
    with tab_region:
        col_lat, col_lon, col_btn = st.columns([2, 2, 1])
        with col_lat:
            pred_lat = st.number_input(
                "Latitude", value=0.0, format="%.4f", step=0.01, key="reg_lat"
            )
        with col_lon:
            pred_lon = st.number_input(
                "Longitude", value=0.0, format="%.4f", step=0.01, key="reg_lon"
            )
        with col_btn:
            st.write("")
            st.write("")
            predict_btn = st.button("Prever Risco", type="primary", key="reg_predict")

        if predict_btn:
            with st.spinner("Buscando dados climáticos via OpenMeteo..."):
                weather = fetch_current_weather(pred_lat, pred_lon)

            if weather is None:
                st.error("Falha ao buscar dados climáticos. Verifique as coordenadas.")
            else:
                features = openmeteo_to_features(weather)
                result = predict_risk(model, features, "OpenMeteo")

                if result is None:
                    st.error("Dados climáticos insuficientes para previsão.")
                else:
                    display_prediction_result(result)


if __name__ == "__main__":
    main()
