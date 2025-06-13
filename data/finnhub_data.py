# data/finnhub_data.py
import requests
import os
import time
from datetime import datetime

class FinnhubClient:
    def __init__(self):
        self.api_key = os.getenv("FINNHUB_API_KEY", "MISSING_API_KEY")
        self.base_url = "https://finnhub.io/api/v1"

    def fetch_candles(self, symbol, interval="1", limit=5, retries=2):
        resolution_map = {
            "1": "1", "5": "5", "15": "15",
            "30": "30", "60": "60", "D": "D"
        }
        resolution = resolution_map.get(interval, "1")

        now = int(time.time())
        from_unix = now - limit * 60

        url = f"{self.base_url}/stock/candle"
        params = {
            "symbol": symbol,
            "resolution": resolution,
            "from": from_unix,
            "to": now,
            "token": self.api_key
        }

        print(f"📡 Finnhub GET {url}")
        print(f"📦 Params: {params}")

        for attempt in range(retries + 1):
            try:
                res = requests.get(url, params=params, timeout=5)
                print(f"📥 Raw response: {res.status_code} {res.text}")

                if res.status_code == 429:
                    print("⏳ Rate limit hit — sleeping 30s")
                    time.sleep(30)
                    continue

                if res.status_code != 200:
                    print(f"❌ HTTP {res.status_code}")
                    time.sleep(1)
                    continue

                data = res.json()

                if data.get("s") != "ok" or not data.get("c"):
                    print("⚠️ No candle data:", data)
                    continue

                candles = []
                for i in range(len(data["t"])):
                    candles.append({
                        "timestamp": data["t"][i],
                        "open": data["o"][i],
                        "high": data["h"][i],
                        "low": data["l"][i],
                        "close": data["c"][i],
                        "volume": data["v"][i]
                    })

                return {
                    "history": candles,
                    "close": candles[-1]["close"]
                }

            except Exception as e:
                print(f"❌ Exception: {e}")
                time.sleep(1)

        print("⛔ Max retries reached.")
        return None
