import krakenex
import pandas as pd
import time
import requests
from datetime import datetime
import threading

# ==============================
# CONFIGURAÇÕES
# ==============================
TELEGRAM_TOKEN = "8335062260:AAGsIUyqS0i0zWGnBS6Z1CFSCqofMNMJLjQ"
CHAT_ID = "8288457417"

PAR = "ETH/EUR"
TIMEFRAME = 60 # 1 minuto
EMA_CURTA = 9
EMA_LONGA = 21

RISCO_POR_TRADE = 0.01 # 1%
STOP_LOSS_PCT = 0.015 # 1.5%
CHECK_INTERVAL = 60

# ==============================
# TELEGRAM
# ==============================
def enviar_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ==============================
# KRAKEN
# ==============================
api = krakenex.API()
api.load_key('kraken.key')

# ==============================
# DADOS DE MERCADO
# ==============================
def obter_ohlc():
    resp = api.query_public("OHLC", {
        "pair": PAR.replace("/", ""),
        "interval": TIMEFRAME
    })
    data = resp["result"][list(resp["result"].keys())[0]]
    df = pd.DataFrame(data, columns=[
        "time","open","high","low","close","vwap","volume","count"
    ])
    df["close"] = df["close"].astype(float)
    return df

def calcular_emas(df):
    df["ema_curta"] = df["close"].ewm(span=EMA_CURTA).mean()
    df["ema_longa"] = df["close"].ewm(span=EMA_LONGA).mean()
    return df

# ==============================
# SALDO
# ==============================
def saldo_eur():
    resp = api.query_private("Balance")
    return float(resp["result"].get("ZEUR", 0))

# ==============================
# EXECUÇÃO DE ORDENS
# ==============================
def comprar(volume):
    api.query_private("AddOrder", {
        "pair": PAR.replace("/", ""),
        "type": "buy",
        "ordertype": "market",
        "volume": volume
    })

def vender(volume):
    api.query_private("AddOrder", {
        "pair": PAR.replace("/", ""),
        "type": "sell",
        "ordertype": "market",
        "volume": volume
    })

# ==============================
# ESTADO DO BOT
# ==============================
em_posicao = False
preco_entrada = 0
volume_atual = 0

# ==============================
# LOOP PRINCIPAL
# ==============================
def loop():
    global em_posicao, preco_entrada, volume_atual

    enviar_telegram("🤖 Bot profissional iniciado")

    while True:
        try:
            df = obter_ohlc()
            df = calcular_emas(df)

            atual = df.iloc[-1]
            anterior = df.iloc[-2]

            saldo = saldo_eur()

            # ===== ENTRADA =====
            if not em_posicao:
                cruzamento_alta = (
                    anterior["ema_curta"] < anterior["ema_longa"] and
                    atual["ema_curta"] > atual["ema_longa"]
                )

                if cruzamento_alta and saldo > 20:
                    risco_valor = saldo * RISCO_POR_TRADE
                    volume = round((risco_valor / atual["close"]), 6)

                    comprar(volume)

                    em_posicao = True
                    preco_entrada = atual["close"]
                    volume_atual = volume

                    enviar_telegram(
                        f"🟢 COMPRA EXECUTADA\nPreço: {preco_entrada:.2f}€\nVolume: {volume}"
                    )

            # ===== SAÍDA =====
            else:
                stop_loss = preco_entrada * (1 - STOP_LOSS_PCT)
                cruzamento_baixa = atual["ema_curta"] < atual["ema_longa"]

                if atual["close"] <= stop_loss or cruzamento_baixa:
                    vender(volume_atual)

                    lucro = (atual["close"] - preco_entrada) * volume_atual

                    enviar_telegram(
                        f"🔴 VENDA EXECUTADA\nPreço: {atual['close']:.2f}€\nLucro: {lucro:.2f}€"
                    )

                    em_posicao = False
                    preco_entrada = 0
                    volume_atual = 0

        except Exception as e:
            enviar_telegram(f"⚠️ Erro no bot: {e}")

        time.sleep(CHECK_INTERVAL)

# ==============================
# START
# ==============================
threading.Thread(target=loop, daemon=True).start()

while True:
    time.sleep(60)
