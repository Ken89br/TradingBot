import numpy as np
from config import CONFIG
from strategy.candlestick_patterns import detect_patterns, PATTERN_STRENGTH

class EMAStrategy:
    def __init__(self, short_period=9, long_period=21, candle_lookback=3, pattern_boost=0.2):
        self.short_period = short_period
        self.long_period = long_period
        self.min_data_points = max(short_period, long_period) + 1
        self.candle_lookback = candle_lookback
        self.pattern_boost = pattern_boost

    def calculate_ema(self, prices, period):
        if len(prices) < period:
            return [None] * len(prices)
        prices = np.array(prices)
        ema = np.zeros_like(prices)
        k = 2 / (period + 1)
        ema[period-1] = np.mean(prices[:period])
        for i in range(period, len(prices)):
            ema[i] = (prices[i] - ema[i-1]) * k + ema[i-1]
        ema[:period-1] = None
        return ema.tolist()

    def generate_signal(self, data):
        try:
            candles = data.get("history", [])
            if len(candles) < max(self.min_data_points, self.candle_lookback):
                return None

            closes = [c["close"] for c in candles[-self.min_data_points:]]
            short_ema = self.calculate_ema(closes, self.short_period)
            long_ema = self.calculate_ema(closes, self.long_period)

            if None in [short_ema[-2], short_ema[-1], long_ema[-2], long_ema[-1]]:
                return None

            prev_cross = short_ema[-2] - long_ema[-2]
            current_cross = short_ema[-1] - long_ema[-1]
            signal = None

            if prev_cross < 0 and current_cross > 0:
                signal = {
                    "signal": "up",
                    "indicator": "ema_crossover",
                    "short_ema": short_ema[-1],
                    "long_ema": long_ema[-1],
                    "confidence": self._calculate_confidence(abs(current_cross))
                }
            elif prev_cross > 0 and current_cross < 0:
                signal = {
                    "signal": "down",
                    "indicator": "ema_crossover",
                    "short_ema": short_ema[-1],
                    "long_ema": long_ema[-1],
                    "confidence": self._calculate_confidence(abs(current_cross))
                }

            if signal:
                patterns = detect_patterns(candles[-self.candle_lookback:])
                signal = self._apply_pattern_boost(signal, patterns)
                return signal

            return None

        except Exception as e:
            print(f"Erro em EMAStrategy: {e}")
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

    def _calculate_confidence(self, spread):
        normalized_spread = min(spread / (self.short_period * 0.1), 1.0)
        return int(50 + 50 * normalized_spread)
