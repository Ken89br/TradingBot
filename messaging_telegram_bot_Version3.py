# messaging/telegram_bot.py
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           ReplyKeyboardMarkup, KeyboardButton)
from aiohttp import web

from config import CONFIG
from utils.signal_logger import log_signal
from utils.telegram_safe import safe_send
from strategy.train_model_historic import main as run_training

import pandas as pd
import os
import time
from dotenv import load_dotenv

from datetime import datetime
import pytz

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TZ_MAPUTO = pytz.timezone("Africa/Maputo")

def to_maputo_time(dt_utc):
    if isinstance(dt_utc, pd.Timestamp):
        dt_utc = dt_utc.to_pydatetime()
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=pytz.UTC)
    return dt_utc.astimezone(TZ_MAPUTO)

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

def menu_main(chat_id):
    lang = user_languages.get(chat_id, "en")
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("📈 Start" if lang == "en" else "📈 Iniciar"))
    markup.add(KeyboardButton("/status"), KeyboardButton("/retrain"), KeyboardButton("/stop"))
    markup.add(KeyboardButton("/help"), KeyboardButton("/support"))
    markup.add(KeyboardButton("🌐 Language" if lang == "en" else "🌐 Idioma"))
    return markup

def menu_cancel(chat_id):
    lang = user_languages.get(chat_id, "en")
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("❌ Cancel" if lang == "en" else "❌ Cancelar"))
    return markup

class TelegramNotifier:
    def __init__(self, token, strategy, data_client):
        self.bot = Bot(token=token)
        self.dp = Dispatcher(self.bot, storage=MemoryStorage())
        self.strategy = strategy
        self.data_client = data_client
        self.mode_map = {}

        @self.dp.message_handler(commands=["start"])
        async def start_cmd(msg: types.Message):
            try:
                chat_id = msg.chat.id
                REGISTERED_USERS.add(chat_id)
                await safe_send(self.bot, chat_id, get_text("start", chat_id=chat_id), reply_markup=menu_main(chat_id))
            except Exception as e:
                logger.exception(f"Error in /start handler: {e}")

        @self.dp.message_handler(lambda msg: msg.text.lower() in ["/help", "help"])
        async def help_cmd(msg: types.Message):
            try:
                await safe_send(self.bot, msg.chat.id, get_text("help", chat_id=msg.chat.id))
            except Exception as e:
                logger.exception(f"Error in /help handler: {e}")

        @self.dp.message_handler(lambda msg: msg.text.lower() in ["/support", "support"])
        async def support_cmd(msg: types.Message):
            try:
                await safe_send(self.bot, msg.chat.id, f"🛟 {get_text('support_contact', chat_id=msg.chat.id)} {CONFIG['support']['username']}")
            except Exception as e:
                logger.exception(f"Error in /support handler: {e}")

        @self.dp.message_handler(lambda msg: msg.text.lower() in ["/stop", "stop"])
        async def stop_cmd(msg: types.Message, state: FSMContext):
            try:
                await state.finish()
                await safe_send(self.bot, msg.chat.id, get_text("stopped", chat_id=msg.chat.id), reply_markup=menu_main(msg.chat.id))
            except Exception as e:
                logger.exception(f"Error in /stop handler: {e}")

        @self.dp.message_handler(lambda msg: msg.text.lower() in ["/status", "status"])
        async def status_cmd(msg: types.Message):
            try:
                user_id = msg.chat.id
                sym_info = signal_context.get(user_id)
                if sym_info:
                    response = get_text("bot_running", chat_id=user_id).format(
                        timeframe=sym_info['timeframe'], symbol=sym_info['symbol']
                    )
                else:
                    response = get_text("bot_running_no_ctx", chat_id=user_id)
                await safe_send(self.bot, user_id, response, parse_mode="Markdown")
            except Exception as e:
                logger.exception(f"Error in /status handler: {e}")

        @self.dp.message_handler(lambda msg: msg.text.lower() in ["/retrain", "retrain"])
        async def retrain_force(msg: types.Message):
            try:
                await safe_send(self.bot, msg.chat.id, get_text("force_retraining", chat_id=msg.chat.id))
                run_training()
            except Exception as e:
                logger.exception(f"Error in /retrain handler: {e}")

        @self.dp.message_handler(lambda msg: msg.text in ["🌐 Language", "🌐 Idioma"])
        async def toggle_lang(msg: types.Message):
            try:
                chat_id = msg.chat.id
                current_lang = user_languages.get(chat_id, "en")
                new_lang = "pt" if current_lang == "en" else "en"
                user_languages[chat_id] = new_lang
                await safe_send(self.bot, chat_id, get_text("language_set", chat_id=chat_id), reply_markup=menu_main(chat_id))
            except Exception as e:
                logger.exception(f"Error in language toggle handler: {e}")

        @self.dp.message_handler(lambda msg: msg.text in ["📈 Start", "📈 Iniciar"], state="*")
        async def start_signal(msg: types.Message):
            try:
                await SignalState.choosing_mode.set()
                kb = InlineKeyboardMarkup(row_width=2)
                kb.add(
                    InlineKeyboardButton("🌍 Normal", callback_data="mode:normal"),
                    InlineKeyboardButton("🕒 OTC", callback_data="mode:otc")
                )
                await safe_send(self.bot, msg.chat.id, get_text("choose_mode", chat_id=msg.chat.id), reply_markup=kb)
                # Mostra menu de cancelamento durante fluxo
                await safe_send(self.bot, msg.chat.id, get_text("cancel_hint", chat_id=msg.chat.id), reply_markup=menu_cancel(msg.chat.id))
            except Exception as e:
                logger.exception(f"Error in start_signal handler: {e}")

        @self.dp.message_handler(lambda msg: msg.text in ["❌ Cancel", "❌ Cancelar"], state="*")
        async def cancel_any(msg: types.Message, state: FSMContext):
            try:
                await state.finish()
                await safe_send(self.bot, msg.chat.id, get_text("cancelled", chat_id=msg.chat.id), reply_markup=menu_main(msg.chat.id))
            except Exception as e:
                logger.exception(f"Error in cancel_any handler: {e}")

        @self.dp.callback_query_handler(lambda c: c.data.startswith("mode:"), state=SignalState.choosing_mode)
        async def select_mode(callback: types.CallbackQuery, state: FSMContext):
            try:
                mode = callback.data.split(":")[1]
                self.mode_map[callback.from_user.id] = mode
                await state.set_state(SignalState.choosing_timeframe.state)
                kb = InlineKeyboardMarkup(row_width=3)
                buttons = [InlineKeyboardButton(tf, callback_data=f"timeframe:{tf}") for tf in CONFIG["timeframes"]]
                kb.add(*buttons)
                kb.add(InlineKeyboardButton(get_text("back", chat_id=callback.from_user.id), callback_data="back_mainmenu"))
                await callback.message.edit_text(get_text("choose_timeframe", chat_id=callback.from_user.id), reply_markup=kb)
                await callback.answer()
                await safe_send(self.bot, callback.from_user.id, get_text("cancel_hint", chat_id=callback.from_user.id), reply_markup=menu_cancel(callback.from_user.id))
            except Exception as e:
                logger.exception(f"Error in select_mode handler: {e}")

        @self.dp.callback_query_handler(lambda c: c.data == "back_mainmenu", state="*")
        async def back_main_menu(callback: types.CallbackQuery, state: FSMContext):
            try:
                await state.finish()
                chat_id = callback.from_user.id
                await callback.message.edit_text(get_text("main_menu", chat_id=chat_id))
                await safe_send(self.bot, chat_id, get_text("start", chat_id=chat_id), reply_markup=menu_main(chat_id))
            except Exception as e:
                logger.exception(f"Error in back_main_menu handler: {e}")

        @self.dp.callback_query_handler(lambda c: c.data.startswith("timeframe:"), state=SignalState.choosing_timeframe)
        async def select_timeframe(callback: types.CallbackQuery, state: FSMContext):
            try:
                tf = callback.data.split(":")[1]
                await state.update_data(timeframe=tf)
                await state.set_state(SignalState.choosing_symbol.state)
                await self.send_symbol_buttons(callback.message, callback.from_user.id, page=0)
                await callback.answer()
                await safe_send(self.bot, callback.from_user.id, get_text("cancel_hint", chat_id=callback.from_user.id), reply_markup=menu_cancel(callback.from_user.id))
            except Exception as e:
                logger.exception(f"Error in select_timeframe handler: {e}")

        @self.dp.callback_query_handler(lambda c: c.data == "more_symbols", state=SignalState.choosing_symbol)
        async def next_symbols(callback: types.CallbackQuery, state: FSMContext):
            try:
                await self.send_symbol_buttons(callback.message, callback.from_user.id, page=1)
                await callback.answer()
            except Exception as e:
                logger.exception(f"Error in next_symbols handler: {e}")

        @self.dp.callback_query_handler(lambda c: c.data == "back_symbols", state=SignalState.choosing_symbol)
        async def back_symbols(callback: types.CallbackQuery, state: FSMContext):
            try:
                await state.set_state(SignalState.choosing_timeframe.state)
                kb = InlineKeyboardMarkup(row_width=3)
                buttons = [InlineKeyboardButton(tf, callback_data=f"timeframe:{tf}") for tf in CONFIG["timeframes"]]
                kb.add(*buttons)
                kb.add(InlineKeyboardButton(get_text("back", chat_id=callback.from_user.id), callback_data="back_mainmenu"))
                await callback.message.edit_text(get_text("choose_timeframe", chat_id=callback.from_user.id), reply_markup=kb)
                await callback.answer()
            except Exception as e:
                logger.exception(f"Error in back_symbols handler: {e}")

        @self.dp.callback_query_handler(lambda c: c.data.startswith("symbol:"), state=SignalState.choosing_symbol)
        async def select_symbol(callback: types.CallbackQuery, state: FSMContext):
            try:
                await callback.answer()
                symbol = callback.data.split(":")[1].replace(" OTC", "")
                await state.update_data(symbol=symbol)
                user_data = await state.get_data()
                timeframe = user_data["timeframe"]
                kb = InlineKeyboardMarkup()
                kb.add(InlineKeyboardButton(get_text("back", chat_id=callback.from_user.id), callback_data="back_symbols"))
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
                    await safe_send(self.bot, callback.from_user.id, get_text("failed_price_data", chat_id=callback.from_user.id), reply_markup=menu_main(callback.from_user.id))
                    return

                signal_data = self.strategy.generate_signal(candles, timeframe=self._map_timeframe(timeframe))
                if not signal_data:
                    await safe_send(self.bot, callback.from_user.id, get_text("no_signal", chat_id=callback.from_user.id), reply_markup=menu_main(callback.from_user.id))
                else:
                    try:
                        latest_candle = candles["history"][-1]
                        candle_close_utc = pd.to_datetime(latest_candle.get('close_time') or latest_candle.get('timestamp'), utc=True)
                        recommended_entry_time = to_maputo_time(candle_close_utc)
                    except Exception:
                        recommended_entry_time = to_maputo_time(pd.Timestamp.utcnow())
                    signal_data["recommended_entry_time"] = recommended_entry_time.strftime("%Y-%m-%d %H:%M:%S")
                    expire_entry_time = recommended_entry_time + pd.Timedelta(minutes=1)