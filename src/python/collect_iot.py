"""
Simulação de leituras de sensores IoT (ESP32 + DHT22 + MQ-2).

Gera valores aleatórios realistas de temperatura, umidade, precipitação
e umidade do solo, salvando-os em JSON para uso pelo dashboard Streamlit.

Uso:
    python src/python/collect_iot.py
"""

import json
import random
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
IOT_OUTPUT = DATA_DIR / "iot_readings.json"


@dataclass
class IoTSensorReading:
    """Leitura simulada de sensores IoT para monitoramento de queimadas."""

    timestamp: str
    temperature: float
    humidity: float
    precipitation: float
    soil_moisture: float


def generate_reading() -> IoTSensorReading:
    """Gera uma leitura aleatória realista de sensores IoT.

    Faixas simuladas (áreas propensas a queimadas):
    - temperature: 20-45°C
    - humidity: 10-90%
    - precipitation: 0-30mm
    - soil_moisture: 0-100%

    Returns:
        Objeto IoTSensorReading com os valores gerados.
    """
    return IoTSensorReading(
        timestamp=datetime.now().isoformat(),
        temperature=round(random.uniform(20.0, 45.0), 1),
        humidity=round(random.uniform(10.0, 90.0), 1),
        precipitation=round(random.uniform(0.0, 30.0), 1),
        soil_moisture=round(random.uniform(0.0, 100.0), 1),
    )


def save_reading(reading: IoTSensorReading) -> Path:
    """Salva a leitura IoT em formato JSON.

    Args:
        reading: Leitura do sensor a ser persistida.

    Returns:
        Caminho do arquivo salvo.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IOT_OUTPUT.write_text(json.dumps(asdict(reading), indent=2, ensure_ascii=False))
    return IOT_OUTPUT


def main() -> None:
    """Ponto de entrada: gera leitura, imprime e salva em JSON."""
    reading = generate_reading()

    print(f"[IoT] Leitura simulada gerada em {reading.timestamp}")
    print(f"  Temperatura:    {reading.temperature} °C")
    print(f"  Umidade:        {reading.humidity} %")
    print(f"  Precipitação:   {reading.precipitation} mm")
    print(f"  Umidade solo:   {reading.soil_moisture} %")

    path = save_reading(reading)
    print(f"\n[IoT] Dados salvos em: {path}")


if __name__ == "__main__":
    main()
