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
}
