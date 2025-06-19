#strategy/macd_reversal.py
import pandas as pd
import ta

class MACDReversalStrategy:
    def __init__(self, config):
        pass

    def generate_signal(self, candle):
        df = pd.DataFrame(candle["history"])
        df = df.astype(float)

        if len(df) < 26:
            return None

        macd = ta.trend.MACD(df["close"])
        hist = macd.macd_diff()

        if hist.iloc[-2] < 0 < hist.iloc[-1]:
            return self._package("call", df, "high")
        elif hist.iloc[-2] > 0 > hist.iloc[-1]:
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
        
