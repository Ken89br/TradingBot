#strategy/bollinger_breakout.py
import pandas as pd
import ta

class BollingerBreakoutStrategy:
    def __init__(self, config):
        self.period = 20

    def generate_signal(self, candle):
        df = pd.DataFrame(candle["history"])
        df = df.astype(float)

        if len(df) < self.period:
            return None

        bb = ta.volatility.BollingerBands(df["close"], window=self.period)
        df["upper"] = bb.bollinger_hband()
        df["lower"] = bb.bollinger_lband()

        price = df["close"].iloc[-1]

        if price < df["lower"].iloc[-1]:
            return self._package("call", df, "medium")
        elif price > df["upper"].iloc[-1]:
            return self._package("put", df, "medium")

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
        
