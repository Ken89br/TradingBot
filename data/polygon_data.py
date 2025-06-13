# data/polygon_data.py

import requests
import os
import time
from datetime import datetime

class PolygonClient:
    def __init__(self):
        self.api_key = os.getenv("POLYGON_API_KEY", "MISSING_API_KEY")
        self.base_url = "https://api.polygon.io"
        print(f"🧪 Formatted symbol: {formatted_symbol}")
        print(f"🔍 Final Polygon URL: {url}")


    def fetch_candles(self, symbol, interval="1min", limit=5, retries=2):
        if not symbol:
            print("❌ Symbol is empty.")
            return None

        # Format symbol for Polygon (Forex = C:, Stocks = X:)
        if ":" not in symbol:
            if symbol.isalpha() and len(symbol) <= 5:
                formatted_symbol = f"X:{symbol.upper()}"  # Stock
            elif len(symbol) == 6:
                formatted_symbol = f"C:{symbol.upper()}"  # Forex
            else:
                print(f"❌ Invalid symbol format: {symbol}")
                return None
        else:
            formatted_symbol = symbol

        now = int(time.time())
        from_unix = now - (limit * 60)

        url = f"{self.base_url}/v2/aggs/ticker/{formatted_symbol}/range/1/minute/{from_unix}/{now}"
        params = {
            "adjusted": "true",
            "sort": "asc",
            "limit": limit,
            "apiKey": self.api_key
        }

        print(f"🔍 Polygon GET {url}")
        print(f"📦 Params: {params}")

        for attempt in range(retries + 1):
            try:
                res = requests.get(url, params=params, timeout=5)
                if res.status_code != 200:
                    print(f"❌ HTTP {res.status_code}: {res.text}")
                    time.sleep(1)
                    continue

                data = res.json()
                if not isinstance(data, dict):
                print("❌ Unexpected response format:", data)
                return None
            
                print("📥 Polygon raw JSON:", data)

                if "results" not in data or not data["results"]:
                    print("⚠️ No valid candle data.", data)
                    continue

                candles = []
                for row in data["results"]:
                    candles.append({
                        "open": row["o"],
                        "high": row["h"],
                        "low": row["l"],
                        "close": row["c"],
                        "volume": row["v"],
                        "timestamp": row["t"]
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
