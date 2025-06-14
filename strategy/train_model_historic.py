#strategy/train_model_historic.py
import os
import pandas as pd
import joblib
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from strategy.ml_utils import add_indicators

MODEL_PATH = "model.pkl"
DUKASCOPY_PATH = os.getenv("DUKASCOPY_TRAINING_CSV", "data/EURUSD_dukascopy.csv")

def load_data():
    if not os.path.exists(DUKASCOPY_PATH):
        print(f"❌ Dukascopy CSV not found: {DUKASCOPY_PATH}")
        return pd.DataFrame()

    df = pd.read_csv(DUKASCOPY_PATH)
    print(f"📥 Loaded Dukascopy candles: {len(df)} rows")

    df = add_indicators(df)
    df.dropna(inplace=True)

    df["target"] = (df["close"].shift(-1) > df["close"]).astype(int)
    return df

def train_model(df):
    features = [
        "open", "high", "low", "close", "volume",
        "sma_5", "sma_10", "rsi_14", "macd", "macd_signal"
    ]

    X = df[features]
    y = df["target"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

    clf = XGBClassifier(use_label_encoder=False, eval_metric="logloss")
    clf.fit(X_train, y_train)

    print("📊 Model trained.")
    print(classification_report(y_test, clf.predict(X_test)))

    joblib.dump(clf, MODEL_PATH)
    print(f"✅ Model saved to {MODEL_PATH}")

def main():
    df = load_data()
    if df.empty:
        print("⚠️ No training data — skipping.")
        return
    train_model(df)

if __name__ == "__main__":
    main()
  
