# data/alpha_vantage_data.py
import requests
import os
import time

class AlphaVantageClient:
    def __init__(self):
        self.api_key = os.getenv("ALPHA_VANTAGE_API_KEY", "MISSING_API_KEY")
        self.base_url = "https://www.alphavantage.co/query"

    def fetch_candles(self, symbol, interval="1min", limit=5, retries=2):
        url = self.base_url
        params = {
            "function": "FX_INTRADAY",
            "from_symbol": symbol[:3],
            "to_symbol": symbol[3:],
            "interval": interval,
            "apikey": self.api_key,
            "outputsize": "compact"
        }

        print(f"📡 AlphaVantage GET {url}")
        print(f"📦 Params: {params}")

        for attempt in range(retries + 1):
            try:
                res = requests.get(url, params=params)
                if res.status_code != 200:
                    print(f"❌ HTTP {res.status_code}")
                    time.sleep(1)
                    continue

                data = res.json()
                key = f"Time Series FX ({interval})"
                if key not in data:
                    print("⚠️ No time series data:", data)
                    continue

                candles = []
                for ts, values in list(data[key].items())[:limit][::-1]:
                    candles.append({
                        "timestamp": int(time.mktime(time.strptime(ts, "%Y-%m-%d %H:%M:%S"))),
                        "open": float(values["1. open"]),
                        "high": float(values["2. high"]),
                        "low": float(values["3. low"]),
                        "close": float(values["4. close"]),
                        "volume": 1  # Fake volume (Alpha Vantage doesn't provide)
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
