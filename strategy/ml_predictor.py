#strategy/ml_predictor.py

import os
import joblib
import pandas as pd
from strategy.ml_utils import add_indicators

class MLPredictor:
    def __init__(self, model_dir="models"):
        self.model_dir = model_dir
        self.models_cache = {}  # ✅ Cache to avoid reloading on every prediction

    def _load_model(self, timeframe):
        tf = timeframe.lower().replace("1min", "m1").replace("s1", "s1").replace("5min", "m5").replace("15min", "m15").replace("30min", "m30").replace("h1", "h1").replace("4h", "h4")
        filename = f"model_{tf}.pkl"
        path = os.path.join(self.model_dir, filename)

        if tf in self.models_cache:
            return self.models_cache[tf]

        if not os.path.exists(path):
            print(f"⚠️ Model not found for timeframe: {tf}")
            return None

        try:
            model = joblib.load(path)
            self.models_cache[tf] = model
            print(f"✅ Loaded model for timeframe: {tf}")
            return model
        except Exception as e:
            print(f"❌ Failed to load {filename}: {e}")
            return None

    def predict(self, candles: list, timeframe="m1"):
        if not candles:
            return None

        try:
            model = self._load_model(timeframe)
            if not model:
                return None

            features = {
                "open": candles[-1]["open"],
                "high": candles[-1]["high"],
                "low": candles[-1]["low"],
                "close": candles[-1]["close"],
                "volume": candles[-1]["volume"],
            }
            # Dummy placeholder; actual indicator values may be added during training
            for k in ["sma_5", "sma_10", "rsi_14", "macd", "macd_signal"]:
                features[k] = candles[-1].get(k, 0)

            df = pd.DataFrame([features])
            df = add_indicators(df)
            df.dropna(inplace=True)

            prediction = model.predict(df)[0]
            return "up" if prediction == 1 else "down"

        except Exception as e:
            print(f"⚠️ ML prediction failed: {e}")
            return None
        
