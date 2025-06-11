# messaging/telegram_bot.py
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiohttp import web
from config import CONFIG

class SignalState(StatesGroup):
    choosing_timeframe = State()
    choosing_symbol = State()

REGISTERED_USERS = set()
signal_context = {}
user_languages = {}  # chat_id: "en" or "pt"

SYMBOL_PAGES = [
    CONFIG["symbols"][:8],
    CONFIG["symbols"][8:]
]

def get_text(key, lang=None, chat_id=None):
    if chat_id:
        lang = user_languages.get(chat_id, "en")
    lang = lang or "en"
    return CONFIG["languages"].get(lang, CONFIG["languages"]["en"]).get(key, key)

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
            keyboard.add(KeyboardButton("🌐 Language"))

            await msg.reply(get_text("start", chat_id=chat_id), reply_markup=keyboard)

        @self.dp.message_handler(lambda msg: msg.text == "🌐 Language")
        async def language_toggle(msg: types.Message):
            chat_id = msg.chat.id
            current_lang = user_languages.get(chat_id, "en")
            new_lang = "pt" if current_lang == "en" else "en"
            user_languages[chat_id] = new_lang
            await msg.reply(f"🌐 Language set to {'Português' if new_lang == 'pt' else 'English'} ✅")

        @self.dp.message_handler(lambda msg: msg.text.lower() in ["/help", "help"])
        async def help_cmd(msg: types.Message):
            await msg.answer("ℹ️ This bot generates real-time forex signals using AI and technical strategies.\nUse 📈 Start to begin.")

        @self.dp.message_handler(lambda msg: msg.text.lower() in ["/support", "support"])
        async def support_cmd(msg: types.Message):
            username = CONFIG["support"]["username"]
            await msg.answer(f"🛟 Contact support at: {username}")

        @self.dp.message_handler(lambda msg: msg.text.lower() in ["/stop", "stop"])
        async def stop_cmd(msg: types.Message, state: FSMContext):
            await state.finish()
            await msg.answer("🛑 Signal generation stopped. Use 📈 Start to begin again.")

        @self.dp.message_handler(lambda msg: msg.text == "📈 Start", state="*")
        async def handle_start_signal(msg: types.Message):
            await SignalState.choosing_timeframe.set()
            kb = InlineKeyboardMarkup(row_width=3)
            buttons = [InlineKeyboardButton(tf, callback_data=f"timeframe:{tf}") for tf in CONFIG["timeframes"]]
            kb.add(*buttons)
            await msg.reply(get_text("choose_timeframe", chat_id=msg.chat.id), reply_markup=kb, parse_mode="Markdown")

        @self.dp.callback_query_handler(lambda c: c.data.startswith("timeframe:"), state=SignalState.choosing_timeframe)
        async def select_timeframe(callback: types.CallbackQuery, state: FSMContext):
            tf = callback.data.split(":")[1]
            await state.update_data(timeframe=tf)
            await state.set_state(SignalState.choosing_symbol.state)
            await self.send_symbol_buttons(callback.message, page=0)
            await callback.answer()

        @self.dp.callback_query_handler(lambda c: c.data == "more_symbols", state=SignalState.choosing_symbol)
        async def more_symbols_callback(callback: types.CallbackQuery, state: FSMContext):
            await self.send_symbol_buttons(callback.message, page=1)
            await callback.answer()

        @self.dp.callback_query_handler(lambda c: c.data.startswith("symbol:"), state=SignalState.choosing_symbol)
        async def select_symbol(callback: types.CallbackQuery, state: FSMContext):
            try:
                symbol = callback.data.split(":")[1].replace(" OTC", "")
                await state.update_data(symbol=symbol)
                user_data = await state.get_data()
                timeframe = user_data["timeframe"]

                await callback.message.edit_text(
                    f"⏱ Timeframe: `{timeframe}`\n💱 Symbol: `{symbol}`\n\n{get_text('generating', chat_id=callback.from_user.id)}",
                    parse_mode="Markdown"
                )

                candle = self.data_client.fetch_candles(symbol, interval=self._map_timeframe(timeframe))
                if CONFIG.get("debug"):
                    print(f"🧪 Raw candle data: {candle}")

                if not candle or "history" not in candle:
                    await self.bot.send_message(callback.from_user.id, "⚠️ Failed to retrieve price data.")
                    return

                signal_data = self.strategy.generate_signal(candle)

                if not signal_data:
                    await self.bot.send_message(callback.from_user.id, get_text("no_signal", chat_id=callback.from_user.id))
                else:
                    signal_context[callback.from_user.id] = {"symbol": symbol, "timeframe": timeframe}
                    await self.send_trade_signal(callback.from_user.id, symbol, signal_data)

            except Exception as e:
                await self.bot.send_message(callback.from_user.id, f"❌ Error: {str(e)}")

            await state.finish()
            await callback.answer()

        @self.dp.callback_query_handler(lambda c: c.data == "refresh_signal")
        async def refresh_callback(callback_query: types.CallbackQuery):
            user_id = callback_query.from_user.id
            if user_id not in signal_context:
                await callback_query.answer("⚠️ No previous signal to refresh.", show_alert=True)
                return

            ctx = signal_context[user_id]
            candle = self.data_client.fetch_candles(ctx["symbol"], self._map_timeframe(ctx["timeframe"]))

            if not candle or "history" not in candle:
                await self.bot.send_message(user_id, get_text("no_signal", chat_id=user_id))
                return

            signal_data = self.strategy.generate_signal(candle)
            if not signal_data:
                await self.bot.send_message(user_id, get_text("no_signal", chat_id=user_id))
            else:
                await self.send_trade_signal(user_id, ctx["symbol"], signal_data)

            await callback_query.answer("🔁 Refreshed.")

    async def send_symbol_buttons(self, message, page=0):
        kb = InlineKeyboardMarkup(row_width=2)
        symbols = SYMBOL_PAGES[page]
        buttons = [InlineKeyboardButton(sym, callback_data=f"symbol:{sym}") for sym in symbols]
        kb.add(*buttons)
        if page == 0:
            kb.add(InlineKeyboardButton("➡️ More", callback_data="more_symbols"))
        await message.edit_text(get_text("choose_symbol", chat_id=message.chat.id), parse_mode="Markdown", reply_markup=kb)

    def _map_timeframe(self, tf):
        return {
            "M1": "1min", "M5": "5min", "M15": "15min",
            "M30": "30min", "H1": "1h", "H4": "4h", "D1": "1day"
        }.get(tf, "1min")

    async def send_trade_signal(self, chat_id, asset, signal_data):
        payout = round(signal_data['price'] * 0.92, 5)
        msg = (
            f"📡 *{get_text('signal_title', chat_id=chat_id)}*\n\n"
            f"📌 *{get_text('pair', chat_id=chat_id)}:* `{asset}`\n"
            f"📈 *{get_text('direction', chat_id=chat_id)}:* `{signal_data['signal'].upper()}`\n"
            f"💪 *{get_text('strength', chat_id=chat_id)}:* `{signal_data['strength'].upper()}`\n"
            f"🎯 *{get_text('confidence', chat_id=chat_id)}:* `{signal_data['confidence']}%`\n\n"
            f"💰 *{get_text('entry', chat_id=chat_id)}:* `{signal_data['price']}`\n"
            f"📊 *{get_text('recommend', chat_id=chat_id)}:* `{signal_data['recommend_entry']}`\n"
            f"📈 *{get_text('high', chat_id=chat_id)}:* `{signal_data['high']}`\n"
            f"📉 *{get_text('low', chat_id=chat_id)}:* `{signal_data['low']}`\n"
            f"📦 *{get_text('volume', chat_id=chat_id)}:* `{signal_data['volume']}`\n\n"
            f"💸 *{get_text('payout', chat_id=chat_id)}:* `{payout}`\n"
            f"⏱ *{get_text('timer', chat_id=chat_id)}*"
        )

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔁 Refresh", callback_data="refresh_signal"))

        await self.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown", reply_markup=keyboard)

    @property
    def token(self):
        return CONFIG["telegram"]["bot_token"]

    async def set_webhook(self):
        webhook_url = f"{CONFIG['webhook']['url']}/webhook/{self.token}"
        await self.bot.set_webhook(webhook_url)

    async def webhook_handler(self, request: web.Request):
        data = await request.json()
        update = types.Update(**data)

        Bot.set_current(self.bot)
        Dispatcher.set_current(self.dp)

        await self.dp.process_update(update)
        return web.Response()
