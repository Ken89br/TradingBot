# messaging/telegram_bot.py
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
from dotenv import load_dotenv

# ==== FUSO HORÁRIO ====
from datetime import datetime
import pytz

TZ_MAPUTO = pytz.timezone("Africa/Maputo")

def to_maputo_time(dt_utc):
    if isinstance(dt_utc, pd.Timestamp):
        dt_utc = dt_utc.to_pydatetime()
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=pytz.UTC)
    return dt_utc.astimezone(TZ_MAPUTO)
# ======================

load_dotenv()

class SignalState(StatesGroup):
    choosing_mode = State()
    choosing_timeframe = State()
    choosing_symbol = State()

REGISTERED_USERS = set()
signal_context = {}
user_languages = {}

SYMBOL_PAGES = [CONFIG["symbols"][:8], CONFIG["symbols"][8:]]
SYMBOL_PAGES_OTC = [CONFIG["otc_symbols"][:8], CONFIG["otc_symbols"][8:]]

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
        self.mode_map = {}

        @self.dp.message_handler(commands=["start"])
        async def start_cmd(msg: types.Message):
            chat_id = msg.chat.id
            REGISTERED_USERS.add(chat_id)
            keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.add(KeyboardButton("📈 Start" if user_languages.get(chat_id, "en") == "en" else "📈 Iniciar"))
            keyboard.add(KeyboardButton("/status"), KeyboardButton("/retrain"), KeyboardButton("/stop"))
            keyboard.add(KeyboardButton("/help"), KeyboardButton("/support"))
            keyboard.add(KeyboardButton("🌐 Language" if user_languages.get(chat_id, "en") == "en" else "🌐 Idioma"))
            await safe_send(self.bot, chat_id, get_text("start", chat_id=chat_id), reply_markup=keyboard)

        @self.dp.message_handler(lambda msg: msg.text.lower() in ["/help", "help"])
        async def help_cmd(msg: types.Message):
            await safe_send(self.bot, msg.chat.id, get_text("help", chat_id=msg.chat.id))

        @self.dp.message_handler(lambda msg: msg.text.lower() in ["/support", "support"])
        async def support_cmd(msg: types.Message):
            await safe_send(self.bot, msg.chat.id, f"🛟 {get_text('support_contact', chat_id=msg.chat.id)} {CONFIG['support']['username']}")

        @self.dp.message_handler(lambda msg: msg.text.lower() in ["/stop", "stop"])
        async def stop_cmd(msg: types.Message, state: FSMContext):
            await state.finish()
            await safe_send(self.bot, msg.chat.id, get_text("stopped", chat_id=msg.chat.id))

        @self.dp.message_handler(lambda msg: msg.text.lower() in ["/status", "status"])
        async def status_cmd(msg: types.Message):
            user_id = msg.chat.id
            sym_info = signal_context.get(user_id)
            if sym_info:
                response = get_text("bot_running", chat_id=user_id).format(
                    timeframe=sym_info['timeframe'], symbol=sym_info['symbol']
                )
            else:
                response = get_text("bot_running_no_ctx", chat_id=user_id)
            await safe_send(self.bot, user_id, response, parse_mode="Markdown")

        @self.dp.message_handler(lambda msg: msg.text.lower() in ["/retrain", "retrain"])
        async def retrain_force(msg: types.Message):
            await safe_send(self.bot, msg.chat.id, get_text("force_retraining", chat_id=msg.chat.id))
            run_training()

        @self.dp.message_handler(lambda msg: msg.text in ["🌐 Language", "🌐 Idioma"])
        async def toggle_lang(msg: types.Message):
            chat_id = msg.chat.id
            current_lang = user_languages.get(chat_id, "en")
            new_lang = "pt" if current_lang == "en" else "en"
            user_languages[chat_id] = new_lang
            await safe_send(self.bot, chat_id, get_text("language_set", chat_id=chat_id))

        @self.dp.message_handler(lambda msg: msg.text in ["📈 Start", "📈 Iniciar"], state="*")
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
            # Botão voltar
            kb.add(InlineKeyboardButton(get_text("back", chat_id=callback.from_user.id), callback_data="back_mainmenu"))
            await callback.message.edit_text(get_text("choose_timeframe", chat_id=callback.from_user.id), reply_markup=kb)
            await callback.answer()

        @self.dp.callback_query_handler(lambda c: c.data == "back_mainmenu", state="*")
        async def back_main_menu(callback: types.CallbackQuery, state: FSMContext):
            await state.finish()
            chat_id = callback.from_user.id
            keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.add(KeyboardButton("📈 Start" if user_languages.get(chat_id, "en") == "en" else "📈 Iniciar"))
            keyboard.add(KeyboardButton("/status"), KeyboardButton("/retrain"), KeyboardButton("/stop"))
            keyboard.add(KeyboardButton("/help"), KeyboardButton("/support"))
            keyboard.add(KeyboardButton("🌐 Language" if user_languages.get(chat_id, "en") == "en" else "🌐 Idioma"))
            await callback.message.edit_text(get_text("main_menu", chat_id=chat_id))
            await safe_send(self.bot, chat_id, get_text("start", chat_id=chat_id), reply_markup=keyboard)

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

        @self.dp.callback_query_handler(lambda c: c.data == "back_symbols", state=SignalState.choosing_symbol)
        async def back_symbols(callback: types.CallbackQuery, state: FSMContext):
            # Voltar para escolha de timeframe
            await state.set_state(SignalState.choosing_timeframe.state)
            kb = InlineKeyboardMarkup(row_width=3)
            buttons = [InlineKeyboardButton(tf, callback_data=f"timeframe:{tf}") for tf in CONFIG["timeframes"]]
            kb.add(*buttons)
            kb.add(InlineKeyboardButton(get_text("back", chat_id=callback.from_user.id), callback_data="back_mainmenu"))
            await callback.message.edit_text(get_text("choose_timeframe", chat_id=callback.from_user.idd),)replymarkup=kb)
            await callback.answer()

        @self.dp.callback_query_handler(lambda c: c.data.startswith("symbol:"), state=SignalState.choosing_symbol)
        async def select_symbol(callback: types.CallbackQuery, state: FSMContext):
            try:
                await callback.answer()
                except Exception as e:
        # Log para análise
                print(f"Erro ao responder callback: {e}")
                symbol = callback.data.split(":")[1].replace(" OTC", "")
                await state.update_data(symbol=symbol)
                user_data = await state.get_data()
                timeframe = user_data["timeframe"]
                kb = InlineKeyboardMarkup()
                kb.add(InlineKeyboardButton(get_text("back", chat_id=callback.from_user.id), callback_data="back_symbols"))
                # Barra de progresso
                progress_bar = get_text("progress_generating", chat_id=callback.from_user.id)
                await callback.message.edit_text(
                    f"⏱ {get_text('timeframe', chat_id=callback.from_user.id)}: `{timeframe}`\n"
                    f"💱 {get_text('pair', chat_id=callback.from_user.id)}: `{symbol}`\n\n"
                    f"{get_text('generating', chat_id=callback.from_user.id)}\n{progress_bar}",
                    parse_mode="Markdown",
                    reply_markup=kb
                )

                candles = self.data_client.fetch_candles(symbol, interval=self._map_timeframe(timeframe))
                if not candles or "history" not in candles:
                    await safe_send(self.bot, callback.from_user.id, get_text("failed_price_data", chat_id=callback.from_user.id))
                    return

                signal_data = self.strategy.generate_signal(candles, timeframe=self._map_timeframe(timeframe))
                if not signal_data:
                    await safe_send(self.bot, callback.from_user.id, get_text("no_signal", chat_id=callback.from_user.id))
                else:
                    try:
                        latest_candle = candles["history"][-1]
                        candle_close_utc = pd.to_datetime(latest_candle.get('close_time') or latest_candle.get('timestamp'), utc=True)
                        recommended_entry_time = to_maputo_time(candle_close_utc)
                    except Exception:
                        recommended_entry_time = to_maputo_time(pd.Timestamp.utcnow())
                    signal_data["recommended_entry_time"] = recommended_entry_time.strftime("%Y-%m-%d %H:%M:%S")
                    expire_entry_time = recommended_entry_time + pd.Timedelta(minutes=1)
                    signal_data["expire_entry_time"] = expire_entry_time.strftime("%Y-%m-%d %H:%M:%S")
                    signal_context[callback.from_user.id] = {"symbol": symbol, "timeframe": timeframe}
                    await self.send_trade_signal(callback.from_user.id, symbol, signal_data)

            except Exception as e:
                await safe_send(self.bot, callback.from_user.id, f"❌ {get_text('error', chat_id=callback.from_user.id)}: {str(e)}")

            await state.finish()

        @self.dp.callback_query_handler(lambda c: c.data == "refresh_signal")
        async def refresh(callback: types.CallbackQuery):
            uid = callback.from_user.id
            await callback.answer()
            if uid not in signal_context:
                await callback.answer(get_text("no_previous_signal", chat_id=uid), show_alert=True)
                return

            ctx = signal_context[uid]
            candles = self.data_client.fetch_candles(ctx["symbol"], interval=self._map_timeframe(ctx["timeframe"]))

            if not candles or "history" not in candles:
                await safe_send(self.bot, uid, get_text("no_signal", chat_id=uid))
                return

            signal_data = self.strategy.generate_signal(candles, timeframe=self._map_timeframe(ctx["timeframe"]))
            if signal_data:
                try:
                    latest_candle = candles["history"][-1]
                    candle_close_utc = pd.to_datetime(latest_candle.get('close_time') or latest_candle.get('timestamp'), utc=True)
                    recommended_entry_time = to_maputo_time(candle_close_utc)
                except Exception:
                    recommended_entry_time = to_maputo_time(pd.Timestamp.utcnow())
                signal_data["recommended_entry_time"] = recommended_entry_time.strftime("%Y-%m-%d %H:%M:%S")
                expire_entry_time = recommended_entry_time + pd.Timedelta(minutes=1)
                signal_data["expire_entry_time"] = expire_entry_time.strftime("%Y-%m-%d %H:%M:%S")
                await self.send_trade_signal(uid, ctx["symbol"], signal_data)

    async def send_symbol_buttons(self, message, user_id, page=0):
        kb = InlineKeyboardMarkup(row_width=2)
        symbols = SYMBOL_PAGES_OTC[page] if self.mode_map.get(user_id) == "otc" else SYMBOL_PAGES[page]
        buttons = [InlineKeyboardButton(sym, callback_data=f"symbol:{sym}") for sym in symbols]
        kb.add(*buttons)
        if page == 0:
            kb.add(InlineKeyboardButton("➡️ " + get_text("more", chat_id=user_id), callback_data="more_symbols"))
        kb.add(InlineKeyboardButton(get_text("back", chat_id=user_id), callback_data="back_mainmenu"))
        await message.edit_text(get_text("choose_symbol", chat_id=message.chat.id), reply_markup=kb)

    def _map_timeframe(self, tf):
        return {
            "S1": "s1", "M1": "1min", "M5": "5min", "M15": "15min",
            "M30": "30min", "H1": "1h", "H4": "4h", "D1": "1day"
        }.get(tf, "1min")

    async def send_trade_signal(self, chat_id, asset, signal_data):
        signal_data["symbol"] = asset
        signal_data["user"] = chat_id
        signal_data["timestamp"] = to_maputo_time(pd.Timestamp.utcnow()).strftime("%Y-%m-%d %H:%M:%S")
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
            f"📈 *{get_text('direction', chat_id=chat_id)}:* `{get_text(signal_data['signal'].lower(), chat_id=chat_id)}`\n"
            f"💪 *{get_text('strength', chat_id=chat_id)}:* `{get_text(signal_data['strength'].lower(), chat_id=chat_id)}`\n"
            f"🎯 *{get_text('confidence', chat_id=chat_id)}:* `{signal_data['confidence']}%`\n\n"
            f"💰 *{get_text('entry', chat_id=chat_id)}:* `{signal_data['price']}`\n"
            f"🕒 *{get_text('recommend_entry', chat_id=chat_id)}:* `{signal_data['recommended_entry_time']}`\n"
            f"⏳ *{get_text('expire_entry', chat_id=chat_id)}:* `{signal_data['expire_entry_time']}`\n"
            f"📈 *{get_text('high', chat_id=chat_id)}:* `{signal_data['high']}`\n"
            f"📉 *{get_text('low', chat_id=chat_id)}:* `{signal_data['low']}`\n"
            f"📦 *{get_text('volume', chat_id=chat_id)}:* `{signal_data['volume']}`\n\n"
            f"💸 *{get_text('payout', chat_id=chat_id)}:* `{payout}`\n"
            f"⏱ *{get_text('timer', chat_id=chat_id)}*"
        )

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔁 " + get_text("refresh", chat_id=chat_id), callback_data="refresh_signal"))
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
