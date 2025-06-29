#serve para importar os dados do candlestick_patterns.py
from config import CONFIG
from strategy.candlestick_patterns import detect_patterns

class CandlestickStrategy:
    def generate_signal(self, data):
        candles = data.get("history", [])
        if len(candles) < 3:
            return None

        patterns = detect_patterns(candles)
        for pattern in reversed(patterns):
            if pattern in CONFIG["candlestick_patterns"]["reversal_up"]:
                return {"signal": "up", "pattern": pattern}
            if pattern in CONFIG["candlestick_patterns"]["reversal_down"]:
                return {"signal": "down", "pattern": pattern}
            if pattern in CONFIG["candlestick_patterns"]["neutral"]:
                return {"signal": "neutral", "pattern": pattern}
        return None
