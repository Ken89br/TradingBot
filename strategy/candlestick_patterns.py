# strategy/candlestick_patterns.py
# Padrões de candlestick completos com todas as velas da lista fornecida

# Dicionário de força/confiança dos padrões atualizado
PATTERN_STRENGTH = {
    # Padrões de reversão
    "bullish_engulfing": 1.0,
    "bearish_engulfing": 1.0,
    "hammer": 0.8,
    "hanging_man": 0.8,
    "inverted_hammer": 0.8,
    "shooting_star": 0.8,
    "morning_star": 1.0,
    "evening_star": 1.0,
    "piercing_line": 0.7,
    "dark_cloud_cover": 0.7,
    "three_white_soldiers": 1.0,
    "three_black_crows": 1.0,
    "abandoned_baby_bullish": 1.0,
    "abandoned_baby_bearish": 1.0,
    "kicker_bullish": 0.8,
    "kicker_bearish": 0.8,
    
    # Padrões de continuação
    "rising_three_methods": 0.9,
    "falling_three_methods": 0.9,
    "upside_tasuki_gap": 0.6,
    "downside_tasuki_gap": 0.6,
    "separating_lines": 0.5,
    
    # Padrões neutros/indecisão
    "doji": 0.3,
    "dragonfly_doji": 0.3,
    "gravestone_doji": 0.3,
    "long_legged_doji": 0.3,
    "spinning_top": 0.3,
    "marubozu": 0.7,
    
    # Padrões híbridos
    "bullish_harami": 0.7,
    "bearish_harami": 0.7,
    "harami_cross": 0.6,
    "tweezer_bottom": 0.5,
    "tweezer_top": 0.5,
    "three_inside_up": 0.7,
    "three_inside_down": 0.7,
    "three_outside_up": 0.7,
    "three_outside_down": 0.7,
    
    # Gap patterns
    "gap_up": 0.4,
    "gap_down": 0.4,
    "on_neckline": 0.4,
    
    # Novos padrões adicionados
    "belt_hold_bullish": 0.7,
    "belt_hold_bearish": 0.7,
    "counterattack_bullish": 0.6,
    "counterattack_bearish": 0.6,
    "unique_three_river_bottom": 0.8,
    "breakaway_bullish": 0.7,
    "breakaway_bearish": 0.7
}

def get_pattern_strength(patterns):
    """Retorna a soma das forças dos padrões detectados."""
    return sum(PATTERN_STRENGTH.get(p, 0.2) for p in patterns)

# ============== FUNÇÕES DE DETECÇÃO DE PADRÕES ==============

# --- Padrões de um candle ---
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
    return is_hammer(candle)  # Formato igual, contexto diferente

def is_inverted_hammer(candle):
    body = abs(candle["close"] - candle["open"])
    upper_wick = candle["high"] - max(candle["open"], candle["close"])
    lower_wick = min(candle["open"], candle["close"]) - candle["low"]
    full = candle["high"] - candle["low"] or 1e-8
    return body / full < 0.3 and upper_wick > 2 * body and lower_wick < body

def is_shooting_star(candle):
    return is_inverted_hammer(candle)  # Formato igual, contexto diferente

def is_marubozu(candle, threshold=0.02):
    body = abs(candle["close"] - candle["open"])
    upper_wick = candle["high"] - max(candle["close"], candle["open"])
    lower_wick = min(candle["close"], candle["open"]) - candle["low"]
    full = candle["high"] - candle["low"] or 1e-8
    return upper_wick / full < threshold and lower_wick / full < threshold

# --- Padrões de dois candles ---
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

def is_kicker_bullish(prev, candle):
    return (
        prev["close"] < prev["open"] and
        candle["open"] > prev["close"] and
        candle["close"] > candle["open"]
    )

def is_kicker_bearish(prev, candle):
    return (
        prev["close"] > prev["open"] and
        candle["open"] < prev["close"] and
        candle["close"] < candle["open"]
    )

def is_gap_up(prev, candle):
    return candle["low"] > prev["high"]

def is_gap_down(prev, candle):
    return candle["high"] < prev["low"]

def is_on_neckline(candle, prev, threshold=0.05):
    return (
        prev["close"] < prev["open"] and
        candle["open"] < prev["close"] and
        abs(candle["close"] - prev["low"]) / prev["low"] < threshold
    )

def is_separating_lines(prev, candle):
    return (
        prev["close"] < prev["open"] and
        candle["open"] == prev["open"] and
        candle["close"] > candle["open"]
    ) or (
        prev["close"] > prev["open"] and
        candle["open"] == prev["open"] and
        candle["close"] < candle["open"]
    )

# --- Padrões de três candles ---
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

def is_abandoned_baby_bullish(prev2, prev1, candle, threshold=0.001):
    return (
        prev2["close"] < prev2["open"] and
        is_doji(prev1) and
        prev1["low"] > prev2["high"] + threshold and
        candle["open"] > prev1["high"] + threshold and
        candle["close"] > candle["open"]
    )

def is_abandoned_baby_bearish(prev2, prev1, candle, threshold=0.001):
    return (
        prev2["close"] > prev2["open"] and
        is_doji(prev1) and
        prev1["high"] < prev2["low"] - threshold and
        candle["open"] < prev1["low"] - threshold and
        candle["close"] < candle["open"]
    )

def is_upside_tasuki_gap(candles):
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

def is_downside_tasuki_gap(candles):
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

# --- Padrões de cinco candles ---
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

# ============== NOVOS PADRÕES ADICIONAIS ==============

def is_belt_hold_bullish(candle):
    """Belt Hold (Alakozakura) - Bullish"""
    body = candle["close"] - candle["open"]
    lower_wick = candle["open"] - candle["low"]
    return (
        body > 0 and
        lower_wick <= body * 0.1 and
        (candle["high"] - candle["close"]) <= body * 0.1
    )

def is_belt_hold_bearish(candle):
    """Belt Hold (Alakozakura) - Bearish"""
    body = candle["open"] - candle["close"]
    upper_wick = candle["high"] - candle["open"]
    return (
        body > 0 and
        upper_wick <= body * 0.1 and
        (candle["close"] - candle["low"]) <= body * 0.1
    )

def is_counterattack_bullish(prev, candle):
    """Counterattack - Bullish"""
    return (
        prev["close"] < prev["open"] and
        candle["open"] < prev["close"] and
        abs(candle["close"] - prev["open"]) < (prev["open"] - prev["close"]) * 0.1
    )

def is_counterattack_bearish(prev, candle):
    """Counterattack - Bearish"""
    return (
        prev["close"] > prev["open"] and
        candle["open"] > prev["close"] and
        abs(candle["close"] - prev["open"]) < (prev["close"] - prev["open"]) * 0.1
    )

def is_unique_three_river_bottom(candles):
    """Unique Three River Bottom"""
    if len(candles) < 3:
        return False
    prev2, prev1, last = candles[-3], candles[-2], candles[-1]
    return (
        prev2["close"] < prev2["open"] and
        is_hammer(prev1) and
        prev1["close"] < prev2["close"] and
        last["open"] > last["close"] and
        last["open"] < prev1["close"] and
        last["close"] > prev2["low"]
    )

def is_breakaway_bullish(candles):
    """Breakaway - Bullish"""
    if len(candles) < 5:
        return False
    a, b, c, d, e = candles[-5:]
    return (
        a["close"] < a["open"] and
        b["close"] < b["open"] and
        c["close"] < c["open"] and
        d["close"] > d["open"] and
        e["close"] > e["open"] and
        e["close"] > a["open"]
    )

def is_breakaway_bearish(candles):
    """Breakaway - Bearish"""
    if len(candles) < 5:
        return False
    a, b, c, d, e = candles[-5:]
    return (
        a["close"] > a["open"] and
        b["close"] > b["open"] and
        c["close"] > c["open"] and
        d["close"] < d["open"] and
        e["close"] < e["open"] and
        e["close"] < a["open"]
    )

# ============== DETECÇÃO PRINCIPAL ==============

def detect_candlestick_patterns(candles):
    """Detecta todos os padrões de candlestick na série de candles fornecida"""
    patterns = []
    l = len(candles)
    if l < 1:
        return patterns

    last = candles[-1]

    # Padrões de um candle
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
    if is_hanging_man(last):
        patterns.append("hanging_man")
    if is_inverted_hammer(last):
        patterns.append("inverted_hammer")
    if is_shooting_star(last):
        patterns.append("shooting_star")
    if is_marubozu(last):
        patterns.append("marubozu")
    if is_belt_hold_bullish(last):
        patterns.append("belt_hold_bullish")
    if is_belt_hold_bearish(last):
        patterns.append("belt_hold_bearish")

    # Padrões de dois candles
    if l >= 2:
        prev = candles[-2]
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
        if is_harami_cross(last, prev):
            patterns.append("harami_cross")
        if is_kicker_bullish(prev, last):
            patterns.append("kicker_bullish")
        if is_kicker_bearish(prev, last):
            patterns.append("kicker_bearish")
        if is_gap_up(prev, last):
            patterns.append("gap_up")
        if is_gap_down(prev, last):
            patterns.append("gap_down")
        if is_on_neckline(last, prev):
            patterns.append("on_neckline")
        if is_separating_lines(prev, last):
            patterns.append("separating_lines")
        if is_counterattack_bullish(prev, last):
            patterns.append("counterattack_bullish")
        if is_counterattack_bearish(prev, last):
            patterns.append("counterattack_bearish")

    # Padrões de três candles
    if l >= 3:
        prev2 = candles[-3]
        prev1 = candles[-2]
        if is_morning_star(prev2, prev1, last):
            patterns.append("morning_star")
        if is_evening_star(prev2, prev1, last):
            patterns.append("evening_star")
        if is_three_white_soldiers(candles[-3:]):
            patterns.append("three_white_soldiers")
        if is_three_black_crows(candles[-3:]):
            patterns.append("three_black_crows")
        if is_three_inside_up(candles[-3:]):
            patterns.append("three_inside_up")
        if is_three_inside_down(candles[-3:]):
            patterns.append("three_inside_down")
        if is_three_outside_up(candles[-3:]):
            patterns.append("three_outside_up")
        if is_three_outside_down(candles[-3:]):
            patterns.append("three_outside_down")
        if is_abandoned_baby_bullish(prev2, prev1, last):
            patterns.append("abandoned_baby_bullish")
        if is_abandoned_baby_bearish(prev2, prev1, last):
            patterns.append("abandoned_baby_bearish")
        if is_upside_tasuki_gap(candles[-3:]):
            patterns.append("upside_tasuki_gap")
        if is_downside_tasuki_gap(candles[-3:]):
            patterns.append("downside_tasuki_gap")
        if is_unique_three_river_bottom(candles[-3:]):
            patterns.append("unique_three_river_bottom")

    # Padrões de cinco candles
    if l >= 5:
        if is_rising_three_methods(candles[-5:]):
            patterns.append("rising_three_methods")
        if is_falling_three_methods(candles[-5:]):
            patterns.append("falling_three_methods")
        if is_breakaway_bullish(candles[-5:]):
            patterns.append("breakaway_bullish")
        if is_breakaway_bearish(candles[-5:]):
            patterns.append("breakaway_bearish")

    return patterns

REVERSAL_UP = [
    "hammer", "bullish_engulfing", "piercing_line", "morning_star", "tweezer_bottom",
    "bullish_harami", "kicker_bullish", "three_inside_up", "three_outside_up", "gap_up",
    "dragonfly_doji", "three_white_soldiers", "inverted_hammer", "belt_hold_bullish",
    "breakaway_bullish", "counterattack_bullish", "unique_three_river_bottom"
]
REVERSAL_DOWN = [
    "hanging_man", "bearish_engulfing", "dark_cloud_cover", "evening_star", "tweezer_top",
    "bearish_harami", "kicker_bearish", "three_inside_down", "three_outside_down", "gap_down",
    "gravestone_doji", "three_black_crows", "shooting_star", "belt_hold_bearish",
    "breakaway_bearish", "counterattack_bearish", "abandoned_baby_bearish"
]
TREND_UP = ["three_white_soldiers", "rising_three_methods", "upside_tasuki_gap", "separating_lines"]
TREND_DOWN = ["three_black_crows", "falling_three_methods", "downside_tasuki_gap", "separating_lines"]
NEUTRAL = ["doji", "dragonfly_doji", "gravestone_doji", "long_legged_doji", "spinning_top", "marubozu"]
HYBRID = ["harami_cross"]

# Alias para compatibilidade
detect_patterns = detect_candlestick_patterns
