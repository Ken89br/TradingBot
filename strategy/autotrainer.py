# strategy/autotrainer.py

import os
import time
from datetime import datetime, timedelta
import subprocess
import json
from strategy.train_model_historic import main as run_training
from config import CONFIG

SYMBOLS = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF", "NZDUSD",
    "USDCAD", "EURJPY", "EURNZD", "AEDCNY", "AUDCAD", "AUDCHF",
    "AUDNZD", "AUDUSD", "CADJPY", "CHFJPY", "EURGBP", "EURJPY",
    "EURUSD OTC", "GBPUSD OTC", "USDJPY OTC", "AUDUSD OTC"
]

TIMEFRAMES = ["s1", "m1", "m5", "m15", "m30", "h1", "h4"]

DATA_DIR = "data"
BOOTSTRAP_FLAG = "autotrainer_bootstrap.flag"
LAST_RETRAIN_PATH = "last_retrain.txt"

def fetch_and_save(symbol, from_dt, to_dt, timeframe):
    try:
        cmd = [
            "node", "--max-old-space-size=1024", "data/dukascopy_client.cjs",
            symbol.lower().replace(" ", ""), timeframe,
            from_dt.isoformat(), to_dt.isoformat()
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise RuntimeError(result.stderr)

        candles = json.loads(result.stdout)
        if not candles:
            print(f"⚠️ No candles fetched for {symbol} {timeframe}")
            return

        # Save to CSV
        path = os.path.join(DATA_DIR, f"{symbol.lower().replace(' ', '')}_{timeframe}.csv")
        header = not os.path.exists(path)
        with open(path, "a") as f:
            if header:
                f.write("timestamp,open,high,low,close,volume\n")
            for c in candles:
                f.write(f"{c['timestamp']},{c['open']},{c['high']},{c['low']},{c['close']},{c['volume']}\n")

        print(f"✅ Saved {len(candles)} rows for {symbol} [{timeframe}]")
    except Exception as e:
        print(f"❌ Error fetching {symbol} [{timeframe}]: {e}")

def bootstrap_initial_data():
    print("🚀 Bootstrapping 7-day historical data...")
    now = datetime.utcnow()
    from_dt = now - timedelta(days=7)
    for symbol in SYMBOLS:
        for tf in TIMEFRAMES:
            fetch_and_save(symbol, from_dt, now, tf)
    with open(BOOTSTRAP_FLAG, "w") as f:
        f.write("done")
    print("✅ Bootstrap complete.")

def should_retrain():
    now = datetime.utcnow()
    if not os.path.exists(LAST_RETRAIN_PATH):
        return True
    try:
        with open(LAST_RETRAIN_PATH, "r") as f:
            ts = f.read().strip()
            last = datetime.fromisoformat(ts)
        return (now - last).total_seconds() >= 30
    except:
        return True

def store_last_retrain_time():
    with open(LAST_RETRAIN_PATH, "w") as f:
        f.write(datetime.utcnow().isoformat())

def main():
    if not os.path.exists(BOOTSTRAP_FLAG):
        bootstrap_initial_data()

    while True:
        now = datetime.utcnow()
        from_dt = now - timedelta(seconds=30)
        print(f"⏱️ {now.isoformat()} - Fetching 30s slice...")

        for symbol in SYMBOLS:
            for tf in TIMEFRAMES:
                fetch_and_save(symbol, from_dt, now, tf)

        if should_retrain():
            print("🧠 Triggering retraining from AutoTrainer...")
            run_training()
            store_last_retrain_time()
        else:
            print("⏳ Skipping retrain (not due yet)")

        time.sleep(30)

if __name__ == "__main__":
    main()
            
