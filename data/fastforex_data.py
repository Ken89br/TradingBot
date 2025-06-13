# data/fastforex_data.py
import requests
import os
import time

class FastForexClient:
    def __init__(self):
        self.api_key = os.getenv("FASTFOREX_API_KEY", "MISSING_API_KEY")
        self.base_url = "https://api.fastforex.io"

    def fetch_candles(self, symbol, interval="1min", limit=5, retries=2):
        if len(symbol) != 6:
            print(f"❌ Invalid symbol format: {symbol}")
            return None

        base = symbol[:3].upper()
        quote = symbol[3:].upper()
        url = f"{self.base_url}/fetch-one"
        params = {
            "from": base,
            "to": quote,
            "api_key": self.api_key
        }

        print(f"📡 FastForex GET {url}")
        print(f"📦 Params: {params}")

        for attempt in range(retries + 1):
            try:
                res = requests.get(url, params=params)
                print(f"📥 Raw response: {res.status_code} {res.text}")

                if res.status_code != 200:
                    time.sleep(1)
                    continue

                data = res.json()
                if "result" not in data or quote not in data["result"]:
                    print("⚠️ Invalid FastForex response:", data)
                    continue

                price = float(data["result"][quote])
                timestamp = int(time.time()) * 1000

                # Fabricated single candle — FastForex only gives last tick price
                candle = {
                    "open": price,
                    "high": price,
                    "low": price,
                    "close": price,
                    "volume": 1,  # synthetic
                    "timestamp": timestamp
                }

                candles = [candle] * limit  # mock candles for compatibility

                return {
                    "history": candles,
                    "close": price
                }

            except Exception as e:
                print(f"❌ Exception: {e}")
                time.sleep(1)

        print("⛔ Max retries reached.")
        return None
                
