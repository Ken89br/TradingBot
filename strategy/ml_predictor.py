# strategy/ml_predictor.py
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
            remote_url = os.getenv("MODEL_URL")
            if remote_url:
                print(f"⬇️ Downloading model from {remote_url}")
                r = requests.get(remote_url)
                with open(self.model_path, "wb") as f:
                    f.write(r.content)
        return joblib.load(self.model_path)

    def predict(self, candles):
        df = pd.DataFrame(candles)
        df = add_indicators(df)
        df.dropna(inplace=True)
        if df.empty:
            return None
        features = ["open", "high", "low", "close", "volume", "sma_5", "sma_10", "rsi_14", "macd", "macd_signal"]
        X = df.iloc[-1:][features]
        return "up" if self.model.predict(X)[0] == 1 else "down"
        
