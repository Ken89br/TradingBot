import pandas as pd
from strategy.ml_utils import add_indicators
from strategy.candlestick_patterns import detect_candlestick_patterns, get_pattern_strength
from strategy.indicator_globe import TechnicalIndicators
from utils.features_extra import calc_obv, calc_spread
from data.fundamental_data import get_cot_feature, get_macro_feature, get_sentiment_feature

def prepare_universal_features(candles: list, symbol: str, timeframe: str) -> pd.DataFrame:
    """
    Recebe candles OHLCV (dicts) e retorna DataFrame enriquecido com todos os indicadores, padrões, price action, etc.
    Todas as estratégias devem consumir esse DataFrame (ou extrair apenas as colunas que precisam).
    """
    if not candles or len(candles) < 3:
        return pd.DataFrame()  # Proteção mínima

    df = pd.DataFrame(candles)
    # Garantir colunas mínimas
    for col in ["open", "high", "low", "close", "volume"]:
        if col not in df.columns:
            raise ValueError(f"Coluna {col} ausente nos candles")

    # Indicadores clássicos e técnicos
    df['returns'] = df['close'].pct_change()
    df['volatility'] = df['returns'].rolling(20).std()
    for period in [5, 10, 20, 50]:
        df[f'sma_{period}'] = df['close'].rolling(period).mean()
    for period in [12, 26]:
        df[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()

    # RSI, MACD
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(span=14, adjust=False).mean()
    avg_loss = loss.ewm(span=14, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    df['rsi'] = 100 - (100 / (1 + rs))

    ema12 = df['ema_12']
    ema26 = df['ema_26']
    df['macd'] = ema12 - ema26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']

    # Bollinger Bands
    sma20 = df['sma_20']
    rolling_std = df['close'].rolling(20).std()
    df['bb_upper'] = sma20 + 2 * rolling_std
    df['bb_lower'] = sma20 - 2 * rolling_std
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / sma20
    df['bb_pct'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

    # ATR, ADX
    tr1 = df['high'] - df['low']
    tr2 = abs(df['high'] - df['close'].shift())
    tr3 = abs(df['low'] - df['close'].shift())
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = true_range.rolling(14).mean()
    closes, highs, lows, volumes = df['close'].tolist(), df['high'].tolist(), df['low'].tolist(), df['volume'].tolist()
    df["adx"] = calc_adx(highs, lows, closes)
    df["atr_proj"] = calc_atr(highs, lows, closes)

    # Suporte/Resistência
    df['support'] = df['low'].rolling(10, min_periods=1).min()
    df['resistance'] = df['high'].rolling(10, min_periods=1).max()
    df['support_distance'] = df['close'] - df['support']
    df['resistance_distance'] = df['resistance'] - df['close']

    # Volume
    df['volume_sma'] = df['volume'].rolling(20).mean()
    df['volume_pct'] = df['volume'] / df['volume_sma']

    # Ratings e Osciladores
    df["ma_rating"] = calc_moving_averages(closes)
    macd_hist, macd_val, macd_signal = calc_macd(closes)
    rsi_val = calc_rsi(closes)
    df["osc_rating"] = calc_oscillators(rsi_val, macd_hist)
    df["volatility_proj"] = calc_volatility(closes)
    df["volume_status"] = calc_volume_status(volumes)
    df["sentiment"] = calc_sentiment(closes)
    df["variation"] = ((df["close"] - df["close"].shift(1)) / df["close"].shift(1)) * 100

    # OBV e Spread
    df["obv"] = calc_obv(df)
    df["spread"] = calc_spread(df)

    # Candlestick Patterns (flags e força)
    pattern_list = ["bullish_engulfing", "bearish_engulfing", "hammer", "shooting_star", "doji"]
    for pattern in pattern_list:
        df[pattern] = 0
    pattern_strengths = []
    patterns_col = []
    for i in range(len(df)):
        candles_slice = df.iloc[max(i-3, 0):i+1][["open", "high", "low", "close", "volume"]].to_dict("records")
        patterns = detect_candlestick_patterns(candles_slice)
        patterns_col.append(patterns)
        for pattern in pattern_list:
            if pattern in patterns:
                df.at[df.index[i], pattern] = 1
        pattern_strengths.append(get_pattern_strength(patterns))
    df["pattern_strength"] = pattern_strengths
    df["patterns"] = patterns_col

    # Fundamentalistas (COT, macro, sentiment news)
    if timeframe and timeframe.lower() in ['h4', 'd1']:
        df["cot"] = get_cot_feature(symbol)
        df["macro"] = get_macro_feature(symbol)
        df["sentiment_news"] = get_sentiment_feature(symbol)
    else:
        for col in ["cot", "macro", "sentiment_news"]:
            df[col] = 0

    # Padronização (mapeamento para números)
    ma_mapping = {"buy": 1, "sell": -1, "neutral": 0}
    osc_mapping = {"buy": 1, "sell": -1, "neutral": 0}
    vol_mapping = {"High": 1, "Low": 0}
    volstat_mapping = {"Spiked": 2, "Normal": 1, "Low": 0}
    sentiment_mapping = {"Optimistic": 1, "Neutral": 0, "Pessimistic": -1}
    df["ma_rating"] = df["ma_rating"].map(ma_mapping)
    df["osc_rating"] = df["osc_rating"].map(osc_mapping)
    df["volatility_proj"] = df["volatility_proj"].map(vol_mapping)
    df["volume_status"] = df["volume_status"].map(volstat_mapping)
    df["sentiment"] = df["sentiment"].map(sentiment_mapping)

    df.ffill(inplace=True)
    df.dropna(inplace=True)
    return df
