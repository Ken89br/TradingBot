# strategy/ml_predictor.py

import os
import joblib
import pandas as pd
from strategy.ml_utils import add_indicators
from data.google_drive_client import download_file

class MLPredictor:
    def __init__(self, model_dir="models"):
        self.model_dir = model_dir
        self.models_cache = {}

    def load_model(self, symbol, timeframe):
        sym = symbol.lower()
        tf = timeframe.lower()
        filename = f"model_{sym}_{tf}.pkl"
        path = os.path.join(self.model_dir, filename)

        cache_key = (sym, tf)
        if cache_key in self.models_cache:
            return self.models_cache[cache_key]

        # Verifica e baixa do Google Drive se necessário
        if not os.path.exists(path):
            try:
                print(f"⬇️ Baixando modelo {filename} do Google Drive...")
                download_file(filename, path)
                print(f"✅ Modelo {filename} baixado do Google Drive.")
            except Exception as e:
                print(f"⚠️ Modelo não encontrado para {symbol.upper()} [{tf.upper()}]: {e}")
                return None

        try:
            model = joblib.load(path)
            self.models_cache[cache_key] = model
            return model
        except Exception as e:
            print(f"⚠️ Falha ao carregar modelo {filename}: {e}")
            return None

    def predict(self, symbol, timeframe, df):
        model = self.load_model(symbol, timeframe)
        if model is None:
            print(f"❌ Modelo não disponível para {symbol} [{timeframe}]")
            return None

        features = [
            "open", "high", "low", "close", "volume",
            "sma_5", "sma_10", "rsi_14", "macd", "macd_signal"
        ]
        if not set(features).issubset(df.columns):
            df = add_indicators(df)
        return model.predict(df[features])

# Exemplo de uso:
# predictor = MLPredictor()
# df = ... # seu DataFrame com os dados do símbolo/timeframe desejado
# preds = predictor.predict("eurusd", "m1", df)