# data/finnhub_data.py
import requests
import os
import time

class FinnhubClient:
    def __init__(self):
        self.api_key = os.getenv("FINNHUB_API_KEY", "MISSING_KEY")
        self.base_url = "https://finnhub.io/api/v1"

    def fetch_candles(self, symbol, interval="1", limit=30, retries=2):
        resolution_map = {
            "1min": "1", "5min": "5", "15min": "15",
            "30min": "30", "1h": "60", "4h": "240", "1day": "D"
        }
        resolution = resolution_map.get(interval, "1")

        # Format OANDA:EUR_USD
        if len(symbol) != 6:
            print(f"❌ Invalid symbol format: {symbol}")
            return None

        formatted_symbol = f"OANDA:{symbol[:3]}_{symbol[3:]}"

        end = int(time.time())
        start = end - limit * 60

        url = f"{self.base_url}/forex/candle"
        params = {
            "symbol": formatted_symbol,
            "resolution": resolution,
            "from": start,
            "to": end,
            "token": self.api_key
        }

        print(f"🔍 Fetching {formatted_symbol} from Finnhub")
        print(f"🛰️ Params: {params}")

        for attempt in range(retries + 1):
            try:
                response = requests.get(url, params=params, timeout=5)
                if response.status_code != 200:
                    print(f"❌ HTTP {response.status_code}: {response.text}")
                    time.sleep(1)
                    continue

                data = response.json()
                if not data or data.get("s") != "ok" or not data.get("c"):
                    print("⚠️ No valid candle data returned.")
                    return None
                    
                if not data or "s" not in data or data.get("s") != "ok":
                    print(f"❌ Bad candle data: {data}")
                    return None
            
                candles = [
                    {
                        "open": data["o"][i],
                        "high": data["h"][i],
                        "low": data["l"][i],
                        "close": data["c"][i],
                        "volume": data["v"][i]
                    }
                    for i in range(len(data["c"]))
                ]

                return {
                    "history": candles,
                    "close": candles[-1]["close"]
                }

            except Exception as e:
                print(f"❌ Exception fetching candles: {e}")
                time.sleep(1)

        print("⛔ Max retries reached.")
        return None
            
