#messaging/telegram_bot.py

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiohttp import web

from config import CONFIG
from utils.signal_logger import log_signal
from utils.telegram_safe import safe_send
from strategy.train_model_historic import main as run_training
import pandas as pd
import os
import time

class SignalState(StatesGroup):
    choosing_mode = State()
    choosing_timeframe = State()
    choosing_symbol = State()

REGISTERED_USERS = set()
signal_context = {}
user_languages = {}

SYMBOL_PAGES = [
    CONFIG["symbols"][:8],
    CONFIG["symbols"][8:]
]
SYMBOL_PAGES_OTC = [
    CONFIG["otc_symbols"][:8],
    CONFIG["otc_symbols"][8:]
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
        self.mode_map = {}  # user_id => "normal" or "otc"

        @self.dp.message_handler(commands=["start"])
        async def start_cmd(msg: types.Message):
            chat_id = msg.chat.id
            REGISTERED_USERS.add(chat_id)
            keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.add(KeyboardButton("📈 Start"))
            keyboard.add(KeyboardButton("/status"), KeyboardButton("/retrain"), KeyboardButton("/stop"))
            keyboard.add(KeyboardButton("/help"), KeyboardButton("/support"))
            keyboard.add(KeyboardButton("🌐 Language"))
            await safe_send(self.bot, chat_id, get_text("start", chat_id=chat_id), reply_markup=keyboard)

        @self.dp.message_handler(lambda msg: msg.text.lower() in ["/help", "help"])
        async def help_cmd(msg: types.Message):
            await safe_send(self.bot, msg.chat.id, get_text("help", chat_id=msg.chat.id))

        @self.dp.message_handler(lambda msg: msg.text.lower() in ["/support", "support"])
        async def support_cmd(msg: types.Message):
            await safe_send(self.bot, msg.chat.id, f"🛟 Contact support: {CONFIG['support']['username']}")

        @self.dp.message_handler(lambda msg: msg.text.lower() in ["/stop", "stop"])
        async def stop_cmd(msg: types.Message, state: FSMContext):
            await state.finish()
            await safe_send(self.bot, msg.chat.id, get_text("stopped", chat_id=msg.chat.id))

        @self.dp.message_handler(lambda msg: msg.text.lower() in ["/status", "status"])
        async def status_cmd(msg: types.Message):
            user_id = msg.chat.id
            sym_info = signal_context.get(user_id)
            if sym_info:
                response = f"✅ Bot is running.\n\n🕐 Timeframe: `{sym_info['timeframe']}`\n💱 Symbol: `{sym_info['symbol']}`"
            else:
                response = "✅ Bot is running.\nℹ️ No signal context found. Use 📈 Start to begin."
            await safe_send(self.bot, user_id, response, parse_mode="Markdown")

        @self.dp.message_handler(lambda msg: msg.text.lower() in ["/retrain", "retrain"])
        async def retrain_force(msg: types.Message):
            await safe_send(self.bot, msg.chat.id, "🔁 Force retraining initiated (manual override).")
            run_training()  # ✅ Force retrain regardless of CSV row count

        @self.dp.message_handler(lambda msg: msg.text == "🌐 Language")
        async def toggle_lang(msg: types.Message):
            chat_id = msg.chat.id
            current_lang = user_languages.get(chat_id, "en")
            new_lang = "pt" if current_lang == "en" else "en"
            user_languages[chat_id] = new_lang
            await safe_send(self.bot, chat_id, f"🌐 Language set to {'Português' if new_lang == 'pt' else 'English'} ✅")

        @self.dp.message_handler(lambda msg: msg.text == "📈 Start", state="*")
        async def start_signal(msg: types.Message):
            await SignalState.choosing_mode.set()
            kb = InlineKeyboardMarkup(row_width=2)
            kb.add(
                InlineKeyboardButton("🌍 Normal", callback_data="mode:normal"),
                InlineKeyboardButton("🕒 OTC", callback_data="mode:otc")
            )
            await safe_send(self.bot, msg.chat.id, get_text("choose_mode", chat_id=msg.chat.id), reply_markup=kb)

        @self.dp.callback_query_handler(lambda c: c.data.startswith("mode:"), state=SignalState.choosing_mode)
        async def select_mode(callback: types.CallbackQuery, state: FSMContext):
            mode = callback.data.split(":")[1]
            self.mode_map[callback.from_user.id] = mode
            await state.set_state(SignalState.choosing_timeframe.state)
            kb = InlineKeyboardMarkup(row_width=3)
            buttons = [InlineKeyboardButton(tf, callback_data=f"timeframe:{tf}") for tf in CONFIG["timeframes"]]
            kb.add(*buttons)
            await callback.message.edit_text(get_text("choose_timeframe", chat_id=callback.from_user.id), reply_markup=kb)
            await callback.answer()

        @self.dp.callback_query_handler(lambda c: c.data.startswith("timeframe:"), state=SignalState.choosing_timeframe)
        async def select_timeframe(callback: types.CallbackQuery, state: FSMContext):
            tf = callback.data.split(":")[1]
            await state.update_data(timeframe=tf)
            await state.set_state(SignalState.choosing_symbol.state)
            await self.send_symbol_buttons(callback.message, callback.from_user.id, page=0)
            await callback.answer()

        @self.dp.callback_query_handler(lambda c: c.data == "more_symbols", state=SignalState.choosing_symbol)
        async def next_symbols(callback: types.CallbackQuery, state: FSMContext):
            await self.send_symbol_buttons(callback.message, callback.from_user.id, page=1)
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
                candles = self.data_client.fetch_candles(symbol, interval=self._map_timeframe(timeframe))
                if not candles or "history" not in candles:
                    await safe_send(self.bot, callback.from_user.id, "⚠️ Failed to retrieve price data.")
                    return
                signal_data = self.strategy.generate_signal(candles)
                if not signal_data:
                    await safe_send(self.bot, callback.from_user.id, get_text("no_signal", chat_id=callback.from_user.id))
                else:
                    signal_data["expire_entry_time"] = pd.Timestamp.now() + pd.Timedelta(seconds=30)
                    signal_context[callback.from_user.id] = {"symbol": symbol, "timeframe": timeframe}
                    await self.send_trade_signal(callback.from_user.id, symbol, signal_data)
            except Exception as e:
                await safe_send(self.bot, callback.from_user.id, f"❌ Error: {str(e)}")
            await state.finish()
            await callback.answer()

        @self.dp.callback_query_handler(lambda c: c.data == "refresh_signal")
        async def refresh(callback: types.CallbackQuery):
            uid = callback.from_user.id
            if uid not in signal_context:
                await callback.answer("⚠️ No previous signal to refresh.", show_alert=True)
                return
            ctx = signal_context[uid]
            candles = self.data_client.fetch_candles(ctx["symbol"], interval=self._map_timeframe(ctx["timeframe"]))
            if not candles or "history" not in candles:
                await safe_send(self.bot, uid, get_text("no_signal", chat_id=uid))
                return
            signal_data = self.strategy.generate_signal(candles)
            if signal_data:
                signal_data["expire_entry_time"] = pd.Timestamp.now() + pd.Timedelta(seconds=30)
                await self.send_trade_signal(uid, ctx["symbol"], signal_data)
            await callback.answer("🔁 Refreshed.")

    async def send_symbol_buttons(self, message, user_id, page=0):
        kb = InlineKeyboardMarkup(row_width=2)
        symbols = SYMBOL_PAGES_OTC[page] if self.mode_map.get(user_id) == "otc" else SYMBOL_PAGES[page]
        buttons = [InlineKeyboardButton(sym, callback_data=f"symbol:{sym}") for sym in symbols]
        kb.add(*buttons)
        if page == 0:
            kb.add(InlineKeyboardButton("➡️ More", callback_data="more_symbols"))
        await message.edit_text(get_text("choose_symbol", chat_id=message.chat.id), reply_markup=kb)

    def _map_timeframe(self, tf):
        return {
            "S1": "s1", "M1": "1min", "M5": "5min", "M15": "15min",
            "M30": "30min", "H1": "1h", "H4": "4h", "D1": "1day"
        }.get(tf, "1min")

    async def send_trade_signal(self, chat_id, asset, signal_data):
        signal_data["symbol"] = asset
        signal_data["user"] = chat_id
        signal_data["timestamp"] = pd.Timestamp.now()
        signal_data["recommend_entry"] = signal_data.get("recommended_entry_time")
        log_signal(chat_id, asset, signal_data.get("timeframe"), signal_data)
        SIGNAL_CSV_PATH = "signals.csv"
        df = pd.DataFrame([signal_data])
        if os.path.exists(SIGNAL_CSV_PATH):
            df.to_csv(SIGNAL_CSV_PATH, mode="a", header=False, index=False)
        else:
            df.to_csv(SIGNAL_CSV_PATH, index=False)

        payout = round(signal_data['price'] * 0.92, 5)
        msg = (
            f"📡 *{get_text('signal_title', chat_id=chat_id)}*\n\n"
            f"📌 *{get_text('pair', chat_id=chat_id)}:* `{asset}`\n"
            f"📈 *{get_text('direction', chat_id=chat_id)}:* `{signal_data['signal'].upper()}`\n"
            f"💪 *{get_text('strength', chat_id=chat_id)}:* `{signal_data['strength'].upper()}`\n"
            f"🎯 *{get_text('confidence', chat_id=chat_id)}:* `{signal_data['confidence']}%`\n\n"
            f"💰 *{get_text('entry', chat_id=chat_id)}:* `{signal_data['price']}`\n"
            f"🕒 *{get_text('recommend', chat_id=chat_id)}:* `{signal_data['recommended_entry_time']}`\n"
            f"⏳ *{get_text('expire_entry', chat_id=chat_id)}:* `{signal_data['expire_entry_time']}`\n"
            f"📈 *{get_text('high', chat_id=chat_id)}:* `{signal_data['high']}`\n"
            f"📉 *{get_text('low', chat_id=chat_id)}:* `{signal_data['low']}`\n"
            f"📦 *{get_text('volume', chat_id=chat_id)}:* `{signal_data['volume']}`\n\n"
            f"💸 *{get_text('payout', chat_id=chat_id)}:* `{payout}`\n"
            f"⏱ *{get_text('timer', chat_id=chat_id)}*"
        )

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔁 Refresh", callback_data="refresh_signal"))
        await safe_send(self.bot, chat_id, msg, parse_mode="Markdown", reply_markup=keyboard)

    @property
    def token(self):
        return CONFIG["telegram"]["bot_token"]

    async def set_webhook(self):
        await self.bot.set_webhook(f"{CONFIG['webhook']['url']}/webhook/{self.token}")

    async def webhook_handler(self, request: web.Request):
        update = types.Update(**(await request.json()))
        Bot.set_current(self.bot)
        Dispatcher.set_current(self.dp)
        await self.dp.process_update(update)
        return web.Response()
