#strategy/atr_strategy.py
import numpy as np
from collections import deque
from config import CONFIG
from strategy.candlestick_patterns import detect_patterns, PATTERN_STRENGTH

class ATRStrategy:
    def __init__(self, config=None):
        self.atr_period = config.get('atr_period', 14) if config else 14
        self.multiplier = config.get('multiplier', 1.2) if config else 1.2
        self.min_history = config.get('min_history', self.atr_period + 5) if config else self.atr_period + 5

        self.require_volume = config.get('require_volume', True) if config else True
        self.volume_threshold = config.get('volume_threshold', 1.5) if config else 1.5
        self.min_confidence = config.get('min_confidence', 65) if config else 65

        self.candle_lookback = config.get('candle_lookback', 3) if config else 3
        self.pattern_boost = config.get('pattern_boost', 0.2) if config else 0.2

        self.high_buffer = deque(maxlen=self.atr_period * 2)
        self.low_buffer = deque(maxlen=self.atr_period * 2)
        self.close_buffer = deque(maxlen=self.atr_period * 2)
        self.volume_buffer = deque(maxlen=self.atr_period * 2)
        self.candle_buffer = deque(maxlen=self.candle_lookback + 1)

    def _calculate_atr(self):
        if len(self.high_buffer) < self.min_history:
            return 0

        highs = np.array(self.high_buffer, dtype=np.float64)
        lows = np.array(self.low_buffer, dtype=np.float64)
        closes = np.array(self.close_buffer, dtype=np.float64)

        tr1 = highs[1:] - lows[1:]
        tr2 = np.abs(highs[1:] - closes[:-1])
        tr3 = np.abs(lows[1:] - closes[:-1])
        true_ranges = np.maximum(np.maximum(tr1, tr2), tr3)

        atr = np.mean(true_ranges[-self.atr_period:])
        return atr

    def _apply_pattern_boost(self, signal, patterns, direction):
        if not patterns:
            return signal
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
                signal.get("confidence", 65) + int(pattern_strength * 20 * self.pattern_boost)
            )
            signal["patterns"] = patterns
            signal["pattern_strength"] = pattern_strength
        return signal

    def generate_signal(self, data):
        try:
            candles = data.get("history", [])
            if len(candles) < self.min_history:
                return None

            current = candles[-1]
            self.high_buffer.append(float(current["high"]))
            self.low_buffer.append(float(current["low"]))
            self.close_buffer.append(float(current["close"]))
            self.volume_buffer.append(float(current.get("volume", 0)))
            self.candle_buffer.append(current)

            atr = self._calculate_atr()
            if atr == 0:
                return None

            body_size = abs(float(current["close"]) - float(current["open"]))
            is_bullish = float(current["close"]) > float(current["open"])
            avg_volume = np.mean(self.volume_buffer[-self.atr_period:])
            volume_ok = not self.require_volume or (float(current.get("volume", 0)) > avg_volume * self.volume_threshold)

            patterns = detect_patterns(list(self.candle_buffer)[-self.candle_lookback:])

            signal = None
            if body_size > atr * self.multiplier:
                direction = "up" if is_bullish else "down"

                base_confidence = 70 if direction == "up" else 75
                size_factor = min(20, (body_size / atr - 1) * 10)
                volume_factor = 10 if volume_ok else 0

                signal = {
                    "signal": direction,
                    "atr": round(atr, 5),
                    "body_ratio": round(body_size / atr, 2),
                    "confidence": min(95, base_confidence + size_factor + volume_factor),
                    "volume_ok": volume_ok,
                    "price": float(current["close"])
                }

                signal = self._apply_pattern_boost(signal, patterns, direction)

                if direction == "up":
                    signal.update({
                        "recommend_entry": float(current["close"]),
                        "recommend_stop": float(current["low"]) - atr * 0.5
                    })
                else:
                    signal.update({
                        "recommend_entry": float(current["close"]),
                        "recommend_stop": float(current["high"]) + atr * 0.5
                    })

            return signal if (signal and signal["confidence"] >= self.min_confidence) else None

        except Exception as e:
            print(f"ATRStrategy error: {e}")
            return None
