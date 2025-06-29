#strategy/bollinger_breakout.py
import numpy as np
from collections import deque
from config import CONFIG
from strategy.candlestick_patterns import detect_patterns, PATTERN_STRENGTH

class BollingerBreakoutStrategy:
    def __init__(self, config=None):
        self.period = config.get('period', 20) if config else 20
        self.std_dev = config.get('std_dev', 2.0) if config else 2.0
        self.min_history = self.period + 3
        
        self.candle_lookback = config.get('candle_lookback', 3) if config else 3
        self.pattern_boost = config.get('pattern_boost', 0.2) if config else 0.2
        self.min_confidence = config.get('min_confidence', 65) if config else 65
        
        self.price_buffer = deque(maxlen=self.period * 2)
        self.candle_buffer = deque(maxlen=self.candle_lookback + 1)

    def _calculate_bands(self):
        if len(self.price_buffer) < self.period:
            return None, None, None
        prices = np.array(self.price_buffer, dtype=np.float64)
        ma = np.mean(prices[-self.period:])
        std = np.std(prices[-self.period:])
        upper = ma + (self.std_dev * std)
        lower = ma - (self.std_dev * std)
        return upper, lower, ma

    def _apply_pattern_boost(self, signal, patterns):
        if not signal or not patterns:
            return signal
        direction = signal["signal"]
        # Adaptação: usa padrões de reversão do config
        if direction == "call":
            confirm_patterns = CONFIG["candlestick_patterns"]["reversal_up"]
        elif direction == "put":
            confirm_patterns = CONFIG["candlestick_patterns"]["reversal_down"]
        else:
            confirm_patterns = []
        pattern_strength = 0
        for pattern in patterns:
            if pattern in confirm_patterns:
                pattern_strength += PATTERN_STRENGTH.get(pattern, 0.1)
        if pattern_strength > 0:
            boost = int(pattern_strength * 20 * self.pattern_boost)
            signal["confidence"] = min(95, signal["confidence"] + boost)
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
            upper, lower, ma = self._calculate_bands()
            if upper is None:
                return None
            patterns = detect_patterns(list(self.candle_buffer)[-self.candle_lookback:])
            signal = None
            band_width = upper - lower
            band_pct = band_width / ma if ma > 0 else 0
            if current_close < lower and band_pct > 0.01:
                confidence = 70 + min(20, int((lower - current_close) / lower * 1000))
                signal = {
                    "signal": "call",
                    "price": current_close,
                    "confidence": confidence,
                    "band_width": band_width,
                    "distance": lower - current_close
                }
            elif current_close > upper and band_pct > 0.01:
                confidence = 75 + min(20, int((current_close - upper) / upper * 1000))
                signal = {
                    "signal": "put",
                    "price": current_close,
                    "confidence": confidence,
                    "band_width": band_width,
                    "distance": current_close - upper
                }
            if signal:
                signal = self._apply_pattern_boost(signal, patterns)
                signal.update({
                    "upper_band": upper,
                    "lower_band": lower,
                    "middle_band": ma,
                    "recommend_entry": (float(current_candle["high"]) + float(current_candle["low"])) / 2,
                    "recommend_stop": ma,
                    "volume": current_candle.get("volume", 0)
                })
                if signal["confidence"] >= self.min_confidence:
                    return signal
            return None
        except Exception as e:
            print(f"BollingerBreakout error: {e}")
            return None
