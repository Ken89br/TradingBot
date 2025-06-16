#straregy/autotrainer.py

import time
import os
import subprocess
import json
import pandas as pd
from datetime import datetime, timedelta
from strategy.train_model_historic import main as retrain_model
from config import CONFIG

def convert_tf(interval):
    return {
        "S1": "s1", "M1": "m1", "M5": "m5", "M15": "m15",
        "M30": "m30", "H1": "h1", "H4": "h4", "D1": "d1"
    }.get(interval, "m1")

def fetch_from_dukascopy(symbol, timeframe):
    now = datetime.utcnow()
    from_dt = now - timedelta(seconds=30)

    cmd = [
        "node", "data/dukascopy_client.cjs",
        symbol.lower(), convert_tf(timeframe),
        from_dt.isoformat(), now.isoformat()
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    candles = json.loads(result.stdout)
    return candles

def save_to_csv(symbol, timeframe, candles):
    if not candles:
        return
    symbol = symbol.replace(" ", "_").lower()
    tf_code = convert_tf(timeframe)
    path = f"data/{symbol}_{tf_code}.csv"
    header = not os.path.exists(path)

    with open(path, "a") as f:
        if header:
            f.write("timestamp,open,high,low,close,volume\n")
        for c in candles:
            f.write(f"{c['timestamp']},{c['open']},{c['high']},{c['low']},{c['close']},{c['volume']}\n")

def main_loop():
    all_symbols = CONFIG["symbols"]
    timeframes = CONFIG["timeframes"]

    print("🔁 Starting auto-trainer loop...")

    while True:
        for symbol in all_symbols:
            for tf in timeframes:
                try:
                    print(f"📡 Fetching {symbol} @ {tf}")
                    candles = fetch_from_dukascopy(symbol, tf)
                    save_to_csv(symbol, tf, candles)
                except Exception as e:
                    print(f"❌ Error fetching {symbol}@{tf}: {e}")
        try:
            print("🧠 Training model...")
            retrain_model()
        except Exception as e:
            print(f"❌ Training failed: {e}")

        print("⏳ Sleeping for 30s...\n")
        time.sleep(30)

if __name__ == "__main__":
    main_loop()
  

