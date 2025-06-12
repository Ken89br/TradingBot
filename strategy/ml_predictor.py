# strategy/ml_predictor.py
import joblib
import pandas as pd
from strategy.ml_utils import add_indicators
import os

class MLPredictor:
    def __init__(self, model_path="model.pkl"):
        if not os.path.exists(model_path):
            print("⚠️ No model found, ML disabled.")
            self.model = None
        else:
            self.model = joblib.load(model_path)

    def predict(self, candles):
        if not self.model:
            return None

        df = pd.DataFrame(candles)
        df = add_indicators(df)
        df.dropna(inplace=True)

        if df.empty:
            return None

        features = ["open", "high", "low", "close", "volume", "sma_5", "sma_10", "rsi_14", "macd", "macd_signal"]
        latest = df.iloc[-1:][features]

        prediction = self.model.predict(latest)[0]
        return "up" if prediction == 1 else "down"
