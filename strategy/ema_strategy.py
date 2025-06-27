import numpy as np

class EMAStrategy:
    def __init__(self, short_period=9, long_period=21):
        self.short_period = short_period
        self.long_period = long_period
        self.min_data_points = max(short_period, long_period) + 1

    def calculate_ema(self, prices, period):
        """Calcula EMA de forma vetorizada com numpy"""
        if len(prices) < period:
            return [None] * len(prices)
        
        prices = np.array(prices)
        ema = np.zeros_like(prices)
        k = 2 / (period + 1)
        
        # SMA inicial
        ema[period-1] = np.mean(prices[:period])
        
        # EMA subsequente
        for i in range(period, len(prices)):
            ema[i] = (prices[i] - ema[i-1]) * k + ema[i-1]
        
        # Preenche com None onde não há dados suficientes
        ema[:period-1] = None
        return ema.tolist()

    def generate_signal(self, data):
        """Gera sinal com tratamento robusto de erros"""
        try:
            candles = data.get("history", [])
            if len(candles) < self.min_data_points:
                return None

            closes = [c["close"] for c in candles[-self.min_data_points:]]  # Otimização: processa apenas os dados necessários
            
            short_ema = self.calculate_ema(closes, self.short_period)
            long_ema = self.calculate_ema(closes, self.long_period)

            # Verifica dados válidos nos últimos 2 períodos
            if None in [short_ema[-2], short_ema[-1], long_ema[-2], long_ema[-1]]:
                return None

            # Lógica de cruzamento com histerese
            prev_cross = short_ema[-2] - long_ema[-2]
            current_cross = short_ema[-1] - long_ema[-1]
            
            if prev_cross < 0 and current_cross > 0:
                return {
                    "signal": "up",
                    "indicator": "ema_crossover",
                    "short_ema": short_ema[-1],
                    "long_ema": long_ema[-1],
                    "confidence": self._calculate_confidence(abs(current_cross))
                }
            elif prev_cross > 0 and current_cross < 0:
                return {
                    "signal": "down",
                    "indicator": "ema_crossover",
                    "short_ema": short_ema[-1],
                    "long_ema": long_ema[-1],
                    "confidence": self._calculate_confidence(abs(current_cross))
                }
                
            return None
            
        except Exception as e:
            print(f"Erro em EMAStrategy: {e}")
            return None

    def _calculate_confidence(self, spread):
        """Calcula confiança baseada na distância entre as EMAs"""
        normalized_spread = min(spread / (self.short_period * 0.1), 1.0)  # Normaliza com base no período curto
        return int(50 + 50 * normalized_spread)  # Range: 50-100
