class AIFilter:
    def __init__(self):
        pass

    def apply(self, signal_data, candles):
        # Example logic: only trust signal if volume is strong + candle body is large
        if not signal_data or not candles:
            return None

        latest = candles[-1]
        body_size = abs(latest["close"] - latest["open"])
        wick_size = abs(latest["high"] - latest["low"])
        body_ratio = body_size / wick_size if wick_size else 0
        volume = latest["volume"]

        # If candle is not strong, mark confidence down
        if body_ratio < 0.3 or volume < 1000:
            signal_data["confidence"] = max(signal_data["confidence"] - 20, 10)
            signal_data["strength"] = "weak"
        else:
            signal_data["confidence"] = min(signal_data["confidence"] + 10, 100)

        return signal_data
