#config
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
        "url": get_env("WEBHOOK_URL", "https://tradingbot-5wgk.onrender.com")
    },

    # ✅ Regular Forex Pairs
    "symbols": [
        "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF", "NZDUSD",
        "USDCAD", "EURJPY", "EURNZD", "AEDCNY", "AUDCAD", "AUDCHF",
        "AUDNZD", "AUDUSD", "CADJPY", "CHFJPY", "EURGBP", "EURJPY"
    ],

    # ✅ OTC Pairs
    "otc_symbols": [
        "EURUSD OTC", "GBPUSD OTC", "USDJPY OTC", "AUDUSD OTC", "EURJPY OTC",
        "NZDUSD OTC", "AUDCAD OTC", "AUDCHF OTC", "GBPJPY OTC", "CADJPY OTC"
    ],

    "timeframes": ["S1", "M1", "M5", "M15", "M30", "H1", "H4", "D1"],

    # ✅ Model retraining triggers after at least N rows
    "min_train_rows": 50,

    "log_level": "INFO",

    "languages": {
        "en": {
            "start": "Welcome! Tap 📈 Start to generate a signal.",
            "choose_mode": "🧭 Choose trading mode:",
            "choose_timeframe": "⏱ Choose a timeframe:",
            "choose_symbol": "💱 Choose a currency pair:",
            "generating": "📡 Generating signal...",
            "progress_generating": "⏳ Please wait, analyzing the market...",
            "no_signal": "⚠️ No signal at this moment.",
            "signal_title": "📡 New Forex Signal Alert!",
            "pair": "Pair",
            "direction": "Direction",
            "strength": "Strength",
            "confidence": "Confidence",
            "entry": "Entry Price",
            "recommend_entry": "Recommended Entry",
            "expire_entry": "Expires At",
            "high": "High",
            "low": "Low",
            "volume": "Volume",
            "payout": "Simulated Payout (92%)",
            "timer": "Action Window: Execute within 1 minute!",
            "refresh": "Refresh",
            "main_menu": "Main menu. Tap 📈 Start to generate a signal.",
            "back": "Back",
            "more": "More",
            "failed_price_data": "⚠️ Failed to retrieve price data.",
            "error": "Error",
            "no_previous_signal": "⚠️ No previous signal to refresh.",
            "bot_running": "✅ Bot is running.\n\n🕐 Timeframe: `{timeframe}`\n💱 Symbol: `{symbol}`",
            "bot_running_no_ctx": "✅ Bot is running.\nℹ️ No signal context found. Use 📈 Start to begin.",
            "force_retraining": "🔁 Force retraining initiated (manual override).",
            "language_set": "🌐 Language set to English ✅",
            "support_contact": "Contact support:",
            # Directions
            "up": "Alta",
            "down": "Baixa",
            "neutral": "Neutro",
            # Strengths
            "strong": "Forte",
            "weak": "Fraco"
        },
        "pt": {
            "start": "Bem-vindo! Toque 📈 Iniciar para gerar um sinal.",
            "choose_mode": "🧭 Escolha o modo de negociação:",
            "choose_timeframe": "⏱ Escolha o timeframe:",
            "choose_symbol": "💱 Escolha o par de moedas:",
            "generating": "📡 Gerando sinal...",
            "progress_generating": "⏳ Aguarde, analisando o mercado...",
            "no_signal": "⚠️ Nenhum sinal neste momento.",
            "signal_title": "📡 Novo Alerta de Sinal Forex!",
            "pair": "Par",
            "direction": "Direção",
            "strength": "Força",
            "confidence": "Confiança",
            "entry": "Preço de Entrada",
            "recommend_entry": "Entrada Recomendada",
            "expire_entry": "Expira em",
            "high": "Alta",
            "low": "Baixa",
            "volume": "Volume",
            "payout": "Lucro Simulado (92%)",
            "timer": "⏱ Execute dentro de 1 minuto!",
            "refresh": "Atualizar",
            "main_menu": "Menu principal. Toque 📈 Iniciar para gerar um sinal.",
            "back": "Voltar",
            "more": "Mais",
            "failed_price_data": "⚠️ Falha ao obter dados de preço.",
            "error": "Erro",
            "no_previous_signal": "⚠️ Nenhum sinal anterior para atualizar.",
            "bot_running": "✅ Bot em execução.\n\n🕐 Timeframe: `{timeframe}`\n💱 Par: `{symbol}`",
            "bot_running_no_ctx": "✅ Bot em execução.\nℹ️ Nenhum contexto de sinal encontrado. Use 📈 Iniciar para começar.",
            "force_retraining": "🔁 Retreinamento forçado iniciado (sob demanda).",
            "language_set": "🌐 Idioma definido para Português ✅",
            "support_contact": "Contato do suporte:",
            # Direções
            "up": "Alta",
            "down": "Baixa",
            "neutral": "Neutro",
            # Força do sinal
            "strong": "Forte",
            "weak": "Fraco"
        }
    }
