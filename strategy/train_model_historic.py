# strategy/train_model_historic.py

import os
import glob
import pandas as pd
import joblib
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from strategy.ml_utils import add_indicators

MODEL_PATH = "model.pkl"
DATA_DIR = "data"

def load_all_dukas_data():
    all_files = glob.glob(os.path.join(DATA_DIR, "dukascopy_*.csv"))
    all_dfs = []

    for file in all_files:
        try:
            df = pd.read_csv(file)
            if not {"timestamp", "open", "high", "low", "close", "volume"}.issubset(df.columns):
                print(f"⚠️ Skipping {file}, missing OHLCV columns")
                continue

            df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')
            df = df.sort_values("timestamp")
            df = add_indicators(df)
            df["target"] = (df["close"].shift(-1) > df["close"]).astype(int)
            df.dropna(inplace=True)
            all_dfs.append(df)
        except Exception as e:
            print(f"❌ Error processing {file}: {e}")

    if not all_dfs:
        print("⚠️ No valid data found in Dukascopy CSVs.")
        return pd.DataFrame()

    return pd.concat(all_dfs, ignore_index=True)

def main():
    print("📥 Loading Dukascopy historical data...")
    df = load_all_dukas_data()

    if df.empty:
        print("⛔ No training data available.")
        return

    features = [
        "open", "high", "low", "close", "volume",
        "sma_5", "sma_10", "rsi_14", "macd", "macd_signal"
    ]

    X = df[features]
    y = df["target"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

    clf = XGBClassifier(use_label_encoder=False, eval_metric="logloss")
    clf.fit(X_train, y_train)

    print("📊 Classification Report:")
    print(classification_report(y_test, clf.predict(X_test)))

    joblib.dump(clf, MODEL_PATH)
    print(f"✅ Model saved to {MODEL_PATH}")

if __name__ == "__main__":
    main()
    
