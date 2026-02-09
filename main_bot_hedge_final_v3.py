import krakenex
import time
import requests
from datetime import datetime
from telebot import TeleBot, types

# ==============================
# CONFIGURAÇÕES TELEGRAM
# ==============================
TELEGRAM_TOKEN = "8335062260:AAGsIUyqS0i0zWGnBS6Z1CFSCqofMNMJLjQ"
CHAT_ID = "8288457417"

bot = TeleBot(TELEGRAM_TOKEN)

def enviar_telegram(msg, chat_id=CHAT_ID):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": chat_id, "text": msg}, timeout=10)
        print(f"[TELEGRAM] {msg}")
    except Exception as e:
        print(f"[TELEGRAM] Erro ao enviar mensagem: {e}")

# ==============================
# CONFIGURAÇÕES KRAKEN
# ==============================
api = krakenex.API()
api.load_key('kraken.key')  # arquivo com API_KEY e SECRET

# ==============================
# CONFIGURAÇÃO DE ESTRATÉGIA
# ==============================
SALDO_MINIMO = 15
QUANTIDADE = {"BTC/EUR": 0.001, "ETH/EUR": 0.01}
STOP_LOSS = 0.95       # 5% abaixo do preço de compra
TAKE_PROFIT = 1.05     # 5% acima do preço de compra
CHECK_INTERVAL = 60
PARS_OPERACAO = ["BTC/EUR", "ETH/EUR"]

# Armazena trades abertos
trades_abertos = {}

# ==============================
# FUNÇÕES
# ==============================
def saldo_eur():
    try:
        resp = api.query_private('Balance')
        if resp.get('error'):
            enviar_telegram(f"⚠️ Erro na API Kraken: {resp['error']}")
            return 0
        return float(resp['result'].get('ZEUR', 0))
    except Exception as e:
        enviar_telegram("⚠️ Erro ao consultar saldo na Kraken.")
        return 0

def registrar_saldo(chat_id=CHAT_ID):
    saldo = saldo_eur()
    enviar_telegram(f"💰 Saldo atual: {saldo:.2f}€", chat_id)
    return saldo

def consultar_preco(par):
    try:
        resp = api.query_public('Ticker', {"pair": par.replace("/", "")})
        preco = float(resp['result'][par.replace("/", "")]['c'][0])
        return preco
    except Exception as e:
        enviar_telegram(f"⚠️ Erro ao consultar preço {par}: {e}")
        return 0

def executar_trade(par, tipo, quantidade, chat_id=CHAT_ID):
    try:
        resp = api.query_private('AddOrder', {
            "pair": par.replace("/", ""),
            "type": tipo.lower(),
            "ordertype": "market",
            "volume": str(quantidade)
        })
        if resp.get('error'):
            enviar_telegram(f"⚠️ Erro ao executar trade {par}: {resp['error']}", chat_id)
            return None
        txid = list(resp['result']['txid'])[0]
        info = api.query_private('QueryOrders', {"txid": txid})
        preco_executado = float(info['result'][txid]['price'])
        registrar_trade(par, tipo, quantidade, preco_executado, chat_id)
        return preco_executado
    except Exception as e:
        enviar_telegram(f"⚠️ Erro inesperado trade {par}: {e}", chat_id)
        return None

def registrar_trade(par, tipo, quantidade, preco, chat_id=CHAT_ID):
    msg = (f"💹 TRADE EXECUTADO\nPar: {par}\nTipo: {tipo}\nQuantidade: {quantidade}\n"
           f"Preço: {preco:.2f}")
    enviar_telegram(msg, chat_id)
    with open("log_trades.txt", "a") as f:
        f.write(f"{datetime.now()} | {msg}\n")

def verificar_venda(par):
    if par not in trades_abertos:
        return
    preco_compra, quantidade = trades_abertos[par]
    preco_atual = consultar_preco(par)
    if preco_atual == 0:
        return
    # Take profit
    if preco_atual >= preco_compra * TAKE_PROFIT:
        executar_trade(par, "SELL", quantidade)
        enviar_telegram(f"💰 Trade vendido com lucro! Par: {par}, Preço: {preco_atual:.2f}")
        del trades_abertos[par]
    # Stop loss
    elif preco_atual <= preco_compra * STOP_LOSS:
        executar_trade(par, "SELL", quantidade)
        enviar_telegram(f"⚠️ Trade vendido no stop-loss. Par: {par}, Preço: {preco_atual:.2f}")
        del trades_abertos[par]

# ==============================
# COMANDOS TELEGRAM
# ==============================
@bot.message_handler(commands=['start'])
def cmd_start(message: types.Message):
    bot.reply_to(message, "🚀 BOT ULTRAPROFISSIONAL LIGADO!\nSistema conectado à Kraken.")
    saldo = registrar_saldo(message.chat.id)
    bot.send_message(message.chat.id, f"💰 Saldo inicial registrado: {saldo:.2f}€")

@bot.message_handler(commands=['saldo'])
def cmd_saldo(message: types.Message):
    saldo = saldo_eur()
    bot.reply_to(message, f"💰 Saldo atual: {saldo:.2f}€")

# Echo genérico
@bot.message_handler(func=lambda m: True)
def echo(message: types.Message):
    bot.reply_to(message, f"Comando recebido: {message.text}")

# ==============================
# LOOP PRINCIPAL 24/7
# ==============================
def loop_principal():
    while True:
        saldo = saldo_eur()
        if saldo < SALDO_MINIMO:
            enviar_telegram(f"⚠️ Saldo insuficiente para operar.\nSaldo atual: {saldo:.2f}€")
            time.sleep(CHECK_INTERVAL)
            continue
        enviar_telegram(f"🔥 Saldo suficiente para operar! Saldo: {saldo:.2f}€")
        for par in PARS_OPERACAO:
            # Se já tiver trade aberto, só verifica venda
            if par in trades_abertos:
                verificar_venda(par)
                continue
            quantidade = QUANTIDADE[par]
            preco_executado = executar_trade(par, "BUY", quantidade)
            if preco_executado:
                trades_abertos[par] = (preco_executado, quantidade)
        time.sleep(CHECK_INTERVAL)

# ==============================
# EXECUÇÃO
# ==============================
import threading
threading.Thread(target=loop_principal, daemon=True).start()
bot.infinity_polling()
