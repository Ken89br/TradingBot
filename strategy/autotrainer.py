import os
import time
import json
import subprocess
import glob
from dotenv import load_dotenv
from datetime import datetime, timedelta
from strategy.train_model_historic import main as run_training
from config import CONFIG
from utils.github_uploader import upload_to_github
load_dotenv()

SYMBOLS = CONFIG["symbols"] + CONFIG.get("otc_symbols", [])
TIMEFRAMES = CONFIG["timeframes"]  # e.g. ["S1", "M1", "M5", ...]
DATA_DIR = "data"
MODEL_DIR = "models"
REPO_NAME = "Ken89br/TradingBot"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
BOOTSTRAP_FLAG = "autotrainer_bootstrap.flag"
LAST_RETRAIN_PATH = "last_retrain.txt"

def fetch_and_save(symbol, from_dt, to_dt, tf):
    try:
        cmd = [
            "node", "data/dukascopy_client.cjs",
            symbol.lower().replace(" ", ""), tf.lower(),
            from_dt.isoformat(), to_dt.isoformat()
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise RuntimeError(result.stderr)

        candles = json.loads(result.stdout)
        if not candles:
            print(f"⚠️ No candles for {symbol} @ {tf}")
            return

        os.makedirs(DATA_DIR, exist_ok=True)
        filename = f"{symbol.lower().replace(' ', '')}_{tf.lower()}.csv"
        filepath = os.path.join(DATA_DIR, filename)

        header = not os.path.exists(filepath)
        with open(filepath, "a") as f:
            if header:
                f.write("timestamp,open,high,low,close,volume\n")
            for c in candles:
                f.write(f"{c['timestamp']},{c['open']},{c['high']},{c['low']},{c['close']},{c['volume']}\n")

        print(f"✅ Saved {len(candles)} rows for {symbol} [{tf}] to {filepath}")
    except Exception as e:
        print(f"❌ Error fetching {symbol} @ {tf}: {e}")

def bootstrap_initial_data():
    print("🚀 Bootstrapping full 7-day historical data...")
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
            last = datetime.fromisoformat(f.read().strip())
        return (now - last).total_seconds() >= 120  # Every 2 minutes
    except:
        return True

def store_last_retrain_time():
    with open(LAST_RETRAIN_PATH, "w") as f:
        f.write(datetime.utcnow().isoformat())

def upload_models_to_github():
    for model_file in glob.glob(f"{MODEL_DIR}/model_*.pkl"):
        file_name = os.path.basename(model_file)
        success = upload_to_github(
            model_file,
            REPO_NAME,
            f"models/{file_name}",
            GITHUB_TOKEN,
            commit_msg=f"Update {file_name}"
        )
        if not success:
            print(f"❌ Failed to upload {file_name}")
        else:
            print(f"📤 Uploaded: {file_name}")

def upload_csvs_to_github():
    for csv_file in glob.glob(f"{DATA_DIR}/*.csv"):
        file_name = os.path.basename(csv_file)
        success = upload_to_github(
            csv_file,
            REPO_NAME,
            f"data/{file_name}",
            GITHUB_TOKEN,
            commit_msg=f"Update {file_name}"
        )
        if not success:
            print(f"❌ Failed to upload {file_name}")
        else:
            print(f"📤 Uploaded: {file_name}")

def main():
    if not os.path.exists(BOOTSTRAP_FLAG):
        bootstrap_initial_data()

    while True:
        print(f"\n⏱️ {datetime.utcnow().isoformat()} - Fetching 30s slice")
        now = datetime.utcnow()
        from_dt = now - timedelta(seconds=30)

        for symbol in SYMBOLS:
            for tf in TIMEFRAMES:
                fetch_and_save(symbol, from_dt, now, tf)

        upload_csvs_to_github()

        if should_retrain():
            print("🧠 Triggering retraining...")
            run_training()
            store_last_retrain_time()
            upload_models_to_github()  # ✅ Upload models after training
        else:
            print("⏳ Skipping retraining...")

        time.sleep(30)

if __name__ == "__main__":
    main()
    
