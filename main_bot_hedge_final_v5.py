import krakenex
import time
import requests
from datetime import datetime
from telebot import TeleBot
import pandas as pd
import os

# ==============================
# CONFIGURAÇÕES TELEGRAM
# ==============================
TELEGRAM_TOKEN = "8335062260:AAGsIUyqS0i0zWGnBS6Z1CFSCqofMNMJLjQ"
CHAT_ID = "8288457417"

bot = TeleBot(TELEGRAM_TOKEN)

def enviar_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        print(f"[TELEGRAM] {msg}")
    except Exception as e:
        print(f"[TELEGRAM] Erro ao enviar mensagem: {e}")

# ==============================
# CONFIGURAÇÕES KRAKEN
# ==============================
api = krakenex.API()
api.load_key('kraken.key')  # Arquivo com suas chaves da Kraken

SALDO_MINIMO = 10.0  # Saldo mínimo para operar
BOT_LIGADO_ENVIADO = False
COINS = ["XXBTZEUR", "XETHZEUR"]
STOP_LOSS_PERCENT = 1.0
TAKE_PROFIT_PERCENT = 1.5
MAX_RISCO_POR_TRADE = 0.3  # % do saldo disponível por operação
PERIODO_MA = 5  # Média móvel simples

# ==============================
# Histórico de preços e trades
# ==============================
precos = {coin: [] for coin in COINS}
arquivo_trades = "historico_trades.csv"
if not os.path.exists(arquivo_trades):
    df = pd.DataFrame(columns=["timestamp", "coin", "tipo", "entrada", "quantidade", "SL", "TP"])
    df.to_csv(arquivo_trades, index=False)

# ==============================
# FUNÇÕES
# ==============================
def verificar_saldo():
    try:
        saldo = api.query_private('Balance')['result']
        saldo_total = sum(float(v) for v in saldo.values())
        return saldo_total
    except Exception as e:
        enviar_telegram(f"Erro ao verificar saldo: {e}")
        return 0

def obter_preco(coin):
    try:
        ticker = api.query_public('Ticker', {'pair': coin})['result'][coin]
        preco = float(ticker['c'][0])
        return preco
    except Exception as e:
        enviar_telegram(f"Erro ao obter preço {coin}: {e}")
        return 0

def enviar_ordem(coin, tipo, quantidade):
    try:
        order_type = 'buy' if tipo == 'buy' else 'sell'
        response = api.query_private('AddOrder', {
            'pair': coin,
            'type': order_type,
            'ordertype': 'market',
            'volume': str(quantidade)
        })
        enviar_telegram(f"💹 Ordem {order_type.upper()} executada: {coin} | Qtd: {quantidade:.6f}")
        return response
    except Exception as e:
        enviar_telegram(f"❌ Erro ao enviar ordem {tipo} {coin}: {e}")
        return None

def registrar_trade(coin, tipo, entrada, quantidade, sl, tp):
    df = pd.read_csv(arquivo_trades)
    df = pd.concat([df, pd.DataFrame([{
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "coin": coin,
        "tipo": tipo,
        "entrada": entrada,
        "quantidade": quantidade,
        "SL": sl,
        "TP": tp
    }])], ignore_index=True)
    df.to_csv(arquivo_trades, index=False)

def executar_trade(coin, tipo, preco_atual, saldo_atual):
    quantidade = (saldo_atual * MAX_RISCO_POR_TRADE) / preco_atual
    stop_loss = preco_atual * (1 - STOP_LOSS_PERCENT/100) if tipo=='buy' else preco_atual * (1 + STOP_LOSS_PERCENT/100)
    take_profit = preco_atual * (1 + TAKE_PROFIT_PERCENT/100) if tipo=='buy' else preco_atual * (1 - TAKE_PROFIT_PERCENT/100)
    
    enviar_telegram(f"💹 {coin} | {tipo.upper()} | Entrada: {preco_atual:.2f} | SL: {stop_loss:.2f} | TP: {take_profit:.2f}")
    enviar_ordem(coin, tipo, quantidade)
    registrar_trade(coin, tipo, preco_atual, quantidade, stop_loss, take_profit)

# ==============================
# Estratégia: média móvel simples
# ==============================
def executar_estrategia():
    saldo_atual = verificar_saldo()
    
    global BOT_LIGADO_ENVIADO
    if not BOT_LIGADO_ENVIADO:
        enviar_telegram("✅ BOT FULL-PROFESSIONAL LIGADO! Conexão Telegram OK.")
        BOT_LIGADO_ENVIADO = True

    enviar_telegram(f"💰 Saldo atual: {saldo_atual:.2f}€")

    if saldo_atual < SALDO_MINIMO:
        enviar_telegram("⚠️ Saldo insuficiente para operar.")
        return

    for coin in COINS:
        preco_atual = obter_preco(coin)
        precos[coin].append(preco_atual)
        if len(precos[coin]) > PERIODO_MA:
            precos[coin].pop(0)
        
        ma = sum(precos[coin])/len(precos[coin])
        delta_percentual = ((preco_atual - ma)/ma)*100

        if delta_percentual >= 0.5:
            executar_trade(coin, 'sell', preco_atual, saldo_atual)
        elif delta_percentual <= -0.5:
            executar_trade(coin, 'buy', preco_atual, saldo_atual)
        else:
            enviar_telegram(f"📊 {coin} sem sinal claro ({delta_percentual:.2f}%), nada a fazer.")

# ==============================
# LOOP PRINCIPAL
# ==============================
if __name__ == "__main__":
    while True:
        try:
            executar_estrategia()
        except Exception as e:
            enviar_telegram(f"❌ Erro inesperado: {e}")
        time.sleep(60)
