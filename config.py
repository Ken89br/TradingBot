# config.py
import os
import logging

def get_env(key, default=None, required=False):
    val = os.getenv(key, default)
    if required and val is None:
        raise EnvironmentError(f"Missing required environment variable: {key}")
    return val

CONFIG = {
    "telegram": {
        "enabled": True,
        "bot_token": get_env("TELEGRAM_BOT_TOKEN", required=True),
        "chat_id": get_env("TELEGRAM_CHAT_ID"),
        "admin_id": get_env("TELEGRAM_ADMIN_ID")
    },

    "support": {
        "username": "@kenbreu"
    },

    "webhook": {
        "url": get_env("WEBHOOK_URL", "https://your-render-url.com")
    },

    "symbols": [
        "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF", "NZDUSD",
        "USDCAD", "EURJPY", "EURNZD", "AEDCNY", "AUDCAD", "AUDCHF",
        "AUDNZD", "AUDUSD", "CADJPY", "CHFJPY", "EURGBP", "EURJPY"
    ],

    "timeframes": ["S1", "M1", "M5", "M15", "M30", "H1", "H4", "D1"],

    "log_level": "INFO",

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
    }
}

# Logger
logging.basicConfig(level=getattr(logging, CONFIG["log_level"].upper(), logging.INFO))
