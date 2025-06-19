# strategy/ai_filter.py

class SmartAIFilter:
    def __init__(self, min_confidence=50, min_volatility=0.00005, min_volume=0):
        self.min_confidence = min_confidence
        self.min_volatility = min_volatility
        self.min_volume = min_volume

    def apply(self, signal_data, candles):
        if not signal_data or not candles:
            print("❌ Invalid input to AI filter.")
            return None

        latest = candles[-1]
        body_size = abs(latest["close"] - latest["open"])
        wick_size = abs(latest["high"] - latest["low"])
        body_ratio = body_size / wick_size if wick_size else 0
        volume = latest["volume"]

        if body_ratio < 0.2 or volume < 500:
            signal_data["confidence"] = max(signal_data["confidence"] - 15, 10)
            signal_data["strength"] = "weak"
        else:
            signal_data["confidence"] = min(signal_data["confidence"] + 10, 100)
            signal_data["strength"] = "strong" if signal_data["confidence"] >= 80 else "moderate"

        price_range = signal_data["high"] - signal_data["low"]
        if signal_data["confidence"] < self.min_confidence:
            print(f"❌ Rejected: low confidence ({signal_data['confidence']}%)")
            return None

        if price_range < self.min_volatility:
            print(f"❌ Rejected: low volatility (range: {price_range})")
            return None

        if signal_data["volume"] < self.min_volume:
            print(f"❌ Rejected: low volume ({signal_data['volume']})")
            return None

        return signal_data
