# strategy/train_model.py

import os
import pandas as pd
import joblib
import requests
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

from strategy.ml_utils import (
    add_indicators,
    upload_model,
    upload_to_github,
    download_model
)

MODEL_PATH = "model.pkl"
DATA_URL = os.getenv("TRAINING_DATA_CSV", "training_data.csv")

def download_csv(url):
    if url.startswith("http"):
        print(f"⬇️ Downloading training data from {url}")
        r = requests.get(url)
        with open("training_data.csv", "wb") as f:
            f.write(r.content)
        return "training_data.csv"
    return url

def load_data():
    """
    Load training_data.csv if it exists; otherwise fallback to signals.csv
    """
    if os.path.exists("training_data.csv"):
        print("📄 Loading training_data.csv")
        df = pd.read_csv("training_data.csv")
    elif os.path.exists("signals.csv"):
        print("📄 training_data.csv missing — using signals.csv instead")
        df = pd.read_csv("signals.csv")
        if "close" not in df.columns and "price" in df.columns:
            df["close"] = df["price"]
    else:
        print("⚠️ No data found: training_data.csv or signals.csv")
        return pd.DataFrame()

    df = add_indicators(df)
    df.dropna(inplace=True)
    return df

def load_or_create_model():
    if os.path.exists(MODEL_PATH):
        print("🔁 Loading existing model.pkl...")
        return joblib.load(MODEL_PATH)
    else:
        print("🧠 Creating new XGBoost model...")
        return XGBClassifier(use_label_encoder=False, eval_metric="logloss")

def main():
    # Step 1: Download existing model if any
    download_model(os.getenv("MODEL_URL"))

    # Step 2: Load training data
    df = load_data()
    if df.empty:
        print("⚠️ No data available for training.")
        return

    # Step 3: Add target label
    df["target"] = (df["close"].shift(-1) > df["close"]).astype(int)

    features = [
        "open", "high", "low", "close", "volume",
        "sma_5", "sma_10", "rsi_14", "macd", "macd_signal"
    ]

    X = df[features]
    y = df["target"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

    # Step 4: Train model
    clf = load_or_create_model()
    clf.fit(X_train, y_train)

    print("📊 Classification Report:")
    print(classification_report(y_test, clf.predict(X_test)))

    # Step 5: Save model
    joblib.dump(clf, MODEL_PATH)
    print(f"✅ Model saved: {MODEL_PATH}")

    # Step 6: Upload model
    if os.path.exists(MODEL_PATH):
        upload_model(MODEL_PATH, os.getenv("UPLOAD_MODEL_URL"))
        upload_to_github(
            "model.pkl",
            repo=os.getenv("GITHUB_REPO"),
            path="model/model.pkl",
            token=os.getenv("GITHUB_TOKEN"),
            commit_msg="Auto update model from Render"
        )

    # Step 7: Upload training data
    if os.path.exists("training_data.csv"):
        upload_to_github(
            "training_data.csv",
            repo=os.getenv("GITHUB_REPO"),
            path="data/training_data.csv",
            token=os.getenv("GITHUB_TOKEN"),
            commit_msg="Auto update training data from Render"
        )

    # Step 8: Upload signals.csv if available
    if os.path.exists("signals.csv"):
        upload_to_github(
            "signals.csv",
            repo=os.getenv("GITHUB_REPO"),
            path="data/signals.csv",
            token=os.getenv("GITHUB_TOKEN"),
            commit_msg="Auto update signals from Render"
        )

if __name__ == "__main__":
    main()
    
