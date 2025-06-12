# strategy/ensemble_strategy.py
from config import CONFIG
from strategy.rsi_ma import AggressiveRSIMA
from strategy.bollinger_breakout import BollingerBreakoutStrategy
from strategy.wick_reversal import WickReversalStrategy
from strategy.macd_reversal import MACDReversalStrategy
from strategy.rsi import RSIStrategy
from strategy.bbands import BollingerStrategy
from strategy.sma_cross import SMACrossStrategy  # ✅ FIXED: import
from strategy.ai_filter import SmartAIFilter
from datetime import datetime, timedelta
from strategy.ml_predictor import MLPredictor

class EnsembleStrategy:
    def __init__(self):
        self.strategies = [
            AggressiveRSIMA(CONFIG),
            BollingerBreakoutStrategy(CONFIG),
            WickReversalStrategy(CONFIG),
            MACDReversalStrategy(CONFIG),
            RSIStrategy(),             # ✅ FIXED: no config
            SMACrossStrategy(),        # ✅ Import added
            BollingerStrategy()        # ✅ no config
        ]
        self.filter = SmartAIFilter()
        self.ml = MLPreditor()

    def generate_signal(self, data):
        votes = []
        meta = []

        for strat in self.strategies:
            try:
                result = strat.generate_signal(data)
                if result:
                    votes.append(result["signal"].lower())
                    meta.append(result)
            except Exception as e:
                print(f"⚠️ Strategy error from {type(strat).__name__}: {e}")

        if not votes:
            return None

        up_votes = votes.count("up")
        down_votes = votes.count("down")

        if up_votes > down_votes:
            signal = "up"
        elif down_votes > up_votes:
            signal = "down"
        else:
            return None

        confidence = round((max(up_votes, down_votes) / len(votes)) * 100)

    # Get UNIX ms timestamp from last candle
    last_ts_ms = data["history"][-1].get("timestamp") or data["history"][-1].get("t")
    last_ts_sec = int(last_ts_ms) / 1000 if last_ts_ms else time.time()

    entry_dt = datetime.utcfromtimestamp(last_ts_sec + 180)  # +3 minutes
    formatted_entry = entry_dt.strftime("%Hh:%Mmin (within 3 min)")

    signal_data = {
        "signal": signal,
        "strength": "strong" if confidence >= 70 else "moderate",
        "confidence": confidence,
        "price": data["close"],
        "recommended_entry_time": formatted_entry,  # ✅ time-based format
        "high": max(c["high"] for c in data["history"]),
        "low": min(c["low"] for c in data["history"]),
        "volume": sum(c["volume"] for c in data["history"])
        }

        result = self.filter.apply(signal_data, data["history"])
        if not result:
            return None

        # ML confirms or downgrades
        ml_prediction = self.ml.predict(data["history"])
        if ml_prediction and ml_prediction != result["signal"]:
            print("⚠️ ML disagrees with signal, downgrading confidence")
            result["confidence"] -= 20
            result["strength"] = "weak"
        return result
