# strategy/ai_filter.py
# AI Filter aprimorado para sinais ricos, com análise de todos os principais campos, padrões de candle e regras quantitativas defensivas.

class SmartAIFilter:
    def __init__(
        self,
        min_confidence=55,
        min_volatility=0.00005,
        min_volume=500,
        allowed_risk=("low", "moderate"),
        allowed_volatility=("high", "moderate"),
        min_support_distance=0.0002,    # distância mínima do preço ao suporte/resistência para operar
        min_pattern_confidence=0.7,     # confiança mínima em padrões para rejeitar
    ):
        self.min_confidence = min_confidence
        self.min_volatility = min_volatility
        self.min_volume = min_volume
        self.allowed_risk = allowed_risk
        self.allowed_volatility = allowed_volatility
        self.min_support_distance = min_support_distance
        self.min_pattern_confidence = min_pattern_confidence

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

        # 2. Risco
        risk = (signal_data.get("risk") or "").lower()
        if risk and risk not in self.allowed_risk:
            print(f"❌ Rejected: risk too high ({risk})")
            return None

        # 3. Volatilidade qualitativa
        volatility_qual = (signal_data.get("volatility") or "").lower()
        if volatility_qual and volatility_qual not in self.allowed_volatility:
            print(f"❌ Rejected: volatility too low ({volatility_qual})")
            return None

        # 4. RSI (evita operar em extremo sobrecompra/sobrevenda)
        rsi_val = -1
        try:
            rsi_val = float(str(signal_data.get("rsi", "")).split()[0])
        except Exception:
            pass
        if rsi_val > 80 and signal_data["signal"] == "up":
            print("❌ Rejected: RSI muito alto — sobrecompra")
            return None
        if rsi_val < 20 and signal_data["signal"] == "down":
            print("❌ Rejected: RSI muito baixo — sobrevenda")
            return None

        # 5. MACD divergente
        macd_str = signal_data.get("macd", "")
        if isinstance(macd_str, str) and "(" in macd_str:
            try:
                macd_val = float(macd_str.split()[0])
                macd_hist = float(macd_str.split("Hist:")[-1].replace(")", "").strip())
                if macd_hist < 0 and signal_data["signal"] == "up":
                    signal_data["confidence"] = max(signal_data["confidence"] - 10, 10)
                if macd_hist > 0 and signal_data["signal"] == "down":
                    signal_data["confidence"] = max(signal_data["confidence"] - 10, 10)
            except Exception:
                pass

        # 6. Bollinger Bands (evita operar contra a banda)
        boll_bands = signal_data.get("bollinger", "")
        if isinstance(boll_bands, str) and "width" in boll_bands:
            if "Pos:" in boll_bands:
                try:
                    pos = float(boll_bands.split("Pos:")[-1])
                    if pos < 0 and signal_data["signal"] == "up":
                        signal_data["confidence"] = max(signal_data["confidence"] - 10, 10)
                    if pos > 0 and signal_data["signal"] == "down":
                        signal_data["confidence"] = max(signal_data["confidence"] - 10, 10)
                except Exception:
                    pass

        # 7. Osciladores e médias móveis
        if signal_data.get("oscillators") == "sell" and signal_data["signal"] == "up":
            signal_data["confidence"] = max(signal_data["confidence"] - 10, 10)
        if signal_data.get("oscillators") == "buy" and signal_data["signal"] == "down":
            signal_data["confidence"] = max(signal_data["confidence"] - 10, 10)

        if signal_data.get("moving_averages") == "sell" and signal_data["signal"] == "up":
            signal_data["confidence"] = max(signal_data["confidence"] - 10, 10)
        if signal_data.get("moving_averages") == "buy" and signal_data["signal"] == "down":
            signal_data["confidence"] = max(signal_data["confidence"] - 10, 10)

        # 8. Sentimento vs direção do sinal
        sentiment = (signal_data.get("sentiment") or "").lower()
        if sentiment == "pessimistic" and signal_data["signal"] == "up":
            print("❌ Rejected: bullish signal with pessimistic sentiment")
            return None
        if sentiment == "optimistic" and signal_data["signal"] == "down":
            print("❌ Rejected: bearish signal with optimistic sentiment")
            return None

        # 9. Padrões de candle (patterns) contrários
        patterns = signal_data.get("patterns", [])
        if isinstance(patterns, list):
            for pat in patterns:
                pl = pat.lower()
                if ("bear" in pl or "engulfing" in pl or "shooting" in pl or "doji" in pl) and signal_data["signal"] == "up":
                    print(f"❌ Rejected: bearish pattern ({pat}) contra o sinal de compra")
                    return None
                if ("bull" in pl or "hammer" in pl or "engulfing" in pl) and signal_data["signal"] == "down":
                    print(f"❌ Rejected: bullish pattern ({pat}) contra o sinal de venda")
                    return None

        # 10. Suporte/resistência (evita compra perto da resistência, venda perto do suporte)
        support = float(signal_data.get("support", 0))
        resistance = float(signal_data.get("resistance", 0))
        if signal_data["signal"] == "up" and resistance and price > 0:
            dist = abs(resistance - price)
            if dist < self.min_support_distance:
                print(f"❌ Rejected: buying too close to resistance ({dist})")
                return None
        if signal_data["signal"] == "down" and support and price > 0:
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
