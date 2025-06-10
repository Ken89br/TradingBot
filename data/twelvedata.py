# data/twelvedata.py
import requests
from config import CONFIG

class TwelveDataClient:
    def __init__(self):
        self.api_key = CONFIG["twelvedata"]["api_key"]
        self.base_url = CONFIG["twelvedata"]["base_url"]
        self.interval = CONFIG["twelvedata"]["default_interval"]

    def fetch_candles(self, symbol, interval=None, limit=30):
        interval = interval or self.interval
        formatted_symbol = symbol.replace("/", "")
        params = {
            "symbol": formatted_symbol,
            "interval": interval,
            "outputsize": limit,
            "apikey": self.api_key
        }
        url = f"{self.base_url}/time_series"
        try:
            response = requests.get(url, params=params)
            data = response.json()
        except Exception as e:
            print(f"❌ Error fetching data: {e}")
            return None

        if "values" not in data:
            print(f"⚠️ Invalid response: {data}")
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

        return {
            "history": candles,
            "close": candles[-1]["close"]
  }
