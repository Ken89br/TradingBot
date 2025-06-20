# strategy/train_model_historic.py
import os
import glob
import pandas as pd
import joblib
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from datetime import datetime

from strategy.ml_utils import add_indicators

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

# Store last retrain time for each timeframe
LAST_RETRAIN_TIMES = {}

def get_timeframe_from_filename(filename):
    base = os.path.basename(filename).lower()
    for tf in RETRAIN_INTERVALS.keys():
        if f"_{tf}.csv" in base:
            return tf
    return None

def ensure_local_file(filename, folder="data"):
    """Baixa arquivo do Google Drive para pasta local se não existir."""
    local_path = os.path.join(folder, filename)
    if not os.path.exists(local_path):
        try:
            print(f"⬇️ Baixando {filename} do Google Drive...")
            download_file(filename, local_path)
            print(f"✅ Baixado {filename} do Google Drive.")
        except Exception as e:
            print(f"⚠️ Não foi possível baixar {filename}: {e}")
    return local_path

def load_data_grouped_by_timeframe():
    grouped = {}
    csv_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))

    for file in csv_files:
        tf = get_timeframe_from_filename(file)
        if not tf:
            continue

        try:
            # Garante que o arquivo está localmente, senão baixa do GDrive
            filename = os.path.basename(file)
            ensure_local_file(filename, folder=DATA_DIR)

            df = pd.read_csv(file)
            if not {"timestamp", "open", "high", "low", "close", "volume"}.issubset(df.columns):
                continue

            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df.sort_values("timestamp", inplace=True)
            df = add_indicators(df)
            df["target"] = (df["close"].shift(-1) > df["close"]).astype(int)
            df.dropna(inplace=True)

            grouped.setdefault(tf, []).append(df)
        except Exception as e:
            print(f"❌ Error reading {file}: {e}")

    return {tf: pd.concat(dfs) for tf, dfs in grouped.items() if dfs}

def train_model_for_timeframe(tf, df):
    print(f"\n🧠 Training model for timeframe: {tf.upper()} with {len(df)} rows")

    features = [
        "open", "high", "low", "close", "volume",
        "sma_5", "sma_10", "rsi_14", "macd", "macd_signal"
    ]

    X = df[features]
    y = df["target"]

    model = XGBClassifier(eval_metric="logloss")
    model.fit(X, y)

    print(classification_report(y, model.predict(X)))
    filename = f"model_{tf}.pkl"
    path = os.path.join(MODEL_DIR, filename)
    joblib.dump(model, path)
    print(f"✅ Saved model to: {path}")

    # Upload model to Google Drive
    try:
        upload_file(path)
        print(f"☁️ Arquivo {filename} enviado ao Google Drive!")
    except Exception as e:
        print(f"⚠️ Falha ao enviar {filename} ao Google Drive: {e}")

def ensure_latest_model(tf):
    """Garante que o modelo .pkl está localmente, se não, baixa do Drive."""
    filename = f"model_{tf}.pkl"
    path = os.path.join(MODEL_DIR, filename)
    if not os.path.exists(path):
        try:
            print(f"⬇️ Baixando modelo {filename} do Google Drive...")
            download_file(filename, path)
            print(f"✅ Modelo {filename} baixado do Google Drive.")
        except Exception as e:
            print(f"⚠️ Não foi possível baixar {filename}: {e}")

def main():
    grouped = load_data_grouped_by_timeframe()
    if not grouped:
        print("⛔ No valid data to train.")
        return

    now = datetime.utcnow()
    for tf, df in grouped.items():
        interval = RETRAIN_INTERVALS.get(tf, 60)  # default to 60s if missing
        last = LAST_RETRAIN_TIMES.get(tf)

        if not last or (now - last).total_seconds() >= interval:
            train_model_for_timeframe(tf, df)
            LAST_RETRAIN_TIMES[tf] = now
        else:
            time_left = interval - (now - last).total_seconds()
            print(f"⏳ Skipping {tf.upper()} — next in {round(time_left)}s")
        # Garante que o modelo mais recente está baixado localmente
        ensure_latest_model(tf)

if __name__ == "__main__":
    main()
