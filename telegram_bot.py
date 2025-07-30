import requests
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

def enviar_alerta(mensaje):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    params = {'chat_id': TELEGRAM_CHAT_ID, 'text': mensaje}
    requests.get(url, params=params)
