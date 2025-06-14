#ml_predictor
import os
import joblib
import pandas as pd
import requests
from strategy.ml_utils import add_indicators

class MLPredictor:
    def __init__(self, model_path="model.pkl"):
        self.model_path = model_path
        self.model = self._load_model()

    def _load_model(self):
        if not os.path.exists(self.model_path):
            print("⚠️ model.pkl not found. Skipping ML prediction.")
            return None
        try:
            return joblib.load(self.model_path)
        except Exception as e:
            print(f"❌ Failed to load model.pkl: {e}")
            return None

    def predict(self, candles: list):
        if not self.model or not candles:
            return None
        try:
            features = {
                "open": candles[-1]["open"],
                "high": candles[-1]["high"],
                "low": candles[-1]["low"],
                "close": candles[-1]["close"],
                "volume": candles[-1]["volume"],
            }
            # Dummy values for now; make sure indicators are added later
            for k in ["sma_5", "sma_10", "rsi_14", "macd", "macd_signal"]:
                features[k] = candles[-1].get(k, 0)

            df = pd.DataFrame([features])
            df = add_indicators(df)  # <== Make sure this is added here
            df.dropna(inplace=True)
            prediction = self.model.predict(df)[0]
            return "up" if prediction == 1 else "down"
        except Exception as e:
            print(f"⚠️ ML prediction failed: {e}")
            return None
            
