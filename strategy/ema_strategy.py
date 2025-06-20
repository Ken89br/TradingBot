class EMAStrategy:
    def __init__(self, short_period=9, long_period=21):
        self.short_period = short_period
        self.long_period = long_period

    def calculate_ema(self, prices, period):
        ema = []
        k = 2 / (period + 1)
        for i in range(len(prices)):
            if i < period - 1:
                ema.append(None)  # Not enough data
            elif i == period - 1:
                sma = sum(prices[:period]) / period
                ema.append(sma)
            else:
                ema.append((prices[i] - ema[i - 1]) * k + ema[i - 1])
        return ema

    def generate_signal(self, data):
        candles = data.get("history", [])
        if len(candles) < max(self.short_period, self.long_period) + 1:
            return None

        closes = [c["close"] for c in candles]
        short_ema = self.calculate_ema(closes, self.short_period)
        long_ema = self.calculate_ema(closes, self.long_period)

        # Ponto mais recente com dados válidos
        if short_ema[-2] is None or long_ema[-2] is None:
            return None

        # Cruzamento de EMAs
        if short_ema[-2] < long_ema[-2] and short_ema[-1] > long_ema[-1]:
            return {"signal": "up", "indicator": "ema_crossover"}
        elif short_ema[-2] > long_ema[-2] and short_ema[-1] < long_ema[-1]:
            return {"signal": "down", "indicator": "ema_crossover"}

        return None
        
