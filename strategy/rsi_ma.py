import numpy as np
from collections import deque
from config import CONFIG
from strategy.candlestick_patterns import PATTERN_STRENGTH, detect_patterns

class AggressiveRSIMA:
    def __init__(self, config=None):
        self.rsi_period = config.get('rsi_period', 14) if config else 14
        self.ma_period = config.get('ma_period', 5) if config else 5
        self.overbought = config.get('overbought', 65) if config else 65
        self.oversold = config.get('oversold', 35) if config else 35
        self.min_history = max(self.rsi_period, self.ma_period) + 5
        self.candle_lookback = config.get('candle_lookback', 3) if config else 3
        self.pattern_boost = config.get('pattern_boost', 0.2) if config else 0.2

        self.price_buffer = deque(maxlen=self.rsi_period * 2)
        self.rsi_buffer = deque(maxlen=3)
        self.ma_buffer = deque(maxlen=3)
        self.require_confirmation = config.get('confirmation', True) if config else True
        self.volume_threshold = config.get('volume_threshold', 1.2) if config else 1.2

    def _calculate_rsi(self, prices):
        deltas = np.diff(prices)
        seed = deltas[:self.rsi_period + 1]
        up = seed[seed >= 0].sum() / self.rsi_period
        down = -seed[seed < 0].sum() / self.rsi_period
        rs = up / (down + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        for i in range(self.rsi_period + 1, len(deltas)):
            delta = deltas[i]
            up = (up * (self.rsi_period - 1) + max(delta, 0)) / self.rsi_period
            down = (down * (self.rsi_period - 1) + max(-delta, 0)) / self.rsi_period
            rs = up / (down + 1e-10)
            rsi = np.append(rsi, 100 - (100 / (1 + rs)))
        return rsi[-1] if isinstance(rsi, np.ndarray) and len(rsi) > 0 else 50

    def _calculate_ma(self, prices):
        return np.mean(prices[-self.ma_period:])

    def _apply_pattern_boost(self, signal, patterns):
        if not signal or not patterns:
            return signal
        direction = signal["signal"]
        if direction == "up":
            confirm_patterns = CONFIG["candlestick_patterns"]["reversal_up"]
        elif direction == "down":
            confirm_patterns = CONFIG["candlestick_patterns"]["reversal_down"]
        else:
            confirm_patterns = []
        pattern_strength = 0
        for pattern in patterns:
            if pattern in confirm_patterns:
                pattern_strength += PATTERN_STRENGTH.get(pattern, 0)
        if pattern_strength > 0:
            signal["confidence"] = min(100, signal.get("confidence", 70) + int(pattern_strength * 20 * self.pattern_boost))
            signal["patterns"] = patterns
            signal["pattern_strength"] = pattern_strength
        return signal

    def generate_signal(self, candle):
        try:
            history = candle.get("history", [])
            if len(history) < max(self.min_history, self.candle_lookback):
                return None
            latest = history[-1]
            prev = history[-2] if len(history) > 1 else None
            current_price = float(latest["close"])
            self.price_buffer.append(current_price)
            if len(self.price_buffer) >= self.rsi_period:
                current_rsi = self._calculate_rsi(np.array(self.price_buffer))
                current_ma = self._calculate_ma(np.array(self.price_buffer))
                self.rsi_buffer.append(current_rsi)
                self.ma_buffer.append(current_ma)
            else:
                return None
            volume_ok = float(latest.get("volume", 0)) > (float(prev.get("volume", 0)) * self.volume_threshold if prev else 0)
            signal = None
            strength = "medium"
            if (current_rsi < self.oversold and
                current_price > current_ma and
                (not self.require_confirmation or
                 (len(self.rsi_buffer) > 1 and self.rsi_buffer[-2] < self.rsi_buffer[-1]))):
                if volume_ok:
                    strength = "high"
                signal = self._package("up", history, strength, current_rsi, current_ma)
            elif (current_rsi > self.overbought and
                  current_price < current_ma and
                  (not self.require_confirmation or
                   (len(self.rsi_buffer) > 1 and self.rsi_buffer[-2] > self.rsi_buffer[-1]))):
                if volume_ok:
                    strength = "high"
                signal = self._package("down", history, strength, current_rsi, current_ma)
            # BOOST
            if signal:
                patterns = detect_patterns(history[-self.candle_lookback:])
                signal = self._apply_pattern_boost(signal, patterns)
            return signal
        except Exception as e:
            print(f"Error in AggressiveRSIMA: {e}")
            return None

    def _package(self, signal, history, strength, rsi_value, ma_value):
        latest = history[-1]
        closes = [float(c["close"]) for c in history]
        highs = [float(c["high"]) for c in history]
        lows = [float(c["low"]) for c in history]
        base_confidence = {"high": 85, "medium": 70, "low": 55}.get(strength, 50)
        rsi_factor = 1 - (abs(rsi_value - 50) / 50)
        ma_distance = abs(float(latest["close"]) - ma_value) / ma_value
        volume_factor = min(1, float(latest.get("volume", 0)) / (np.mean([float(c.get("volume", 0)) for c in history[-5:]]) + 1e-10))
        confidence = min(100, base_confidence +
                         (15 * rsi_factor) +
                         (10 * ma_distance * 100) +
                         (5 * volume_factor))
        return {
            "signal": signal,
            "price": float(latest["close"]),
            "high": float(latest["high"]),
            "low": float(latest["low"]),
            "volume": float(latest.get("volume", 0)),
            "rsi": rsi_value,
            "ma": ma_value,
            "recommend_entry": (float(latest["high"]) + float(latest["low"])) / 2,
            "recommend_stop": float(latest["low"]) if signal == "up" else float(latest["high"]),
            "strength": strength,
            "confidence": int(confidence),
            "indicators": {
                "rsi_trend": "rising" if len(self.rsi_buffer) > 1 and self.rsi_buffer[-1] > self.rsi_buffer[-2] else "falling",
                "price_ma_ratio": float(latest["close"]) / ma_value,
                "volatility": np.std(closes[-10:]) if len(closes) >= 10 else 0
            }
        }
