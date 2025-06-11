# data/twelvedata.py
import requests
import os
import time

class TwelveDataClient:
    def __init__(self):
        self.api_key = os.getenv("TWELVE_DATA_API_KEY", "MISSING_API_KEY")
        self.base_url = "https://api.twelvedata.com"

    def fetch_candles(self, symbol, interval="1min", limit=30, retries=2):
        symbol = symbol.replace("/", "").upper()  # e.g., EUR/USD → EURUSD

        params = {
            "symbol": symbol,
            "interval": interval,
            "outputsize": limit,
            "apikey": self.api_key
        }

        url = f"{self.base_url}/time_series"
        print(f"\n🔍 Fetching candles for {symbol} ({interval})")
        print(f"🛰️  URL: {url}")
        print(f"📦 Params: {params}")

        attempt = 0
        while attempt <= retries:
            try:
                response = requests.get(url, params=params, timeout=5)
                print(f"📥 Response {response.status_code}")

                if response.status_code != 200:
                    print(f"❌ HTTP Error: {response.text}")
                    attempt += 1
                    time.sleep(1)
                    continue

                data = response.json()

                if "values" not in data:
                    print(f"⚠️ Invalid response: {data}")
                    return None

                candles = []
                for entry in reversed(data["values"]):
                    candles.append({
                        "open": float(entry["open"]),
                        "high": float(entry["high"]),
                        "low": float(entry["low"]),
                        "close": float(entry["close"]),
                        "volume": float(entry.get("volume", 0))
                    })

                if not candles:
                    print("⚠️ No candles returned.")
                    return None

                return {
                    "history": candles,
                    "close": candles[-1]["close"]
                }

            except Exception as e:
                print(f"❌ Exception: {e}")
                attempt += 1
                time.sleep(1)

        return None
