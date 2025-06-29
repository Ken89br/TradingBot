import numpy as np
from config import CONFIG
from strategy.candlestick_patterns import detect_patterns, PATTERN_STRENGTH

class SMACrossStrategy:
    def __init__(self, short_period=5, long_period=10, min_history=20, confirmation_candles=3, candle_lookback=3, pattern_boost=0.2):
        self.short_period = short_period
        self.long_period = long_period
        self.min_history = max(min_history, long_period)
        self.confirmation_candles = confirmation_candles
        self.candle_lookback = candle_lookback
        self.pattern_boost = pattern_boost

    def calculate_sma(self, closes, period):
        if len(closes) < period:
            return None
        return np.mean(closes[-period:])

    def generate_signal(self, data):
        try:
            candles = data.get("history", [])
            if len(candles) < max(self.min_history, self.candle_lookback):
                return None

            closes = [float(c["close"]) for c in candles]

            sma_short = self.calculate_sma(closes, self.short_period)
            sma_long = self.calculate_sma(closes, self.long_period)

            if sma_short is None or sma_long is None:
                return None

            current_cross = sma_short - sma_long
            signal = None

            if current_cross > 0 and (getattr(self, 'trend', None) != "up" or not getattr(self, 'trend', None)):
                if len(candles) >= self.confirmation_candles:
                    prev_closes = [float(c["close"]) for c in candles[-self.confirmation_candles-1:-1]]
                    if all(c > self.calculate_sma(prev_closes, self.short_period) for c in closes[-self.confirmation_candles:]):
                        signal = {"signal": "up", "type": "sma_cross"}
                        self.trend = "up"

            elif current_cross < 0 and (getattr(self, 'trend', None) != "down" or not getattr(self, 'trend', None)):
                if len(candles) >= self.confirmation_candles:
                    prev_closes = [float(c["close"]) for c in candles[-self.confirmation_candles-1:-1]]
                    if all(c < self.calculate_sma(prev_closes, self.short_period) for c in closes[-self.confirmation_candles:]):
                        signal = {"signal": "down", "type": "sma_cross"}
                        self.trend = "down"

            if signal:
                patterns = detect_patterns(candles[-self.candle_lookback:])
                signal = self._apply_pattern_boost(signal, patterns)
                signal.update({
                    "sma_short": sma_short,
                    "sma_long": sma_long,
                    "spread": abs(sma_short - sma_long),
                    "confidence": self._calculate_confidence(closes),
                    "price": closes[-1],
                    "volume": candles[-1].get("volume", 0)
                })
                return signal

            return None

        except Exception as e:
            print(f"Error in SMACrossStrategy: {e}")
            return None

    def _apply_pattern_boost(self, signal, patterns):
        if not signal or not patterns:
            return signal
        direction = signal["signal"]
        # Usa padrões de continuação e neutros
        if direction == "up":
            confirm_patterns = CONFIG["candlestick_patterns"]["trend_up"] + CONFIG["candlestick_patterns"]["neutral"]
        else:
            confirm_patterns = CONFIG["candlestick_patterns"]["trend_down"] + CONFIG["candlestick_patterns"]["neutral"]

        pattern_strength = 0
        for pattern in patterns:
            if pattern in confirm_patterns:
                pattern_strength += PATTERN_STRENGTH.get(pattern, 0.1)

        if pattern_strength > 0:
            boost = int(pattern_strength * 20 * self.pattern_boost)
            signal["confidence"] = min(100, signal.get("confidence", 70) + boost)
            signal["patterns"] = patterns
            signal["pattern_strength"] = pattern_strength

        return signal

    def _calculate_confidence(self, closes):
        price_change = closes[-1] - closes[-5]
        spread = abs(self.calculate_sma(closes, self.short_period) - self.calculate_sma(closes, self.long_period))
        price_factor = min(max(price_change / (closes[-5] * 0.01), -2), 2)
        spread_factor = spread / (closes[-1] * 0.01)
        confidence = 50 + (20 * price_factor) + (30 * min(spread_factor, 1))
        return min(max(int(confidence), 0), 100)
