# strategy/train_model_historic.py
# Pipeline unificado: Treinamento de modelos com upload/download via Google Drive e máxima compatibilidade

import os
import glob
import logging
import joblib
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Tuple, List, Optional

from xgboost import XGBClassifier
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report
from sklearn.model_selection import TimeSeriesSplit

# Indicadores e padrões do seu projeto
from strategy.ml_utils import add_indicators
from strategy.candlestick_patterns import detect_candlestick_patterns, get_pattern_strength
from strategy.indicators import (
    calc_rsi, calc_macd, calc_bollinger, calc_atr, calc_adx,
    calc_moving_averages, calc_oscillators, calc_volatility,
    calc_volume_status, calc_sentiment
)

# Google Drive utilities
from data.google_drive_client import upload_or_update_file as upload_file, download_file, find_file_id, get_folder_id_for_file

from data.fundamental_data import get_cot_feature, get_macro_feature, get_sentiment_feature
from utils.features_extra import calc_obv, calc_spread
from utils.aggregation import resample_candles

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('model_training.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DATA_DIR = "data"
MODEL_DIR = "models"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

RETRAIN_INTERVALS = {
    "s1": 30, "m1": 60, "m5": 300, "m15": 900, "m30": 1800, "h1": 3600, "h4": 14400
}
LAST_RETRAIN_TIMES = {}

MIN_CANDLES = 100  # Patch: mínimo de candles válidos para treinar

def get_symbol_and_timeframe_from_filename(filename):
    base = os.path.basename(filename).lower()
    if "_" in base and base.endswith(".csv"):
        symbol, tf_part = base.rsplit("_", 1)
        tf = tf_part.replace(".csv", "")
        return symbol, tf
    return None, None

def ensure_local_file(filename, folder="data"):
    local_path = os.path.join(folder, filename)
    if not os.path.exists(local_path):
        try:
            logger.info(f"⬇️ Baixando {filename} do Google Drive...")
            download_file(filename, local_path, drive_folder_id=get_folder_id_for_file(filename))
            logger.info(f"✅ Baixado {filename} do Google Drive.")
        except Exception as e:
            logger.error(f"⚠️ Não foi possível baixar {filename}: {e}")
    return local_path

class DataProcessor:
    """Processamento seguro de dados temporais para trading"""

    @staticmethod
    def load_and_validate_data(filepath: str) -> Optional[pd.DataFrame]:
        try:
            df = pd.read_csv(filepath)
            required_cols = {"timestamp", "open", "high", "low", "close", "volume"}
            if not required_cols.issubset(df.columns):
                raise ValueError(f"Arquivo {filepath} não contém colunas necessárias")
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df.sort_values("timestamp", inplace=True)
            df = df.reset_index(drop=True)
            if df.isnull().values.any():
                logger.warning(f"Dados ausentes encontrados em {filepath}")
            return df
        except Exception as e:
            logger.error(f"Erro ao carregar {filepath}: {str(e)}", exc_info=True)
            return None

    @staticmethod
    def merge_and_save_candles(filepath, new_candles):
        # Mantém histórico anterior e adiciona apenas candles novos, sem duplicar timestamp
        if os.path.exists(filepath):
            try:
                df_old = pd.read_csv(filepath)
            except Exception:
                df_old = pd.DataFrame()
        else:
            df_old = pd.DataFrame()
        df_new = pd.DataFrame(new_candles)
        if df_new.empty:
            return
        if not df_old.empty:
            df_all = pd.concat([df_old, df_new], ignore_index=True)
        else:
            df_all = df_new
        df_all.drop_duplicates(subset=['timestamp'], keep='last', inplace=True)
        df_all.sort_values('timestamp', inplace=True)
        df_all.to_csv(filepath, index=False)

    @staticmethod
    def create_target_variable(df: pd.DataFrame, future_bars: int = 1) -> pd.DataFrame:
        """Cria variável target para previsão de tendência"""
        df = df.copy()
        future_price = df["close"].shift(-future_bars)
        df["target"] = (future_price > df["close"]).astype(int)
        df.dropna(subset=["target"], inplace=True)
        return df

    @staticmethod
    def temporal_split(df: pd.DataFrame, test_size: float = 0.2) -> Tuple[pd.DataFrame, pd.DataFrame]:
        split_idx = int(len(df) * (1 - test_size))
        return df.iloc[:split_idx], df.iloc[split_idx:]

class FeatureEngineer:
    """Engenharia de features para trading"""

    INDICATOR_CONFIG = {
        'sma_periods': [5, 10, 20, 50],
        'ema_periods': [12, 26],
        'rsi_period': 14,
        'macd_fast': 12,
        'macd_slow': 26,
        'macd_signal': 9,
        'bollinger_period': 20,
        'bollinger_std': 2,
        'atr_period': 14,
        'volatility_window': 20
    }

    @staticmethod
    # ADICIONE ISSO LOGO NO INÍCIO DE add_technical_indicators
    def add_technical_indicators(df: pd.DataFrame, timeframe: str = None) -> pd.DataFrame:
    # --- Agrupamento de S1 em 10s ---
        if timeframe and timeframe.lower() in ['s1', '1s']:
        df = resample_candles(df, freq='10S')

        """Adiciona indicadores técnicos e candlestick patterns"""
        df = df.copy()
        closes = df["close"].values
        highs = df["high"].values
        lows = df["low"].values

        # Retornos e Volatilidade
        df["returns"] = df["close"].pct_change()
        df["volatility"] = df["returns"].rolling(
            FeatureEngineer.INDICATOR_CONFIG['volatility_window']
        ).std()

        # Médias Móveis
        for period in FeatureEngineer.INDICATOR_CONFIG['sma_periods']:
            df[f"sma_{period}"] = df["close"].rolling(period).mean()
        for period in FeatureEngineer.INDICATOR_CONFIG['ema_periods']:
            df[f"ema_{period}"] = df["close"].ewm(span=period, adjust=False).mean()

        # RSI
        delta = df["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(span=FeatureEngineer.INDICATOR_CONFIG['rsi_period'], adjust=False).mean()
        avg_loss = loss.ewm(span=FeatureEngineer.INDICATOR_CONFIG['rsi_period'], adjust=False).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        df["rsi"] = 100 - (100 / (1 + rs))

        # MACD
        ema_fast = df[f"ema_{FeatureEngineer.INDICATOR_CONFIG['macd_fast']}"]
        ema_slow = df[f"ema_{FeatureEngineer.INDICATOR_CONFIG['macd_slow']}"]
        df["macd"] = ema_fast - ema_slow
        df["macd_signal"] = df["macd"].ewm(span=FeatureEngineer.INDICATOR_CONFIG['macd_signal'], adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]

        # Bollinger Bands
        sma = df[f"sma_{FeatureEngineer.INDICATOR_CONFIG['bollinger_period']}"]
        rolling_std = df["close"].rolling(FeatureEngineer.INDICATOR_CONFIG['bollinger_period']).std()
        df["bb_upper"] = sma + (FeatureEngineer.INDICATOR_CONFIG['bollinger_std'] * rolling_std)
        df["bb_lower"] = sma - (FeatureEngineer.INDICATOR_CONFIG['bollinger_std'] * rolling_std)
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / sma
        df["bb_pct"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])

        # ATR
        tr1 = highs - lows
        tr2 = np.abs(highs - df["close"].shift())
        tr3 = np.abs(lows - df["close"].shift())
        true_range = np.maximum(np.maximum(tr1, tr2), tr3)
        df["atr"] = pd.Series(true_range).rolling(FeatureEngineer.INDICATOR_CONFIG['atr_period']).mean().values

        # Volume Analysis
        df["volume_sma"] = df["volume"].rolling(20).mean()
        df["volume_pct"] = df["volume"] / df["volume_sma"]

        # Candlestick Patterns
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

        # Indicadores do seu projeto (rating, volatility, etc)
        closes_list = df["close"].tolist()
        highs_list = df["high"].tolist()
        lows_list = df["low"].tolist()
        volumes_list = df["volume"].tolist()
        df["atr_proj"] = calc_atr(highs_list, lows_list, closes_list)
        df["adx"] = calc_adx(highs_list, lows_list, closes_list)
        bb_res = calc_bollinger(closes_list)
        if isinstance(bb_res, tuple) and len(bb_res) == 3:
            _, df["bb_width_proj"], df["bb_pos"] = bb_res
        else:
            df["bb_width_proj"] = 0
            df["bb_pos"] = 0
        df["ma_rating"] = calc_moving_averages(closes_list)
        macd_hist, macd_val, macd_signal = calc_macd(closes_list)
        rsi_val = calc_rsi(closes_list)
        df["osc_rating"] = calc_oscillators(rsi_val, macd_hist)
        df["volatility_proj"] = calc_volatility(closes_list)
        df["volume_status"] = calc_volume_status(volumes_list)
        df["sentiment"] = calc_sentiment(closes_list)
        df["variation"] = ((df["close"] - df["close"].shift(1)) / df["close"].shift(1)) * 100
        df["support"] = df["low"].rolling(window=10, min_periods=1).min()
        df["resistance"] = df["high"].rolling(window=10, min_periods=1).max()
        df["support_distance"] = df["close"] - df["support"]
        df["resistance_distance"] = df["resistance"] - df["close"]

        # OBV e Spread
        df["obv"] = calc_obv(df)
        df["spread"] = calc_spread(df)

        # Fundamentalistas
        if timeframe and timeframe.lower() in ['h4', 'd1']:
            df["cot"] = get_cot_feature(symbol)
            df["macro"] = get_macro_feature(symbol)
            df["sentiment_news"] = get_sentiment_feature(symbol)

        # Mapeamento para valores numéricos compatíveis com o restante do bot
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

        # Preenche e limpa
        df.ffill(inplace=True)
        df.dropna(inplace=True)
        return df

    @staticmethod
    def get_feature_columns() -> List[str]:
        """Lista de features para treino - ajuste para compatibilidade"""
        return [
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

    @staticmethod
    def create_feature_pipeline() -> Pipeline:
        """Pipeline de transformação de features"""
        return Pipeline([
            ('imputer', SimpleImputer(strategy='mean')),
            ('scaler', StandardScaler())
        ])

class ModelTrainer:
    """Treinamento e avaliação de modelos"""

    MODEL_CONFIG = {
        'n_estimators': 300,
        'max_depth': 6,
        'learning_rate': 0.05,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'objective': 'binary:logistic',
        'eval_metric': 'logloss',
        'early_stopping_rounds': 50,
        'random_state': 42
    }

    def __init__(self):
        self.features = FeatureEngineer.get_feature_columns()
        self.feature_pipeline = FeatureEngineer.create_feature_pipeline()

    def prepare_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        X = self.feature_pipeline.fit_transform(df[self.features])
        y = df["target"].values
        return X, y

    def train_model(self, X: np.ndarray, y: np.ndarray) -> XGBClassifier:
        model = XGBClassifier(**self.MODEL_CONFIG)
        tscv = TimeSeriesSplit(n_splits=5)
        for train_idx, val_idx in tscv.split(X):
            X_train, X_val = X[train_idx], X[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]
            model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                verbose=10
            )
        return model

    def evaluate_model(self, model: XGBClassifier, X_test: np.ndarray, y_test: np.ndarray) -> Dict:
        y_pred = model.predict(X_test)
        clf_report = classification_report(y_test, y_pred, output_dict=True)
        return {"classification_report": clf_report}

    def save_model(self, model: XGBClassifier, symbol: str, tf: str) -> str:
        """Salva modelo SEM timestamp (sempre sobrescreve)"""
        model_name = f"model_{symbol}_{tf}.pkl"
        model_path = os.path.join(MODEL_DIR, model_name)
        joblib.dump({
            'model': model,
            'features': self.features,
            'pipeline': self.feature_pipeline,
            'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S")
        }, model_path)
        return model_path

def ensure_latest_model(symbol, tf):
    """Baixa modelo do Drive se não existir localmente (usado só na predição!)"""
    filename = f"model_{symbol.lower()}_{tf}.pkl"
    path = os.path.join(MODEL_DIR, filename)
    if not os.path.exists(path):
        try:
            logger.info(f"⬇️ Baixando modelo {filename} do Google Drive...")
            download_file(filename, path, drive_folder_id=get_folder_id_for_file(filename))
            logger.info(f"✅ Modelo {filename} baixado do Google Drive.")
        except Exception as e:
            logger.error(f"⚠️ Não foi possível baixar {filename}: {e}")

def train_pipeline(filepath: str) -> Optional[Dict]:
    """Pipeline completo para um arquivo de dados"""
    from data.data_client import FallbackDataClient
    try:
        logger.info(f"Iniciando processamento para: {filepath}")
        df = DataProcessor.load_and_validate_data(filepath)
        symbol, tf = get_symbol_and_timeframe_from_filename(os.path.basename(filepath))
        if not symbol or not tf:
            logger.warning(f"Arquivo com nome inesperado: {filepath}")
            return None

        if df is None or len(df) < MIN_CANDLES:
            logger.warning(f"Arquivo {filepath} inválido ou com poucos dados ({0 if df is None else len(df)} linhas). Buscando candles frescos...")
            fallback_client = FallbackDataClient()
            interval = tf
            candles_result = fallback_client.fetch_candles(symbol, interval=interval, limit=500)
            candles = candles_result["history"] if candles_result and "history" in candles_result else None
            if not candles or len(candles) < MIN_CANDLES:
                logger.error(f"Não foi possível obter candles válidos para {symbol}/{tf}. Abortando.")
                return None
            DataProcessor.merge_and_save_candles(filepath, candles)
            df = DataProcessor.load_and_validate_data(filepath)

        logger.info(f"Processando dados para {symbol}/{tf} ({len(df)} registros)")
        df = FeatureEngineer.add_technical_indicators(df, timeframe=tf)
        df = DataProcessor.create_target_variable(df, future_bars=3)
        train_df, test_df = DataProcessor.temporal_split(df, test_size=0.2)
        trainer = ModelTrainer()
        X_train, y_train = trainer.prepare_data(train_df)
        model = trainer.train_model(X_train, y_train)
        X_test, y_test = trainer.prepare_data(test_df)
        evaluation = trainer.evaluate_model(model, X_test, y_test)
        model_path = trainer.save_model(model, symbol, tf)
        logger.info(f"Modelo treinado e salvo em: {model_path}")
        logger.info("Relatório de classificação:\n%s", evaluation["classification_report"])
        try:
            file_id = upload_file(model_path)
            logger.info(f"☁️ Arquivo {os.path.basename(model_path)} enviado ao Google Drive! ID: {file_id}")
        except Exception as e:
            logger.error(f"⚠️ Falha ao enviar {os.path.basename(model_path)} ao Google Drive: {e}")
        return {
            "symbol": symbol,
            "timeframe": tf,
            "model_path": model_path,
            "evaluation": evaluation,
            "train_samples": len(train_df),
            "test_samples": len(test_df)
        }
    except Exception as e:
        logger.error(f"Erro no pipeline para {filepath}: {str(e)}", exc_info=True)
        return None
        
def main():
    """Fluxo principal"""
    try:
        logger.info("Iniciando pipeline de treinamento de modelos")
        data_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
        if not data_files:
            logger.error(f"Nenhum arquivo CSV encontrado em {DATA_DIR}")
            return
        logger.info(f"Encontrados {len(data_files)} arquivos para processamento")
        results = []
        now = datetime.utcnow()
        for filepath in data_files:
            symbol, tf = get_symbol_and_timeframe_from_filename(os.path.basename(filepath))
            if not symbol or not tf:
                logger.warning(f"Pulo arquivo com nome inesperado: {filepath}")
                continue
            interval = RETRAIN_INTERVALS.get(tf, 60)
            last = LAST_RETRAIN_TIMES.get((symbol, tf))
            if not last or (now - last).total_seconds() >= interval:
                ensure_local_file(os.path.basename(filepath), folder=DATA_DIR)
                result = train_pipeline(filepath)
                if result:
                    results.append(result)
                LAST_RETRAIN_TIMES[(symbol, tf)] = now
            else:
                time_left = interval - (now - last).total_seconds()
                logger.info(f"⏳ Skipping {symbol.upper()} [{tf.upper()}] — next in {round(time_left)}s")
            ensure_latest_model(symbol, tf)
        logger.info("\n=== Resumo do Treinamento ===")
        for res in results:
            logger.info(
                f"{res['symbol']} [{res['timeframe']}]: "
                f"Train={res['train_samples']}, Test={res['test_samples']}, "
                f"Accuracy={res['evaluation']['classification_report']['accuracy']:.2f}"
            )
        logger.info("Pipeline concluído com sucesso!")
    except Exception as e:
        logger.error(f"Erro fatal no pipeline principal: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
