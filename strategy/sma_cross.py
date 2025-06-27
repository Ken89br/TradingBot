import numpy as np

class SMACrossStrategy:
    def __init__(self, short_period=5, long_period=10, min_history=20, confirmation_candles=3):
        self.short_period = short_period
        self.long_period = long_period
        self.min_history = max(min_history, long_period)  # Garante dados suficientes
        self.confirmation_candles = confirmation_candles
        self.trend = None  # Rastreia a tendência atual

    def calculate_sma(self, closes, period):
        """Calcula SMA de forma otimizada com numpy"""
        if len(closes) < period:
            return None
        return np.mean(closes[-period:])

    def generate_signal(self, data):
        """Gera sinal com confirmação de tendência e filtros adicionais"""
        try:
            candles = data.get("history", [])
            if len(candles) < self.min_history:
                return None

            closes = [float(c["close"]) for c in candles]  # Garante tipo numérico
            
            # Calcula SMAs
            sma_short = self.calculate_sma(closes, self.short_period)
            sma_long = self.calculate_sma(closes, self.long_period)
            
            if sma_short is None or sma_long is None:
                return None

            # Verifica cruzamento com confirmação
            current_cross = sma_short - sma_long
            signal = None
            
            # Lógica de cruzamento com confirmação
            if current_cross > 0 and (self.trend != "up" or not self.trend):
                # Confirmação em n candles
                if len(candles) >= self.confirmation_candles:
                    prev_closes = [float(c["close"]) for c in candles[-self.confirmation_candles-1:-1]]
                    if all(c > self.calculate_sma(prev_closes, self.short_period) for c in closes[-self.confirmation_candles:]):
                        signal = {"signal": "up", "type": "sma_cross"}
                        self.trend = "up"
            
            elif current_cross < 0 and (self.trend != "down" or not self.trend):
                if len(candles) >= self.confirmation_candles:
                    prev_closes = [float(c["close"]) for c in candles[-self.confirmation_candles-1:-1]]
                    if all(c < self.calculate_sma(prev_closes, self.short_period) for c in closes[-self.confirmation_candles:]):
                        signal = {"signal": "down", "type": "sma_cross"}
                        self.trend = "down"

            if signal:
                # Adiciona metadados para análise
                signal.update({
                    "sma_short": sma_short,
                    "sma_long": sma_long,
                    "spread": abs(sma_short - sma_long),
                    "confidence": self._calculate_confidence(closes),
                    "price": closes[-1],
                    "volume": candles[-1].get("volume", 0)
                })
                return signal
            
            return None

        except Exception as e:
            print(f"Error in SMACrossStrategy: {e}")
            return None

    def _calculate_confidence(self, closes):
        """Calcula confiança baseada no momentum e spread"""
        price_change = closes[-1] - closes[-5]  # Mudança de preço em 5 períodos
        spread = abs(self.calculate_sma(closes, self.short_period) - self.calculate_sma(closes, self.long_period))
        
        # Normaliza os fatores
        price_factor = min(max(price_change / (closes[-5] * 0.01), -2), 2)  # Cap at ±2%
        spread_factor = spread / (closes[-1] * 0.01)  # Spread como % do preço
        
        # Fórmula de confiança (ajustável)
        confidence = 50 + (20 * price_factor) + (30 * min(spread_factor, 1))
        return min(max(int(confidence), 0), 100)
