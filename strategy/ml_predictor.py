# strategy/ml_predictor.py
# Função: Previsão de direção com modelo de machine learning treinado.
# Enriquecido para usar força dos padrões de candlestick (pattern_strength).
# Predictor otimizado e compatível para modelos de ML de trading, com todos os principais indicadores e padrões.

import os
import joblib
import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from functools import lru_cache
from datetime import datetime, timedelta

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ml_predictor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Imports do seu projeto
from strategy.ml_utils import add_indicators
from strategy.candlestick_patterns import detect_candlestick_patterns, get_pattern_strength
from strategy.indicators import (
    calc_rsi, calc_macd, calc_bollinger, calc_atr, calc_adx,
    calc_moving_averages, calc_oscillators, calc_volatility,
    calc_volume_status, calc_sentiment
)
from data.google_drive_client import download_file, get_folder_id_for_file

from data.fundamental_data import get_cot_feature, get_macro_feature, get_sentiment_feature
from utils.features_extra import calc_obv, calc_spread
from utils.aggregation import resample_candles

class MLPredictor:
    """Predictor otimizado para modelos de trading com cache, validação e download do Google Drive."""

    def __init__(self, model_dir: str = "models", min_candles: int = 100):
        self.model_dir = model_dir
        self.min_candles = max(min_candles, 50)
        self._init_cache()
        self.TF_MAPPING = {
            '1min': 'm1', '5min': 'm5', '15min': 'm15',
            '30min': 'm30', '1h': 'h1', '4h': 'h4',
            's1': 's1', '1m': 'm1', '5m': 'm5'
        }

    def _init_cache(self):
        self.model_cache = {}
        self.last_used = {}
        self.cache_expiry = timedelta(hours=1)

    def _normalize_timeframe(self, timeframe: str) -> str:
        tf = timeframe.lower().strip()
        return self.TF_MAPPING.get(tf, tf)

    def _ensure_model_local(self, symbol: str, timeframe: str) -> str:
        """Garante que o modelo está salvo localmente, baixando do Google Drive se necessário."""
        tf = self._normalize_timeframe(timeframe)
        sym = symbol.lower()
        filename = f"model_{sym}_{tf}.pkl"
        path = os.path.join(self.model_dir, filename)
        if not os.path.exists(path):
            try:
                logger.info(f"⬇️ Baixando modelo {filename} do Google Drive...")
                download_file(filename, path, drive_folder_id=get_folder_id_for_file(filename))
                logger.info(f"✅ Modelo {filename} baixado do Google Drive.")
            except Exception as e:
                logger.error(f"⚠️ Não foi possível baixar modelo {filename} do Google Drive: {e}")
        return path

    @lru_cache(maxsize=10)
    def _load_model(self, symbol: str, timeframe: str) -> Optional[object]:
        """Carrega modelo do disco (ou do Google Drive se necessário), com cache LRU."""
        try:
            sym = symbol.lower().strip()
            tf = self._normalize_timeframe(timeframe)
            model_key = (sym, tf)
            if model_key in self.model_cache:
                last_used = self.last_used.get(model_key)
                if last_used and (datetime.now() - last_used) < self.cache_expiry:
                    return self.model_cache[model_key]

            model_path = self._ensure_model_local(sym, tf)
            if not os.path.exists(model_path):
                logger.warning(f"Modelo não encontrado localmente nem no Drive: {model_path}")
                return None

            model_obj = joblib.load(model_path)
            if isinstance(model_obj, dict) and 'model' in model_obj:
                model = model_obj['model']
                self.features = model_obj.get('features', None)
            else:
                model = model_obj
                self.features = None

            if not hasattr(model, 'predict'):
                raise ValueError("Objeto carregado não é um modelo válido")

            self.model_cache[model_key] = model
            self.last_used[model_key] = datetime.now()
            logger.info(f"Modelo carregado: {sym.upper()} [{tf.upper()}]")
            return model
        except Exception as e:
            logger.error(f"Falha ao carregar modelo {symbol}/{timeframe}: {str(e)}")
            return None

    def _validate_candles(self, candles: List[Dict]) -> Optional[pd.DataFrame]:
        """Valida e converte lista de candles para DataFrame"""
        if not candles:
            logger.error("Lista de candles vazia")
            return None
        required_keys = {'open', 'high', 'low', 'close', 'volume', 'timestamp'}
        if not all(required_keys.issubset(c) for c in candles):
            logger.error("Candles com campos incompletos")
            return None
        try:
            df = pd.DataFrame(candles)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.sort_values('timestamp', inplace=True)
            return df
        except Exception as e:
            logger.error(f"Falha ao processar candles: {str(e)}")
            return None

    @staticmethod
    def add_technical_indicators(df: pd.DataFrame, timeframe: str = None, symbol: str = None) -> pd.DataFrame:

        if timeframe and timeframe.lower() in ['s1', '1s']:
            df = resample_candles(df, freq='10S')
        
        """Cálculo dos principais indicadores e features compatíveis com o pipeline de treino"""
        df = df.copy()
        # Rolling indicators
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(20).std()
        for period in [5, 10, 20, 50]:
            df[f'sma_{period}'] = df['close'].rolling(period).mean()
        for period in [12, 26]:
            df[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
        # RSI
        delta = df['close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(span=14, adjust=False).mean()
        avg_loss = loss.ewm(span=14, adjust=False).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        df['rsi'] = 100 - (100 / (1 + rs))
        # MACD
        ema12 = df['ema_12']
        ema26 = df['ema_26']
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        # Bollinger Bands
        sma20 = df['sma_20']
        rolling_std = df['close'].rolling(20).std()
        df['bb_upper'] = sma20 + 2 * rolling_std
        df['bb_lower'] = sma20 - 2 * rolling_std
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / sma20
        df['bb_pct'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        # ATR
        tr1 = df['high'] - df['low']
        tr2 = np.abs(df['high'] - df['close'].shift())
        tr3 = np.abs(df['low'] - df['close'].shift())
        true_range = np.maximum(np.maximum(tr1, tr2), tr3)
        df['atr'] = pd.Series(true_range).rolling(14).mean().values
        # Suporte/Resistência
        df['support'] = df['low'].rolling(10, min_periods=1).min()
        df['resistance'] = df['high'].rolling(10, min_periods=1).max()
        df['support_dist'] = df['close'] - df['support']
        df['resistance_dist'] = df['resistance'] - df['close']
        # Volume
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['volume_pct'] = df['volume'] / df['volume_sma']
        # Extras do projeto (compatível com pipeline de treino)
        closes, highs, lows, volumes = df['close'].tolist(), df['high'].tolist(), df['low'].tolist(), df['volume'].tolist()
        df["atr_proj"] = calc_atr(highs, lows, closes)
        df["adx"] = calc_adx(highs, lows, closes)
        bb_res = calc_bollinger(closes)
        if isinstance(bb_res, tuple) and len(bb_res) == 3:
            _, df["bb_width_proj"], df["bb_pos"] = bb_res
        else:
            df["bb_width_proj"] = 0
            df["bb_pos"] = 0
        df["ma_rating"] = calc_moving_averages(closes)
        macd_hist, macd_val, macd_signal = calc_macd(closes)
        rsi_val = calc_rsi(closes)
        df["osc_rating"] = calc_oscillators(rsi_val, macd_hist)
        df["volatility_proj"] = calc_volatility(closes)
        df["volume_status"] = calc_volume_status(volumes)
        df["sentiment"] = calc_sentiment(closes)
        df["variation"] = ((df["close"] - df["close"].shift(1)) / df["close"].shift(1)) * 100
        df["support_distance"] = df["close"] - df["support"]
        df["resistance_distance"] = df["resistance"] - df["close"]

        # OBV e Spread
        df["obv"] = calc_obv(df)
        df['spread'] = calc_spread(df)
        
        # Fundamentalistas para H4/D1
        if timeframe and timeframe.lower() in ['h4', 'd1']:
            df["cot"] = get_cot_feature(symbol)
            df["macro"] = get_macro_feature(symbol)
            df["sentiment_news"] = get_sentiment_feature(symbol)
        
        # Sempre garantir as colunas fundamentais, mesmo para timeframes baixos
        for col in ["cot", "macro", "sentiment_news"]:
            if col not in df.columns:
                df[col] = 0

        # Mapeamento para valores numérico
        ma_mapping = {"buy": 1, "sell": -1, "neutral": 0}
        osc_mapping = {"buy": 1, "sell": -1, "neutral": 0}
        vol_mapping = {"High": 1, "Low": 0}
        volstat_mapping = {"Spiked": 2, "Normal": 1, "Low": 0}
        sentiment_mapping = {"Optimistic": 1, "Neutral": 0, "Pessimistic": -1}
        df["ma_rating"] = df["ma_rating"].map(ma_mapping)
        df["osc_rating"] = df["osc_rating"].map(osc_mapping)
        df["volatility_proj"] = df["volatility_proj"].map(vol_mapping)
        df["volume_status"] = df["volume_status"].map(volstat_mapping)
        df["sentiment"] = df["sentiment"].map(sentiment_mapping)
        return df

    def _add_candlestick_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Adiciona padrões de candles clássicos + força dos padrões"""
        pattern_list = [
            "bullish_engulfing", "bearish_engulfing", "hammer", "shooting_star", "doji"
            # Adicione mais padrões aqui se desejar!
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

    def _get_features(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Seleciona e valida features para previsão (compatível com pipeline de treino)"""
        # Use a lista salva no modelo, se disponível, senão use o padrão
        features = getattr(self, "features", None)
        if not features:
            features = [
                'open', 'high', 'low', 'close', 'volume',
                'returns', 'volatility',
                'sma_5', 'sma_10', 'sma_20', 'sma_50',
                'ema_12', 'ema_26',
                'rsi', 'macd', 'macd_signal', 'macd_hist',
                'bb_upper', 'bb_lower', 'bb_width', 'bb_pct',
                'atr', 'volume_sma', 'volume_pct',
                "adx", "bb_width_proj", "bb_pos", "ma_rating", "osc_rating",
                "volatility_proj", "volume_status", "sentiment", "support_distance", "resistance_distance", "variation",
                "bullish_engulfing", "bearish_engulfing", "hammer", "shooting_star", "doji", "pattern_strength", "obv", "spread", "cot", "macro", "sentiment_news"
            ]
        missing = [f for f in features if f not in df.columns]
        if missing:
            logger.error(f"Features obrigatórias ausentes: {missing}")
            return None
        return df[features].iloc[[-1]]

    def predict(self, symbol: str, timeframe: str, candles: List[Dict]) -> Optional[str]:
        """
        Faz previsão de direção usando modelo de ML ('up', 'down' ou None)
        """
        try:
            if not candles or len(candles) < 30:
                logger.warning(f"Dados insuficientes: fornecidos {len(candles) if candles else 0} candles")
                return None

            df = self._validate_candles(candles)
            if df is None:
                return None

            # Mantém últimos candles necessários
            candles_to_use = candles[-self.min_candles:] if len(candles) >= self.min_candles else candles
            df = self._validate_candles(candles_to_use)
            if df is None:
                return None

            model = self._load_model(symbol, timeframe)
            if model is None:
                return None

            df = MLPredictor.add_technical_indicators(df, timeframe, symbol)
            df = self._add_candlestick_features(df)
            df.dropna(inplace=True)

            features = self._get_features(df)
            if features is None:
                return None

            pred = model.predict(features)
            return 'up' if pred[0] == 1 else 'down'

        except Exception as e:
            logger.error(f"Erro durante previsão: {str(e)}", exc_info=True)
            return None

    def predict_with_confidence(self, symbol: str, timeframe: str, candles: List[Dict]) -> Optional[Dict]:
        """
        Faz previsão e retorna direção, confiança, features e timestamp
        """
        try:
            prediction = self.predict(symbol, timeframe, candles)
            if prediction is None:
                return None

            df = self._validate_candles(candles)
            candles_to_use = candles[-self.min_candles:] if len(candles) >= self.min_candles else candles
            df = self._validate_candles(candles_to_use)
            if df is None:
                return None

            df = MLPredictor.add_technical_indicators(df, timeframe, symbol)
            df = self._add_candlestick_features(df)
            df.dropna(inplace=True)

            model = self._load_model(symbol, timeframe)
            features = self._get_features(df)
            if features is None:
                return None

            proba = model.predict_proba(features)[0]
            confidence = float(np.max(proba))
            features_dict = features.iloc[0].to_dict()

            return {
                'direction': prediction,
                'confidence': confidence,
                'features': features_dict,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Erro em predict_with_confidence: {str(e)}", exc_info=True)
            return None
