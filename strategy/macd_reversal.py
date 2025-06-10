import talib
import numpy as np

class MACDReversalStrategy:
    def __init__(self, config):
        pass

    def generate_signal(self, candle):
        closes = np.array([float(c["close"]) for c in candle["history"]])
        macd, signal, hist = talib.MACD(closes)
        if hist[-2] < 0 and hist[-1] > 0:
            return self._package("call", candle["history"], "high")
        elif hist[-2] > 0 and hist[-1] < 0:
            return self._package("put", candle["history"], "high")
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
