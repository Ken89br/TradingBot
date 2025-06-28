#strategy/macd_reversal.py
import numpy as np
from collections import deque

class EnhancedMACDReversal:
    def __init__(self, config=None):
        # Parâmetros configuráveis
        self.fast = config.get('fast', 12) if config else 12
        self.slow = config.get('slow', 26) if config else 26
        self.signal = config.get('signal', 9) if config else 9
        self.threshold = config.get('threshold', 0.1) if config else 0.1
        self.min_history = max(self.slow, self.signal) + 10

        # Otimização: buffers para cálculos incrementais
        self.price_buffer = deque(maxlen=self.slow * 2)
        self.macd_buffer = deque(maxlen=5)
        self.hist_buffer = deque(maxlen=5)

    def _calculate_macd(self, prices):
        """Cálculo MACD otimizado com numpy"""
        if len(prices) < self.slow:
            return None, None, None

        # EMA rápida e lenta
        fast_ema = self._ema(prices, self.fast)
        slow_ema = self._ema(prices, self.slow)
        if fast_ema is None or slow_ema is None:
            return None, None, None

        macd_line = fast_ema - slow_ema

        # Linha de sinal (EMA do MACD)
        if len(macd_line) >= self.signal:
            signal_line = self._ema(macd_line[-self.signal*2:], self.signal)
        else:
            signal_line = None
        histogram = macd_line[-1] - signal_line[-1] if signal_line is not None else None

        return macd_line[-1], signal_line[-1] if signal_line is not None else None, histogram

    def _ema(self, data, window):
        """Cálculo EMA otimizado"""
        if len(data) < window:
            return None
        weights = np.exp(np.linspace(-1., 0., window))
        weights /= weights.sum()
        padded = np.concatenate([np.ones(window-1)*data[0], data])
        return np.convolve(padded, weights, mode='valid')

    def generate_signal(self, data):
        """Geração de sinal com múltiplas confirmações"""
        try:
            candles = data.get("history", [])
            if len(candles) < self.min_history:
                return None

            # Atualiza buffer de preços
            self.price_buffer.extend([c['close'] for c in candles[-self.min_history:]])

            # Calcula MACD
            macd, signal_line, hist = self._calculate_macd(np.array(self.price_buffer, dtype=np.float64))
            if macd is None or signal_line is None:
                return None

            # Atualiza buffers de indicadores
            self.macd_buffer.append(macd)
            self.hist_buffer.append(hist)

            if len(self.hist_buffer) < 2:
                return None

            # Lógica de reversão aprimorada
            result_signal = None
            strength = "medium"
            prev_hist, curr_hist = self.hist_buffer[-2], self.hist_buffer[-1]

            # Confirmações adicionais
            price_above_ma = candles[-1]['close'] > np.mean([c['close'] for c in candles[-self.slow:]])
            volume_spike = candles[-1].get('volume', 0) > 1.5 * np.mean([c.get('volume', 0) for c in candles[-5:-1]] or [1])

            # Bullish Reversal
            if (prev_hist < 0 < curr_hist) or \
               (prev_hist < -self.threshold and curr_hist > -self.threshold/2):
                if price_above_ma:
                    strength = "high"
                result_signal = self._package("up", candles, strength, macd, signal_line, hist)

            # Bearish Reversal
            elif (prev_hist > 0 > curr_hist) or \
                 (prev_hist > self.threshold and curr_hist < self.threshold/2):
                if not price_above_ma:
                    strength = "high"
                result_signal = self._package("down", candles, strength, macd, signal_line, hist)

            # Filtro de volume para sinais médios
            if result_signal and strength == "medium" and volume_spike:
                result_signal['confidence'] += 10

            return result_signal

        except Exception as e:
            print(f"MACDReversal error: {str(e)}")
            return None

    def _package(self, signal, candles, strength, macd, signal_line, hist):
        """Pacote de sinal enriquecido"""
        latest = candles[-1]
        price = float(latest['close'])
        high = float(latest['high'])
        low = float(latest['low'])

        # Cálculo dinâmico de confiança
        base_conf = {"high": 85, "medium": 70, "low": 55}.get(strength, 50)
        hist_boost = min(20, abs(hist) * 100)  # Quanto maior o histograma, mais confiança
        ma_boost = 10 if signal == "up" and price > signal_line else \
                  -10 if signal == "down" and price < signal_line else 0

        confidence = min(100, base_conf + hist_boost + ma_boost)

        return {
            "signal": signal,
            "price": price,
            "high": high,
            "low": low,
            "volume": latest.get('volume', 0),
            "macd": macd,
            "signal_line": signal_line,
            "histogram": hist,
            "recommend_entry": (high + low) / 2,
            "recommend_stop": low if signal == "up" else high,
            "strength": strength,
            "confidence": int(confidence),
            "indicators": {
                "price_vs_signal": price / signal_line if signal_line else 1,
                "macd_cross": "golden" if signal == "up" else "death",
                "volatility": np.std([c['close'] for c in candles[-10:]]) if len(candles) >= 10 else 0
            }
        }
