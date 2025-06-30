# TradingBot

[ENGLISH BELOW]

---

## 📊 TradingBot — Automação Completa para Coleta, Treinamento e Sinais de Trading

Projeto robusto para automação de coleta de dados de mercado, treinamento periódico de modelos de machine learning e geração de sinais em tempo real para Forex e OTC. Inclui integração com Google Drive, Telegram e múltiplos provedores de dados.

---

## 🚀 Principais Funcionalidades

- **Coleta automática de dados**: Baixa candles de múltiplos símbolos e timeframes usando Dukascopy, TwelveData, Tiingo, Polygon.
- **Armazenamento seguro e incremental**: Históricos de candles .csv e modelos .pkl versionados e sincronizados com Google Drive.
- **Engenharia de features e treinamento**: Pipeline de ML com XGBoost, indicadores técnicos, padrões de velas e split temporal.
- **Retreinamento periódico e inteligente**: Dispara treinamentos automáticos conforme novos dados chegam, com controle por intervalo.
- **Geração de sinais e integração com Telegram**: Envia sinais ricos e detalhados para canais/grupos, com suporte multilíngue.
- **Gerenciamento de múltiplos modelos**: Um modelo para cada par/timeframe, otimizando performance e controle.
- **Painel e webhook prontos para integração**: API e bot para orquestração, comandos e acompanhamento remoto.

---

## 📂 Estrutura dos Principais Diretórios/Arquivos

```
.
├── data/
│   ├── google_drive_client.py   # Cliente Google Drive (upload/download incremental, OAuth2)
│   ├── dukascopy_client.cjs     # Cliente Node para dados históricos Dukascopy
│   ├── data_client.py           # Fallback client para múltiplos provedores
│   └── *.csv                    # Arquivos históricos de candles (por par/timeframe)
├── models/
│   └── model_<par>_<tf>_<ts>.pkl # Modelos treinados (um por par/timeframe)
├── strategy/
│   ├── autotrainer.py           # Orquestrador principal (coleta, treino, upload)
│   ├── train_model_historic.py  # Pipeline de treinamento de modelos ML
│   └── ...                     # Utilitários de ML, engenharia de features, etc
├── messaging/
│   └── telegram_bot.py          # Bot Telegram para sinais/triggers
├── config.py                    # Parâmetros do projeto e variáveis de ambiente
├── requirements.txt             # Dependências Python
├── package.json                 # Dependências Node.js para dukascopy-node
├── credentials.json             # Credenciais Google OAuth2 (pessoal)
├── token.json                   # Token OAuth2 gerado após login (não versionar!)
├── render.yaml                  # Deploy no Render.com
├── .env                         # Variáveis de ambiente
└── README.md                    # Este arquivo
```

---

## ✅ Como Rodar Localmente

### 1. **Pré-requisitos**
- Python 3.11+
- Node.js 20+
- [Google Cloud OAuth2 Client ID](https://console.cloud.google.com/apis/credentials) (Desktop app)
- Telegram Bot Token

### 2. **Instale dependências**
```bash
pip install -r requirements.txt
npm install --prefix data dukascopy-node --save
```

### 3. **Configure variáveis**
- Crie/edite `.env` com suas chaves de API.

### 4. **Configuração Google Drive**
- Baixe o `credentials.json` (OAuth Client ID) do Google Cloud Console.
- Rode qualquer script que use o Drive (ex: `python data/google_drive_client.py`) para autenticar no navegador e gerar `token.json`.

### 5. **Rodando Autotrainer**
```bash
python -m strategy.autotrainer
```

### 6. **Rodando o Bot Telegram**
```bash
python server.py
```
ou conforme seu framework web.

### 7. **Deploy no Render**
- Veja o arquivo `render.yaml`. Suba o projeto e configure as variáveis de ambiente.

---

## ⚙️ Principais Fluxos

### 1. **Coleta e Enriquecimento de Dados**

- O `autotrainer` busca candles periodicamente de múltiplos provedores.
- Mescla incrementalmente novos candles em arquivos `.csv` por par/timeframe.
- Sincroniza e faz upload incremental desses arquivos para Google Drive.

### 2. **Treinamento de Modelos**

- A cada ciclo (ou sempre que há dados novos suficientes), dispara o pipeline de treino.
- Um modelo XGBoost é treinado para cada par/timeframe, salvo em `models/`.
- Modelos são versionados pelo timestamp e enviados ao Google Drive.

### 3. **Sinais e Bot**

- O bot Telegram processa comandos, gera sinais em tempo real, responde a triggers e envia mensagens ricas.
- Suporte multilíngue (PT/EN).
- Webhook configurável para integração externa.

---

## 🔐 Observações de Segurança

- **NUNCA** faça commit de `token.json` ou `.env` com chaves reais!
- Proteja suas credenciais do Google, APIs e Telegram.

---

## 🏆 Créditos e Licença

- Desenvolvido por [@kenbreu](https://github.com/Ken89br)
- Licença: MIT

---

---

# 🇬🇧 TradingBot — Complete Automation for Market Data, Training & Trading Signals

A robust project for fully automated financial data collection, periodic machine learning model training, and real-time signal generation for Forex and OTC. Integrates with Google Drive, Telegram, and multiple data providers.

---

## 🚀 Main Features

- **Automatic data collection**: Downloads candles for multiple pairs/timeframes using Dukascopy, TwelveData, Tiingo, Polygon.
- **Secure, incremental storage**: .csv and .pkl historical data and models, versioned and synced with Google Drive.
- **Feature engineering & ML training**: XGBoost pipeline with technical indicators, candlestick patterns, and time series split.
- **Smart periodic retraining**: Triggers training automatically as new data arrive, with interval control.
- **Signal generation & Telegram integration**: Sends rich, detailed signals to channels/groups, multilingual support.
- **Multiple model management**: One model per pair/timeframe for best performance and control.
- **Ready-to-integrate webhook and dashboard**: API and bot for orchestration, commands, and remote monitoring.

---

## 📂 Main Directory/File Structure

```
.
├── data/
│   ├── google_drive_client.py   # Google Drive client (incremental upload/download, OAuth2)
│   ├── dukascopy_client.cjs     # Node client for Dukascopy historical data
│   ├── data_client.py           # Fallback client for multiple providers
│   └── *.csv                    # Historical candle files (per pair/timeframe)
├── models/
│   └── model_<pair>_<tf>_<ts>.pkl # Trained models (one per pair/timeframe)
├── strategy/
│   ├── autotrainer.py           # Main orchestrator (collection, training, upload)
│   ├── train_model_historic.py  # ML model training pipeline
│   └── ...                     # ML utilities, feature engineering, etc
├── messaging/
│   └── telegram_bot.py          # Telegram bot for signals/triggers
├── config.py                    # Project parameters and environment variables
├── requirements.txt             # Python dependencies
├── package.json                 # Node.js dependencies for dukascopy-node
├── credentials.json             # Google OAuth2 credentials (personal)
├── token.json                   # OAuth2 token generated after login (do not commit!)
├── render.yaml                  # Render.com deployment
├── .env                         # Environment variables
└── README.md                    # This file
```

---

## ✅ How to Run Locally

### 1. **Requirements**
- Python 3.11+
- Node.js 20+
- [Google Cloud OAuth2 Client ID](https://console.cloud.google.com/apis/credentials) (Desktop app)
- Telegram Bot Token

### 2. **Install dependencies**
```bash
pip install -r requirements.txt
npm install --prefix data dukascopy-node --save
```

### 3. **Configure variables**
- Create/edit your `.env` with your API keys.

### 4. **Google Drive Setup**
- Download `credentials.json` (OAuth Client ID) from Google Cloud Console.
- Run any Drive-using script (e.g. `python data/google_drive_client.py`) to authenticate in your browser and generate `token.json`.

### 5. **Run Autotrainer**
```bash
python -m strategy.autotrainer
```

### 6. **Run Telegram Bot**
```bash
python server.py
```
or according to your web framework.

### 7. **Render Deployment**
- See `render.yaml`. Deploy and set environment variables accordingly.

---

## ⚙️ Key Workflows

### 1. **Data Collection & Enrichment**

- The autotrainer periodically fetches candles from multiple data sources.
- Incrementally merges new candles into `.csv` files per pair/timeframe.
- Syncs and uploads these files to Google Drive.

### 2. **Model Training**

- On each cycle (or when enough new data is available), triggers the ML pipeline.
- A separate XGBoost model is trained for each pair/timeframe, saved to `models/`.
- Models are timestamped and uploaded to Google Drive.

### 3. **Signals & Bot**

- The Telegram bot processes commands, generates real-time signals, responds to triggers, and sends rich messages.
- Multilingual support (EN/PT).
- Configurable webhook for external integration.

---

## 🔐 Security Notes

- **NEVER** commit your real `token.json` or `.env` with secrets!
- Protect your Google, API, and Telegram credentials.

---

## 🏆 Credits & License

- Developed by [@kenbreu](https://github.com/Ken89br)
- License: MIT
