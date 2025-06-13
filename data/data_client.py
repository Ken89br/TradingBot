# data/data_client.py

from data.polygon_data import PolygonClient
from data.finnhub_data import FinnhubClient

class FallbackDataClient:
    def __init__(self):
        self.primary = PolygonClient()
        self.secondary = FinnhubClient()

    def fetch_candles(self, symbol, interval="1", limit=5, retries=2):
        result = self.primary.fetch_candles(symbol, interval, limit, retries)
        if result:
            print("✅ Used Polygon successfully.")
            return result
        print("⚠️ Polygon failed, trying Finnhub...")
        result = self.secondary.fetch_candles(symbol, interval, limit, retries)
        if result:
            print("✅ Fallback to Finnhub successful.")
        else:
            print("❌ Both data providers failed.")
        return result
