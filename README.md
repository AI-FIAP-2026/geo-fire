# FIAP - Faculdade de Informática e Administração Paulista

<p align="center">
<a href="https://www.fiap.com.br/">
  <img src="assets/logo-fiap.png" 
       alt="FIAP - Faculdade de Informática e Administração Paulista" 
       width="40%">
</a>
</p>

<br>

# Geo Fire — Monitoramento Inteligente de Queimadas

> ***QUERO CONCORRER***

## Grupo Minervah

## 👨‍🎓 Integrantes: 
- <a href="https://github.com/NeuralXP">Heitor Exposito de Sousa - RM 566013</a>
- <a href="https://github.com/MarcoR-S">Marco Antonio Rodrigues Siqueira - RM 569975</a>
- <a href="https://github.com/nadnakvie">Nadia Nakamura Vieira - RM 568906</a> 
- <a href="https://github.com/optimizasavings-byte">Rafael Bassani - RM 569930</a> 
- <a href="https://github.com/ViniciusX22">Vinicius Xavier da Silva - RM 572108</a>

## 📜 Descrição

O **Geo Fire** é um sistema híbrido de monitoramento ambiental desenvolvido para a Global Solution 2026.1 (Tema: Economia Espacial). A solução visa reduzir a defasagem temporal entre a detecção espacial e a ação em campo no combate aos incêndios florestais e queimadas agrícolas. 

Para isso, o ecossistema cruza dados abertos de satélites da **NASA (FIRMS)** com históricos meteorológicos do **OpenMeteo**. Modelos de inteligência artificial (RandomForest e K-Means) processam essas bases para classificar riscos e delimitar zonas de urgência. Em terra, dispositivos **IoT de baixo custo (ESP32)** instalados nas fazendas atuam não apenas na coleta em tempo real das condições de solo e ar, mas disparam alertas imediatos em campo, servindo como uma primeira linha de defesa robusta baseada em Edge Computing.

## 📁 Estrutura de pastas

Dentre os arquivos e pastas presentes na raiz do projeto, definem-se:

- <b>docs</b>: Pasta contendo a documentação completa do projeto (`Geo Fire - Monitoramento Inteligente de Queimadas.pdf`).
- <b>src</b>: Todo o código fonte desenvolvido, incluindo:
  - `/python`: Scripts de coleta e enriquecimento de dados via API (`collect_weather.py`), Notebooks de ML exploratório (`analise_firms.ipynb`), Servidor IoT em FastAPI e o Dashboard interativo via Streamlit.
  - `/r`: Scripts voltados para estatística não-supervisionada (`kmeans_risco.R`).
- <b>esp32</b>: Contém o firmware desenvolvido em C++ (`src/firmware.ino`) e os esquemas de simulação do circuito no Wokwi (`diagram.json`).
- <b>data</b>: Contém os dados utilizados, como extrações brutas do FIRMS em formato CSV e os dataframes enriquecidos.
- <b>assets</b>: Imagens, fluxogramas, gráficos da EDA e o print do modelo lógico de banco de dados (MER 3FN).

## 📎 Links

- <b>Vídeo (Demo):</b> https://youtu.be/JCbrSeO46HI
- <b>Documentação Completa:</b> `docs/Geo Fire - Monitoramento Inteligente de Queimadas.pdf`

## 🔧 Como executar o código

O projeto possui três frentes distintas de execução. Abaixo, o passo a passo para rodar cada uma delas:

### 1. Dashboard e Pipeline de ML (Python)

Requisitos: Python 3.11+.

```bash
# Clone o repositório
git clone https://github.com/AI-FIAP-2026/geo-fire.git
cd geo-fire

# Instale as dependências (Pandas, Scikit-learn, Streamlit, FastAPI, etc.)
pip install -r requirements.txt

# Rodar a aplicação Web / Dashboard:
streamlit run src/python/dashboard.py
```

### 2. Edge Computing / IoT (ESP32 via Wokwi)

Recomendamos o uso do **VS Code** para testar a integração contínua do firmware.

1. Instale as extensões **Wokwi Simulator** e **PlatformIO IDE** no seu VS Code.
2. Abra a pasta específica `esp32` no VS Code (ou adicione-a ao seu workspace).
3. Abra o arquivo `esp32/diagram.json` e clique no botão Play do simulador Wokwi.
4. Você poderá alterar os potenciômetros (Chuva e Solo), o MQ-2 e o DHT22. O ESP32 enviará os dados diretamente para a porta `:8001` da sua máquina (onde o `iot_server.py` deve estar rodando).

### 3. Estatística Espacial e Clusters (R)

Requisitos: Linguagem R instalada e acessível no PATH. Bibliotecas `ggplot2` e `cluster` serão instaladas automaticamente se ausentes.

```bash
cd geo-fire
Rscript src/r/kmeans_risco.R
```
Isso recalculará os centróides e salvará o gráfico na pasta `assets/`.

## 🗃 Histórico de lançamentos

* 1.0.0 - 09/06/2026 (Release Global Solution)
* 0.2.0 - 08/06/2026
* 0.1.0 - 01/06/2026

---

## 📋 Licença

<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1"><p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="https://github.com/SabrinaOtoni/TEMPLATE-FIAP-GRAD-ON-IA">MODELO GIT FIAP</a> por <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://fiap.com.br">FIAP</a> está licenciado sobre <a href="http://creativecommons.org/licenses/by/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">Attribution 4.0 International</a>.</p>
