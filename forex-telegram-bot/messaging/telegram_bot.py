from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from config import CONFIG
from aiogram.dispatcher.webhook import WebhookRequestHandler
from aiogram.utils.executor import start_webhook


class SignalState(StatesGroup):
    choosing_timeframe = State()
    choosing_symbol = State()

REGISTERED_USERS = set()
signal_context = {}

SYMBOL_PAGES = [
    CONFIG["symbols"][:8],
    CONFIG["symbols"][8:]
]

class TelegramNotifier:
    def __init__(self, token, strategy, data_client):
        self.bot = Bot(token=token)
        self.dp = Dispatcher(self.bot, storage=MemoryStorage())
        self.strategy = strategy
        self.data_client = data_client

        @self.dp.message_handler(commands=['start'])
        async def start_cmd(msg: types.Message):
            chat_id = msg.chat.id
            REGISTERED_USERS.add(chat_id)
            keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.add(KeyboardButton("📈 Start"))
            keyboard.add(KeyboardButton("/status"), KeyboardButton("/stop"))
            keyboard.add(KeyboardButton("/help"), KeyboardButton("/support"))
            await msg.reply("🤖 Welcome! Tap 📈 *Start* to generate a signal.", reply_markup=keyboard)

        @self.dp.message_handler(lambda msg: msg.text == "📈 Start", state="*")
        async def handle_start_signal(msg: types.Message):
            await SignalState.choosing_timeframe.set()
            kb = InlineKeyboardMarkup(row_width=3)
            buttons = [InlineKeyboardButton(tf, callback_data=f"timeframe:{tf}") for tf in CONFIG["timeframes"]]
            kb.add(*buttons)
            await msg.reply("⏱ *Choose a timeframe:*", reply_markup=kb, parse_mode="Markdown")

        @self.dp.callback_query_handler(lambda c: c.data.startswith("timeframe:"), state=SignalState.choosing_timeframe)
        async def select_timeframe(callback: types.CallbackQuery, state: FSMContext):
            tf = callback.data.split(":")[1]
            await state.update_data(timeframe=tf)
            await SignalState.choosing_symbol.set()
            await self.send_symbol_buttons(callback.message, page=0)

        @self.dp.callback_query_handler(lambda c: c.data == "more_symbols", state=SignalState.choosing_symbol)
        async def more_symbols_callback(callback: types.CallbackQuery, state: FSMContext):
            await self.send_symbol_buttons(callback.message, page=1)

        async def send_symbol_buttons(message, page=0):
            kb = InlineKeyboardMarkup(row_width=2)
            symbols = SYMBOL_PAGES[page]
            buttons = [InlineKeyboardButton(sym, callback_data=f"symbol:{sym}") for sym in symbols]
            kb.add(*buttons)
            if page == 0:
                kb.add(InlineKeyboardButton("➡️ More", callback_data="more_symbols"))
            await message.edit_text("💱 *Choose a currency pair:*", parse_mode="Markdown", reply_markup=kb)

        @self.dp.callback_query_handler(lambda c: c.data.startswith("symbol:"), state=SignalState.choosing_symbol)
        async def select_symbol(callback: types.CallbackQuery, state: FSMContext):
            try:
                symbol = callback.data.split(":")[1]
                await state.update_data(symbol=symbol)
                user_data = await state.get_data()
                timeframe = user_data["timeframe"]

                await callback.message.edit_text(
                    f"⏱ Timeframe: `{timeframe}`\n💱 Symbol: `{symbol}`\n\n📡 Generating signal...",
                    parse_mode="Markdown"
                )

                candle = self.data_client.fetch_candles(symbol, interval=self._map_timeframe(timeframe))
                if not candle:
                    await self.bot.send_message(callback.from_user.id, "⚠️ Failed to retrieve price data.")
                    return

                signal_data = self.strategy.generate_signal(candle)
                if not signal_data:
                    await self.bot.send_message(callback.from_user.id, "⚠️ No signal at this moment.")
                else:
                    signal_context[callback.from_user.id] = {"symbol": symbol, "timeframe": timeframe}
                    await self.send_trade_signal(callback.from_user.id, symbol, signal_data)

            except Exception as e:
                await self.bot.send_message(callback.from_user.id, f"❌ Error: {str(e)}")

            await state.finish()

        @self.dp.callback_query_handler(lambda c: c.data == "refresh_signal")
        async def refresh_callback(callback_query: types.CallbackQuery):
            user_id = callback_query.from_user.id
            if user_id not in signal_context:
                await callback_query.answer("⚠️ No previous signal to refresh.", show_alert=True)
                return

            ctx = signal_context[user_id]
            candle = self.data_client.fetch_candles(ctx["symbol"], self._map_timeframe(ctx["timeframe"]))
            signal_data = self.strategy.generate_signal(candle)
            if not signal_data:
                await self.bot.send_message(user_id, "⚠️ Still no signal.")
            else:
                await self.send_trade_signal(user_id, ctx["symbol"], signal_data)
            await callback_query.answer("🔁 Refreshed.")

    def _map_timeframe(self, tf):
        return {
            "M1": "1min", "M5": "5min", "M15": "15min",
            "M30": "30min", "H1": "1h", "H4": "4h", "D1": "1day"
        }.get(tf, "1min")

    async def send_trade_signal(self, chat_id, asset, signal_data):
        payout = round(signal_data['price'] * 0.92, 5)
        msg = (
            f"📡 *New Forex Signal Alert!*\n\n"
            f"📌 *Pair:* `{asset}`\n"
            f"📈 *Direction:* `{signal_data['signal'].upper()}`\n"
            f"💪 *Strength:* `{signal_data['strength'].upper()}`\n"
            f"🎯 *Confidence:* `{signal_data['confidence']}%`\n\n"
            f"💰 *Entry Price:* `{signal_data['price']}`\n"
            f"📊 *Recommended Entry:* `{signal_data['recommend_entry']}`\n"
            f"📈 *High:* `{signal_data['high']}`\n"
            f"📉 *Low:* `{signal_data['low']}`\n"
            f"📦 *Volume:* `{signal_data['volume']}`\n\n"
            f"💸 *Simulated Payout (92%):* `{payout}`\n"
            f"⏱ *Action Window:* Execute within *1 minute!*"
        )

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔁 Refresh", callback_data="refresh_signal"))

        await self.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown", reply_markup=keyboard)

    async def start(self):
        await self.dp.start_polling()
