# strategy/ai_filter.py

class SmartAIFilter:
    def __init__(self, min_confidence=60, min_volatility=0.0001, min_volume=1):
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

        # 🔁 Part 1: Dynamic adjustment
        if body_ratio < 0.3 or volume < 1000:
            signal_data["confidence"] = max(signal_data["confidence"] - 20, 10)
            signal_data["strength"] = "weak"
            print(f"⚠️ Weak structure: body_ratio={round(body_ratio, 2)}, volume={volume}")
        else:
            signal_data["confidence"] = min(signal_data["confidence"] + 10, 100)
            if signal_data["confidence"] >= 80:
                signal_data["strength"] = "strong"
            elif signal_data["confidence"] >= 60:
                signal_data["strength"] = "moderate"
            else:
                signal_data["strength"] = "weak"

        # 🔁 Part 2: Hard filters
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

        # ✅ Passed all filters
        return signal_data
        
