/*
 * Geo Fire — Monitoramento de Queimadas (ESP32)
 * Sensores: DHT22, MQ-2 (fumaça), chuva, umidade do solo
 * Saídas: LED + Buzzer para alerta
 */

#include <DHT.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <time.h>

// ── WiFi / Servidor ───────────────────────────────────────────────────
const char* WIFI_SSID  = "Wokwi-GUEST";
const char* WIFI_PASS  = "";
const char* SERVER_URL = "http://host.wokwi.internal:8001/api/sensor";

// ── Pinos ──────────────────────────────────────────────────────────────
constexpr uint8_t PIN_DHT       = 4;
constexpr uint8_t PIN_MQ2       = 34;  // ADC1
constexpr uint8_t PIN_RAIN      = 35;  // ADC1
constexpr uint8_t PIN_SOIL      = 32;  // ADC1
constexpr uint8_t PIN_LED       = 2;
constexpr uint8_t PIN_BUZZER    = 26;

constexpr uint8_t DHT_TYPE      = DHT22;

// ── Limites de alerta ──────────────────────────────────────────────────
constexpr int     SMOKE_THRESHOLD = 1000;
constexpr float   TEMP_THRESHOLD  = 50.0;

// ── Sensores ───────────────────────────────────────────────────────────
DHT dht(PIN_DHT, DHT_TYPE);

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);  // 0–4095

  dht.begin();

  // ── Conexão WiFi (não-bloqueante) ──────────────────────────────────
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Conectando ao WiFi");
  unsigned long wifiStart = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - wifiStart < 10000) {
    Serial.print(".");
    delay(500);
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("\nWiFi conectado! IP: ");
    Serial.println(WiFi.localIP());

    // Sincroniza relógio via NTP (UTC)
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");
    Serial.print("Aguardando NTP...");
    struct tm t;
    int retries = 0;
    while (!getLocalTime(&t) && retries < 10) {
      Serial.print(".");
      delay(500);
      retries++;
    }
    if (retries < 10) {
      Serial.println(" OK");
    } else {
      Serial.println(" falhou — usando millis()");
    }
  } else {
    Serial.println("\nWiFi falhou — modo Serial apenas");
  }

  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  digitalWrite(PIN_LED, LOW);
  digitalWrite(PIN_BUZZER, LOW);
}

// Leitura segura do DHT — retorna 0.0 se isnan
float readDHTTemp() {
  float t = dht.readTemperature();
  return isnan(t) ? 0.0 : t;
}

float readDHTHumidity() {
  float h = dht.readHumidity();
  return isnan(h) ? 0.0 : h;
}

// Inverte e mapeia: ADC alto = seco, ADC baixo = úmido → 0–100%
int analogToPercent(int raw) {
  int inverted = 4095 - raw;
  return map(inverted, 0, 4095, 0, 100);
}

// ── Loop principal ─────────────────────────────────────────────────────
void loop() {
  // Leituras
  float temp      = readDHTTemp();
  float humidity  = readDHTHumidity();
  int   smokeRaw  = analogRead(PIN_MQ2);
  int   rainRaw   = analogRead(PIN_RAIN);
  int   soilRaw   = analogRead(PIN_SOIL);

  int rainPct     = analogToPercent(rainRaw);
  int soilPct     = analogToPercent(soilRaw);

  // Alerta: fumaça alta OU temperatura extrema
  bool alert = (smokeRaw > SMOKE_THRESHOLD) || (temp > TEMP_THRESHOLD);

  digitalWrite(PIN_LED, alert ? HIGH : LOW);
  digitalWrite(PIN_BUZZER, alert ? HIGH : LOW);

  // JSON para dashboard
  struct tm timeinfo;
  char ts[25];
  if (getLocalTime(&timeinfo)) {
    strftime(ts, sizeof(ts), "%Y-%m-%dT%H:%M:%S", &timeinfo);
  } else {
    snprintf(ts, sizeof(ts), "%lu", millis() / 1000);
  }

  String jsonPayload = "{\"timestamp\":\"";
  jsonPayload += ts;
  jsonPayload += "\",\"temperature\":";
  jsonPayload += String(temp, 1);
  jsonPayload += ",\"humidity\":";
  jsonPayload += String(humidity, 1);
  jsonPayload += ",\"precipitation\":";
  jsonPayload += String(rainPct);
  jsonPayload += ",\"soil_moisture\":";
  jsonPayload += String(soilPct);
  jsonPayload += "}";

  // Envia via HTTP se WiFi conectado
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(SERVER_URL);
    http.setTimeout(2000);
    http.addHeader("Content-Type", "application/json");
    int httpCode = http.POST(jsonPayload);
    if (httpCode > 0) {
      Serial.print("HTTP POST -> ");
      Serial.println(httpCode);
    } else {
      Serial.print("HTTP POST falhou: ");
      Serial.println(http.errorToString(httpCode));
    }
    http.end();
  }

  // Sempre imprime no Serial
  Serial.println(jsonPayload);

  // Log legível
  Serial.print("T=");
  Serial.print(String(temp, 1));
  Serial.print(" H=");
  Serial.print(String(humidity, 1));
  Serial.print(" SMK=");
  Serial.print(smokeRaw);
  Serial.print(" RAIN=");
  Serial.print(rainPct);
  Serial.print(" SOIL=");
  Serial.print(soilPct);
  Serial.print(" ALERT=");
  Serial.println(alert ? "SIM" : "NAO");

  delay(2000);
}
