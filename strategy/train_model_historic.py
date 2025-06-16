# strategy/train_model_historic.py

import os
import glob
import pandas as pd
import joblib
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

from strategy.ml_utils import add_indicators

DATA_DIR = "data"
MODEL_DIR = "models"
os.makedirs(MODEL_DIR, exist_ok=True)

def get_timeframe_from_filename(filename):
    base = os.path.basename(filename).lower()
    for tf in ["s1", "m1", "m5", "m15", "m30", "h1", "h4", "d1"]:
        if f"_{tf}.csv" in base:
            return tf
    return None

def load_data_grouped_by_timeframe():
    grouped = {}
    csv_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))

    for file in csv_files:
        tf = get_timeframe_from_filename(file)
        if not tf:
            continue

        try:
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

    model = XGBClassifier(use_label_encoder=False, eval_metric="logloss")
    model.fit(X, y)

    print(classification_report(y, model.predict(X)))
    path = os.path.join(MODEL_DIR, f"model_{tf}.pkl")
    joblib.dump(model, path)
    print(f"✅ Saved model to: {path}")

def main():
    grouped = load_data_grouped_by_timeframe()
    if not grouped:
        print("⛔ No valid data to train.")
        return

    for tf, df in grouped.items():
        train_model_for_timeframe(tf, df)

if __name__ == "__main__":
    main()
                
