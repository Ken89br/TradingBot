# strategy/train_model.py
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib
from ml_utils import add_indicators

# === Load your CSV ===
df = pd.read_csv("training_data.csv")  # Make sure you have this file

# === Add indicators ===
df = add_indicators(df)
df.dropna(inplace=True)

# === Label target ===
df["target"] = df["close"].shift(-1) > df["close"]
df["target"] = df["target"].astype(int)  # 1 = up, 0 = down

# === Features ===
features = ["open", "high", "low", "close", "volume", "sma_5", "sma_10", "rsi_14", "macd", "macd_signal"]
X = df[features]
y = df["target"]

# === Train ===
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X_train, y_train)

# === Evaluate ===
print(classification_report(y_test, clf.predict(X_test)))

# === Save model ===
joblib.dump(clf, "model.pkl")
print("✅ Model saved as model.pkl")
