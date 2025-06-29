# strategy/candlestick_patterns.py
# Padrões de candlestick completos, com enriquecimento de informações (força/“confiança” de cada padrão).

# Dicionário de força/confiança dos padrões (0.0 = fraco, 1.0 = muito forte)
PATTERN_STRENGTH = {
    "bullish_engulfing": 1.0,
    "bearish_engulfing": 1.0,
    "hammer": 0.8,
    "hanging_man": 0.8,
    "inverted_hammer": 0.8,
    "shooting_star": 0.8,
    "marubozu": 0.7,
    "doji": 0.3,
    "dragonfly_doji": 0.3,
    "gravestone_doji": 0.3,
    "long_legged_doji": 0.3,
    "spinning_top": 0.3,
    "bullish_harami": 0.7,
    "bearish_harami": 0.7,
    "harami_cross": 0.6,
    "piercing_line": 0.7,
    "dark_cloud_cover": 0.7,
    "tweezer_bottom": 0.5,
    "tweezer_top": 0.5,
    "morning_star": 1.0,
    "evening_star": 1.0,
    "three_white_soldiers": 1.0,
    "three_black_crows": 1.0,
    "three_inside_up": 0.7,
    "three_inside_down": 0.7,
    "three_outside_up": 0.7,
    "three_outside_down": 0.7,
    "abandoned_baby_bullish": 1.0,
    "abandoned_baby_bearish": 1.0,
    "kicker_bullish": 0.8,
    "kicker_bearish": 0.8,
    "gap_up": 0.4,
    "gap_down": 0.4,
    "upside_tasuki_gap": 0.6,
    "downside_tasuki_gap": 0.6,
    "on_neckline": 0.4,
    "separating_lines": 0.5,
    "rising_three_methods": 1.0,
    "falling_three_methods": 1.0,
}

def get_pattern_strength(patterns):
    """Retorna a soma das forças dos padrões detectados."""
    return sum(PATTERN_STRENGTH.get(p, 0.2) for p in patterns)

# --- FUNÇÕES DE PADRÃO (todas as suas funções originais, sem alteração de lógica) ---

def is_doji(candle, threshold=0.1):
    body = abs(candle["close"] - candle["open"])
    full = candle["high"] - candle["low"] or 1e-8
    return body / full < threshold

def is_dragonfly_doji(candle):
    body = abs(candle["close"] - candle["open"])
    lower_wick = min(candle["close"], candle["open"]) - candle["low"]
    upper_wick = candle["high"] - max(candle["close"], candle["open"])
    full = candle["high"] - candle["low"] or 1e-8
    return is_doji(candle) and lower_wick > 2 * body and upper_wick < body

def is_gravestone_doji(candle):
    body = abs(candle["close"] - candle["open"])
    lower_wick = min(candle["close"], candle["open"]) - candle["low"]
    upper_wick = candle["high"] - max(candle["close"], candle["open"])
    full = candle["high"] - candle["low"] or 1e-8
    return is_doji(candle) and upper_wick > 2 * body and lower_wick < body

def is_long_legged_doji(candle):
    upper_wick = candle["high"] - max(candle["close"], candle["open"])
    lower_wick = min(candle["close"], candle["open"]) - candle["low"]
    return is_doji(candle) and upper_wick > 0 and lower_wick > 0

def is_spinning_top(candle):
    body = abs(candle["close"] - candle["open"])
    full = candle["high"] - candle["low"] or 1e-8
    upper_wick = candle["high"] - max(candle["close"], candle["open"])
    lower_wick = min(candle["close"], candle["open"]) - candle["low"]
    return 0.2 < body / full < 0.5 and upper_wick > 0 and lower_wick > 0

def is_hammer(candle):
    body = abs(candle["close"] - candle["open"])
    lower_wick = min(candle["open"], candle["close"]) - candle["low"]
    upper_wick = candle["high"] - max(candle["open"], candle["close"])
    full = candle["high"] - candle["low"] or 1e-8
    return body / full < 0.3 and lower_wick > 2 * body and upper_wick < body

def is_hanging_man(candle):
    # Mesmo formato do hammer, mas contexto é topo
    return is_hammer(candle)

def is_inverted_hammer(candle):
    body = abs(candle["close"] - candle["open"])
    upper_wick = candle["high"] - max(candle["open"], candle["close"])
    lower_wick = min(candle["open"], candle["close"]) - candle["low"]
    full = candle["high"] - candle["low"] or 1e-8
    return body / full < 0.3 and upper_wick > 2 * body and lower_wick < body

def is_shooting_star(candle):
    # Mesmo formato do inverted hammer, mas contexto é topo
    return is_inverted_hammer(candle)

def is_marubozu(candle, threshold=0.02):
    body = abs(candle["close"] - candle["open"])
    upper_wick = candle["high"] - max(candle["close"], candle["open"])
    lower_wick = min(candle["close"], candle["open"]) - candle["low"]
    full = candle["high"] - candle["low"] or 1e-8
    return upper_wick / full < threshold and lower_wick / full < threshold

def is_bullish_engulfing(candle, prev):
    return (
        candle["close"] > candle["open"] and
        prev["close"] < prev["open"] and
        candle["open"] < prev["close"] and
        candle["close"] > prev["open"]
    )

def is_bearish_engulfing(candle, prev):
    return (
        candle["close"] < candle["open"] and
        prev["close"] > prev["open"] and
        candle["open"] > prev["close"] and
        candle["close"] < prev["open"]
    )

def is_bullish_harami(candle, prev):
    return (
        prev["close"] < prev["open"] and
        candle["close"] > candle["open"] and
        candle["open"] > prev["close"] and
        candle["close"] < prev["open"]
    )

def is_bearish_harami(candle, prev):
    return (
        prev["close"] > prev["open"] and
        candle["close"] < candle["open"] and
        candle["open"] < prev["close"] and
        candle["close"] > prev["open"]
    )

def is_harami_cross(candle, prev):
    return is_doji(candle) and (is_bullish_harami(candle, prev) or is_bearish_harami(candle, prev))

def is_piercing_line(candle, prev):
    mid_prev = (prev["open"] + prev["close"]) / 2
    return (
        prev["close"] < prev["open"] and
        candle["open"] < prev["close"] and
        candle["close"] > mid_prev and
        candle["close"] < prev["open"]
    )

def is_dark_cloud_cover(candle, prev):
    mid_prev = (prev["open"] + prev["close"]) / 2
    return (
        prev["close"] > prev["open"] and
        candle["open"] > prev["close"] and
        candle["close"] < mid_prev and
        candle["close"] > prev["open"]
    )

def is_tweezer_bottom(candle, prev, threshold=0.1):
    return (
        prev["close"] < prev["open"] and
        candle["close"] > candle["open"] and
        abs(prev["low"] - candle["low"]) / (abs(prev["low"]) + 1e-8) < threshold
    )

def is_tweezer_top(candle, prev, threshold=0.1):
    return (
        prev["close"] > prev["open"] and
        candle["close"] < candle["open"] and
        abs(prev["high"] - candle["high"]) / (abs(prev["high"]) + 1e-8) < threshold
    )

def is_morning_star(prev2, prev1, candle):
    return (
        prev2["close"] < prev2["open"] and
        abs(prev1["close"] - prev1["open"]) < (prev2["open"] - prev2["close"]) * 0.5 and
        candle["close"] > candle["open"] and
        candle["close"] > ((prev2["close"] + prev2["open"]) / 2)
    )

def is_evening_star(prev2, prev1, candle):
    return (
        prev2["close"] > prev2["open"] and
        abs(prev1["close"] - prev1["open"]) < (prev2["close"] - prev2["open"]) * 0.5 and
        candle["close"] < candle["open"] and
        candle["close"] < ((prev2["close"] + prev2["open"]) / 2)
    )

def is_three_white_soldiers(candles):
    if len(candles) < 3:
        return False
    last = candles[-1]
    prev1 = candles[-2]
    prev2 = candles[-3]
    return (
        all(c["close"] > c["open"] for c in [prev2, prev1, last]) and
        prev2["close"] < prev1["open"] and
        prev1["close"] < last["open"]
    )

def is_three_black_crows(candles):
    if len(candles) < 3:
        return False
    last = candles[-1]
    prev1 = candles[-2]
    prev2 = candles[-3]
    return (
        all(c["close"] < c["open"] for c in [prev2, prev1, last]) and
        prev2["close"] > prev1["open"] and
        prev1["close"] > last["open"]
    )

def is_three_inside_up(candles):
    if len(candles) < 3:
        return False
    prev2 = candles[-3]
    prev1 = candles[-2]
    last = candles[-1]
    return (
        is_bearish_engulfing(prev1, prev2) and
        last["close"] > prev1["close"]
    )

def is_three_inside_down(candles):
    if len(candles) < 3:
        return False
    prev2 = candles[-3]
    prev1 = candles[-2]
    last = candles[-1]
    return (
        is_bullish_engulfing(prev1, prev2) and
        last["close"] < prev1["close"]
    )

def is_three_outside_up(candles):
    if len(candles) < 3:
        return False
    prev2 = candles[-3]
    prev1 = candles[-2]
    last = candles[-1]
    return (
        is_bullish_engulfing(prev1, prev2) and
        last["close"] > prev1["close"]
    )

def is_three_outside_down(candles):
    if len(candles) < 3:
        return False
    prev2 = candles[-3]
    prev1 = candles[-2]
    last = candles[-1]
    return (
        is_bearish_engulfing(prev1, prev2) and
        last["close"] < prev1["close"]
    )

def is_abandoned_baby_bullish(prev2, prev1, last, threshold=0.001):
    return (
        prev2["close"] < prev2["open"] and
        is_doji(prev1) and
        prev1["low"] > prev2["high"] + threshold and
        last["open"] > prev1["high"] + threshold and
        last["close"] > last["open"]
    )

def is_abandoned_baby_bearish(prev2, prev1, last, threshold=0.001):
    return (
        prev2["close"] > prev2["open"] and
        is_doji(prev1) and
        prev1["high"] < prev2["low"] - threshold and
        last["open"] < prev1["low"] - threshold and
        last["close"] < last["open"]
    )

def is_kicker_bullish(prev, last):
    return (
        prev["close"] < prev["open"] and
        last["open"] > prev["close"] and
        last["close"] > last["open"]
    )

def is_kicker_bearish(prev, last):
    return (
        prev["close"] > prev["open"] and
        last["open"] < prev["close"] and
        last["close"] < last["open"]
    )

def is_gap_up(prev, last):
    return last["low"] > prev["high"]

def is_gap_down(prev, last):
    return last["high"] < prev["low"]

def is_upsidetasukigap(candles):
    if len(candles) < 3:
        return False
    prev2, prev1, last = candles[-3], candles[-2], candles[-1]
    return (
        prev2["close"] > prev2["open"] and
        prev1["close"] > prev1["open"] and
        is_gap_up(prev2, prev1) and
        last["close"] < last["open"] and
        last["open"] > prev1["close"] and
        last["close"] > prev1["open"]
    )

def is_downsidetasukigap(candles):
    if len(candles) < 3:
        return False
    prev2, prev1, last = candles[-3], candles[-2], candles[-1]
    return (
        prev2["close"] < prev2["open"] and
        prev1["close"] < prev1["open"] and
        is_gap_down(prev2, prev1) and
        last["close"] > last["open"] and
        last["open"] < prev1["close"] and
        last["close"] < prev1["open"]
    )

def is_on_neckline(candle, prev, threshold=0.05):
    return (
        prev["close"] < prev["open"] and
        candle["open"] < prev["close"] and
        abs(candle["close"] - prev["low"]) / prev["low"] < threshold
    )

def is_separating_lines(prev, last):
    return (
        prev["close"] < prev["open"] and
        last["open"] == prev["open"] and
        last["close"] > last["open"]
    ) or (
        prev["close"] > prev["open"] and
        last["open"] == prev["open"] and
        last["close"] < last["open"]
    )

def is_rising_three_methods(candles):
    if len(candles) < 5:
        return False
    a, b, c, d, e = candles[-5:]
    return (
        a["close"] > a["open"] and
        all(x["close"] < x["open"] for x in [b, c, d]) and
        e["close"] > e["open"] and
        e["close"] > a["close"]
    )

def is_falling_three_methods(candles):
    if len(candles) < 5:
        return False
    a, b, c, d, e = candles[-5:]
    return (
        a["close"] < a["open"] and
        all(x["close"] > x["open"] for x in [b, c, d]) and
        e["close"] < e["open"] and
        e["close"] < a["close"]
    )

# --- DETECÇÃO DOS PADRÕES ---

def detect_candlestick_patterns(candles):
    patterns = []
    l = len(candles)
    if l < 2:
        return patterns

    last = candles[-1]
    prev = candles[-2]

    # Dois candles
    if is_bullish_engulfing(last, prev):
        patterns.append("bullish_engulfing")
    if is_bearish_engulfing(last, prev):
        patterns.append("bearish_engulfing")
    if is_piercing_line(last, prev):
        patterns.append("piercing_line")
    if is_dark_cloud_cover(last, prev):
        patterns.append("dark_cloud_cover")
    if is_tweezer_bottom(last, prev):
        patterns.append("tweezer_bottom")
    if is_tweezer_top(last, prev):
        patterns.append("tweezer_top")
    if is_bullish_harami(last, prev):
        patterns.append("bullish_harami")
    if is_bearish_harami(last, prev):
        patterns.append("bearish_harami")
    if is_kicker_bullish(prev, last):
        patterns.append("kicker_bullish")
    if is_kicker_bearish(prev, last):
        patterns.append("kicker_bearish")
    if is_on_neckline(last, prev):
        patterns.append("on_neckline")
    if is_separating_lines(prev, last):
        patterns.append("separating_lines")
    if is_gap_up(prev, last):
        patterns.append("gap_up")
    if is_gap_down(prev, last):
        patterns.append("gap_down")

    # Um candle
    if is_doji(last):
        patterns.append("doji")
    if is_dragonfly_doji(last):
        patterns.append("dragonfly_doji")
    if is_gravestone_doji(last):
        patterns.append("gravestone_doji")
    if is_long_legged_doji(last):
        patterns.append("long_legged_doji")
    if is_spinning_top(last):
        patterns.append("spinning_top")
    if is_hammer(last):
        patterns.append("hammer")
    if is_inverted_hammer(last):
        patterns.append("inverted_hammer")
    if is_shooting_star(last):
        patterns.append("shooting_star")
    if is_hanging_man(last):
        patterns.append("hanging_man")
    if is_marubozu(last):
        patterns.append("marubozu")

    # Três candles
    if l >= 3:
        prev2 = candles[-3]
        if is_morning_star(prev2, prev, last):
            patterns.append("morning_star")
        if is_evening_star(prev2, prev, last):
            patterns.append("evening_star")
        if is_three_inside_up(candles[-3:]):
            patterns.append("three_inside_up")
        if is_three_inside_down(candles[-3:]):
            patterns.append("three_inside_down")
        if is_three_outside_up(candles[-3:]):
            patterns.append("three_outside_up")
        if is_three_outside_down(candles[-3:]):
            patterns.append("three_outside_down")
        if is_upsidetasukigap(candles):
            patterns.append("upside_tasuki_gap")
        if is_downsidetasukigap(candles):
            patterns.append("downside_tasuki_gap")

    if l >= 3 and is_three_white_soldiers(candles[-3:]):
        patterns.append("three_white_soldiers")
    if l >= 3 and is_three_black_crows(candles[-3:]):
        patterns.append("three_black_crows")
    if l >= 5 and is_rising_three_methods(candles):
        patterns.append("rising_three_methods")
    if l >= 5 and is_falling_three_methods(candles):
        patterns.append("falling_three_methods")
    if l >= 3 and is_abandoned_baby_bullish(candles[-3], candles[-2], candles[-1]):
        patterns.append("abandoned_baby_bullish")
    if l >= 3 and is_abandoned_baby_bearish(candles[-3], candles[-2], candles[-1]):
        patterns.append("abandoned_baby_bearish")

    return patterns
    
detect_patterns = detect_candlestick_patterns
