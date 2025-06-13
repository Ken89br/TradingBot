# data/finnhub_data.py
import requests
import os
import time
from datetime import datetime

class FinnhubClient:
    def __init__(self):
        self.api_key = os.getenv("FINNHUB_API_KEY", "MISSING_API_KEY")
        self.base_url = "https://finnhub.io/api/v1"

    def fetch_candles(self, symbol, interval="1", limit=5, retries=2):
    def _map_resolution(tf):
    resolution_map = {
        "1min": "1",
        "5min": "5",
        "15min": "15",
        "30min": "30",
        "1h": "60",
        "4h": "60",   # optional override
        "1day": "D"
    }
    return resolution_map.get(tf, "1")

    now = int(time.time())
    from_unix = now - limit * 60

    # Detect and convert forex symbol format
    if len(symbol) == 6:
        base = symbol[:3].upper()
        quote = symbol[3:].upper()
        finnhub_symbol = f"OANDA:{base}_{quote}"
        url = f"{self.base_url}/forex/candle"
    else:
        finnhub_symbol = symbol
        url = f"{self.base_url}/stock/candle"

    params = {
        "symbol": finnhub_symbol,
        "resolution": resolution,
        "from": from_unix,
        "to": now,
        "token": self.api_key
    }

    print(f"📡 Finnhub GET {url}")
    print(f"📦 Params: {params}")

    for attempt in range(retries + 1):
        try:
            res = requests.get(url, params=params, timeout=5)
            print(f"📥 Raw response: {res.status_code} {res.text}")

            if res.status_code != 200:
                time.sleep(1)
                continue

            data = res.json()

            if data.get("s") != "ok":
                print("⚠️ No candle data:", data)
                continue

            candles = []
            for i in range(len(data["t"])):
                candles.append({
                    "timestamp": data["t"][i],
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
            print(f"❌ Exception: {e}")
            time.sleep(1)

    print("⛔ Max retries reached.")
    return None

                        "close": data["c"][i],
                        "volume": data["v"][i]
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
