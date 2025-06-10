# strategy/wick_reversal.py

class WickReversalStrategy:
    def __init__(self, config):
        self.wick_ratio = 2.0

    def generate_signal(self, candle):
        latest = candle["history"][-1]
        open_price = float(latest["open"])
        close_price = float(latest["close"])
        high = float(latest["high"])
        low = float(latest["low"])

        body = abs(close_price - open_price)
        upper_wick = high - max(open_price, close_price)
        lower_wick = min(open_price, close_price) - low

        if body == 0:
            return None

        if lower_wick > body * self.wick_ratio:
            return self._package("call", candle["history"], "medium")
        elif upper_wick > body * self.wick_ratio:
            return self._package("put", candle["history"], "medium")

        return None

    def _package(self, signal, history, strength):
        confidence = {"high": 95, "medium": 80, "low": 65}.get(strength, 50)
        closes = [float(c["close"]) for c in history]
        highs = [float(c["high"]) for c in history]
        lows = [float(c["low"]) for c in history]
        volumes = [float(c.get("volume", 0)) for c in history]

        return {
            "signal": signal,
            "price": closes[-1],
            "high": highs[-1],
            "low": lows[-1],
            "volume": volumes[-1],
            "recommend_entry": (highs[-1] + lows[-1]) / 2,
            "strength": strength,
            "confidence": confidence
        }
        
