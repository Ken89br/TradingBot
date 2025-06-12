# strategy/train_model.py
import os
import pandas as pd
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from joblib import dump
from strategy.ml_utils import add_indicators

DATA_URL = os.getenv("TRAINING_DATA_CSV")  # Set in Render as ENV VAR

def load_data():
    if DATA_URL and DATA_URL.startswith("http"):
        print(f"⬇️ Downloading training data from {DATA_URL}")
        return pd.read_csv(DATA_URL)
    return pd.read_csv("training_data.csv")

def main():
    df = load_data()
    df = add_indicators(df)
    df.dropna(inplace=True)

    df["target"] = (df["close"].shift(-1) > df["close"]).astype(int)
    features = ["open", "high", "low", "close", "volume", "sma_5", "sma_10", "rsi_14", "macd", "macd_signal"]

    X_train, X_test, y_train, y_test = train_test_split(df[features], df["target"], test_size=0.2)
    clf = XGBClassifier(use_label_encoder=False, eval_metric="logloss")
    clf.fit(X_train, y_train)

    print("📊 Accuracy Report:")
    print(classification_report(y_test, clf.predict(X_test)))

    # Save to file
    model_path = "model.pkl"
    dump(clf, model_path)
    print(f"✅ Trained model saved: {model_path}")

if __name__ == "__main__":
    main()
  
