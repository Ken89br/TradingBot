# strategy/ai_filter.py
# AI Filter aprimorado: rejeita/penaliza sinais com base na força de padrões de candlestick,
# além dos critérios clássicos de qualidade, risco, volatilidade, suporte/resistência, etc.

from strategy.candlestick_patterns import PATTERN_STRENGTH

class SmartAIFilter:
    def __init__(
        self,
        min_confidence=30,
        min_volatility=0.00001,
        min_volume=100,
        allowed_risk=("low", "moderate", "high"),
        allowed_volatility=("high", "moderate", "low"),
        min_support_distance=0.00005,
        min_pattern_reject_strength=0.99,  # rejeita direto se soma da força >= esse valor
        pattern_penalty_factor=6          # penalização de confiança por força dos padrões contrários
    ):
        self.min_confidence = min_confidence
        self.min_volatility = min_volatility
        self.min_volume = min_volume
        self.allowed_risk = allowed_risk
        self.allowed_volatility = allowed_volatility
        self.min_support_distance = min_support_distance
        self.min_pattern_reject_strength = min_pattern_reject_strength
        self.pattern_penalty_factor = pattern_penalty_factor

    def pattern_strength(self, patterns, direction):
        """
        Calcula força total dos padrões contrários ao sinal.
        """
        total_strength = 0
        for p in patterns:
            s = PATTERN_STRENGTH.get(p, 0.2)
            # Bearish patterns contra compra
            if direction == "up" and ("bear" in p or "engulfing" in p or "shooting" in p or "dark_cloud" in p or "evening_star" in p):
                total_strength += s
            # Bullish patterns contra venda
            if direction == "down" and ("bull" in p or "hammer" in p or "morning_star" in p or "piercing" in p):
                total_strength += s
            # Doji penaliza ambos levemente
            if p == "doji":
                total_strength += 0.15
        return total_strength

    def apply(self, signal_data, candles):
        if not signal_data or not candles:
            print("❌ Invalid input to AI filter.")
            return None

        latest = candles[-1]
        price = latest.get("close", signal_data.get("price", 0))
        body_size = abs(latest["close"] - latest["open"])
        wick_size = abs(latest["high"] - latest["low"])
        body_ratio = body_size / wick_size if wick_size else 0
        volume = latest.get("volume", 0)

        # 1. Candle e volume (filtro clássico)
        if body_ratio < 0.2 or volume < self.min_volume:
            signal_data["confidence"] = max(signal_data["confidence"] - 20, 10)
            signal_data["strength"] = "weak"
        else:
            signal_data["confidence"] = min(signal_data["confidence"] + 10, 100)
            signal_data["strength"] = "strong" if signal_data["confidence"] >= 80 else "moderate"

        # 2. Padrões de candle e força
        patterns = signal_data.get("patterns", [])
        if isinstance(patterns, dict):
            patterns = list(patterns.keys())
        direction = signal_data.get("signal", "")
        total_pattern_strength = self.pattern_strength(patterns, direction)

        if total_pattern_strength >= self.min_pattern_reject_strength:
            print(f"❌ Rejeitado: força total dos padrões contrários ({total_pattern_strength:.2f}) excede limite para '{direction}'")
            return None
        elif total_pattern_strength > 0:
            penalty = int(total_pattern_strength * self.pattern_penalty_factor)
            print(f"ℹ️ Penalizando confiança em {penalty} por padrões contrários (força={total_pattern_strength:.2f})")
            signal_data["confidence"] = max(signal_data["confidence"] - penalty, 10)

        # 3. Risco
        risk = (signal_data.get("risk") or "").lower()
        if risk and risk not in self.allowed_risk:
            print(f"❌ Rejected: risk too high ({risk})")
            return None

        # 4. Volatilidade qualitativa
        volatility_qual = (signal_data.get("volatility") or "").lower()
        if volatility_qual and volatility_qual not in self.allowed_volatility:
            print(f"❌ Rejected: volatility too low ({volatility_qual})")
            return None

        # 5. RSI extremos
        rsi_val = -1
        try:
            rsi_val = float(str(signal_data.get("rsi", "")).split()[0])
        except Exception:
            pass
        if rsi_val > 80 and direction == "up":
            print("❌ Rejected: RSI muito alto — sobrecompra")
            return None
        if rsi_val < 20 and direction == "down":
            print("❌ Rejected: RSI muito baixo — sobrevenda")
            return None

        # 6. MACD divergente (penaliza, não rejeita)
        macd_str = signal_data.get("macd", "")
        if isinstance(macd_str, str) and "(" in macd_str:
            try:
                macd_val = float(macd_str.split()[0])
                macd_hist = float(macd_str.split("Hist:")[-1].replace(")", "").strip())
                if macd_hist < 0 and direction == "up":
                    signal_data["confidence"] = max(signal_data["confidence"] - 10, 10)
                if macd_hist > 0 and direction == "down":
                    signal_data["confidence"] = max(signal_data["confidence"] - 10, 10)
            except Exception:
                pass

        # 7. Bollinger Bands (penaliza, não rejeita)
        boll_bands = signal_data.get("bollinger", "")
        if isinstance(boll_bands, str) and "width" in boll_bands:
            if "Pos:" in boll_bands:
                try:
                    pos = float(boll_bands.split("Pos:")[-1])
                    if pos < 0 and direction == "up":
                        signal_data["confidence"] = max(signal_data["confidence"] - 10, 10)
                    if pos > 0 and direction == "down":
                        signal_data["confidence"] = max(signal_data["confidence"] - 10, 10)
                except Exception:
                    pass

        # 8. Osciladores e médias móveis
        if signal_data.get("osc_rating") == -1 and direction == "up":
            signal_data["confidence"] = max(signal_data["confidence"] - 10, 10)
        if signal_data.get("osc_rating") == 1 and direction == "down":
            signal_data["confidence"] = max(signal_data["confidence"] - 10, 10)

        if signal_data.get("ma_rating") == -1 and direction == "up":
            signal_data["confidence"] = max(signal_data["confidence"] - 10, 10)
        if signal_data.get("ma_rating") == 1 and direction == "down":
            signal_data["confidence"] = max(signal_data["confidence"] - 10, 10)

        # 9. Sentimento vs direção do sinal
        sentiment = signal_data.get("sentiment")
        if sentiment == -1 and direction == "up":
            print("❌ Rejected: bullish signal with pessimistic sentiment")
            return None
        if sentiment == 1 and direction == "down":
            print("❌ Rejected: bearish signal with optimistic sentiment")
            return None

        # 10. Suporte/resistência (evita compra perto da resistência, venda perto do suporte)
        support = float(signal_data.get("support", 0))
        resistance = float(signal_data.get("resistance", 0))
        if direction == "up" and resistance and price > 0:
            dist = abs(resistance - price)
            if dist < self.min_support_distance:
                print(f"❌ Rejected: buying too close to resistance ({dist})")
                return None
        if direction == "down" and support and price > 0:
            dist = abs(price - support)
            if dist < self.min_support_distance:
                print(f"❌ Rejected: selling too close to support ({dist})")
                return None

        # 11. Variação/volatilidade extrema (pode evitar operar em spikes)
        try:
            variation = float(signal_data.get("variation", "0").replace("%", ""))
            if abs(variation) > 3.0:
                print(f"❌ Rejected: variation too high ({variation}%)")
                return None
        except Exception:
            pass

        # Filtros clássicos finais
        price_range = signal_data["high"] - signal_data["low"]
        if signal_data["confidence"] < self.min_confidence:
            print(f"❌ Rejected: low confidence ({signal_data['confidence']}%)")
            return None

        if price_range < self.min_volatility:
            print(f"❌ Rejected: low volatility (range: {price_range})")
            return None

        if signal_data["volume"] < self.min_volume:
            print(f"❌ Rejected: low volume ({signal_data['volume']})")
            return None

        return signal_data