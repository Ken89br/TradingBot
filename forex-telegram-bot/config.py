# config.py
import os

CONFIG = {
    "telegram": {
        "enabled": True,
        "bot_token": os.getenv("TELEGRAM_BOT_TOKEN"),
        "chat_id": os.getenv("TELEGRAM_CHAT_ID"),
        "admin_id": os.getenv("TELEGRAM_ADMIN_ID")
    },
    "support": {
        "username": "@kenbreu"
    },
    "data_feed": "twelvedata",
    "twelvedata": {
        "api_key": os.getenv("TWELVE_DATA_API_KEY"),
        "base_url": "https://api.twelvedata.com",
        "default_interval": "1min"
    },
    "symbols": [
        "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CHF", "NZD/USD", "USDCAD", "EURJPY",
        "EUR/NZD", "AED/CNY OTC", "AUD/CAD OTC", "AUD/CHF OTC", "AUD/NZD OTC", "AUD/USD OTC",
        "CAD/JPY OTC", "CHF/JPY OTC", "EUR/GBP OTC", "EUR/JPY OTC"
    ],
    "timeframes": ["M1", "M5", "M15", "M30", "H1", "H4", "D1"],
    "log_level": "INFO"
    },
    "languages": {
    "en": {
        "start": "Welcome! Tap 📈 Start to generate a signal.",
        "choose_timeframe": "⏱ Choose a timeframe:",
        "choose_symbol": "💱 Choose a currency pair:",
        "generating": "📡 Generating signal...",
        "no_signal": "⚠️ No signal at this moment.",
        "signal_title": "📡 New Forex Signal Alert!",
        "pair": "Pair",
        "direction": "Direction",
        "strength": "Strength",
        "confidence": "Confidence",
        "entry": "Entry Price",
        "recommend": "Recommended Entry",
        "high": "High",
        "low": "Low",
        "volume": "Volume",
        "payout": "Simulated Payout (92%)",
        "timer": "Action Window: Execute within 1 minute!",
        "refresh": "Refresh"
    },
    "pt": {
        "start": "Bem-vindo! Toque 📈 Iniciar para gerar um sinal.",
        "choose_timeframe": "⏱ Escolha o timeframe:",
        "choose_symbol": "💱 Escolha o par de moedas:",
        "generating": "📡 Gerando sinal...",
        "no_signal": "⚠️ Nenhum sinal neste momento.",
        "signal_title": "📡 Novo Alerta de Sinal Forex!",
        "pair": "Par",
        "direction": "Direção",
        "strength": "Força",
        "confidence": "Confiança",
        "entry": "Preço de Entrada",
        "recommend": "Entrada Recomendada",
        "high": "Alta",
        "low": "Baixa",
        "volume": "Volume",
        "payout": "Lucro Simulado (92%)",
        "timer": "⏱ Execute dentro de 1 minuto!",
        "refresh": "Atualizar"
    }
    "webhook": {
    "url": "https://your-render-app.onrender.com"
}
