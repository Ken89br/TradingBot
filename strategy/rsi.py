#strategy/rsi py
class RSIStrategy:
    def __init__(self, overbought=65, oversold=35, window=14):
        self.overbought = overbought
        self.oversold = oversold
        self.window = window
        self.min_data_points = window + 1  # Mínimo necessário para cálculo

    def calculate_rsi(self, closes):
        """Calcula o RSI de forma vetorizada e segura"""
        try:
            if len(closes) < self.min_data_points:
                return None

            # Converte para array numpy para operações vetorizadas
            import numpy as np
            closes = np.array(closes[-self.window-1:])  # Pega apenas os últimos pontos necessários
            
            deltas = np.diff(closes)
            gains = deltas.clip(min=0)
            losses = -deltas.clip(max=0)
            
            # Médias móveis exponenciais (mais preciso que SMA para RSI)
            avg_gain = np.mean(gains[:self.window])
            avg_loss = np.mean(losses[:self.window])
            
            for i in range(self.window, len(gains)):
                avg_gain = (avg_gain * (self.window - 1) + gains[i]) / self.window
                avg_loss = (avg_loss * (self.window - 1) + losses[i]) / self.window

            # Evita divisão por zero e valores extremos
            rs = avg_gain / (avg_loss + 1e-10)  # Adiciona pequeno valor para evitar divisão por zero
            rsi = 100 - (100 / (1 + rs))
            
            return max(0, min(100, rsi))  # Garante RSI entre 0-100
            
        except Exception as e:
            print(f"Erro ao calcular RSI: {e}")
            return None

    def generate_signal(self, data):
        """Gera sinais de trading com tratamento robusto"""
        try:
            if not data or "history" not in data:
                return None

            candles = data["history"]
            if len(candles) < self.min_data_points:
                return None

            closes = [c["close"] for c in candles]
            rsi = self.calculate_rsi(closes)
            
            if rsi is None:
                return None

            # Lógica de sinal com histerese para evitar flip-flop
            if rsi > self.overbought:
                return {"signal": "down", "rsi": rsi}
            elif rsi < self.oversold:
                return {"signal": "up", "rsi": rsi}
            return None
            
        except Exception as e:
            print(f"Erro ao gerar sinal: {e}")
            return None
