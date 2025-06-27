class WickReversalStrategy:
    def __init__(self, config=None):
        # Se config vier do ensemble, ele é o dict global CONFIG.
        # Se vier de uso manual, pode ser None, ou o próprio dict de parâmetros.
        if config and "wick_reversal" in config:
            cfg = config["wick_reversal"]
        else:
            cfg = config or {}
        self.wick_ratio = cfg.get('wick_ratio', 2.0)
        self.min_body_ratio = cfg.get('min_body_ratio', 0.1)
        self.volume_multiplier = cfg.get('volume_multiplier', 1.5)
        self.trend_confirmation = cfg.get('trend_confirmation', True)

    def generate_signal(self, data):
        try:
            history = data.get("history", [])
            if len(history) < 3:
                return None

            latest = history[-1]
            prev = history[-2]

            # Convert values to float
            latest = {k: float(latest.get(k, 0)) for k in ["open", "close", "high", "low", "volume"]}
            prev = {k: float(prev.get(k, 0)) for k in ["open", "close", "high", "low", "volume"]}

            # Calculate wick and body metrics
            body_size = abs(latest["close"] - latest["open"])
            upper_wick = latest["high"] - max(latest["open"], latest["close"])
            lower_wick = min(latest["open"], latest["close"]) - latest["low"]

            # Validation
            if body_size == 0 or (upper_wick + lower_wick) == 0:
                return None

            # Volume confirmation
            volume_ok = latest["volume"] > prev["volume"] * self.volume_multiplier

            # Trend confirmation (optional)
            trend_aligned = True
            if self.trend_confirmation:
                prev_trend = prev["close"] - prev["open"]
                # Se for sinal de alta, o candle anterior deve ser de baixa; se for baixa, anterior de alta
                trend_aligned = (
                    (lower_wick > body_size * self.wick_ratio and prev_trend < 0) or
                    (upper_wick > body_size * self.wick_ratio and prev_trend > 0)
                )

            # Sinal de alta (martelo)
            if lower_wick > body_size * self.wick_ratio and body_size / (upper_wick + 1e-8) > self.min_body_ratio:
                if volume_ok and trend_aligned:
                    strength = "high"
                else:
                    strength = "medium"
                return self._package("up", history, strength)
            # Sinal de baixa (estrela cadente)
            elif upper_wick > body_size * self.wick_ratio and body_size / (lower_wick + 1e-8) > self.min_body_ratio:
                if volume_ok and trend_aligned:
                    strength = "high"
                else:
                    strength = "medium"
                return self._package("down", history, strength)

            return None

        except Exception as e:
            print(f"Error in WickReversalStrategy: {e}")
            return None

    def _package(self, signal, history, strength):
        latest = history[-1]
        closes = [float(c["close"]) for c in history]
        highs = [float(c["high"]) for c in history]
        lows = [float(c["low"]) for c in history]
        volumes = [float(c.get("volume", 0)) for c in history]

        # Dynamic confidence calculation
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
            "pattern": "hammer" if signal == "up" else "shooting_star",
            "candle_size": highs[-1] - lows[-1],
            "context": {
                "prev_trend": closes[-2] - closes[-3] if len(history) >= 3 else 0,
                "volume_change": volumes[-1] / volumes[-2] if len(history) >= 2 and volumes[-2] > 0 else 1
            }
            }
