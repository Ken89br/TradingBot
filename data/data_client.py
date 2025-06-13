# data/data_client.py
from data.polygon_data import PolygonClient
from data.alpha_vantage_data import AlphaVantageClient

class FallbackDataClient:
    def __init__(self):
        self.sources = [
            PolygonClient(),
            AlphaVantageClient()
        ]

    def fetch_candles(self, symbol, interval="1min", limit=5):
        for source in self.sources:
            print(f"🔁 Trying: {source.__class__.__name__}")
            data = source.fetch_candles(symbol, interval=interval, limit=limit)
            if data and "history" in data:
                return data
        print("❌ All data providers failed.")
        return None
        
