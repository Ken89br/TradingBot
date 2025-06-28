#strategy/rsi_ma.py
import numpy as np
from collections import deque

class AggressiveRSIMA:
    def __init__(self, config=None):
        # Parâmetros configuráveis
        self.rsi_period = config.get('rsi_period', 14) if config else 14
        self.ma_period = config.get('ma_period', 5) if config else 5
        self.overbought = config.get('overbought', 65) if config else 65
        self.oversold = config.get('oversold', 35) if config else 35
        self.min_history = max(self.rsi_period, self.ma_period) + 5  # Buffer adicional
        
        # Otimização: buffers circulares para cálculos
        self.price_buffer = deque(maxlen=self.rsi_period * 2)
        self.rsi_buffer = deque(maxlen=3)  # Armazena últimos valores RSI
        self.ma_buffer = deque(maxlen=3)   # Armazena últimos valores MA
        
        # Configurações avançadas
        self.require_confirmation = config.get('confirmation', True) if config else True
        self.volume_threshold = config.get('volume_threshold', 1.2) if config else 1.2

    def _calculate_rsi(self, prices):
        """Cálculo RSI otimizado sem pandas"""
        deltas = np.diff(prices)
        seed = deltas[:self.rsi_period + 1]
        up = seed[seed >= 0].sum() / self.rsi_period
        down = -seed[seed < 0].sum() / self.rsi_period
        rs = up / (down + 1e-10)  # Evita divisão por zero
        rsi = 100 - (100 / (1 + rs))
        for i in range(self.rsi_period + 1, len(deltas)):
            delta = deltas[i]
            up = (up * (self.rsi_period - 1) + max(delta, 0)) / self.rsi_period
            down = (down * (self.rsi_period - 1) + max(-delta, 0)) / self.rsi_period
            rs = up / (down + 1e-10)
            rsi = np.append(rsi, 100 - (100 / (1 + rs)))
        return rsi[-1] if isinstance(rsi, np.ndarray) and len(rsi) > 0 else 50  # Valor neutro se não calcular

    def _calculate_ma(self, prices):
        """Cálculo MA otimizado"""
        return np.mean(prices[-self.ma_period:])

    def generate_signal(self, candle):
        """Geração de sinal com múltiplas camadas de confirmação"""
        try:
            history = candle.get("history", [])
            if len(history) < self.min_history:
                return None

            # Processamento eficiente dos dados
            latest = history[-1]
            prev = history[-2] if len(history) > 1 else None
            
            # Atualiza buffers
            current_price = float(latest["close"])
            self.price_buffer.append(current_price)
            
            # Cálculos somente quando tiver dados suficientes
            if len(self.price_buffer) >= self.rsi_period:
                current_rsi = self._calculate_rsi(np.array(self.price_buffer))
                current_ma = self._calculate_ma(np.array(self.price_buffer))
                self.rsi_buffer.append(current_rsi)
                self.ma_buffer.append(current_ma)
            else:
                return None

            # Confirmações adicionais
            volume_ok = float(latest.get("volume", 0)) > \
                       (float(prev.get("volume", 0)) * self.volume_threshold if prev else 0)
            
            # Lógica principal do sinal
            signal = None
            strength = "medium"
            
            # Condição de compra com confirmações
            if (current_rsi < self.oversold and 
                current_price > current_ma and 
                (not self.require_confirmation or 
                 (len(self.rsi_buffer) > 1 and self.rsi_buffer[-2] < self.rsi_buffer[-1]))):
                
                if volume_ok:
                    strength = "high"
                signal = self._package("up", history, strength, current_rsi, current_ma)
            
            # Condição de venda com confirmações
            elif (current_rsi > self.overbought and 
                  current_price < current_ma and 
                  (not self.require_confirmation or 
                   (len(self.rsi_buffer) > 1 and self.rsi_buffer[-2] > self.rsi_buffer[-1]))):
                
                if volume_ok:
                    strength = "high"
                signal = self._package("down", history, strength, current_rsi, current_ma)
            
            return signal

        except Exception as e:
            print(f"Error in AggressiveRSIMA: {e}")
            return None

    def _package(self, signal, history, strength, rsi_value, ma_value):
        """Pacote de sinal enriquecido"""
        latest = history[-1]
        closes = [float(c["close"]) for c in history]
        highs = [float(c["high"]) for c in history]
        lows = [float(c["low"]) for c in history]
        
        # Cálculo dinâmico de confiança
        base_confidence = {"high": 85, "medium": 70, "low": 55}.get(strength, 50)
        rsi_factor = 1 - (abs(rsi_value - 50) / 50)  # Mais extremo = mais confiança
        ma_distance = abs(float(latest["close"]) - ma_value) / ma_value
        volume_factor = min(1, float(latest.get("volume", 0)) / (np.mean([float(c.get("volume", 0)) for c in history[-5:]]) + 1e-10))
        
        confidence = min(100, base_confidence + 
                         (15 * rsi_factor) + 
                         (10 * ma_distance * 100) + 
                         (5 * volume_factor))

        return {
            "signal": signal,
            "price": float(latest["close"]),
            "high": float(latest["high"]),
            "low": float(latest["low"]),
            "volume": float(latest.get("volume", 0)),
            "rsi": rsi_value,
            "ma": ma_value,
            "recommend_entry": (float(latest["high"]) + float(latest["low"])) / 2,
            "recommend_stop": float(latest["low"]) if signal == "up" else float(latest["high"]),
            "strength": strength,
            "confidence": int(confidence),
            "indicators": {
                "rsi_trend": "rising" if len(self.rsi_buffer) > 1 and self.rsi_buffer[-1] > self.rsi_buffer[-2] else "falling",
                "price_ma_ratio": float(latest["close"]) / ma_value,
                "volatility": np.std(closes[-10:]) if len(closes) >= 10 else 0
            }
            }
