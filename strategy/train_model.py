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
    path = download_csv(DATA_URL)
    df = pd.read_csv(path)
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
    # Step 1: Download latest model from GitHub or remote
    download_model(os.getenv("MODEL_URL"))

    # Step 2: Load and prepare training data
    df = load_data()
    if df.empty:
        print("⚠️ No data available for training.")
        return

    df["target"] = (df["close"].shift(-1) > df["close"]).astype(int)

    features = [
        "open", "high", "low", "close", "volume",
        "sma_5", "sma_10", "rsi_14", "macd", "macd_signal"
    ]

    X = df[features]
    y = df["target"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

    # Step 3: Train or update model
    clf = load_or_create_model()
    clf.fit(X_train, y_train)

    print("📊 Classification Report:")
    print(classification_report(y_test, clf.predict(X_test)))

    # Step 4: Save model
    joblib.dump(clf, MODEL_PATH)
    print(f"✅ Model saved: {MODEL_PATH}")

    # Step 5: Upload model to cloud (optional)
    upload_model(MODEL_PATH, os.getenv("UPLOAD_MODEL_URL"))

    # Step 6: Upload model to GitHub (optional)
    upload_to_github(
        file_path=MODEL_PATH,
        repo=os.getenv("GITHUB_REPO"),
        path="model/model.pkl",
        token=os.getenv("GITHUB_TOKEN"),
        commit_msg="Auto update model from Render"
    )

if __name__ == "__main__":
    main()
    
