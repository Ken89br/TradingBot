import pandas as pd
from strategy.candlestick_patterns import detect_candlestick_patterns, get_pattern_strength
from strategy.indicator_globe import TechnicalIndicators
from utils.features_extra import calc_obv, calc_spread
from data.fundamental_data import get_cot_feature, get_macro_feature, get_sentiment_feature

def prepare_universal_features(candles: list, symbol: str, timeframe: str) -> pd.DataFrame:
    """
    Recebe candles OHLCV (dicts) e retorna DataFrame enriquecido com TODOS os indicadores e padrões.
    """
    if not candles or len(candles) < 6:
        return pd.DataFrame()  # Proteção mínima

    df = pd.DataFrame(candles)
    for col in ["open", "high", "low", "close", "volume"]:
        if col not in df.columns:
            raise ValueError(f"Coluna {col} ausente nos candles")

    closes = pd.Series(df["close"].values)
    highs = pd.Series(df["high"].values)
    lows = pd.Series(df["low"].values)
    volumes = pd.Series(df["volume"].values)

    # ==== INDICADORES ENRIQUECIDOS ====
    # RSI
    rsi = TechnicalIndicators.calc_rsi(closes)
    df["rsi_value"] = rsi["value"]
    df["rsi_zone"] = rsi["zone"]
    df["rsi_trend"] = rsi["trend"]

    # MACD
    macd = TechnicalIndicators.calc_macd(closes)
    df["macd_histogram"] = macd["histogram"]
    df["macd_line"] = macd["macd_line"]
    df["macd_signal_line"] = macd["signal_line"]
    df["macd_momentum"] = macd["momentum"]

    # Bollinger Bands
    bb = TechnicalIndicators.calc_bollinger(closes)
    df["bb_upper"] = bb["upper"]
    df["bb_lower"] = bb["lower"]
    df["bb_width"] = bb["width"]
    df["bb_percent_b"] = bb["percent_b"]
    df["bb_position"] = bb["position"]

    # ATR
    atr = TechnicalIndicators.calc_atr(highs, lows, closes)
    df["atr_value"] = atr["value"]
    df["atr_ratio"] = atr["ratio"]
    df["atr_trend"] = atr["trend"]

    # ADX
    adx = TechnicalIndicators.calc_adx(highs, lows, closes)
    df["adx_value"] = adx["adx"]
    df["adx_di_plus"] = adx["di_plus"]
    df["adx_di_minus"] = adx["di_minus"]
    df["adx_strength"] = adx["strength"]

    # Ichimoku
    ichimoku = TechnicalIndicators.calc_ichimoku(highs, lows, closes)
    df["ichimoku_conversion"] = ichimoku["conversion"]
    df["ichimoku_base"] = ichimoku["base"]
    df["ichimoku_leading_a"] = ichimoku["leading_a"]
    df["ichimoku_leading_b"] = ichimoku["leading_b"]
    df["ichimoku_cloud_position"] = ichimoku["cloud_position"]

    # Fibonacci
    fibo = TechnicalIndicators.calc_fibonacci(highs, lows)
    df["fibo_23_6"] = fibo["23.6%"]
    df["fibo_38_2"] = fibo["38.2%"]
    df["fibo_50"] = fibo["50%"]
    df["fibo_61_8"] = fibo["61.8%"]

    # Supertrend
    supertrend = TechnicalIndicators.calc_supertrend(highs, lows, closes)
    df["supertrend_value"] = supertrend["value"]
    df["supertrend_direction"] = supertrend["direction"]
    df["supertrend_changed"] = supertrend["changed"]

    # Market Profile
    mprofile = TechnicalIndicators.get_market_profile(closes, volumes)
    df["market_poc"] = mprofile["poc"]
    df["market_va_low"] = mprofile["value_area"]["low"]
    df["market_va_high"] = mprofile["value_area"]["high"]

    # Stochastic
    stoch = TechnicalIndicators.calc_stochastic(highs, lows, closes)
    df["stoch_k"] = stoch["k_line"]
    df["stoch_d"] = stoch["d_line"]
    df["stoch_state"] = stoch["state"]
    df["stoch_cross"] = stoch["cross"]

    # CCI
    cci = TechnicalIndicators.calc_cci(highs, lows, closes)
    df["cci_value"] = cci["value"]
    df["cci_state"] = cci["state"]
    df["cci_momentum"] = cci["momentum"]
    df["cci_strength"] = cci["strength"]

    # Williams %R
    wr = TechnicalIndicators.calc_williams_r(highs, lows, closes)
    df["williamsr_value"] = wr["value"]
    df["williamsr_state"] = wr["state"]
    df["williamsr_trend"] = wr["trend"]

    # Parabolic SAR
    psar = TechnicalIndicators.calc_parabolic_sar(highs, lows)
    df["psar_value"] = psar["value"]
    df["psar_trend"] = psar["trend"]
    df["psar_acceleration"] = psar["acceleration"]

    # Momentum
    mom = TechnicalIndicators.calc_momentum(closes)
    df["momentum_value"] = mom["value"]
    df["momentum_trend"] = mom["trend"]
    df["momentum_acceleration"] = mom["acceleration"]
    df["momentum_strength"] = mom["strength"]

    # ROC
    roc = TechnicalIndicators.calc_roc(closes)
    df["roc_value"] = roc["value"]
    df["roc_trend"] = roc["trend"]
    df["roc_momentum"] = roc["momentum"]
    df["roc_extreme"] = roc["extreme"]

    # DMI
    dmi = TechnicalIndicators.calc_dmi(highs, lows, closes)
    df["dmi_adx"] = dmi["adx"]
    df["dmi_plus_di"] = dmi["plus_di"]
    df["dmi_minus_di"] = dmi["minus_di"]
    df["dmi_trend"] = dmi["trend"]
    df["dmi_crossover"] = dmi["crossover"]

    # VWAP
    vwap = TechnicalIndicators.calc_vwap(highs, lows, closes, volumes)
    df["vwap_value"] = vwap["value"]
    df["vwap_relation"] = vwap["relation"]
    df["vwap_spread"] = vwap["spread"]
    df["vwap_trend"] = vwap["trend"]

    # Envelope
    envelope = TechnicalIndicators.calc_envelope(closes)
    df["envelope_upper"] = envelope["upper"]
    df["envelope_lower"] = envelope["lower"]
    df["envelope_center"] = envelope["center"]
    df["envelope_position"] = envelope["position"]
    df["envelope_band_width"] = envelope["band_width"]
    df["envelope_percent_center"] = envelope["percent_from_center"]

    # Elliott Wave
    elliott = TechnicalIndicators.calc_elliott_wave(closes)
    df["elliott_peaks"] = str(elliott.get("peaks", []))
    df["elliott_troughs"] = str(elliott.get("troughs", []))
    df["elliott_phase"] = elliott.get("phase", "")
    df["elliott_wave_counts"] = str(elliott.get("wave_counts", {}))

    # Zigzag
    zz = TechnicalIndicators.calc_zigzag(closes)
    df["zigzag_peaks"] = str(zz.get("peaks", []))
    df["zigzag_troughs"] = str(zz.get("troughs", []))
    df["zigzag_trend"] = zz.get("trend", "")
    df["zigzag_pattern"] = zz.get("pattern", "")
    df["zigzag_retracements"] = str(zz.get("retracements", []))

    # ========= AUXILIARES CONTEXTUAIS =========
    ma_rating = TechnicalIndicators.calc_moving_averages(closes)
    osc_rating = TechnicalIndicators.calc_oscillators(rsi["value"], macd["histogram"])
    vol = TechnicalIndicators.calc_volatility(closes)
    volstat = TechnicalIndicators.calc_volume_status(volumes)
    sentiment = TechnicalIndicators.calc_sentiment(closes)
    trendctx = TechnicalIndicators.get_trend_context(closes)
    sr = TechnicalIndicators.get_support_resistance(closes)
    df["ma_rating"] = ma_rating["rating"]
    df["osc_rating"] = osc_rating["rating"]
    df["volatility_level"] = vol["level"]
    df["volume_status"] = volstat["status"]
    df["sentiment"] = sentiment["sentiment"]
    df["trend_score"] = trendctx["trend_score"]
    df["trend_strength"] = trendctx["trend_strength"]
    df["trend_suggestion"] = trendctx["suggestion"]
    df["support_lvls"] = str(sr.get("support", []))
    df["resistance_lvls"] = str(sr.get("resistance", []))
    df["price_position"] = sr.get("current_position", "")

    # ========= PADRÕES DE VELA (TODOS OS SUPORTADOS) =========
    pattern_list = [
        "bullish_engulfing", "bearish_engulfing", "hammer", "shooting_star", "doji",
        "dragonfly_doji", "gravestone_doji", "long_legged_doji", "spinning_top",
        "hanging_man", "inverted_hammer", "marubozu", "bullish_harami", "bearish_harami",
        "harami_cross", "piercing_line", "dark_cloud_cover", "tweezer_bottom", "tweezer_top",
        "morning_star", "evening_star", "three_white_soldiers", "three_black_crows",
        "three_inside_up", "three_inside_down", "three_outside_up", "three_outside_down",
        "abandoned_baby_bullish", "abandoned_baby_bearish", "kicker_bullish", "kicker_bearish",
        "gap_up", "gap_down", "upside_tasuki_gap", "downside_tasuki_gap", "on_neckline",
        "separating_lines", "rising_three_methods", "falling_three_methods"
    ]
    for pattern in pattern_list:
        df[pattern] = 0
    pattern_strengths = []
    patterns_col = []
    for i in range(len(df)):
        candles_slice = df.iloc[max(i-5, 0):i+1][["open", "high", "low", "close", "volume"]].to_dict("records")
        patterns = detect_candlestick_patterns(candles_slice)
        patterns_col.append(patterns)
        for pattern in pattern_list:
            if pattern in patterns:
                df.at[df.index[i], pattern] = 1
        pattern_strengths.append(get_pattern_strength(patterns))
    df["pattern_strength"] = pattern_strengths
    df["patterns"] = patterns_col

    # ========= EXTRAS =========
    df["returns"] = df["close"].pct_change()
    df["volatility"] = df["returns"].rolling(20).std()
    for period in [5, 10, 20, 50]:
        df[f"sma_{period}"] = df["close"].rolling(period).mean()
    for period in [12, 26]:
        df[f"ema_{period}"] = df["close"].ewm(span=period, adjust=False).mean()
    df["obv"] = calc_obv(df)
    df["spread"] = calc_spread(df)
    df["variation"] = ((df["close"] - df["close"].shift(1)) / df["close"].shift(1)) * 100

    # Fundamentalistas
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
    trend_mapping = {"strong": 2, "moderate": 1, "weak": 0, "bearish": -1}
    zone_mapping = {"overbought": 1, "neutral": 0, "oversold": -1}

    df["ma_rating"] = df["ma_rating"].map(ma_mapping)
    df["osc_rating"] = df["osc_rating"].map(osc_mapping)
    df["volatility_level"] = df["volatility_level"].map(vol_mapping)
    df["volume_status"] = df["volume_status"].map(volstat_mapping)
    df["sentiment"] = df["sentiment"].map(sentiment_mapping)
    df["rsi_zone"] = df["rsi_zone"].map(zone_mapping)
    df["trend_strength"] = df["trend_strength"].map(trend_mapping)
    # Diferença entre médias móveis (curta e longa)
    df['diff_sma_5_20'] = df['sma_5'] - df['sma_20']
    df['diff_ema_12_26'] = df['ema_12'] - df['ema_26']

    # Cruzamento de médias móveis (flag booleana)
    df['cross_sma_5_20'] = ((df['sma_5'] > df['sma_20']) & (df['sma_5'].shift(1) <= df['sma_20'].shift(1))).astype(int)
    df['cross_ema_12_26'] = ((df['ema_12'] > df['ema_26']) & (df['ema_12'].shift(1) <= df['ema_26'].shift(1))).astype(int)

    # Cruzamento MACD/Signal
    df['macd_cross'] = ((df['macd_line'] > df['macd_signal_line']) & (df['macd_line'].shift(1) <= df['macd_signal_line'].shift(1))).astype(int)

    # Eventos raros: 3+ padrões de vela no mesmo candle
    df['num_patterns'] = df['patterns'].apply(lambda x: len(x) if isinstance(x, list) else 0)
    df['rare_pattern_event'] = (df['num_patterns'] >= 3).astype(int)

    # ATR para múltiplos períodos
    for period in [7, 14, 21, 28]:
        tr1 = df['high'] - df['low']
        tr2 = abs(df['high'] - df['close'].shift())
        tr3 = abs(df['low'] - df['close'].shift())
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df[f'atr_{period}'] = true_range.rolling(period).mean()
        # Razão ATR/close
        df[f'atr_{period}_pct'] = df[f'atr_{period}'] / df['close']

    # Bandas de Bollinger para múltiplos períodos
    for period in [10, 20, 50]:
        sma = df['close'].rolling(period).mean()
        std = df['close'].rolling(period).std()
        df[f'bb_upper_{period}'] = sma + 2 * std
        df[f'bb_lower_{period}'] = sma - 2 * std
        df[f'bb_width_{period}'] = (df[f'bb_upper_{period}'] - df[f'bb_lower_{period}']) / sma
        df[f'bb_pct_{period}'] = (df['close'] - df[f'bb_lower_{period}']) / (df[f'bb_upper_{period}'] - df[f'bb_lower_{period}'])
    
    df.ffill(inplace=True)
    df.dropna(inplace=True)
    return df
