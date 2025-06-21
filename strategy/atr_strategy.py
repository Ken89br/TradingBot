#strategy/atr_strategy.py
import pandas as pd
import ta

class ATRStrategy:
    def calculate_atr(self, candles, period=14):
        trs = []
        for i in range(-period, -1):
            high = candles[i]["high"]
            low = candles[i]["low"]
            prev_close = candles[i - 1]["close"]
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)
        return sum(trs) / period if trs else 0

    def generate_signal(self, data):
        candles = data["history"]
        if len(candles) < 15:
            return None

        atr = self.calculate_atr(candles)
        last_candle = candles[-1]
        body = abs(last_candle["close"] - last_candle["open"])

        if body > atr * 1.2:
            direction = "up" if last_candle["close"] > last_candle["open"] else "down"
            return {"signal": direction, "atr": round(atr, 5)}
        return None
