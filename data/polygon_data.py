# data/polygon_data.py

import requests
import os
import time

class PolygonClient:
    def __init__(self):
        self.api_key = os.getenv("POLYGON_API_KEY", "MISSING_API_KEY")
        self.base_url = "https://api.polygon.io"
    
    def fetch_candles(self, symbol, interval="1min", limit=30, retries=2):
        interval_map = {
            "1min": "1", "5min": "5", "15min": "15",
            "30min": "30", "1h": "60", "4h": "240", "1day": "D"
        }
        # Convert to Polygon's expected timeframe format
        resolution = interval_map.get(interval, "1")
        
        # Format symbol: EURUSD → C:EURUSD
        if len(symbol) != 6:
            print(f"❌ Invalid symbol format: {symbol}")
            return None
        formatted_symbol = f"C:{symbol.upper()}"

        # Calculate Unix timestamps
        end = int(time.time())
        start = end - (limit * 60)

        # Polygon expects YYYY-MM-DD dates in the path
        from_date = time.strftime("%Y-%m-%d", time.gmtime(start))
        to_date = time.strftime("%Y-%m-%d", time.gmtime(end))

        url = f"{self.base_url}/v2/aggs/ticker/{formatted_symbol}/range/1/minute/{from_date}/{to_date}"
        params = {
            "adjusted": "true",
            "sort": "desc",
            "limit": limit,
            "apiKey": self.api_key
        }

        print(f"🔍 Fetching {formatted_symbol} from Polygon.io")
        print(f"🛰️ URL: {url}")
        print(f"📦 Params: {params}")

        for attempt in range(retries + 1):
            try:
                response = requests.get(url, params=params, timeout=5)
                if response.status_code != 200:
                    print(f"❌ HTTP {response.status_code}: {response.text}")
                    time.sleep(1)
                    continue

                data = response.json()
                print("📥 Polygon raw JSON:", data)

                if not data or "results" not in data or not data["results"]:
                    print("⚠️ No valid candle data returned.")
                    return None

                # Sort candles in ascending time
                sorted_candles = sorted(data["results"], key=lambda x: x["t"])

                candles = []
                for entry in sorted_candles:
                    candles.append({
                        "open": entry["o"],
                        "high": entry["h"],
                        "low": entry["l"],
                        "close": entry["c"],
                        "volume": entry["v"]
                    })

                return {
                    "history": candles,
                    "close": candles[-1]["close"]
                }

            except Exception as e:
                print(f"❌ Exception fetching candles: {e}")
                time.sleep(1)

        print("⛔ Max retries reached.")
        return None
