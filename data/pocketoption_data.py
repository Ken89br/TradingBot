#data/pocketoption.py
import os
import json
import time
from datetime import datetime
import websocket

class PocketOptionClient:
    def __init__(self):
        self.ws_url = "wss://socket.pocketoption.com/socket.io/?EIO=3&transport=websocket"
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
        except Exception as e:
            print(f"❌ PocketOption WS error: {e}")
        return None

    def _fetch_ws_candles(self, asset, period, limit):
        ws = websocket.create_connection(self.ws_url)
        # Etapa 1: handshake inicial
        ws.recv()  # 0{"sid":"..."}
        # Etapa 2: enviar AUTH com SSID
        auth_payload = json.dumps({"auth": {"session": self.ssid}})
        ws.send(f'42["auth",{auth_payload}]')
        # Espera confirmação de AUTH
        for _ in range(5):
            msg = ws.recv()
            if '"auth"' in msg and '"success":true' in msg:
                break
            time.sleep(0.2)
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
            
