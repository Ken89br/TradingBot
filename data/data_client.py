# data/data_client.py
from config import CONFIG

from data.polygon_data import PolygonClient
from data.finnhub_data import FinnhubClient

def get_data_client():
    provider = CONFIG.get("data_feed", "polygon").lower()

    if provider == "polygon":
        print("🔌 Using PolygonClient as data provider")
        return PolygonClient()
    elif provider == "finnhub":
        print("🔌 Using FinnhubClient as data provider")
        return FinnhubClient()
    else:
        raise ValueError(f"❌ Unsupported data provider: {provider}")
    
