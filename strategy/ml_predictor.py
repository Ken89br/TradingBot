#strategy/ml_preditor.py
import os
import joblib
import pandas as pd
from strategy.ml_utils import (
    add_indicators,
    add_macd,
    add_rsi,
    add_sma
)
from data.google_drive_client import download_file

class MLPredictor:
    def __init__(self, model_dir="models"):
        self.model_dir = model_dir
        self.models_cache = {}

    def _normalize_timeframe(self, timeframe):
        tf = timeframe.lower()
        tf = tf.replace("1min", "m1").replace("5min", "m5").replace("15min", "m15")
        tf = tf.replace("30min", "m30").replace("s1", "s1").replace("h1", "h1").replace("4h", "h4")
        return tf

    def _load_model(self, symbol, timeframe):
        tf = self._normalize_timeframe(timeframe)
        sym = symbol.lower()
        filename = f"model_{sym}_{tf}.pkl"
        path = os.path.join(self.model_dir, filename)

        cache_key = (sym, tf)
        if cache_key in self.models_cache:
            return self.models_cache[cache_key]

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

    def predict(self, symbol, timeframe, candles: list):
        if not candles:
            return None

        model = self._load_model(symbol, timeframe)
        if not model:
            return None

        # Cria DataFrame de todos os candles recebidos
        df = pd.DataFrame(candles)
        # Adiciona indicadores se necessário
        if not {"sma_5", "sma_10", "rsi_14", "macd", "macd_signal"}.issubset(df.columns):
            df = add_indicators(df)
        df.dropna(inplace=True)

        features = [
            "open", "high", "low", "close", "volume",
            "sma_5", "sma_10", "rsi_14", "macd", "macd_signal"
        ]
        # Usa sempre a última linha para prever
        try:
            last_row = df.iloc[[-1]][features]
            prediction = model.predict(last_row)[0]
            return "up" if prediction == 1 else "down"
        except Exception as e:
            print(f"⚠️ ML prediction failed: {e}")
            return None

    # Funções auxiliares de indicadores
    def add_macd(self, df):
        return add_macd(df)

    def add_rsi(self, df, period=14):
        return add_rsi(df, period=period)

    def add_sma(self, df, period):
        return add_sma(df, period=period)
