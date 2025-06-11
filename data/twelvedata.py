# data/twelvedata.py
import requests
import os

class TwelveDataClient:
    def __init__(self):
        self.api_key = os.getenv("TWELVE_DATA_API_KEY") or "MISSING_API_KEY"
        self.base_url = "https://api.twelvedata.com"

    def fetch_candles(self, symbol, interval="1min", limit=30):
        symbol = symbol.replace("/", "").upper()  # e.g., EUR/USD → EURUSD

        params = {
            "symbol": symbol,
            "interval": interval,
            "outputsize": limit,
            "apikey": self.api_key
        }

        try:
            url = f"{self.base_url}/time_series"
            print(f"🔍 Fetching candles for {symbol} with {interval}")
            print(f"🛰️  URL: {url}")
            print(f"📦  Params: {params}")
            response = requests.get(url, params=params)
            print(f"📥  Response: {response.status_code} {response.text}")
                return None

            data = response.json()

            if "values" not in data:
                print(f"⚠️ No data returned: {data}")
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
            print(f"❌ TwelveData fetch error: {e}")
            return None
