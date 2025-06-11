from aiohttp import web
from data.finnhub_data import FinnhubClient
from strategy.rsi_ma import AggressiveRSIMA
from messaging.telegram_bot import TelegramNotifier
from config import CONFIG

async def init_app():
    data_client = FinnhubClient()
    strategy = AggressiveRSIMA(CONFIG)
    notifier = TelegramNotifier(CONFIG["telegram"]["bot_token"], strategy, data_client)

    app = web.Application()
    app.router.add_post(f"/webhook/{notifier.token}", notifier.webhook_handler)
    await notifier.set_webhook()
    return app


if __name__ == "__main__":
    web.run_app(init_app(), host="0.0.0.0", port=10000)
