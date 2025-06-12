# strategy/ensemble_strategy.py
import time
from config import CONFIG
from strategy.rsi_ma import AggressiveRSIMA
from strategy.bollinger_breakout import BollingerBreakoutStrategy
from strategy.wick_reversal import WickReversalStrategy
from strategy.macd_reversal import MACDReversalStrategy
from strategy.rsi import RSIStrategy
from strategy.bbands import BollingerStrategy
from strategy.sma_cross import SMACrossStrategy
from strategy.ai_filter import SmartAIFilter
from strategy.ml_predictor import MLPredictor
from datetime import datetime, timedelta

class EnsembleStrategy:
    def __init__(self):
        self.strategies = [
            AggressiveRSIMA(CONFIG),
            BollingerBreakoutStrategy(CONFIG),
            WickReversalStrategy(CONFIG),
            MACDReversalStrategy(CONFIG),
            RSIStrategy(),
            SMACrossStrategy(),
            BollingerStrategy()
        ]
        self.filter = SmartAIFilter()
        self.ml = MLPredictor()

    def generate_signal(self, data):
        votes = []
        details = []

        for strat in self.strategies:
            try:
                result = strat.generate_signal(data)
                if result:
                    votes.append(result["signal"].lower())
                    details.append(result)
            except Exception as e:
                print(f"⚠️ {type(strat).__name__} failed: {e}")

        if not votes:
            print("⚠️ No strategies returned a signal.")
            return None

        # Voting mechanism
        up_votes = votes.count("up")
        down_votes = votes.count("down")

        if up_votes > down_votes:
            direction = "up"
        elif down_votes > up_votes:
            direction = "down"
        else:
            print("⚠️ Equal votes — skipping signal.")
            return None

        confidence = round((max(up_votes, down_votes) / len(votes)) * 100)
        strength = "strong" if confidence >= 70 else "moderate"

        # Timestamp-based recommended entry
        last_ts = data["history"][-1].get("timestamp") or data["history"][-1].get("t")
        last_ts = int(last_ts) / 1000 if last_ts else time.time()
        entry_dt = datetime.utcfromtimestamp(last_ts + 180)
        entry_time_str = entry_dt.strftime("%Hh:%Mmin (within 3 min)")

        signal_data = {
            "signal": direction,
            "strength": strength,
            "confidence": confidence,
            "price": data["close"],
            "recommended_entry_time": entry_time_str,
            "high": max(c["high"] for c in data["history"]),
            "low": min(c["low"] for c in data["history"]),
            "volume": sum(c["volume"] for c in data["history"]),
        }

        # ML adjustment
        try:
            ml_prediction = self.ml.predict(data["history"])
            if ml_prediction and ml_prediction != signal_data["signal"]:
                print("⚠️ ML disagrees with signal — downgrading confidence")
                signal_data["confidence"] = max(signal_data["confidence"] - 20, 10)
                signal_data["strength"] = "weak"
        except Exception as e:
            print(f"⚠️ ML predictor failed: {e}")

        return self.filter.apply(signal_data, data["history"])
                    
