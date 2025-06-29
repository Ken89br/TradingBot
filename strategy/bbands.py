#strategy/bbands.py
import numpy as np
from collections import deque
from config import CONFIG
from strategy.candlestick_patterns import detect_patterns, PATTERN_STRENGTH

class BollingerStrategy:
    def __init__(self, config=None):
        self.period = config.get('period', 20) if config else 20
        self.std_dev = config.get('std_dev', 2.0) if config else 2.0
        self.min_history = self.period + 5        
        self.candle_lookback = config.get('candle_lookback', 3) if config else 3
        self.min_confidence = config.get('min_confidence', 70) if config else 70
        self.pattern_boost = config.get('pattern_boost', 0.2) if config else 0.2

        self.price_buffer = deque(maxlen=self.period * 2)
        self.candle_buffer = deque(maxlen=self.candle_lookback + 1)

    def _calculate_bands(self):
        if len(self.price_buffer) < self.period:
            return None, None, None
        prices = np.array(self.price_buffer, dtype=np.float64)
        sma = np.mean(prices[-self.period:])
        std = np.std(prices[-self.period:])
        return sma + (self.std_dev * std), sma - (self.std_dev * std), sma

    def _apply_pattern_boost(self, signal, patterns, direction):
        if not patterns:
            return signal
        # Usa padrões do CONFIG
        if direction == "up":
            relevant_patterns = CONFIG["candlestick_patterns"]["reversal_up"]
        elif direction == "down":
            relevant_patterns = CONFIG["candlestick_patterns"]["reversal_down"]
        else:
            relevant_patterns = []
        pattern_strength = sum(
            PATTERN_STRENGTH.get(p, 0) 
            for p in patterns 
            if p in relevant_patterns
        )
        if pattern_strength > 0:
            signal["confidence"] = min(
                95, 
                signal.get("confidence", 70) + int(pattern_strength * 20 * self.pattern_boost)
            )
            signal["patterns"] = patterns
            signal["pattern_strength"] = pattern_strength
        return signal

    def generate_signal(self, data):
        try:
            candles = data.get("history", [])
            if len(candles) < self.min_history:
                return None

            current_candle = candles[-1]
            current_close = float(current_candle["close"])
            self.price_buffer.append(current_close)
            self.candle_buffer.append(current_candle)
            upper, lower, sma = self._calculate_bands()
            if upper is None:
                return None
            patterns = detect_patterns(list(self.candle_buffer)[-self.candle_lookback:])
            signal = None
            band_width = upper - lower

            if current_close < lower:
                signal = {
                    "signal": "up",
                    "price": current_close,
                    "confidence": 75,
                    "distance_from_band": lower - current_close,
                    "band_width": band_width
                }
                signal = self._apply_pattern_boost(signal, patterns, "up")
            elif current_close > upper:
                signal = {
                    "signal": "down",
                    "price": current_close,
                    "confidence": 80,
                    "distance_from_band": current_close - upper,
                    "band_width": band_width
                }
                signal = self._apply_pattern_boost(signal, patterns, "down")
            if signal:
                signal.update({
                    "upper_band": upper,
                    "lower_band": lower,
                    "sma": sma,
                    "recommend_entry": current_close,
                    "recommend_stop": sma,
                    "volume": current_candle.get("volume", 0)
                })
                if signal["confidence"] >= self.min_confidence:
                    return signal
            return None
        except Exception as e:
            print(f"BollingerStrategy error: {e}")
            return None
