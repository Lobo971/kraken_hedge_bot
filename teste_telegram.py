
import requests

# ==============================
# CONFIGURAÇÕES
# ==============================
TELEGRAM_TOKEN = "8333319654:AAHyN5GRDtFd51z2ppEajuLOIQjUdCEB750"
CHAT_ID = "8288457417"  # seu chat ID correto

# ==============================
# FUNÇÃO PARA ENVIAR MENSAGEM
# ==============================
def enviar_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        print(f"[TELEGRAM] Mensagem enviada: {msg}")
    except Exception as e:
        print(f"[TELEGRAM] Erro: {e}")

# ==============================
# TESTE
# ==============================
enviar_telegram("✅ Teste Telegram funcionando! O bot consegue enviar mensagens!")