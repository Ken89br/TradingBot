import asyncio
from pocketoptionapi.api import PocketOption
import os
import pandas as pd
from datetime import datetime

class PocketOptionDataFeed:
    def __init__(self, symbols, timeframes, data_dir="data"):
        self.symbols = symbols  # ["EURUSD", "GBPUSD", ...]
        self.timeframes = timeframes  # [60, 300, ...] (em segundos: 60=M1, 300=M5...)
        self.data_dir = data_dir
        self.po = PocketOption()
        self.callbacks = {}

    async def on_candle(self, symbol, timeframe, candle):
        filename = f"{symbol.lower()}_{self.tf_to_str(timeframe)}.csv"
        filepath = os.path.join(self.data_dir, filename)

        # Formata o candle para o padrão do seu projeto
        row = {
            "timestamp": int(candle["timestamp"]),
            "open": candle["open"],
            "high": candle["high"],
            "low": candle["low"],
            "close": candle["close"],
            "volume": candle.get("volume", 1)
        }

        # Salva incrementalmente
        df = pd.DataFrame([row])
        if os.path.exists(filepath):
            df_old = pd.read_csv(filepath)
            df = pd.concat([df_old, df], ignore_index=True)
            df.drop_duplicates(subset=['timestamp'], keep='last', inplace=True)
            df.sort_values('timestamp', inplace=True)
        df.to_csv(filepath, index=False)
        print(f"🟢 {symbol} {self.tf_to_str(timeframe)} candle salvo: {row}")

    def tf_to_str(self, tf):
        # Converte sec para str igual Dukascopy
        if tf == 5:
            return "s1"
        elif tf == 60:
            return "m1"
        elif tf == 300:
            return "m5"
        elif tf == 900:
            return "m15"
        elif tf == 1800:
            return "m30"
        elif tf == 3600:
            return "h1"
        elif tf == 14400:
            return "h4"
        elif tf == 86400:
            return "d1"
        else:
            return f"s{tf}"

    async def subscribe_all(self):
        await self.po.connect()
        for symbol in self.symbols:
            for tf in self.timeframes:
                # Cria callback dedicado para cada par/tf
                async def cb(candle, symbol=symbol, tf=tf):
                    await self.on_candle(symbol, tf, candle)
                await self.po.subscribe_candles(symbol, tf, cb)
                print(f"✅ Subscribed: {symbol} {self.tf_to_str(tf)}")
        print("🚀 Capturando candles Pocket Option (Ctrl+C para parar)")
        try:
            while True:
                await asyncio.sleep(60)
        except KeyboardInterrupt:
            await self.po.close()
            print("⛔ Finalizado.")

if __name__ == "__main__":
    # Exemplo com todos pares e timeframes do seu CONFIG
    # Você pode importar de config.py se preferir
    SYMBOLS = [
        "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF", "NZDUSD",
        "USDCAD", "EURJPY", "EURNZD", "AEDCNY", "AUDCAD", "AUDCHF",
        "AUDNZD", "AUDUSD", "CADJPY", "CHFJPY", "EURGBP", "EURJPY",
        "EURUSD OTC", "GBPUSD OTC", "USDJPY OTC", "AUDUSD OTC", "EURJPY OTC",
        "NZDUSD OTC", "AUDCAD OTC", "AUDCHF OTC", "GBPJPY OTC", "CADJPY OTC"
    ]
    # Timeframes em segundos
    TIMEFRAMES = [5, 60, 300, 900, 1800, 3600, 14400, 86400]
    # Crie a pasta data/ se não existir
    os.makedirs("data", exist_ok=True)
    feed = PocketOptionDataFeed(SYMBOLS, TIMEFRAMES)
    asyncio.run(feed.subscribe_all())
