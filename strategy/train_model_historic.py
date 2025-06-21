# strategy/train_model_historic.py
# Função principal: Treinar o(s) modelo(s) de machine learning com os dados históricos.
# Lê CSVs de dados de candles do diretório de dados.
# Adiciona colunas de indicadores técnicos (através do add_indicators e indicadores extras).
# Prepara os dados, define os alvos, divide em treino/teste.
# Treina um modelo XGBoost para cada símbolo e timeframe.
# Avalia o modelo e salva o arquivo .pkl do modelo treinado.
# Faz upload do modelo para o Google Drive.

import os
import glob
import pandas as pd
import joblib
from xgboost import XGBClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from datetime import datetime

from strategy.ml_utils import add_indicators

# Novos imports para indicadores extras
from strategy.indicators import (
    calc_rsi, calc_macd, calc_bollinger, calc_atr, calc_adx,
    calc_moving_averages, calc_oscillators, calc_volatility,
    calc_volume_status, calc_sentiment
)

# Google Drive integration
from data.google_drive_client import upload_file, download_file, find_file_id

# Directories
DATA_DIR = "data"
MODEL_DIR = "models"
os.makedirs(MODEL_DIR, exist_ok=True)

# Retraining frequency (in seconds) per timeframe
RETRAIN_INTERVALS = {
    "s1": 30,       # every 30 seconds
    "m1": 60,       # every 1 minute
    "m5": 300,      # every 5 minutes
    "m15": 900,     # every 15 minutes
    "m30": 1800,    # every 30 minutes
    "h1": 3600,     # every hour
    "h4": 14400     # every 4 hours
}

# Store last retrain time for each symbol/timeframe
LAST_RETRAIN_TIMES = {}

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
            print(f"⬇️ Baixando {filename} do Google Drive...")
            download_file(filename, local_path)
            print(f"✅ Baixado {filename} do Google Drive.")
        except Exception as e:
            print(f"⚠️ Não foi possível baixar {filename}: {e}")
    return local_path

def enrich_indicators(df):
    closes = df["close"].tolist()
    highs = df["high"].tolist()
    lows = df["low"].tolist()
    volumes = df["volume"].tolist()

    # Indicadores extras
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

    # Suporte e resistência: rolling min/max
    df["support"] = df["low"].rolling(window=10, min_periods=1).min()
    df["resistance"] = df["high"].rolling(window=10, min_periods=1).max()
    df["support_distance"] = df["close"] - df["support"]
    df["resistance_distance"] = df["resistance"] - df["close"]

    # Codificar variáveis categóricas
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

def load_data_grouped_by_symbol_and_timeframe():
    grouped = {}
    csv_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))

    for file in csv_files:
        symbol, tf = get_symbol_and_timeframe_from_filename(file)
        if not symbol or not tf:
            continue
        try:
            filename = os.path.basename(file)
            ensure_local_file(filename, folder=DATA_DIR)
            df = pd.read_csv(file)
            if not {"timestamp", "open", "high", "low", "close", "volume"}.issubset(df.columns):
                continue
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df.sort_values("timestamp", inplace=True)
            df = add_indicators(df)
            df = enrich_indicators(df)
            # Target: 1 = próxima candle sobe, 0 = cai/empata
            df["target"] = (df["close"].shift(-1) > df["close"]).astype(int)
            df.dropna(inplace=True)
            grouped.setdefault((symbol, tf), []).append(df)
        except Exception as e:
            print(f"❌ Error reading {file}: {e}")
    return {k: pd.concat(v) for k, v in grouped.items() if v}

def train_model_for_symbol_timeframe(symbol, tf, df):
    print(f"\n🧠 Training model for {symbol.upper()} [{tf.upper()}] with {len(df)} rows")
    features = [
        "open", "high", "low", "close", "volume",
        "sma_5", "sma_10", "rsi_14", "macd", "macd_signal",
        "atr", "adx", "bb_width", "bb_pos",
        "ma_rating", "osc_rating",
        "volatility", "volume_status", "sentiment",
        "support_distance", "resistance_distance", "variation"
    ]
    # Garante que só pega colunas existentes
    features = [f for f in features if f in df.columns]
    X = df[features]
    y = df["target"]

    # Split em treino e teste apenas para avaliação honesta
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, shuffle=False
    )

    model = XGBClassifier(eval_metric="logloss")
    model.fit(X_train, y_train)

    # Avaliação em dados de teste
    y_pred = model.predict(X_test)
    print("Relatório de classificação nos dados de teste:")
    print(classification_report(y_test, y_pred))

    filename = f"model_{symbol.lower()}_{tf}.pkl"
    path = os.path.join(MODEL_DIR, filename)
    joblib.dump(model, path)
    print(f"✅ Saved model to: {path}")

    try:
        upload_file(path)
        print(f"☁️ Arquivo {filename} enviado ao Google Drive!")
    except Exception as e:
        print(f"⚠️ Falha ao enviar {filename} ao Google Drive: {e}")

def ensure_latest_model(symbol, tf):
    filename = f"model_{symbol.lower()}_{tf}.pkl"
    path = os.path.join(MODEL_DIR, filename)
    if not os.path.exists(path):
        try:
            print(f"⬇️ Baixando modelo {filename} do Google Drive...")
            download_file(filename, path)
            print(f"✅ Modelo {filename} baixado do Google Drive.")
        except Exception as e:
            print(f"⚠️ Não foi possível baixar {filename}: {e}")

def main():
    grouped = load_data_grouped_by_symbol_and_timeframe()
    if not grouped:
        print("⛔ No valid data to train.")
        return

    now = datetime.utcnow()
    for (symbol, tf), df in grouped.items():
        interval = RETRAIN_INTERVALS.get(tf, 60)
        last = LAST_RETRAIN_TIMES.get((symbol, tf))
        if not last or (now - last).total_seconds() >= interval:
            train_model_for_symbol_timeframe(symbol, tf, df)
            LAST_RETRAIN_TIMES[(symbol, tf)] = now
        else:
            time_left = interval - (now - last).total_seconds()
            print(f"⏳ Skipping {symbol.upper()} [{tf.upper()}] — next in {round(time_left)}s")
        ensure_latest_model(symbol, tf)

if __name__ == "__main__":
    main()