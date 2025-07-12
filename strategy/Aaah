from strategy.candlestick_patterns import detect_candlestick_patterns

class CandlestickStrategy:
    def __init__(self):
        # Padrões de reversão altista clássicos (buy)
        self.bullish_patterns = [
            "bullish_engulfing",
            "hammer",
            "morning_star",
            "piercing_line",
            "three_white_soldiers",
            "bullish_harami",
            "tweezer_bottom",
            "marubozu",
            "dragonfly_doji"  # Adicionado
        ]
        # Padrões de reversão baixista clássicos (sell)
        self.bearish_patterns = [
            "bearish_engulfing",
            "shooting_star",
            "hanging_man",
            "evening_star",
            "dark_cloud_cover",
            "three_black_crows",
            "bearish_harami",
            "tweezer_top",
            "marubozu"
        ]
        # Indecisão (alerta, normalmente não opera)
        self.indecision_patterns = [
            "doji",
            "spinning_top"  # Adicionado (Peão)
        ]

    def generate_signal(self, data):
        candles = data.get("history", [])
        if len(candles) < 3:
            return None

        patterns = detect_candlestick_patterns(candles)
        # Sinal de compra
        for pattern in reversed(patterns):
            if pattern in self.bullish_patterns:
                return {"signal": "up", "pattern": pattern}
        # Sinal de venda
        for pattern in reversed(patterns):
            if pattern in self.bearish_patterns:
                return {"signal": "down", "pattern": pattern}
        # Indecisão
        for pattern in reversed(patterns):
            if pattern in self.indecision_patterns:
                return {"signal": "neutral", "pattern": pattern}
        return None
