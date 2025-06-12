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

        signal_data = {
            "signal": signal,
            "strength": "strong" if confidence >= 70 else "moderate",
            "confidence": confidence,
            "price": data["close"],
            "recommend_entry": data["close"],
            "high": max(c["high"] for c in data["history"]),
            "low": min(c["low"] for c in data["history"]),
            "volume": sum(c["volume"] for c in data["history"])
        }

        return self.filter.apply(signal_data, data["history"])
            
