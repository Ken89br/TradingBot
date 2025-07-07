#data/pocketoption_data.py
import os
import json
import time
from datetime import datetime
import websocket

class PocketOptionAuthError(Exception):
    """Erro de autenticação/SSID inválido ou expirado."""
    pass

class PocketOptionClient:
    def __init__(self):
        # Atualize para EIO=4 se necessário pelo site.
        self.ws_url = "wss://socket.pocketoption.com/socket.io/?EIO=4&transport=websocket"
        self.ssid = os.getenv("POCKETOPTION_SSID")
        if not self.ssid:
            raise RuntimeError("POCKETOPTION_SSID não encontrado no .env!")
        self.ws = None

    def _to_tf(self, interval):
        mapping = {
            "s1": 5,
            "m1": 60,
            "m5": 300,
            "m15": 900,
            "m30": 1800,
            "h1": 3600,
            "h4": 14400,
            "d1": 86400
        }
        return mapping.get(interval.lower(), 60)

    def fetch_candles(self, symbol, interval="m1", limit=5, retries=2):
        symbol_api = symbol.lower().replace(" ", "").replace("/", "")
        tf_sec = self._to_tf(interval)
        try:
            candles = self._fetch_ws_candles(symbol_api, tf_sec, limit)
            if candles:
                return {"history": candles, "close": candles[-1]["close"]}
        except PocketOptionAuthError as e:
            print(f"❌ PocketOption Auth error: {e}")
            # Aqui você pode acionar alerta Telegram se desejar
            raise
        except Exception as e:
            print(f"❌ PocketOption WS error: {e}")
        return None

    def _fetch_ws_candles(self, asset, period, limit):
        ws = websocket.create_connection(self.ws_url)
        # Etapa 1: handshake inicial
        ws.recv()  # 0{"sid":"..."}
        # Etapa 2: enviar AUTH com SSID (payload atualizado para conta real)
        auth_payload = json.dumps({
            "session": self.ssid,
            "isDemo": 0,
            "platform": 2,
            "isFastHistory": True,
            "isOptimized": True
        })
        ws.send(f'42["auth",{auth_payload}]')
        # Espera confirmação de AUTH
        auth_ok = False
        for _ in range(5):
            msg = ws.recv()
            if '"auth"' in msg:
                if '"success":true' in msg or "authenticated" in msg:
                    auth_ok = True
                    break
                elif '"success":false' in msg or "error" in msg or "invalid" in msg:
                    ws.close()
                    raise PocketOptionAuthError("Autenticação PocketOption falhou: SSID inválido ou expirado.")
            time.sleep(0.2)
        if not auth_ok:
            ws.close()
            raise PocketOptionAuthError("Autenticação PocketOption não confirmada (timeout ou resposta inesperada).")
        # Etapa 3: solicitar candles
        now = int(time.time())
        req_payload = json.dumps({
            "asset": asset,
            "period": period,
            "limit": limit,
            "end": now
        })
        ws.send(f'42["get-candles",{req_payload}]')
        candles = None
        # Espera resposta dos candles
        for _ in range(10):
            msg = ws.recv()
            if '"get-candles"' in msg:
                try:
                    arr = json.loads(msg[2:])  # remove o '42'
                    # arr[1] é o dict de resposta
                    data = arr[1].get("data", [])
                    candles = []
                    for c in data:
                        candles.append({
                            "timestamp": int(c["time"]),
                            "open": float(c["open"]),
                            "high": float(c["high"]),
                            "low": float(c["low"]),
                            "close": float(c["close"]),
                            "volume": float(c.get("volume", 1))
                        })
                    break
                except Exception as e:
                    print(f"⚠️ Erro ao parsear resposta get-candles: {e}")
            time.sleep(0.2)
        ws.close()
        return candles
