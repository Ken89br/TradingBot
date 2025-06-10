import pandas as pd
import numpy as np
import ta


class AggressiveRSIMA:
    def __init__(self, config):
        self.rsi_period = 14
        self.ma_period = 5
        self.overbought = 65
        self.oversold = 35

    def generate_signal(self, candle):
        history = candle["history"]
        df = pd.DataFrame(history)
        df["close"] = df["close"].astype(float)

        if len(df) < max(self.rsi_period, self.ma_period):
            return None

        df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=self.rsi_period).rsi()
        df["ma"] = ta.trend.SMAIndicator(df["close"], window=self.ma_period).sma_indicator()

        last_rsi = df["rsi"].iloc[-1]
        last_ma = df["ma"].iloc[-1]
        last_price = df["close"].iloc[-1]

        if last_rsi < self.oversold and last_price > last_ma:
            return self._package("call", history, "high")
        elif last_rsi > self.overbought and last_price < last_ma:
            return self._package("put", history, "high")

        return None

    def _package(self, signal, history, strength):
        closes = [float(c["close"]) for c in history]
        highs = [float(c["high"]) for c in history]
        lows = [float(c["low"]) for c in history]
        volumes = [float(c.get("volume", 0)) for c in history]
        confidence = {"high": 95, "medium": 80, "low": 65}.get(strength, 50)

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
