# data/polygon_data.py

import requests
import os
import time

class PolygonClient:
    def __init__(self):
        self.api_key = os.getenv("POLYGON_API_KEY", "MISSING_API_KEY")
        self.base_url = "https://api.polygon.io"

    def fetch_candles(self, symbol, interval="1min", limit=5, retries=2):
        if len(symbol) != 6:
            print(f"❌ Invalid symbol format: {symbol}")
            return None

        formatted_symbol = f"C:{symbol.upper()}"

        # Build dates
        end_unix = int(time.time())
        start_unix = end_unix - (limit * 60)

        from_date = time.strftime("%Y-%m-%d", time.gmtime(start_unix))
        to_date = time.strftime("%Y-%m-%d", time.gmtime(end_unix))

        url = f"{self.base_url}/v2/aggs/ticker/{formatted_symbol}/range/1/minute/{from_date}/{to_date}"
        params = {
            "adjusted": "true",
            "sort": "desc",
            "limit": limit,
            "apiKey": self.api_key
        }

        print(f"🔍 Polygon GET {url}")
        print(f"📦 Params: {params}")

        for attempt in range(retries + 1):
            try:
                res = requests.get(url, params=params, timeout=5)
                data = res.json()
                print("📥 Polygon raw JSON:", data)

                if "results" not in data or not data["results"]:
                    print("⚠️ No candle data.")
                    continue

                # Sort candles oldest → newest
                results = sorted(data["results"], key=lambda x: x["t"])

                candles = []
                for row in results:
                    candles.append({
                        "open": row["o"],
                        "high": row["h"],
                        "low": row["l"],
                        "close": row["c"],
                        "volume": row["v"]
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
        
