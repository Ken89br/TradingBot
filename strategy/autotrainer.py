#strategy/autotrainer.py
import os
import time
import json
import subprocess
import glob
from dotenv import load_dotenv
from datetime import datetime, timedelta
from strategy.train_model_historic import main as run_training
from config import CONFIG
from data.google_drive_client import upload_file  # Google Drive integration
load_dotenv()

SYMBOLS = CONFIG["symbols"] + CONFIG.get("otc_symbols", [])
TIMEFRAMES = CONFIG["timeframes"]  # e.g. ["S1", "M1", "M5", ...]
DATA_DIR = "data"
MODEL_DIR = "models"
BOOTSTRAP_FLAG = "autotrainer_bootstrap.flag"
LAST_RETRAIN_PATH = "last_retrain.txt"

def fetch_and_save(symbol, from_dt, to_dt, tf):
    try:
        cmd = [
            "node", "data/dukascopy_client.cjs",
            symbol.lower().replace(" ", ""), tf.lower(),
            from_dt.isoformat(), to_dt.isoformat()
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
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

        # Upload CSV to Google Drive
        try:
            upload_file(filepath)
            print(f"☁️ Arquivo {filename} enviado ao Google Drive!")
        except Exception as e:
            print(f"⚠️ Falha ao enviar {filename} ao Google Drive: {e}")

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
    # Upload last retrain time to Drive
    try:
        upload_file(LAST_RETRAIN_PATH)
    except Exception as e:
        print(f"⚠️ Falha ao enviar {LAST_RETRAIN_PATH} ao Google Drive: {e}")

def upload_models_to_drive():
    for model_file in glob.glob(f"{MODEL_DIR}/model_*.pkl"):
        file_name = os.path.basename(model_file)
        try:
            upload_file(model_file)
            print(f"☁️ Arquivo {file_name} enviado ao Google Drive!")
        except Exception as e:
            print(f"❌ Falha ao enviar {file_name} ao Google Drive: {e}")

def upload_csvs_to_drive():
    for csv_file in glob.glob(f"{DATA_DIR}/*.csv"):
        file_name = os.path.basename(csv_file)
        try:
            upload_file(csv_file)
            print(f"☁️ Arquivo {file_name} enviado ao Google Drive!")
        except Exception as e:
            print(f"❌ Falha ao enviar {file_name} ao Google Drive: {e}")

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

        upload_csvs_to_drive()

        if should_retrain():
            print("🧠 Triggering retraining...")
            run_training()
            store_last_retrain_time()
            upload_models_to_drive()  # Upload models after training
        else:
            print("⏳ Skipping retraining...")

        time.sleep(30)

if __name__ == "__main__":
    main()
