import subprocess
import json
import os
import pandas as pd
import joblib
from datetime import datetime, timedelta
from data.twelvedata_data import TwelveDataClient
from data.tiingo_data import TiingoClient
from data.polygon_data import PolygonClient
from strategy.train_model_historic import main as run_training

LAST_RETRAIN_PATH = "last_retrain.txt"

class FallbackDataClient:
    IN_ROWS_BEFORE_RETRAIN = 50
    def __init__(self):
        self.providers = [
            TwelveDataClient(),
            TiingoClient(),
            PolygonClient()
        ]
        self.initialized = False

    def fetch_candles(self, symbol, interval="1min", limit=5):
        print(f"📡 Fetching from Dukascopy: {symbol} @ {interval}")
        try:
            candles = self._fetch_from_dukascopy(symbol, interval)
            if candles and "history" in candles:
                print("✅ Dukascopy succeeded.")
                self._save_to_csv(symbol, interval, candles["history"])
                self._maybe_retrain()
                return candles
        except Exception as e:
            print(f"❌ Dukascopy failed: {e}")

        # Try fallbacks
        for i, provider in enumerate(self.providers):
            print(f"⚙️ Trying fallback #{i+1}: {provider.__class__.__name__}")
            try:
                result = provider.fetch_candles(symbol, interval=interval, limit=limit)
                if result and "history" in result:
                    print(f"✅ Success from fallback: {provider.__class__.__name__}")
                    return result
            except Exception as e:
                print(f"❌ Fallback #{i+1} error: {e}")
        print("❌ All providers failed.")
        return None

    def _fetch_from_dukascopy(self, symbol, interval):
        now = datetime.utcnow()

        # If it's the first call since start, fetch 7 days
        if not self.initialized:
            from_dt = now - timedelta(days=7)
            self.initialized = True
        else:
            from_dt = now - timedelta(seconds=30)

        cmd = [
            "node", "--max-old-space-size=5120", "data/dukascopy_client.cjs",
            symbol.lower(), self._convert_tf(interval),
            from_dt.isoformat(), now.isoformat()
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(result.stderr)

        candles = json.loads(result.stdout)
        return {
            "history": candles,
            "close": candles[-1]["close"] if candles else None
        }

    def _save_to_csv(self, symbol, interval, candles):
        if not candles:
            return
        path = f"data/{symbol.lower()}_{self._convert_tf(interval)}.csv"
        header = not os.path.exists(path)
        with open(path, "a") as f:
            if header:
                f.write("timestamp,open,high,low,close,volume\n")
            for c in candles:
                line = f"{c['timestamp']},{c['open']},{c['high']},{c['low']},{c['close']},{c['volume']}\n"
                f.write(line)

    def _maybe_retrain(self):
        now = datetime.utcnow()
        last = self._load_last_retrain_time()
        if not last or (now - last).total_seconds() >= 30:
            print("🧠 Triggering model retraining...")
            run_training()
            self._store_last_retrain_time(now)

    def _load_last_retrain_time(self):
        if not os.path.exists(LAST_RETRAIN_PATH):
            return None
        try:
            with open(LAST_RETRAIN_PATH, "r") as f:
                ts = f.read().strip()
                return datetime.fromisoformat(ts)
        except:
            return None

    def _store_last_retrain_time(self, dt):
        with open(LAST_RETRAIN_PATH, "w") as f:
            f.write(dt.isoformat())

    def _convert_tf(self, interval):
        return {
            "1min": "m1", "5min": "m5", "15min": "m15",
            "30min": "m30", "1h": "h1",
            "4h": "h4", "1day": "d1", "s1": "s1"
        }.get(interval.lower(), "m1")
    
