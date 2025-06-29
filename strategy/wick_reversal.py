from config import CONFIG
from strategy.candlestick_patterns import detect_patterns, PATTERN_STRENGTH

class WickReversalStrategy:
    def __init__(self, config=None):
        if config and "wick_reversal" in config:
            cfg = config["wick_reversal"]
        else:
            cfg = config or {}
        self.wick_ratio = cfg.get('wick_ratio', 2.0)
        self.min_body_ratio = cfg.get('min_body_ratio', 0.1)
        self.volume_multiplier = cfg.get('volume_multiplier', 1.5)
        self.trend_confirmation = cfg.get('trend_confirmation', True)
        self.pattern_boost = cfg.get("pattern_boost", 0.2)  # Novo parâmetro (ajuste conforme desejar)
        self.candle_lookback = cfg.get("candle_lookback", 3)

    def generate_signal(self, data):
        try:
            history = data.get("history", [])
            if len(history) < max(3, self.candle_lookback):
                return None

            latest = history[-1]
            prev = history[-2]

            latest = {k: float(latest.get(k, 0)) for k in ["open", "close", "high", "low", "volume"]}
            prev = {k: float(prev.get(k, 0)) for k in ["open", "close", "high", "low", "volume"]}

            body_size = abs(latest["close"] - latest["open"])
            upper_wick = latest["high"] - max(latest["open"], latest["close"])
            lower_wick = min(latest["open"], latest["close"]) - latest["low"]

            if body_size == 0 or (upper_wick + lower_wick) == 0:
                return None

            volume_ok = latest["volume"] > prev["volume"] * self.volume_multiplier

            trend_aligned = True
            if self.trend_confirmation:
                prev_trend = prev["close"] - prev["open"]
                trend_aligned = (
                    (lower_wick > body_size * self.wick_ratio and prev_trend < 0) or
                    (upper_wick > body_size * self.wick_ratio and prev_trend > 0)
                )

            # Detecta padrões de vela nos últimos candles
            patterns = detect_patterns(history[-self.candle_lookback:])
            wick_signal = None

            if lower_wick > body_size * self.wick_ratio and body_size / (upper_wick + 1e-8) > self.min_body_ratio:
                wick_signal = "up"
            elif upper_wick > body_size * self.wick_ratio and body_size / (lower_wick + 1e-8) > self.min_body_ratio:
                wick_signal = "down"

            if wick_signal:
                if volume_ok and trend_aligned:
                    strength = "high"
                else:
                    strength = "medium"

                signal = self._package(wick_signal, history, strength)
                signal = self._apply_pattern_boost(signal, patterns)
                return signal

            return None

        except Exception as e:
            print(f"Error in WickReversalStrategy: {e}")
            return None

    def _apply_pattern_boost(self, signal, patterns):
        if not signal or not patterns:
            return signal
        direction = signal["signal"]
        # Usa padrões de reversão e indecisão
        if direction == "up":
            confirm_patterns = CONFIG["candlestick_patterns"]["reversal_up"] + CONFIG["candlestick_patterns"]["neutral"]
        else:
            confirm_patterns = CONFIG["candlestick_patterns"]["reversal_down"] + CONFIG["candlestick_patterns"]["neutral"]

        pattern_strength = 0
        for pattern in patterns:
            if pattern in confirm_patterns:
                pattern_strength += PATTERN_STRENGTH.get(pattern, 0.1)

        if pattern_strength > 0:
            boost = int(pattern_strength * 20 * self.pattern_boost)  # até 20%
            signal["confidence"] = min(100, signal["confidence"] + boost)
            signal["patterns"] = patterns
            signal["pattern_strength"] = pattern_strength

        return signal

    def _package(self, signal, history, strength):
        latest = history[-1]
        closes = [float(c["close"]) for c in history]
        highs = [float(c["high"]) for c in history]
        lows = [float(c["low"]) for c in history]
        volumes = [float(c.get("volume", 0)) for c in history]

        base_confidence = {"high": 90, "medium": 75, "low": 60}.get(strength, 50)
        if len(volumes) >= 4 and sum(volumes[-4:-1]) > 0:
            volume_boost = min(10, max(0, (volumes[-1] - sum(volumes[-4:-1])/3) / (sum(volumes[-4:-1])/3 + 1e-8) * 10))
        else:
            volume_boost = 0
        confidence = min(100, base_confidence + volume_boost)

        return {
            "signal": signal,
            "price": closes[-1],
            "high": highs[-1],
            "low": lows[-1],
            "volume": volumes[-1],
            "recommend_entry": (highs[-1] + lows[-1]) / 2,
            "recommend_stop": lows[-1] if signal == "up" else highs[-1],
            "strength": strength,
            "confidence": confidence,
            "wick_ratio": self.wick_ratio,
            "candle_size": highs[-1] - lows[-1],
            "context": {
                "prev_trend": closes[-2] - closes[-3] if len(history) >= 3 else 0,
                "volume_change": volumes[-1] / volumes[-2] if len(history) >= 2 and volumes[-2] > 0 else 1
            }
        }
