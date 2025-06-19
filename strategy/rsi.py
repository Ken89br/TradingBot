class RSIStrategy:
    def generate_signal(self, data):
        candles = data["history"]
        closes = [c["close"] for c in candles]
        if len(closes) < 15:
            return None

        gains, losses = [], []
        for i in range(-14, -1):
            diff = closes[i + 1] - closes[i]
            (gains if diff > 0 else losses).append(abs(diff))

        avg_gain = sum(gains) / 14 if gains else 0.01
        avg_loss = sum(losses) / 14 if losses else 0.01
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        if rsi > 70:
            return {"signal": "down"}
        elif rsi < 30:
            return {"signal": "up"}
        elif 40 < rsi < 60:
        return None
