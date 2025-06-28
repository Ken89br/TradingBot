#strategy/rsi py
import numpy as np
from collections import deque

class RSIStrategy:
    def __init__(self, config=None):
        # Parâmetros com valores padrão otimizados
        self.overbought = config.get('overbought', 70) if config else 70  # Mais conservador
        self.oversold = config.get('oversold', 30) if config else 30      # Mais conservador
        self.window = config.get('window', 14) if config else 14
        self.min_data_points = self.window + 2  # Buffer de segurança
        
        # Configurações avançadas
        self.require_confirmation = config.get('confirmation', True) if config else True
        self.trend_filter = config.get('trend_filter', False) if config else False
        self.volume_threshold = config.get('volume_threshold', 1.3) if config else 1.3
        
        # Estado interno para cálculo incremental
        self.price_buffer = deque(maxlen=self.window * 3)
        self.prev_avg_gain = 0
        self.prev_avg_loss = 0
        self.last_rsi = None

    def _calculate_rsi(self):
        """Cálculo RSI profissional com:
        - EMA em vez de SMA
        - Tratamento de bordas
        - Suavização"""
        if len(self.price_buffer) < self.min_data_points:
            return None

        prices = np.array(self.price_buffer, dtype=np.float64)
        deltas = np.diff(prices)
        
        gains = deltas.clip(min=0)
        losses = -deltas.clip(max=0)
        
        # Primeiro cálculo (SMA)
        if self.prev_avg_gain == 0:
            self.prev_avg_gain = np.mean(gains[:self.window])
            self.prev_avg_loss = np.mean(losses[:self.window])
        # Cálculos subsequentes (EMA)
        else:
            self.prev_avg_gain = (self.prev_avg_gain * (self.window - 1) + gains[-1]) / self.window
            self.prev_avg_loss = (self.prev_avg_loss * (self.window - 1) + losses[-1]) / self.window

        # Evita divisão por zero e valores extremos
        rs = self.prev_avg_gain / (self.prev_avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        # Suavização para evitar flutuações bruscas
        if self.last_rsi:
            rsi = 0.7 * rsi + 0.3 * self.last_rsi  # Filtro de suavização
            
        self.last_rsi = rsi
        return np.clip(rsi, 0, 100)

    def _get_trend(self, candles):
        """Determina tendência com base em EMAs rápidas e lentas"""
        if len(candles) < 20:
            return None
            
        closes = [c['close'] for c in candles[-20:]]
        ema_fast = sum(closes[-5:]) / 5
        ema_slow = sum(closes[-20:]) / 20
        return 'up' if ema_fast > ema_slow else 'down'

    def generate_signal(self, data):
        """Geração de sinal profissional com múltiplas camadas de confirmação"""
        try:
            if not data or "history" not in data:
                return None

            candles = data["history"]
            if len(candles) < self.min_data_points:
                return None

            # Atualiza buffer e calcula RSI
            current_close = float(candles[-1]["close"])
            self.price_buffer.append(current_close)
            rsi = self._calculate_rsi()
            
            if rsi is None:
                return None

            # Confirmações adicionais
            current_volume = candles[-1].get("volume", 0)
            prev_volume = candles[-2].get("volume", 1) if len(candles) > 1 else 1
            volume_ok = current_volume > prev_volume * self.volume_threshold
            
            trend = self._get_trend(candles[:-1]) if self.trend_filter else None
            
            # Lógica de sinal aprimorada
            signal = None
            strength = "medium"
            
            # Condição de compra com confirmações
            if rsi < self.oversold:
                if (not self.require_confirmation or 
                    (volume_ok and (not self.trend_filter or trend == 'down'))):
                    strength = "high" if volume_ok and rsi < (self.oversold - 5) else "medium"
                    signal = {
                        "signal": "up",
                        "rsi": rsi,
                        "confidence": self._calculate_confidence(rsi, 'up', volume_ok, trend),
                        "price": current_close,
                        "indicators": {
                            "trend": trend,
                            "volume_ratio": current_volume / prev_volume
                        }
                    }

            # Condição de venda com confirmações
            elif rsi > self.overbought:
                if (not self.require_confirmation or 
                    (volume_ok and (not self.trend_filter or trend == 'up'))):
                    strength = "high" if volume_ok and rsi > (self.overbought + 5) else "medium"
                    signal = {
                        "signal": "down",
                        "rsi": rsi,
                        "confidence": self._calculate_confidence(rsi, 'down', volume_ok, trend),
                        "price": current_close,
                        "indicators": {
                            "trend": trend,
                            "volume_ratio": current_volume / prev_volume
                        }
                    }

            return signal

        except Exception as e:
            print(f"ProfessionalRSI error: {e}")
            return None

    def _calculate_confidence(self, rsi, direction, volume_ok, trend):
        """Cálculo sofisticado de confiança"""
        # Fator de distância do RSI
        rsi_factor = abs(rsi - 50) / 50  # 0-1
        
        # Fator de volume
        volume_factor = 0.2 if volume_ok else 0
        
        # Fator de tendência
        trend_factor = 0.15 if (
            (trend == 'up' and direction == 'up') or 
            (trend == 'down' and direction == 'down')
        ) else 0
        
        # Base + fatores ajustados
        base = 60 if direction == 'up' else 65  # Viés conservador para vendas
        confidence = base + (rsi_factor * 30) + (volume_factor * 15) + (trend_factor * 10)
        
        return min(95, max(50, int(confidence)))  # Mantém entre 50-95
