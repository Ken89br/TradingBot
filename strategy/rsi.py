#strategy/rsi py
import numpy as np
from collections import deque
from strategy.candlestick_patterns import PATTERN_STRENGTH, detect_patterns

class ProfessionalRSIStrategy:
    def __init__(self, config=None):
        # Configuração básica do RSI
        self.overbought = config.get('overbought', 70) if config else 70
        self.oversold = config.get('oversold', 30) if config else 30
        self.window = config.get('window', 14) if config else 14
        
        # Configurações de confirmação
        self.candle_lookback = config.get('candle_lookback', 3) if config else 3
        self.volume_threshold = config.get('volume_threshold', 1.5) if config else 1.5
        self.min_confidence = config.get('min_confidence', 65) if config else 65
        
        # Estado interno
        self.price_buffer = deque(maxlen=self.window * 3)
        self.prev_avg_gain = 0
        self.prev_avg_loss = 0

    def _calculate_rsi(self):
        """Cálculo otimizado do RSI com suavização"""
        if len(self.price_buffer) < self.window + 1:
            return None

        deltas = np.diff(np.array(self.price_buffer, dtype=np.float64))
        gains = deltas.clip(min=0)
        losses = -deltas.clip(max=0)

        # Primeiro cálculo (SMA)
        if self.prev_avg_gain == 0:
            self.prev_avg_gain = gains[:self.window].mean()
            self.prev_avg_loss = losses[:self.window].mean()
        # Cálculos subsequentes (EMA)
        else:
            self.prev_avg_gain = (self.prev_avg_gain * (self.window - 1) + gains[-1]) / self.window
            self.prev_avg_loss = (self.prev_avg_loss * (self.window - 1) + losses[-1]) / self.window

        rs = self.prev_avg_gain / (self.prev_avg_loss + 1e-10)
        return 100 - (100 / (1 + rs))

    def _apply_pattern_boost(self, signal, patterns):
        """Aumenta confiança baseado em padrões de velas"""
        if not signal:
            return signal

        direction = signal["signal"]
        pattern_strength = 0
        
        # Padrões de confirmação (por direção)
        confirm_patterns = {
            "up": ["hammer", "bullish_engulfing", "piercing_line", "morning_star"],
            "down": ["hanging_man", "bearish_engulfing", "dark_cloud", "evening_star"]
        }[direction]

        # Soma a força dos padrões relevantes
        for pattern in patterns:
            if pattern in confirm_patterns:
                pattern_strength += PATTERN_STRENGTH.get(pattern, 0)

        # Boost de confiança proporcional
        if pattern_strength > 0:
            signal["confidence"] = min(95, signal["confidence"] + (pattern_strength * 15))
            signal["patterns"] = patterns
            signal["pattern_strength"] = pattern_strength

        return signal

    def generate_signal(self, data):
        """Gera sinais com confirmação de padrões de velas"""
        try:
            candles = data.get("history", [])
            if len(candles) < max(self.window + 1, self.candle_lookback):
                return None

            # Atualiza preços e calcula RSI
            current_candle = candles[-1]
            self.price_buffer.append(float(current_candle["close"]))
            rsi = self._calculate_rsi()
            
            if rsi is None:
                return None

            # Detecta padrões nos últimos candles
            patterns = detect_patterns(candles[-self.candle_lookback:])
            volume_ok = current_candle.get("volume", 0) > np.mean(
                [c.get("volume", 0) for c in candles[-self.candle_lookback:-1]] or [0]) * self.volume_threshold

            # Lógica principal
            signal = None
            if rsi < self.oversold:
                signal = {
                    "signal": "up",
                    "rsi": rsi,
                    "confidence": 60 + min(30, (self.oversold - rsi) / 2),  # 60-75
                    "price": float(current_candle["close"]),
                    "volume_ok": volume_ok
                }
            elif rsi > self.overbought:
                signal = {
                    "signal": "down",
                    "rsi": rsi,
                    "confidence": 65 + min(30, (rsi - self.overbought) / 2),  # 65-80
                    "price": float(current_candle["close"]),
                    "volume_ok": volume_ok
                }

            # Aplica boost de padrões de velas
            signal = self._apply_pattern_boost(signal, patterns)
            
            # Filtro final de confiança
            if signal and signal.get("confidence", 0) >= self.min_confidence:
                return signal
            return None

        except Exception as e:
            print(f"RSIStrategy error: {e}")
            return None
