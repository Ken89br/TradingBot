#strategy/adx_strategy.py
import numpy as np
from collections import deque
from config import CONFIG
from strategy.candlestick_patterns import detect_patterns, PATTERN_STRENGTH

class ADXStrategy:
    def __init__(self, config=None):
        self.adx_period = config.get('adx_period', 14) if config else 14
        self.di_period = config.get('di_period', 14) if config else 14
        self.adx_threshold = config.get('adx_threshold', 25) if config else 25
        self.min_history = config.get('min_history', self.adx_period + 5) if config else self.adx_period + 5

        self.require_trend_confirmation = config.get('trend_confirmation', True) if config else True
        self.volume_threshold = config.get('volume_threshold', 1.3) if config else 1.3
        self.candle_lookback = config.get('candle_lookback', 3) if config else 3
        self.pattern_boost = config.get('pattern_boost', 0.2) if config else 0.2
        self.min_confidence = config.get('min_confidence', 70) if config else 70

        self.high_buffer = deque(maxlen=self.adx_period * 2)
        self.low_buffer = deque(maxlen=self.adx_period * 2)
        self.close_buffer = deque(maxlen=self.adx_period * 2)
        self.candle_buffer = deque(maxlen=self.candle_lookback + 1)

    def _calculate_adx(self):
        if len(self.high_buffer) < self.min_history:
            return None, None, None

        highs = np.array(self.high_buffer, dtype=np.float64)
        lows = np.array(self.low_buffer, dtype=np.float64)
        closes = np.array(self.close_buffer, dtype=np.float64)

        up_moves = highs[1:] - highs[:-1]
        down_moves = lows[:-1] - lows[1:]

        plus_dm = np.where((up_moves > down_moves) & (up_moves > 0), up_moves, 0)
        minus_dm = np.where((down_moves > up_moves) & (down_moves > 0), down_moves, 0)

        tr1 = highs[1:] - lows[1:]
        tr2 = np.abs(highs[1:] - closes[:-1])
        tr3 = np.abs(lows[1:] - closes[:-1])
        tr = np.maximum(np.maximum(tr1, tr2), tr3)

        def smooth(values, period):
            return np.convolve(values, np.ones(period)/period, mode='valid')

        plus_di = 100 * smooth(plus_dm, self.di_period)[-1] / smooth(tr, self.di_period)[-1]
        minus_di = 100 * smooth(minus_dm, self.di_period)[-1] / smooth(tr, self.di_period)[-1]

        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        adx = smooth(dx, self.adx_period)[-1] if len(dx) >= self.adx_period else 0

        return adx, plus_di, minus_di

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

            current = candles[-1]
            prev = candles[-2] if len(candles) > 1 else current
            self.high_buffer.append(float(current["high"]))
            self.low_buffer.append(float(current["low"]))
            self.close_buffer.append(float(current["close"]))
            self.candle_buffer.append(current)

            adx, plus_di, minus_di = self._calculate_adx()
            if adx is None:
                return None

            patterns = detect_patterns(list(self.candle_buffer)[-self.candle_lookback:])

            volume_ok = current.get("volume", 0) > prev.get("volume", 0) * self.volume_threshold
            trend_up = plus_di > minus_di
            price_up = float(current["close"]) > float(prev["close"])

            signal = None
            if adx > self.adx_threshold:
                if trend_up and (price_up or not self.require_trend_confirmation):
                    signal = {
                        "signal": "up",
                        "adx": round(adx, 2),
                        "plus_di": round(plus_di, 2),
                        "minus_di": round(minus_di, 2),
                        "confidence": 70 + min(20, int((adx - 25) / 2)),  # 70-90
                        "volume_ok": volume_ok
                    }
                    signal = self._apply_pattern_boost(signal, patterns, "up")
                elif not trend_up and (not price_up or not self.require_trend_confirmation):
                    signal = {
                        "signal": "down",
                        "adx": round(adx, 2),
                        "plus_di": round(plus_di, 2),
                        "minus_di": round(minus_di, 2),
                        "confidence": 75 + min(20, int((adx - 25) / 2)),  # 75-95
                        "volume_ok": volume_ok
                    }
                    signal = self._apply_pattern_boost(signal, patterns, "down")

            if signal and volume_ok:
                signal["confidence"] = min(95, signal["confidence"] + 10)

            # Só retorna sinal se confiança mínima atingida
            return signal if (signal and signal["confidence"] >= self.min_confidence) else None

        except Exception as e:
            print(f"ADXStrategy error: {e}")
            return None
