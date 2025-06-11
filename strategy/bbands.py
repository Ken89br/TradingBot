class BollingerStrategy:
    def generate_signal(self, data):
        candles = data["history"]
        closes = [c["close"] for c in candles]
        if len(closes) < 20:
            return None

        sma = sum(closes[-20:]) / 20
        std = (sum((c - sma) ** 2 for c in closes[-20:]) / 20) ** 0.5

        upper = sma + (2 * std)
        lower = sma - (2 * std)
        price = closes[-1]

        if price > upper:
            return {"signal": "down"}
        elif price < lower:
            return {"signal": "up"}
        return None
