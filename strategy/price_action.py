class PriceActionStrategy:
    def __init__(self):
        self.min_wick_ratio = 2.0  # Relação mínima entre sombra e corpo

    def generate_signal(self, data):
        candles = data.get("history", [])
        if len(candles) < 2:
            return None

        current = candles[-1]
        prev = candles[-2]

        open_ = current["open"]
        close = current["close"]
        high = current["high"]
        low = current["low"]

        body = abs(close - open_)
        upper_wick = high - max(open_, close)
        lower_wick = min(open_, close) - low
        total_range = high - low if high != low else 0.0001

        # DOJI: Corpo muito pequeno, indecisão
        if body / total_range < 0.1:
            return {"signal": None, "pattern": "doji"}

        # HAMMER / HANGING MAN
        if body / total_range < 0.3 and lower_wick / body > self.min_wick_ratio:
            direction = "up" if close > open_ else "down"
            pattern = "hammer" if direction == "up" else "hanging_man"
            return {"signal": "up" if pattern == "hammer" else "down", "pattern": pattern}

        # ENGULFING BULLISH
        if close > open_ and prev["close"] < prev["open"] and close > prev["open"] and open_ < prev["close"]:
            return {"signal": "up", "pattern": "bullish_engulfing"}

        # ENGULFING BEARISH
        if close < open_ and prev["close"] > prev["open"] and close < prev["open"] and open_ > prev["close"]:
            return {"signal": "down", "pattern": "bearish_engulfing"}

        # PIN BAR (forte rejeição de preço)
        if upper_wick > body * self.min_wick_ratio and lower_wick < body * 0.3:
            return {"signal": "down", "pattern": "pinbar_top"}
        elif lower_wick > body * self.min_wick_ratio and upper_wick < body * 0.3:
            return {"signal": "up", "pattern": "pinbar_bottom"}

        return None
      
