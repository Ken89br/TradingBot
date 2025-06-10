# strategy/rsi_ma.py

import ta
import numpy as np

class AggressiveRSIMA:
    def __init__(self, config):
        self.rsi_period = 14
        self.ma_period = 5
        self.overbought = 65
        self.oversold = 35

    def generate_signal(self, candle):
        history = candle["history"]
        closes = np.array([float(c["close"]) for c in history])

        if len(closes) < max(self.rsi_period, self.ma_period):
            return None

        rsi = talib.RSI(closes, timeperiod=self.rsi_period)
        ma = talib.SMA(closes, timeperiod=self.ma_period)
        last_price = closes[-1]
        last_rsi = rsi[-1]
        last_ma = ma[-1]

        if last_rsi < self.oversold and last_price > last_ma:
            return self._package("call", history, "high")
        elif last_rsi > self.overbought and last_price < last_ma:
            return self._package("put", history, "high")

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
    
