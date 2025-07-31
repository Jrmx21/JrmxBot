from telegram.ext import (
    ContextTypes
)
# Job periódico async que llama a analizar_moneda y envía alertas
from analysis import analizar_moneda
from messagging_bot import enviar_alerta


async def auto_monitor_job(context: ContextTypes.DEFAULT_TYPE):
    monitored = context.bot_data.get('monitored_users', {})
    if not monitored:
        return

    for user_id, coins in monitored.items():
        for coin in coins:
            try:
                senales = await analizar_moneda(coin)

                # Filtrar señales válidas, ignorando 'ninguno'
                señales_validas = [s for s in senales if s != 'ninguno']

                if señales_validas:
                    mensaje = f"🔔 *Alerta para {coin}:*\n"

                    for s in señales_validas:
                        if s == 'compra':
                            mensaje += "🔵 Señal de COMPRA detectada.\n"
                        elif s == 'venta':
                            mensaje += "🔴 Señal de VENTA detectada.\n"
                        else:
                            # Si es texto de anomalía u otro mensaje
                            mensaje += f"⚠️ {s}\n"

                    await enviar_alerta(mensaje, context, user_id)

            except Exception as e:
                print(f"Error analizando {coin} para usuario {user_id}: {e}")