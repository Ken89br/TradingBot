# data/data_client.py

from data.twelvedata_data import TwelveDataClient
from data.tiingo_data import TiingoClient
from data.polygon_data import PolygonClient

class FallbackDataClient:
    def __init__(self):
        self.providers = [
            TwelveDataClient(),
            TiingoClient(),
            PolygonClient()
        ]

    def fetch_candles(self, symbol, interval="1min", limit=5):
        for i, provider in enumerate(self.providers):
            print(f"⚙️ Trying provider #{i+1}: {provider.__class__.__name__}")
            try:
                result = provider.fetch_candles(symbol, interval=interval, limit=limit)
                if result and "history" in result:
                    print(f"✅ Success from: {provider.__class__.__name__}")
                    return result
            except Exception as e:
                print(f"❌ Provider #{i+1} error: {e}")
        print("❌ All providers failed.")
        return None
                
