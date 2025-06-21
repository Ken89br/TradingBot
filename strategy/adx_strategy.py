#strategy/adx_strategy.py
class ADXStrategy:
    def calculate_adx(self, candles, period=14):
        plus_dm, minus_dm, trs = [], [], []
        for i in range(-period - 1, -1):
            current = candles[i]
            prev = candles[i - 1]

            up_move = current["high"] - prev["high"]
            down_move = prev["low"] - current["low"]

            plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0)
            minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0)

            tr = max(
                current["high"] - current["low"],
                abs(current["high"] - prev["close"]),
                abs(current["low"] - prev["close"]),
            )
            trs.append(tr)

        tr_sum = sum(trs)
        plus_di = (sum(plus_dm) / tr_sum) * 100 if tr_sum else 0
        minus_di = (sum(minus_dm) / tr_sum) * 100 if tr_sum else 0
        dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100 if (plus_di + minus_di) != 0 else 0
        return dx, plus_di, minus_di

    def generate_signal(self, data):
        candles = data["history"]
        if len(candles) < 16:
            return None

        adx, plus_di, minus_di = self.calculate_adx(candles)
        last = candles[-1]
        prev = candles[-2]

        if adx > 25:
            if plus_di > minus_di and last["close"] > prev["close"]:
                return {"signal": "up", "adx": round(adx, 2)}
            elif minus_di > plus_di and last["close"] < prev["close"]:
                return {"signal": "down", "adx": round(adx, 2)}

        return None
