class SMACrossStrategy:
    def generate_signal(self, data):
        candles = data["history"]
        closes = [c["close"] for c in candles]
        if len(closes) < 20:
            return None

        sma5 = sum(closes[-5:]) / 5
        sma10 = sum(closes[-10:]) / 10

        if sma5 > sma10:
            return {"signal": "up"}
        elif sma5 < sma10:
            return {"signal": "down"}
        return None
