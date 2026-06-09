"""
Coleta de clima histórico via OpenMeteo para focos FIRMS.

Para cada registro de foco de incêndio no dataset FIRMS, busca as condições
climáticas históricas (temperatura, umidade, vento, precipitação) na API
do OpenMeteo e gara um dataset enriquecido para treinamento do modelo ML.

API: https://archive-api.open-meteo.com/v1/archive (gratuita, sem API key)
"""

import time
import logging
from pathlib import Path

import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

OPENMETEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Colunas diárias solicitadas ao OpenMeteo
DAILY_PARAMS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "wind_speed_10m_max",
    "precipitation_sum",
]

# Coluna horária que precisamos agregar manualmente
HOURLY_PARAMS = [
    "relative_humidity_2m",
    "soil_moisture_0_to_7cm",
]


def fetch_weather(lat: float, lon: float, date: str, retries: int = 3) -> dict | None:
    """Busca clima histórico para uma coordenada/data via OpenMeteo.

    Args:
        lat: Latitude (WGS84).
        lon: Longitude (WGS84).
        date: Data no formato YYYY-MM-DD.
        retries: Número de tentativas em caso de falha.

    Returns:
        Dict com as variáveis climáticas ou None em caso de erro.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": date,
        "end_date": date,
        "daily": ",".join(DAILY_PARAMS),
        "hourly": ",".join(HOURLY_PARAMS),
        "timezone": "auto",
    }

    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(OPENMETEO_ARCHIVE_URL, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            result = {}

            # Dados diários (1 valor por dia)
            daily = data.get("daily", {})
            for param in DAILY_PARAMS:
                values = daily.get(param, [None])
                result[param] = values[0] if values else None

            # Dados horários → agregar (média para umidade e umidade do solo)
            hourly = data.get("hourly", {})
            for param in HOURLY_PARAMS:
                values = hourly.get(param, [])
                valid = [v for v in values if v is not None]
                if valid:
                    result[param] = sum(valid) / len(valid)
                else:
                    result[param] = None

            return result

        except requests.exceptions.RequestException as e:
            logger.warning(f"Tentativa {attempt}/{retries} falhou para ({lat}, {lon}, {date}): {e}")
            if attempt < retries:
                time.sleep(2 ** attempt)  # backoff exponencial

    return None


def collect_weather_for_dataset(df: pd.DataFrame, delay: float = 0.5) -> pd.DataFrame:
    """Busca clima histórico para todos os registros do DataFrame.

    Agrupa por (lat_arredondada, lon_arredondada, data) para reduzir
    o número de requests à API.

    Args:
        df: DataFrame com colunas latitude, longitude, acq_date.
        delay: Delay entre requests (segundos) para respeitar rate limit.

    Returns:
        DataFrame com colunas climáticas adicionadas.
    """
    # Criar chaves de agrupamento (arredondar para 2 casas)
    df = df.copy()
    df["_lat_round"] = df["latitude"].round(2)
    df["_lon_round"] = df["longitude"].round(2)

    # Encontrar combinações únicas
    unique_keys = df[["_lat_round", "_lon_round", "acq_date"]].drop_duplicates()
    n_unique = len(unique_keys)
    logger.info(f"Total de combinações únicas (lat, lon, data): {n_unique}")

    # Buscar clima para cada combinação única
    weather_cache: dict[tuple, dict] = {}
    failed_count = 0

    for i, (_, row) in enumerate(unique_keys.iterrows(), 1):
        lat = row["_lat_round"]
        lon = row["_lon_round"]
        date = row["acq_date"]
        key = (lat, lon, date)

        if key in weather_cache:
            continue

        logger.info(f"[{i}/{n_unique}] Buscando clima para lat={lat}, lon={lon}, date={date}...")

        weather = fetch_weather(lat, lon, date)
        if weather is not None:
            weather_cache[key] = weather
            logger.info(f"  → temp_mean={weather.get('temperature_2m_mean')}°C, "
                        f"humidity={weather.get('relative_humidity_2m')}%, "
                        f"wind={weather.get('wind_speed_10m_max')}km/h")
        else:
            weather_cache[key] = {p: None for p in DAILY_PARAMS + HOURLY_PARAMS}
            failed_count += 1
            logger.warning(f"  → Falha ao buscar dados para ({lat}, {lon}, {date})")

        # Rate limiting
        if i < n_unique:
            time.sleep(delay)

    logger.info(f"Coleta concluída: {len(weather_cache)} combinações, {failed_count} falhas")

    # Mapear dados climáticos de volta para o DataFrame original
    weather_cols = DAILY_PARAMS + HOURLY_PARAMS
    for col in weather_cols:
        df[col] = df.apply(
            lambda row: weather_cache.get(
                (row["_lat_round"], row["_lon_round"], row["acq_date"]), {}
            ).get(col),
            axis=1,
        )

    # Renomear colunas para o padrão do projeto
    df = df.rename(columns={
        "temperature_2m_max": "temp_max",
        "temperature_2m_min": "temp_min",
        "temperature_2m_mean": "temp_mean",
        "relative_humidity_2m": "humidity",
        "wind_speed_10m_max": "wind_speed",
        "precipitation_sum": "precipitation",
        "soil_moisture_0_to_7cm": "soil_moisture",
    })

    # Remover colunas auxiliares
    df = df.drop(columns=["_lat_round", "_lon_round"])

    return df


def main():
    """Função principal: carrega FIRMS, busca clima, salva dataset enriquecido."""
    # Detectar caminho do dataset
    candidates = [
        Path("data/firms_brasil.csv"),
        Path("../../data/firms_brasil.csv"),
        Path("../data/firms_brasil.csv"),
    ]
    data_path = next((p for p in candidates if p.exists()), candidates[0])

    logger.info(f"Carregando dataset FIRMS de: {data_path}")
    df = pd.read_csv(data_path)
    logger.info(f"Dataset FIRMS: {df.shape[0]} linhas, {df.shape[1]} colunas")

    # Buscar clima histórico
    logger.info("Iniciando coleta de clima histórico via OpenMeteo...")
    df_enriched = collect_weather_for_dataset(df, delay=0.5)

    # Salvar dataset enriquecido
    output_path = data_path.parent / "firms_com_clima.csv"
    df_enriched.to_csv(output_path, index=False)

    logger.info(f"Dataset enriquecido salvo em: {output_path}")
    logger.info(f"Shape final: {df_enriched.shape[0]} linhas, {df_enriched.shape[1]} colunas")
    logger.info(f"Colunas: {list(df_enriched.columns)}")

    # Estatísticas de completude
    weather_cols = ["temp_max", "temp_min", "temp_mean", "humidity", "wind_speed",
                    "precipitation", "soil_moisture"]
    logger.info("\nCompletude dos dados climáticos:")
    for col in weather_cols:
        if col in df_enriched.columns:
            pct = df_enriched[col].notna().mean() * 100
            logger.info(f"  {col}: {pct:.1f}% preenchido")


if __name__ == "__main__":
    main()
