import time
from bot import get_ohlcv
from analysis import detectar_cruce_ma, detectar_anomalias
from telegram_bot import enviar_alerta
import datetime
def run_bot():
    enviar_alerta("Encendido "+ datetime.datetime)
    while True:
        df = get_ohlcv()
        mensaje = detectar_cruce_ma(df) or detectar_anomalias(df)
        if mensaje:
            enviar_alerta(mensaje)
        time.sleep(300)  # Espera 5 minutos

if __name__ == "__main__":
    run_bot()
