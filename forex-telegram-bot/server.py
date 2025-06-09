# server.py
from data.twelvedata import TwelveDataClient
from strategy.rsi_ma import AggressiveRSIMA
from messaging.telegram_bot import TelegramNotifier
from config import CONFIG
import asyncio

async def main():
    data_client = TwelveDataClient()
    strategy = AggressiveRSIMA(CONFIG)  # Swap with other strategies if needed
    notifier = TelegramNotifier(CONFIG["telegram"]["bot_token"], strategy, data_client)
    await notifier.start()

if __name__ == "__main__":
    asyncio.run(main())
