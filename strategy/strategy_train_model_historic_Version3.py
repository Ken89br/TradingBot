import os
import glob
import pandas as pd
from datetime import datetime
from strategy.ml_utils import add_indicators
from data.google_drive_client import upload_file, download_file

DATA_DIR = "data"
MODEL_DIR = "models"
RETRAIN_INTERVALS = {
    "s1": 60, "m1": 60, "m5": 120, "m15": 300, "m30": 600, "h1": 1800, "h4": 3600, "d1": 86400
}
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
            df["target"] = (df["close"].shift(-1) > df["close"]).astype(int)
            df.dropna(inplace=True)
            grouped.setdefault((symbol, tf), []).append(df)
        except Exception as e:
            print(f"❌ Error reading {file}: {e}")
    return {k: pd.concat(v) for k, v in grouped.items() if v}

def train_model_for_symbol_timeframe(symbol, tf, df):
    from xgboost import XGBClassifier
    from sklearn.metrics import classification_report
    import joblib

    print(f"\n🧠 Training model for {symbol.upper()} [{tf.upper()}] with {len(df)} rows")
    features = [
        "open", "high", "low", "close", "volume",
        "sma_5", "sma_10", "rsi_14", "macd", "macd_signal"
    ]
    X = df[features]
    y = df["target"]

    model = XGBClassifier(eval_metric="logloss")
    model.fit(X, y)

    print(classification_report(y, model.predict(X)))
    filename = f"model_{symbol.lower()}_{tf}.pkl"
    os.makedirs(MODEL_DIR, exist_ok=True)
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