import krakenex
import time
import requests
from datetime import datetime
from telebot import TeleBot, types  # nova biblioteca para responder mensagens

# ==============================
# CONFIGURAÇÕES TELEGRAM
# ==============================
TELEGRAM_TOKEN = "8333319654:AAHyN5GRDtFd51z2ppEajuLOIQjUdCEB750"
CHAT_ID = "8288457417"  # seu chat ID correto

bot = TeleBot(TELEGRAM_TOKEN)  # inicializa bot

def enviar_telegram(msg, chat_id=CHAT_ID):
    """
    Envia mensagem para um chat específico (padrão: CHAT_ID)
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": chat_id, "text": msg}, timeout=10)
        print(f"[TELEGRAM] Mensagem enviada: {msg}")
    except Exception as e:
        print(f"[TELEGRAM] Erro ao enviar mensagem: {e}")

# ==============================
# CONFIGURAÇÕES KRAKEN
# ==============================
api = krakenex.API()
api.load_key('kraken.key')

# ==============================
# FUNÇÕES DE OPERAÇÃO
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
            return 0
        txid = list(resp['result']['txid'])[0]
        info = api.query_private('QueryOrders', {"txid": txid})
        preco_executado = float(info['result'][txid]['price'])
        lucro = 0
        registrar_trade(par, tipo, quantidade, preco_executado, lucro, chat_id)
        return lucro
    except Exception as e:
        enviar_telegram(f"⚠️ Erro inesperado trade {par}: {e}", chat_id)
        return 0

def registrar_trade(par, tipo, quantidade, preco, lucro, chat_id=CHAT_ID):
    msg = (f"💹 TRADE EXECUTADO\nPar: {par}\nTipo: {tipo}\nQuantidade: {quantidade}\n"
           f"Preço: {preco:.2f}\nLucro: {lucro:.2f}€")
    print(msg)
    enviar_telegram(msg, chat_id)
    with open("log_trades.txt", "a") as f:
        f.write(f"{datetime.now()} | {msg}\n")

# ==============================
# CONFIGURAÇÕES DE ESTRATÉGIA
# ==============================
SALDO_MINIMO = 15
CHECK_INTERVAL = 60
PARS_OPERACAO = ["BTC/EUR", "ETH/EUR"]
QUANTIDADE = {"BTC/EUR": 0.001, "ETH/EUR": 0.01}

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

# echo genérico (opcional)
@bot.message_handler(func=lambda m: True)
def echo(message: types.Message):
    bot.reply_to(message, f"Comando recebido: {message.text}")

# ==============================
# INÍCIO DO BOT AUTOMÁTICO
# ==============================
print("🚀 BOT ULTRAPROFISSIONAL INICIADO")
time.sleep(3)
enviar_telegram("🚀 BOT ULTRAPROFISSIONAL LIGADO!\nSistema conectado à Kraken.")
saldo_inicial = registrar_saldo()
time.sleep(1)
enviar_telegram(f"💰 Saldo inicial registrado: {saldo_inicial:.2f}€")
lucro_total = 0

# ==============================
# LOOP PRINCIPAL 24/7 (rodando em paralelo com o bot)
# ==============================
def loop_principal():
    global lucro_total
    while True:
        agora = datetime.now().strftime('%H:%M:%S')
        saldo = saldo_eur()
        print(f"[{agora}] Verificando mercado...")
        if saldo < SALDO_MINIMO:
            aviso = f"⚠️ Saldo insuficiente para operar.\nSaldo atual: {saldo:.2f}€"
            print(aviso)
            enviar_telegram(aviso)
            time.sleep(CHECK_INTERVAL)
            continue
        pronto = f"🔥 Saldo suficiente para operar! Saldo: {saldo:.2f}€"
        print(pronto)
        enviar_telegram(pronto)
        for par in PARS_OPERACAO:
            tipo = "BUY"
            quantidade = QUANTIDADE[par]
            lucro = executar_trade(par, tipo, quantidade)
            lucro_total += lucro
        print(f"[LUCRO] Lucro total acumulado: {lucro_total:.2f}€")
        enviar_telegram(f"📈 Lucro total acumulado: {lucro_total:.2f}€")
        time.sleep(CHECK_INTERVAL)

# ==============================
# EXECUÇÃO
# ==============================
import threading
threading.Thread(target=loop_principal, daemon=True).start()  # roda loop de trades em paralelo
bot.infinity_polling()  # mantém bot escutando comandos
