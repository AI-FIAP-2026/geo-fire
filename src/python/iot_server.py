"""
Servidor IoT — FastAPI que recebe dados de sensores ESP32 via HTTP POST
e salva no arquivo data/iot_readings.json para uso pelo dashboard.

Execução standalone: python src/python/iot_server.py
Execução via import: from iot_server import start_server
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ─── Caminho do arquivo de leituras (relativo à raiz do projeto) ─────────────
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
IOT_FILE = DATA_DIR / "iot_readings.json"

# ─── Modelo Pydantic para validação dos dados recebidos ──────────────────────


class SensorReading(BaseModel):
    """Leitura de sensor IoT enviada pelo ESP32."""

    timestamp: str = Field(..., description="Data/hora da leitura (ISO 8601)")
    temperature: float = Field(..., ge=-40, le=80, description="Temperatura em °C")
    humidity: float = Field(..., ge=0, le=100, description="Umidade relativa em %")
    precipitation: float = Field(
        ..., ge=0, le=500, description="Precipitação em mm"
    )
    soil_moisture: float = Field(
        ..., ge=0, le=100, description="Umidade do solo em %"
    )


# ─── App FastAPI ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="Geo Fire IoT Server",
    description="Recebe dados de sensores ESP32 e salva para o dashboard.",
    version="1.0.0",
)

# CORS aberto para desenvolvimento local e Wokwi
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Utilitários de arquivo ──────────────────────────────────────────────────


def _save_reading(reading: dict) -> None:
    """Persiste a leitura mais recente no arquivo JSON (sobrescreve)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IOT_FILE.write_text(
        json.dumps(reading, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ─── Endpoints ───────────────────────────────────────────────────────────────


@app.get("/api/health", tags=["health"])
async def health_check():
    """Verificação de saúde do servidor."""
    return {"status": "running"}


@app.post("/api/sensor", tags=["sensor"])
async def receive_sensor_data(reading: SensorReading):
    """
    Recebe uma leitura de sensor do ESP32 e persiste no arquivo JSON.

    O dashboard lê esse mesmo arquivo para exibir dados IoT em tempo real.

    Se o timestamp não for ISO 8601 válido, usa o horário do servidor.
    """
    data = reading.model_dump()

    # Validação do timestamp: aceita ISO 8601, fallback para horário do servidor
    try:
        datetime.fromisoformat(data["timestamp"])
    except (ValueError, TypeError):
        data["timestamp"] = datetime.now(timezone.utc).isoformat()

    _save_reading(data)
    return {"status": "ok"}


# ─── Função de inicialização (importável pelo dashboard) ─────────────────────


def start_server(host: str = "0.0.0.0", port: int = 8001) -> threading.Thread:
    """
    Inicia o servidor IoT em uma thread separada.

    Uso a partir do dashboard::

        from iot_server import start_server
        start_server()  # roda em background na porta 8001
    """
    import uvicorn

    def _run() -> None:
        uvicorn.run(app, host=host, port=port, log_level="info")

    thread = threading.Thread(target=_run, daemon=True, name="iot-server")
    thread.start()
    return thread


# ─── Execução standalone ─────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🔥 Geo Fire IoT Server — http://0.0.0.0:8001")
    print("   POST /api/sensor  — enviar leitura")
    print("   GET  /api/health  — verificação de saúde")
    start_server()
    # Mantém a thread principal viva
    threading.Event().wait()
