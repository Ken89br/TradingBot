import logging
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

from datetime import datetime
import pytz

# Configuração básica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuração de fuso horário
TZ_MAPUTO = pytz.timezone("Africa/Maputo")

def to_maputo_time(dt_utc):
    """Converte datetime UTC para o fuso horário de Maputo"""
    if isinstance(dt_utc, pd.Timestamp):
        dt_utc = dt_utc.to_pydatetime()
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=pytz.UTC)
    return dt_utc.astimezone(TZ_MAPUTO)

load_dotenv()

# Estados do bot
class SignalState(StatesGroup):
    choosing_mode = State()
    choosing_timeframe = State()
    choosing_symbol = State()

# Variáveis globais
REGISTERED_USERS = set()
signal_context = {}
user_languages = {}

# Paginação de símbolos
SYMBOL_PAGES = [CONFIG["symbols"][:8], CONFIG["symbols"][8:]]
SYMBOL_PAGES_OTC = [CONFIG["otc_symbols"][:8], CONFIG["otc_symbols"][8:]]

def get_text(key, lang=None, chat_id=None):
    """Obtém texto traduzido com fallback para inglês"""
    if chat_id:
        lang = user_languages.get(chat_id, "en")
    lang = lang or "en"
    return CONFIG["languages"].get(lang, CONFIG["languages"]["en"]).get(key, key)

def menu_main(chat_id):
    """Menu principal com base no idioma do usuário"""
    lang = user_languages.get(chat_id, "en")
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("📈 Start" if lang == "en" else "📈 Iniciar"))
    markup.add(KeyboardButton("/status"), KeyboardButton("/retrain"), KeyboardButton("/stop"))
    markup.add(KeyboardButton("/help"), KeyboardButton("/support"))
    markup.add(KeyboardButton("🌐 Language" if lang == "en" else "🌐 Idioma"))
    return markup

def menu_cancel(chat_id):
    """Menu de cancelamento com texto localizado"""
    lang = user_languages.get(chat_id, "en")
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("❌ Cancell" if lang == "en" else "❌ Cancelar"))
    return markup

class TelegramNotifier:
    def __init__(self, token, strategy, data_client):
        self.bot = Bot(token=token)
        self.dp = Dispatcher(self.bot, storage=MemoryStorage())
        self.strategy = strategy
        self.data_client = data_client
        self.mode_map = {}  # Mapeamento de modo por usuário

        # Handler para comando /start
        @self.dp.message_handler(commands=["start"])
        async def start_cmd(msg: types.Message):
            try:
                chat_id = msg.chat.id
                REGISTERED_USERS.add(chat_id)
                await safe_send(
                    self.bot, 
                    chat_id, 
                    get_text("start", chat_id=chat_id), 
                    reply_markup=menu_main(chat_id)
                )
            except Exception as e:
                logger.exception(f"Error in /start handler: {e}")

        # Handler para comando /help
        @self.dp.message_handler(lambda msg: msg.text.lower() in ["/help", "help"])
        async def help_cmd(msg: types.Message):
            try:
                await safe_send(self.bot, msg.chat.id, get_text("help", chat_id=msg.chat.id))
            except Exception as e:
                logger.exception(f"Error in /help handler: {e}")

        # Handler para comando /support
        @self.dp.message_handler(lambda msg: msg.text.lower() in ["/support", "support"])
        async def support_cmd(msg: types.Message):
            try:
                await safe_send(
                    self.bot, 
                    msg.chat.id, 
                    f"🛟 {get_text('support_contact', chat_id=msg.chat.id)} {CONFIG['support']['username']}"
                )
            except Exception as e:
                logger.exception(f"Error in /support handler: {e}")

        # Handler para comando /stop
        @self.dp.message_handler(lambda msg: msg.text.lower() in ["/stop", "stop"])
        async def stop_cmd(msg: types.Message, state: FSMContext):
            try:
                await state.finish()
                await safe_send(
                    self.bot, 
                    msg.chat.id, 
                    get_text("stopped", chat_id=msg.chat.id), 
                    reply_markup=menu_main(msg.chat.id)
                )
            except Exception as e:
                logger.exception(f"Error in /stop handler: {e}")

        # Handler para comando /status
        @self.dp.message_handler(lambda msg: msg.text.lower() in ["/status", "status"])
        async def status_cmd(msg: types.Message):
            try:
                user_id = msg.chat.id
                sym_info = signal_context.get(user_id)
                if sym_info:
                    response = get_text("bot_running", chat_id=user_id).format(
                        timeframe=sym_info['timeframe'], 
                        symbol=sym_info['symbol']
                    )
                else:
                    response = get_text("bot_running_no_ctx", chat_id=user_id)
                await safe_send(self.bot, user_id, response, parse_mode="Markdown")
            except Exception as e:
                logger.exception(f"Error in /status handler: {e}")

        # Handler para comando /retrain
        @self.dp.message_handler(lambda msg: msg.text.lower() in ["/retrain", "retrain"])
        async def retrain_force(msg: types.Message):
            try:
                await safe_send(
                    self.bot, 
                    msg.chat.id, 
                    get_text("force_retraining", chat_id=msg.chat.id)
                )
                run_training()
            except Exception as e:
                logger.exception(f"Error in /retrain handler: {e}")

        # Handler para alternar idioma
        @self.dp.message_handler(lambda msg: msg.text in ["🌐 Language", "🌐 Idioma"])
        async def toggle_lang(msg: types.Message):
            try:
                chat_id = msg.chat.id
                current_lang = user_languages.get(chat_id, "en")
                new_lang = "pt" if current_lang == "en" else "en"
                user_languages[chat_id] = new_lang
                await safe_send(
                    self.bot, 
                    chat_id, 
                    get_text("language_set", chat_id=chat_id), 
                    reply_markup=menu_main(chat_id)
                )
            except Exception as e:
                logger.exception(f"Error in language toggle handler: {e}")

        # Handler para iniciar sinal
        @self.dp.message_handler(lambda msg: msg.text in ["📈 Start", "📈 Iniciar"], state="*")
        async def start_signal(msg: types.Message):
            try:
                await SignalState.choosing_mode.set()
                kb = InlineKeyboardMarkup(row_width=2)
                kb.add(
                    InlineKeyboardButton("🌍 CoreFX", callback_data="mode:normal"),
                    InlineKeyboardButton("🕒 OTC", callback_data="mode:otc")
                )
                await safe_send(
                    self.bot, 
                    msg.chat.id, 
                    get_text("choose_mode", chat_id=msg.chat.id), 
                    reply_markup=kb
                )
                # Envia menu de cancelamento separadamente
                await safe_send(
                    self.bot,
                    msg.chat.id,
                    " ",
                    reply_markup=menu_cancel(msg.chat.id)
                )
            except Exception as e:
                logger.exception(f"Error in start_signal handler: {e}")

        # Handler para cancelamento (corrigido para "Cancell" e "Cancelar")
        @self.dp.message_handler(
            lambda msg: msg.text in ["❌ Cancell", "❌ Cancelar"], 
            state="*"
        )
        async def cancel_any(msg: types.Message, state: FSMContext):
            try:
                current_state = await state.get_state()
                if current_state:
                    await state.finish()
                    await safe_send(
                        self.bot, 
                        msg.chat.id, 
                        get_text("cancelled", chat_id=msg.chat.id),
                        reply_markup=menu_main(msg.chat.id)
                    )
                else:
                    await safe_send(
                        self.bot,
                        msg.chat.id,
                        get_text("no_active_process", chat_id=msg.chat.id),
                        reply_markup=menu_main(msg.chat.id)
                    )
            except Exception as e:
                logger.exception(f"Error in cancel_any handler: {e}")

        # ... (restante dos handlers mantidos conforme original)

    async def send_symbol_buttons(self, message, user_id, page=0):
        """Mostra os símbolos disponíveis com paginação"""
        try:
            kb = InlineKeyboardMarkup(row_width=2)
            symbols = SYMBOL_PAGES_OTC[page] if self.mode_map.get(user_id) == "otc" else SYMBOL_PAGES[page]
            buttons = [InlineKeyboardButton(sym, callback_data=f"symbol:{sym}") for sym in symbols]
            kb.add(*buttons)
            
            # Adiciona navegação entre páginas se necessário
            if len(SYMBOL_PAGES) > 1:
                if page > 0:
                    kb.add(InlineKeyboardButton(
                        "⬅️ " + get_text("back", chat_id=user_id), 
                        callback_data=f"symbol_page:{page-1}"
                    ))
                if page < len(SYMBOL_PAGES)-1:
                    kb.add(InlineKeyboardButton(
                        "➡️ " + get_text("more", chat_id=user_id), 
                        callback_data=f"symbol_page:{page+1}"
                    ))
            
            kb.add(InlineKeyboardButton(
                get_text("back", chat_id=user_id), 
                callback_data="back_symbols"
            ))
            
            await message.edit_text(
                get_text("choose_symbol", chat_id=user_id),
                reply_markup=kb
            )
            
            # Envia menu de cancelamento separadamente
            await safe_send(
                self.bot,
                user_id,
                " ",
                reply_markup=menu_cancel(user_id)
            )
        except Exception as e:
            logger.exception(f"Error in send_symbol_buttons: {e}")

    # ... ( Adicona KEN original)

    async def send_trade_signal(self, chat_id, asset, signal_data):
        signal_data["symbol"] = asset
        signal_data["user"] = chat_id
        signal_data["timestamp"] = to_maputo_time(pd.Timestamp.utcnow()).strftime("%Y-%m-%d %H:%M:%S")
        signal_data["recommend_entry"] = signal_data.get("recommended_entry_time")

        # ======== LOTE BASEADO NA CONFIANÇA ==========
        try:
            confidence = float(signal_data.get("confidence", 0))
            confidence = max(0, min(confidence, 100))
        except Exception:
            confidence = 0

        min_lot = 1
        max_lot = 100
        lot_size = min_lot + (max_lot - min_lot) * (confidence / 100)
        lot_size = round(lot_size)
        lot_display = f"${lot_size}"

        signal_data["lot_size"] = lot_size
        signal_data["lot_display"] = lot_display
        # =============================================

        log_signal(chat_id, asset, signal_data.get("timeframe"), signal_data)

        SIGNAL_CSV_PATH = "signals.csv"
        df = pd.DataFrame([signal_data])
        if os.path.exists(SIGNAL_CSV_PATH):
            df.to_csv(SIGNAL_CSV_PATH, mode="a", header=False, index=False)
        else:
            df.to_csv(SIGNAL_CSV_PATH, index=False)

        payout = round(signal_data.get('price', 0) * 0.92, 5)
        patterns_list = signal_data.get("patterns", [])
        patterns_str = ", ".join([get_text(p, chat_id=chat_id) for p in patterns_list]) if patterns_list else "-"

        par = asset
        timer = signal_data.get('timer', get_text('timer', chat_id=chat_id))
        direction = get_text(signal_data.get('signal', '').lower(), chat_id=chat_id)
        strength = get_text(signal_data.get('strength', '-').lower(), chat_id=chat_id)
        confidence_disp = signal_data.get('confidence', '-')
        entry = signal_data.get('recommended_entry_price', signal_data.get('price', '-'))
        recommend_entry = signal_data.get('recommended_entry_time', '-')
        expire_entry = signal_data.get('expire_entry_time', '-')
        expire_entry_price = signal_data.get('expire_entry_price', entry)
        high = signal_data.get('high', '-')
        low = signal_data.get('low', '-')
        volume = signal_data.get('volume', '-')
        volatility = signal_data.get('volatility', '-')
        sentiment = signal_data.get('sentiment', '-')
        variation = signal_data.get('variation', '-')
        risk = signal_data.get('risk', get_text('low_risk', chat_id=chat_id))
        support = signal_data.get('support', '-')
        resistance = signal_data.get('resistance', '-')
        summary = get_text(signal_data.get('summary', '-').lower(), chat_id=chat_id)
        ma = get_text(signal_data.get('moving_averages', '-').lower(), chat_id=chat_id)
        osc = get_text(signal_data.get('oscillators', '-').lower(), chat_id=chat_id)
        rsi = signal_data.get('rsi', '-')
        macd = signal_data.get('macd', '-')
        bollinger = signal_data.get('bollinger', '-')
        atr = signal_data.get('atr', '-')
        adx = signal_data.get('adx', '-')
        volume_status = get_text(signal_data.get('volume_status', '-').lower(), chat_id=chat_id)

        # Mensagem rica: hora/expiração/preço sempre dinâmicos vindos do ensemble
        msg = (
            f"📡 *{get_text('signal_title', chat_id=chat_id)}*\n\n"
            f"📌 *{get_text('pair', chat_id=chat_id)}:* `{par}`\n"
            f"⏱ *{get_text('timer', chat_id=chat_id)}:* {timer}\n"
            f"🕒 *{get_text('recommend_entry', chat_id=chat_id)}:* `{recommend_entry} (entry price: {entry})`\n"
            f"⏳ *{get_text('expire_entry', chat_id=chat_id)}:* `{expire_entry} (entry price: {expire_entry_price})`\n"
            f"💵 *{get_text('lot_size', chat_id=chat_id)}:* `{lot_display}`\n\n"
            f"📈 *{get_text('direction', chat_id=chat_id)}:* `{direction}`\n"
            f"💪 *{get_text('strength', chat_id=chat_id)}:* `{strength}`\n"
            f"🎯 *{get_text('confidence', chat_id=chat_id)}:* `{confidence_disp}%`\n"
            f"💰 *{get_text('entry', chat_id=chat_id)}:* `{entry}`\n"
            f"📈 *{get_text('high', chat_id=chat_id)}:* `{high}`\n"
            f"📉 *{get_text('low', chat_id=chat_id)}:* `{low}`\n"
            f"📦 *{get_text('volume', chat_id=chat_id)}:* `{volume}`\n"
            f"💸 *{get_text('payout', chat_id=chat_id)}:* `{payout}`\n\n"
            f"__*{get_text('market_overview', chat_id=chat_id)}*__\n"
            f"• {get_text('volatility', chat_id=chat_id)}: *{volatility}*\n"
            f"• {get_text('sentiment', chat_id=chat_id)}: *{sentiment}*\n"
            f"• {get_text('variation', chat_id=chat_id)}: *{variation}*\n"
            f"• {get_text('risk', chat_id=chat_id)}: *{risk}*\n"
            f"• {get_text('support', chat_id=chat_id)}: `{support}`\n"
            f"• {get_text('resistance', chat_id=chat_id)}: `{resistance}`\n\n"
            f"__*{get_text('tradingview_rating', chat_id=chat_id)}*__\n"
            f"• {get_text('summary', chat_id=chat_id)}: *{summary}*\n"
            f"• {get_text('moving_averages', chat_id=chat_id)}: *{ma}*\n"
            f"• {get_text('oscillators', chat_id=chat_id)}: *{osc}*\n\n"
            f"__*{get_text('technical_analysis', chat_id=chat_id)}*__\n"
            f"• RSI: *{rsi}*\n"
            f"• MACD: *{macd}*\n"
            f"• {get_text('bollinger_bands', chat_id=chat_id)}: *{bollinger}*\n"
            f"• {get_text('atr', chat_id=chat_id)}: *{atr}*\n"
            f"• {get_text('adx', chat_id=chat_id)}: *{adx}*\n"
            f"• {get_text('patterns', chat_id=chat_id)}: *{patterns_str}*\n"
            f"• {get_text('volume_status', chat_id=chat_id)}: *{volume_status}*\n"
        )

            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton(
                "🔁 " + get_text("refresh", chat_id=chat_id), 
                callback_data="refresh_signal"
            ))
            
            await safe_send(
                self.bot, 
                chat_id, 
                msg, 
                parse_mode="Markdown", 
                reply_markup=keyboard
            )
        except Exception as e:
            logger.exception(f"Error in send_trade_signal: {e}")

    # ... (restante dos métodos mantidos conforme original)
