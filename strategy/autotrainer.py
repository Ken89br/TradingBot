# autotrainer.py
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

TIMEFRAME = "m1"  # Always use 1-min for training

DATA_DIR = "data"
BOOTSTRAP_FLAG = "autotrainer_bootstrap.flag"
LAST_RETRAIN_PATH = "last_retrain.txt"

def fetch_and_save(symbol, from_dt, to_dt):
    try:
        cmd = [
            "node", "data/dukascopy_client.cjs",
            symbol.lower().replace(" ", ""), TIMEFRAME,
            from_dt.isoformat(), to_dt.isoformat()
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(result.stderr)

        candles = json.loads(result.stdout)
        if not candles:
            print(f"⚠️ No candles fetched for {symbol}")
            return

        # Save to CSV
        path = os.path.join(DATA_DIR, f"{symbol.lower().replace(' ', '')}_{TIMEFRAME}.csv")
        header = not os.path.exists(path)
        with open(path, "a") as f:
            if header:
                f.write("timestamp,open,high,low,close,volume\n")
            for c in candles:
                f.write(f"{c['timestamp']},{c['open']},{c['high']},{c['low']},{c['close']},{c['volume']}\n")

        print(f"✅ Saved {len(candles)} rows for {symbol}")
    except Exception as e:
        print(f"❌ Error fetching {symbol}: {e}")

def bootstrap_initial_data():
    print("🚀 Bootstrapping 7-day historical data...")
    now = datetime.utcnow()
    from_dt = now - timedelta(days=7)
    for symbol in SYMBOLS:
        fetch_and_save(symbol, from_dt, now)
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
    # Only bootstrap if flag doesn't exist
    if not os.path.exists(BOOTSTRAP_FLAG):
        bootstrap_initial_data()

    while True:
        print(f"⏱️ {datetime.utcnow().isoformat()} - Fetching 30s slice")
        now = datetime.utcnow()
        from_dt = now - timedelta(seconds=30)

        for symbol in SYMBOLS:
            fetch_and_save(symbol, from_dt, now)

        if should_retrain():
            print("🧠 Triggering retraining from AutoTrainer...")
            run_training()
            store_last_retrain_time()
        else:
            print("⏳ Skipping retrain (not due yet)")

        time.sleep(30)

if __name__ == "__main__":
    main()
                
