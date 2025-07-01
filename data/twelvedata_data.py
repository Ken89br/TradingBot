# data/twelvedata_client.py

import requests
import os
import time
from datetime import datetime

class TwelveDataClient:
    def __init__(self):
        self.api_key = os.getenv("TWELVEDATA_API_KEY", "MISSING_API_KEY")
        self.base_url = "https://api.twelvedata.com"

    def fetch_candles(self, symbol, interval="1min", limit=5, retries=2):
        formatted_symbol = symbol.upper() if "/" in symbol else f"{symbol[:3]}/{symbol[3:]}"
        
        url = f"{self.base_url}/time_series"
        params = {
            "symbol": formatted_symbol,
            "interval": interval,
            "outputsize": limit,
            "format": "JSON",
            "apikey": self.api_key
        }

        print(f"📡 TwelveData GET {url}")
        print(f"📦 Params: {params}")

        for attempt in range(retries + 1):
            try:
                res = requests.get(url, params=params, timeout=10)
                print(f"📥 Raw response: {res.status_code} {res.text}")

                if res.status_code != 200:
                    time.sleep(1)
                    continue

                data = res.json()

                if "values" not in data:
                    print("⚠️ No candle data returned.")
                    continue

                candles = []
                for row in reversed(data["values"]):
                    dt_raw = row["datetime"]
                    ts = None
                    try:
                        # Primeiro tenta com hora, depois só data
                        ts = int(datetime.strptime(dt_raw, "%Y-%m-%d %H:%M:%S").timestamp())
                    except ValueError:
                        try:
                            ts = int(datetime.strptime(dt_raw, "%Y-%m-%d").timestamp())
                        except Exception as err:
                            print(f"⚠️ Erro ao converter data '{dt_raw}': {err}")
                            continue
                    candles.append({
                        "timestamp": ts,
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                        "volume": float(row.get("volume", 1))  # fallback if missing
                    })

                return {
                    "history": candles,
                    "close": candles[-1]["close"]
                }

            except Exception as e:
                print(f"❌ Exception fetching from TwelveData: {e}")
                time.sleep(1)

        print("⛔ Max retries reached.")
        return None
