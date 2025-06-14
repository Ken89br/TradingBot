# data/tiingo_data.py

import os
import time
import requests
from datetime import datetime

class TiingoClient:
    def __init__(self):
        self.api_key = os.getenv("TIINGO_API_KEY", "MISSING_API_KEY")
        self.base_url = "https://api.tiingo.com/tiingo/fx"

    def fetch_candles(self, symbol, interval="1min", limit=5, retries=2):
        if not symbol or len(symbol) != 6:
            print(f"❌ Invalid symbol format: {symbol}")
            return None

        # Tiingo expects "EURUSD" → "eurusd"
        tiingo_symbol = symbol.lower()

        end = int(time.time())
        start = end - limit * 60

        url = f"{self.base_url}/prices"
        params = {
            "tickers": tiingo_symbol,
            "startDate": datetime.utcfromtimestamp(start).isoformat(),
            "resampleFreq": interval,
            "token": self.api_key
        }

        print(f"📡 Tiingo GET {url}")
        print(f"📦 Params: {params}")

        for attempt in range(retries + 1):
            try:
                res = requests.get(url, params=params, timeout=5)
                print(f"📥 Raw response: {res.status_code} {res.text}")

                if res.status_code != 200:
                    time.sleep(1)
                    continue

                data = res.json()

                if not data:
                    print("⚠️ No data returned from Tiingo.")
                    continue

                candles = []
                for row in data[-limit:]:
                    candles.append({
                        "timestamp": int(datetime.fromisoformat(row["date"]).timestamp()),
                        "open": row["open"],
                        "high": row["high"],
                        "low": row["low"],
                        "close": row["close"],
                        "volume": row.get("volume", 1) or 1  # fallback to 1 if None/0
                    })

                return {
                    "history": candles,
                    "close": candles[-1]["close"]
                }

            except Exception as e:
                print(f"❌ Exception from Tiingo: {e}")
                time.sleep(1)

        print("⛔ Max retries reached for Tiingo.")
        return None
                      
