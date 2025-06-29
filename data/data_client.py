#data/data_client.py
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
from data.google_drive_client import upload_or_update_file as upload_file, download_file, find_file_id, get_folder_id_for_file

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
                    self._save_to_csv(symbol, interval, result["history"])
                    return result
            except Exception as e:
                print(f"❌ Fallback #{i+1} error: {e}")
        print("❌ All providers failed.")
        return None

    def _fetch_from_dukascopy(self, symbol, interval):
        now = datetime.utcnow()

        # Se for a primeira chamada, tenta baixar arquivo do Google Drive antes de criar novo
        filename = f"{symbol.lower()}_{self._convert_tf(interval)}.csv"
        filepath = f"data/{filename}"
        if not os.path.exists(filepath):
            try:
                print(f"⬇️ Baixando {filename} do Google Drive...")
                download_file(filename, filepath, drive_folder_id=get_folder_id_for_file(filename))
                print(f"✅ Baixado {filename} do Google Drive.")
            except Exception as e:
                print(f"⚠️ Não foi possível baixar {filename}: {e}")

        # Se for a primeira chamada desde o start, busca 7 dias
        if not self.initialized:
            from_dt = now - timedelta(days=7)
            self.initialized = True
        else:
            from_dt = now - timedelta(seconds=30)

        cmd = [
            "node", "--max-old-space-size=1024", "data/dukascopy_client.cjs",
            symbol.lower(), self._convert_tf(interval),
            from_dt.isoformat(), now.isoformat()
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
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
        filename = f"{symbol.lower()}_{self._convert_tf(interval)}.csv"
        path = f"data/{filename}"
        header = not os.path.exists(path)
        with open(path, "a") as f:
            if header:
                f.write("timestamp,open,high,low,close,volume\n")
            for c in candles:
                line = f"{c['timestamp']},{c['open']},{c['high']},{c['low']},{c['close']},{c['volume']}\n"
                f.write(line)
        try:
            file_id = upload_file(path)
            print(f"☁️ Arquivo {filename} enviado ao Google Drive! ID: {file_id}")
        except Exception as e:
            print(f"⚠️ Falha ao enviar {filename} ao Google Drive: {e}")

    def _maybe_retrain(self):
        now = datetime.utcnow()
        last = self._load_last_retrain_time()
        if not last or (now - last).total_seconds() >= 30:
            print("🧠 Triggering model retraining...")
            run_training()
            self._store_last_retrain_time(now)

    def _load_last_retrain_time(self):
        # Tenta pegar do Google Drive primeiro
        try:
            if not os.path.exists(LAST_RETRAIN_PATH):
                download_file(LAST_RETRAIN_PATH, LAST_RETRAIN_PATH, drive_folder_id=get_folder_id_for_file(LAST_RETRAIN_PATH))
        except Exception as e:
            pass
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
        try:
            upload_file(LAST_RETRAIN_PATH)
        except Exception as e:
            print(f"⚠️ Falha ao enviar {LAST_RETRAIN_PATH} ao Google Drive: {e}")

    def _convert_tf(self, interval):
        return {
            "1min": "m1", "5min": "m5", "15min": "m15",
            "30min": "m30", "1h": "h1",
            "4h": "h4", "1day": "d1", "s1": "s1"
        }.get(interval.lower(), "m1")
