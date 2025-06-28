#Função: Estratégia “conselho de especialistas” (ensemble).
#O que faz:
#Reúne várias estratégias (incluindo suas próprias, ML, etc).
#Cada uma vota no sinal (“up” ou “down”).
#Decide a direção final baseada na maioria dos votos, ou usa ML em caso de empate.
#Calcula indicadores ricos (RSI, MACD, ATR, ADX, etc) com o arquivo indicators.py e monta um dicionário de sinal completo.
#Aplica um filtro inteligente (SmartAIFilter) antes de retornar o sinal.

# strategy/ensemble_strategy.py
import time
from datetime import datetime
from config import CONFIG

from strategy.candlestick_strategy import CandlestickStrategy
from strategy.rsi_ma import AggressiveRSIMA
from strategy.bollinger_breakout import BollingerBreakoutStrategy
from strategy.wick_reversal import WickReversalStrategy
from strategy.macd_reversal import MACDReversalStrategy
from strategy.rsi import RSIStrategy
from strategy.bbands import BollingerStrategy
from strategy.sma_cross import SMACrossStrategy
from strategy.ai_filter import SmartAIFilter
from strategy.ml_predictor import MLPredictor
from strategy.price_action import EnhancedPriceActionStrategy
from strategy.ema_strategy import EMAStrategy
from strategy.atr_strategy import ATRStrategy
from strategy.adx_strategy import ADXStrategy

from strategy.candlestick_patterns import detect_candlestick_patterns
from strategy.indicators import (
    calc_rsi, calc_macd, calc_bollinger, calc_atr, calc_adx,
    calc_moving_averages, calc_oscillators, calc_volatility,
    calc_volume_status, calc_sentiment
)

class EnsembleStrategy:
    def __init__(self):
        self.strategies = [
            CandlestickStrategy(),
            AggressiveRSIMA(CONFIG["rsi_ma"]),
            BollingerBreakoutStrategy(CONFIG),
            WickReversalStrategy(CONFIG["wick_reversal"]),
            MACDReversalStrategy(CONFIG),
            RSIStrategy(),
            SMACrossStrategy(),
            BollingerStrategy(),
            PriceActionStrategy(CONFIG["price_action"]),
            EMAStrategy(),
            ATRStrategy(),
            ADXStrategy(),
        ]
        self.filter = SmartAIFilter()
        self.ml = MLPredictor()

    def generate_signal(self, data, timeframe="1min"):
        votes, details = [], []
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

        up_votes = votes.count("up")
        down_votes = votes.count("down")

        ml_direction = None

        if up_votes > down_votes:
            direction = "up"
        elif down_votes > up_votes:
            direction = "down"
        else:
            print("⚠️ Equal votes — using ML to break tie.")
            try:
                ml_direction = self.ml.predict(data["symbol"], timeframe, data["history"])
                if ml_direction:
                    direction = ml_direction
                else:
                    print("⚠️ ML undecided — skipping signal.")
                    return None
            except Exception as e:
                print(f"⚠️ ML predictor failed during tiebreaker: {e}")
                return None

        confidence = round((max(up_votes, down_votes) / len(votes)) * 100)
        strength = "strong" if confidence >= 70 else "moderate"

        last_ts = data["history"][-1].get("timestamp") or data["history"][-1].get("t")
        last_ts = int(last_ts) / 1000 if last_ts else time.time()

        entry_dt = datetime.utcfromtimestamp(last_ts + 180)
        expire_dt = datetime.utcfromtimestamp(last_ts + 300)

        candles = data["history"]
        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        volumes = [c.get("volume", 0) for c in candles]

        rsi = calc_rsi(closes)
        macd_hist, macd_val, macd_signal = calc_macd(closes)
        bollinger_str, bb_width, bb_pos = calc_bollinger(closes)
        atr = calc_atr(highs, lows, closes)
        adx = calc_adx(highs, lows, closes)
        ma_rating = calc_moving_averages(closes)
        osc_rating = calc_oscillators(rsi, macd_hist)
        volatility = calc_volatility(closes)
        volume_status = calc_volume_status(volumes)
        sentiment = calc_sentiment(closes)
        patterns = detect_candlestick_patterns(candles)

        support = min(lows[-10:])
        resistance = max(highs[-10:])

        variation = f"{((closes[-1] - closes[-2]) / closes[-2]) * 100:.2f}%"

        rsi_str = f"{rsi:.1f} ({'Overbought' if rsi > 70 else 'Oversold' if rsi < 30 else 'Neutral'})"
        macd_str = f"{macd_val:.4f} (Hist: {macd_hist:.4f})"
        atr_str = f"{atr:.5f}"
        adx_str = f"{adx:.2f}"

        signal_data = {
            "signal": direction,
            "strength": strength,
            "confidence": confidence,
            "price": data["close"],
            "recommended_entry_time": entry_dt.strftime("%Hh:%Mmin"),
            "expire_entry_time": expire_dt.strftime("%Hh:%Mmin"),
            "high": max(c["high"] for c in data["history"]),
            "low": min(c["low"] for c in data["history"]),
            "volume": sum(c["volume"] for c in data["history"]),

            "variation": variation,
            "risk": "Low" if volatility == "Low" and adx < 25 else "High",
            "volatility": volatility,
            "sentiment": sentiment,
            "volume_status": volume_status,
            "support": support,
            "resistance": resistance,
            "summary": "strong buy" if direction == "up" else "strong sell" if direction == "down" else "neutral",
            "moving_averages": ma_rating,
            "oscillators": osc_rating,
            "rsi": rsi_str,
            "macd": macd_str,
            "bollinger": bollinger_str,
            "atr": atr_str,
            "adx": adx_str,
            "patterns": patterns  # <-- padrões já vão para o filtro
        }

        try:
            ml_prediction = self.ml.predict(data["symbol"], timeframe, data["history"])
            if ml_prediction and ml_prediction != signal_data["signal"]:
                print("⚠️ ML disagrees — downgrading confidence")
                signal_data["confidence"] = max(signal_data["confidence"] - 20, 10)
                signal_data["strength"] = "weak"
        except Exception as e:
            print(f"⚠️ ML predictor failed: {e}")

        return self.filter.apply(signal_data, data["history"])
