import pandas as pd
import ta

class AggressiveRSIMA:
    def __init__(self, config):
        self.rsi_period = 14
        self.ma_period = 5
        self.overbought = 65
        self.oversold = 35

    def generate_signal(self, candle):
        df = pd.DataFrame(candle["history"])
        df = df.astype(float)

        if len(df) < max(self.rsi_period, self.ma_period):
            return None

        df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=self.rsi_period).rsi()
        df["ma"] = ta.trend.SMAIndicator(df["close"], window=self.ma_period).sma_indicator()

        last_rsi = df["rsi"].iloc[-1]
        last_ma = df["ma"].iloc[-1]
        last_price = df["close"].iloc[-1]

        if last_rsi < self.oversold and last_price > last_ma:
            return self._package("call", df, "high")
        elif last_rsi > self.overbought and last_price < last_ma:
            return self._package("put", df, "high")

        return None

    def _package(self, signal, df, strength):
        confidence = {"high": 95, "medium": 80, "low": 65}.get(strength, 50)

        return {
            "signal": signal,
            "price": df["close"].iloc[-1],
            "high": df["high"].iloc[-1],
            "low": df["low"].iloc[-1],
            "volume": df["volume"].iloc[-1],
            "recommend_entry": (df["high"].iloc[-1] + df["low"].iloc[-1]) / 2,
            "strength": strength,
            "confidence": confidence
        }
        
