from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes
)
import asyncio
import matplotlib.pyplot as plt
from io import BytesIO

from backtest import (
    command_backtest, command_capital, command_fin_backtest,
    command_ver_backtest, command_ver_capital
)
from config import TELEGRAM_TOKEN
from messagging_bot import  button_callback, enviar_grafico_btc, enviar_precio_actual, help_command, sel, set_bot_commands
from monitoring import auto_monitor_job


# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💰 Precio BTC/USDT", callback_data='precio_btc')],
        [InlineKeyboardButton("💎 Precio ETH/USDT", callback_data='precio_eth')],
        [InlineKeyboardButton("🔷 Precio SOL/USDT", callback_data='precio_sol')],
        [InlineKeyboardButton("📊 Ver gráfico BTC (8h)", callback_data='grafico_btc')],
        [InlineKeyboardButton("🔍 Ver señales activas", callback_data='ver_senales')],
        [InlineKeyboardButton("📈 Variación 24h", callback_data='variacion_24h')],
        [InlineKeyboardButton("⚙️ Seleccionar criptomonedas para monitoreo (/sel)", callback_data='sel_command')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Elige una opción:", reply_markup=reply_markup)

# Registro de comandos y handlers
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sel", sel))
    
    # Handlers de backtest
    app.add_handler(CommandHandler("backtest", command_backtest))
    app.add_handler(CommandHandler("capital", command_capital))
    app.add_handler(CommandHandler("fin_backtest", command_fin_backtest))
    app.add_handler(CommandHandler("ver_backtest", command_ver_backtest))
    app.add_handler(CommandHandler("ver_capital", command_ver_capital))
    app.add_handler(CommandHandler("grafico_btc", enviar_grafico_btc))
    app.add_handler(CommandHandler("precio", enviar_precio_actual))
    app.add_handler(CommandHandler("help", help_command))

    # Callback query handler general
    app.add_handler(CallbackQueryHandler(button_callback))

    # Job para monitorización automática (cada 5 min)
    job_queue = app.job_queue
    job_queue.run_repeating(auto_monitor_job, interval=300, first=10)

    print("Bot iniciado. Esperando mensajes...")
   ##AYUDA EN COMANDOS
   ## asyncio.get_event_loop().run_until_complete(set_bot_commands(app))

    app.run_polling()
    

if __name__ == "__main__":
    main()
