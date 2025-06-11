# data/finnhub_data.py
import requests
import os
import time

class FinnhubClient:
    def __init__(self):
        self.api_key = os.getenv("FINNHUB_API_KEY", "MISSING_KEY")
        self.base_url = "https://finnhub.io/api/v1"

    def fetch_candles(self, symbol, interval="1", limit=30, retries=2):
        # Map timeframe: 1min → 1, 5min → 5, etc.
        resolution_map = {
            "1min": "1", "5min": "5", "15min": "15",
            "30min": "30", "1h": "60", "4h": "240", "1day": "D"
        }
        resolution = resolution_map.get(interval, "1")

        # Use OANDA symbols
        formatted_symbol = f"OANDA:{symbol}"

        # Calculate UNIX timestamps
        end = int(time.time())
        start = end - limit * 60  # 1 candle per minute by default

        url = f"{self.base_url}/forex/candle"
        params = {
            "symbol": formatted_symbol,
            "resolution": resolution,
            "from": start,
            "to": end,
            "token": self.api_key
        }

        print(f"📡 Finnhub Request: {url}")
        print(f"Params: {params}")

        try:
            response = requests.get(url, params=params, timeout=5)
            if response.status_code != 200:
                print(f"❌ HTTP {response.status_code}: {response.text}")
                return None

            data = response.json()
            if data.get("s") != "ok":
                print(f"⚠️ Bad response from Finnhub: {data}")
                return None

            candles = []
            for i in range(len(data["c"])):
                candles.append({
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
            print(f"❌ Finnhub error: {e}")
            return None
          
