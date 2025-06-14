# data/data_client.py

from data.twelvedata_data import TwelveDataClient
from data.tiingo_data import TiingoClient

class FallbackDataClient:
    def __init__(self, primary=None, fallback=None):
        self.primary = primary or TwelveDataClient()
        self.fallback = fallback or TiingoClient()

    def fetch_candles(self, symbol, interval="1min", limit=5):
        print("⚙️ Trying primary provider...")
        result = self.primary.fetch_candles(symbol, interval=interval, limit=limit)

        if result and "history" in result:
            return result

        print("⚠️ Primary provider failed. Trying fallback provider...")
        fallback_result = self.fallback.fetch_candles(symbol, interval=interval, limit=limit)

        if fallback_result and "history" in fallback_result:
            return fallback_result

        print("❌ Both data providers failed.")
        return None
        
