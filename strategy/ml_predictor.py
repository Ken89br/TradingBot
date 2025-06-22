# strategy/ml_predictor.py
# Função: Previsão de direção com modelo de machine learning treinado.
# Enriquecido para usar força dos padrões de candlestick (pattern_strength).

import os
import joblib
import pandas as pd
from strategy.ml_utils import add_indicators
from strategy.candlestick_patterns import detect_candlestick_patterns, get_pattern_strength
from strategy.indicators import (
    calc_rsi, calc_macd, calc_bollinger, calc_atr, calc_adx,
    calc_moving_averages, calc_oscillators, calc_volatility,
    calc_volume_status, calc_sentiment
)
from data.google_drive_client import download_file, get_folder_id_for_file

class MLPredictor:
    def __init__(self, model_dir="models", min_candles=70):
        self.model_dir = model_dir
        self.models_cache = {}
        self.min_candles = min_candles

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
                download_file(filename, path, drive_folder_id=get_folder_id_for_file(filename))
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

    def add_candlestick_features(self, df):
        pattern_list = [
            "bullish_engulfing", "bearish_engulfing", "hammer", "shooting_star", "doji"
        ]
        for pattern in pattern_list:
            df[pattern] = 0
        pattern_strengths = []
        for i in range(len(df)):
            candles = df.iloc[max(i-3, 0):i+1][["open", "high", "low", "close", "volume"]].to_dict("records")
            patterns = detect_candlestick_patterns(candles)
            for pattern in pattern_list:
                if pattern in patterns:
                    df.at[df.index[i], pattern] = 1
            pattern_strengths.append(get_pattern_strength(patterns))
        df["pattern_strength"] = pattern_strengths
        return df

    def enrich_indicators(self, df):
        closes = df["close"].tolist()
        highs = df["high"].tolist()
        lows = df["low"].tolist()
        volumes = df["volume"].tolist()

        df["atr"] = calc_atr(highs, lows, closes)
        df["adx"] = calc_adx(highs, lows, closes)
        bb_res = calc_bollinger(closes)
        if isinstance(bb_res, tuple) and len(bb_res) == 3:
            _, df["bb_width"], df["bb_pos"] = bb_res
        else:
            df["bb_width"] = 0
            df["bb_pos"] = 0

        df["ma_rating"] = calc_moving_averages(closes)
        macd_hist, macd_val, macd_signal = calc_macd(closes)
        rsi_val = calc_rsi(closes)
        df["osc_rating"] = calc_oscillators(rsi_val, macd_hist)
        df["volatility"] = calc_volatility(closes)
        df["volume_status"] = calc_volume_status(volumes)
        df["sentiment"] = calc_sentiment(closes)
        df["variation"] = ((df["close"] - df["close"].shift(1)) / df["close"].shift(1)) * 100

        df["support"] = df["low"].rolling(window=10, min_periods=1).min()
        df["resistance"] = df["high"].rolling(window=10, min_periods=1).max()
        df["support_distance"] = df["close"] - df["support"]
        df["resistance_distance"] = df["resistance"] - df["close"]

        ma_mapping = {"buy": 1, "sell": -1, "neutral": 0}
        osc_mapping = {"buy": 1, "sell": -1, "neutral": 0}
        vol_mapping = {"High": 1, "Low": 0}
        volstat_mapping = {"Spiked": 2, "Normal": 1, "Low": 0}
        sentiment_mapping = {"Optimistic": 1, "Neutral": 0, "Pessimistic": -1}

        df["ma_rating"] = df["ma_rating"].map(ma_mapping)
        df["osc_rating"] = df["osc_rating"].map(osc_mapping)
        df["volatility"] = df["volatility"].map(vol_mapping)
        df["volume_status"] = df["volume_status"].map(volstat_mapping)
        df["sentiment"] = df["sentiment"].map(sentiment_mapping)

        return df

    def predict(self, symbol, timeframe, candles: list):
        if not candles:
            print(f"⚠️ Lista de candles vazia!")
            return None

        if len(candles) < self.min_candles:
            print(f"⚠️ Aviso: Foram fornecidos apenas {len(candles)} candles, mínimo recomendado é {self.min_candles} para máxima precisão.")

        candles_to_use = candles[-self.min_candles:] if len(candles) >= self.min_candles else candles

        model = self._load_model(symbol, timeframe)
        if not model:
            return None

        df = pd.DataFrame(candles_to_use)
        if not {"sma_5", "sma_10", "rsi_14", "macd", "macd_signal"}.issubset(df.columns):
            df = add_indicators(df)
        df = self.enrich_indicators(df)
        df = self.add_candlestick_features(df)
        df.dropna(inplace=True)

        features = [
            "open", "high", "low", "close", "volume",
            "sma_5", "sma_10", "rsi_14", "macd", "macd_signal",
            "atr", "adx", "bb_width", "bb_pos",
            "ma_rating", "osc_rating",
            "volatility", "volume_status", "sentiment",
            "support_distance", "resistance_distance", "variation",
            "bullish_engulfing", "bearish_engulfing", "hammer", "shooting_star", "doji",
            "pattern_strength"
        ]
        features = [f for f in features if f in df.columns]

        try:
            last_row = df.iloc[[-1]][features]
            prediction = model.predict(last_row)[0]
            return "up" if prediction == 1 else "down"
        except Exception as e:
            print(f"⚠️ ML prediction failed: {e}")
            return None
