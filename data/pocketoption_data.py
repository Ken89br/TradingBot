import requests
import time
from datetime import datetime

class PocketOptionClient:
    def __init__(self):
        # Não requer autenticação para candles públicos
        self.base_url = "https://api.pocketoption.com/api/v1/public/candles"

    def _to_tf(self, interval):
        # Mapeia do padrão do projeto para o da API
        mapping = {
            "s1": 5,
            "m1": 60,
            "m5": 300,
            "m15": 900,
            "m30": 1800,
            "h1": 3600,
            "h4": 14400,
            "d1": 86400
        }
        return mapping.get(interval.lower(), 60)

    def fetch_candles(self, symbol, interval="m1", limit=5, retries=2):
        # Pocket Option usa "eurusd" minúsculo, sem OTC
        symbol_api = symbol.lower().replace(" ", "").replace("/", "")
        tf_sec = self._to_tf(interval)
        params = {
            "asset": symbol_api,
            "period": tf_sec,
            "limit": limit
        }
        url = self.base_url
        for attempt in range(retries + 1):
            try:
                res = requests.get(url, params=params, timeout=5)
                if res.status_code != 200:
                    time.sleep(1)
                    continue
                data = res.json()
                if not data or "data" not in data or not data["data"]:
                    continue
                candles = []
                for c in data["data"]:
                    candles.append({
                        "timestamp": int(c["time"]),
                        "open": float(c["open"]),
                        "high": float(c["high"]),
                        "low": float(c["low"]),
                        "close": float(c["close"]),
                        "volume": float(c.get("volume", 1))
                    })
                return {
                    "history": candles,
                    "close": candles[-1]["close"]
                }
            except Exception as e:
                print(f"❌ PocketOptionClient error: {e}")
                time.sleep(1)
        print("⛔ PocketOption: Max retries reached.")
        return None
