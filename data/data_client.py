#data/data_client.py

import subprocess
import json
from datetime import datetime, timedelta
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
        print(f"📡 Fetching from Dukascopy: {symbol} @ {interval}")
        try:
            candles = self._fetch_from_dukascopy(symbol, interval)
            if candles and "history" in candles:
                print("✅ Dukascopy succeeded.")
                return candles
        except Exception as e:
            print(f"❌ Dukascopy failed: {e}")

        # Try fallbacks
        for i, provider in enumerate(self.providers):
            print(f"⚙️ Trying fallback #{i+1}: {provider.__class__.__name__}")
            try:
                result = provider.fetch_candles(symbol, interval=interval, limit=limit)
                if result and "history" in result:
                    print(f"✅ Success from fallback: {provider.__class__.__name__}")
                    return result
            except Exception as e:
                print(f"❌ Fallback #{i+1} error: {e}")
        print("❌ All providers failed.")
        return None

    def _fetch_from_dukascopy(self, symbol, interval):
        now = datetime.utcnow()
        from_dt = now - timedelta(days=2)  # Decreased from 3 years to 2 days for performance

        cmd = [
            "node", "data/dukascopy_client.cjs",
            symbol.lower(), self._convert_tf(interval),
            from_dt.isoformat(), now.isoformat()
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(result.stderr)

        candles = json.loads(result.stdout)
        return {
            "history": candles,
            "close": candles[-1]["close"] if candles else None
        }

    def _convert_tf(self, interval):
        return {
            "1min": "m1", "5min": "m5", "15min": "m15",
            "30min": "m30", "1h": "h1", "4h": "h4", "1day": "d1"
        }.get(interval.lower(), "m1")
        
