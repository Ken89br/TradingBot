from strategy.sma_cross import SMACrossStrategy
from strategy.rsi import RSIStrategy
from strategy.bbands import BollingerStrategy
from strategy.ai_filter import AIFilter  # ✅ new import
from strategy.rsi_ma import AggressiveRSIMA
from strategy.bollinger_breakout import BollingerBreakoutStrategy
from strategy.wick_reversal import WickReversalStrategy
from strategy.macd_reversal import MACDReversalStrategy

class EnsembleStrategy:
    def __init__(self):
        self.strategies = [
            AggressiveRSIMA(),
            BollingerBreakoutStrategy(),
            WickReversalStrategy(),
            MACDReversalStrategy(),
            RSIStrategy(),
            SMACrossStrategy(),
            BollingerStrategy()
        ]
        self.filter = AIFilter()  # ✅ instantiate AI filter

    def generate_signal(self, data):
        votes = []
        meta = []

        for strat in self.strategies:
            result = strat.generate_signal(data)
            if result:
                votes.append(result["signal"].lower())
                meta.append(result)

        if not votes:
            return None

        up_votes = votes.count("up")
        down_votes = votes.count("down")

        if up_votes > down_votes:
            signal = "up"
        elif down_votes > up_votes:
            signal = "down"
        else:
            return None  # no consensus

        confidence = round((max(up_votes, down_votes) / len(votes)) * 100)

        result = {
            "signal": signal,
            "strength": "strong" if confidence >= 70 else "moderate",
            "confidence": confidence,
            "price": data["close"],
            "recommend_entry": data["close"],
            "high": max(c["high"] for c in data["history"]),
            "low": min(c["low"] for c in data["history"]),
            "volume": sum(c["volume"] for c in data["history"])
        }

        # ✅ apply AI filter
        return self.filter.apply(result, data["history"])
