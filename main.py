from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler
)
import asyncio
import matplotlib.pyplot as plt
from io import BytesIO

from backtest import command_backtest, command_capital, command_fin_backtest, command_ver_backtest, command_ver_capital
from bot import get_ohlcv
from analysis import  detectar_cruce_ma, detectar_anomalias, obtener_senales_activas, obtener_variacion_24h
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

# Lista larga de criptomonedas para selección (puedes ampliarla)
ALL_COINS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT', 'XRP/USDT',
    'DOT/USDT', 'DOGE/USDT', 'LTC/USDT', 'BCH/USDT', 'LINK/USDT',
    'MATIC/USDT', 'UNI/USDT', 'VET/USDT', 'TRX/USDT', 'EOS/USDT',
]

# --- FUNCIONES PARA CONSULTAR PRECIO ACTUAL ---
def obtener_precio_actual(symbol='BTC/USDT'):
    df = get_ohlcv(symbol=symbol, limit=1)
    return df['close'].iloc[-1]

async def enviar_grafico_btc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    df = get_ohlcv(symbol='BTC/USDT', timeframe='15m', limit=32)  # 8h = 32 velas de 15m

    plt.style.use('dark_background')
    fig, ax = plt.subplots()
    ax.plot(df.index, df['close'], color='cyan', linewidth=2)
    ax.set_title("BTC/USDT - Últimas 8 horas")
    ax.set_xlabel("Hora")
    ax.set_ylabel("Precio ($)")
    plt.xticks(rotation=45)
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()

    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=buf)

# --- COMANDO /start ---
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

# --- COMANDO /sel: Selección múltiple de criptos ---
async def sel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    
    user_data['selected_coins'] = ALL_COINS
    # Inicializamos la lista de seleccionadas si no existe
    if 'selected_coins' not in user_data:
        user_data['selected_coins'] = []

    keyboard = []

    for coin in ALL_COINS:
        marcado = "✅" if coin in user_data['selected_coins'] else "⬜"
        keyboard.append([InlineKeyboardButton(f"{marcado} {coin}", callback_data=f"sel_{coin}")])

 
    # Botón para confirmar selección
    keyboard.append([InlineKeyboardButton("Confirmar selección ✅", callback_data="sel_confirm")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(
            "Selecciona las criptomonedas para monitorear (toca para marcar/desmarcar):",
            reply_markup=reply_markup
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            "Selecciona las criptomonedas para monitorear (toca para marcar/desmarcar):",
            reply_markup=reply_markup
        )

# --- CALLBACK para selección múltiple ---
async def sel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_data = context.user_data
    if 'selected_coins' not in user_data:
        user_data['selected_coins'] = []

    data = query.data

    if data.startswith('sel_') and data != 'sel_confirm':
        coin = data[4:]
        if coin in user_data['selected_coins']:
            user_data['selected_coins'].remove(coin)
        else:
            user_data['selected_coins'].append(coin)

        # Actualizar teclado con selección actualizada
        keyboard = []
        for c in ALL_COINS:
            marcado = "✅" if c in user_data['selected_coins'] else "⬜"
            keyboard.append([InlineKeyboardButton(f"{marcado} {c}", callback_data=f"sel_{c}")])
        keyboard.append([InlineKeyboardButton("Confirmar selección ✅", callback_data="sel_confirm")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_reply_markup(reply_markup=reply_markup)
    elif data == 'sel_confirm':
        # Guardar selección definitiva en bot_data para monitoreo global
        if 'monitored_users' not in context.bot_data:
            context.bot_data['monitored_users'] = {}
        context.bot_data['monitored_users'][query.from_user.id] = user_data['selected_coins']

        await query.edit_message_text(f"Selección guardada:\n{', '.join(user_data['selected_coins']) or 'Nada seleccionado'}")
    

# --- CALLBACK principal para botones (menos selección múltiple) ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith('sel_') or query.data == 'sel_confirm' or query.data == 'sel_command':
        # Delegamos a la función de selección múltiple
        if query.data == 'sel_command':
            await sel(update, context)
        else:
            await sel_callback(update, context)
        return

    mensaje = None

    if query.data == 'precio_btc':
        precio = obtener_precio_actual('BTC/USDT')
        mensaje = f'💰 Precio BTC/USDT: ${precio:.2f}'
    elif query.data == 'precio_eth':
        precio = obtener_precio_actual('ETH/USDT')
        mensaje = f'💎 Precio ETH/USDT: ${precio:.2f}'
    elif query.data == 'precio_sol':
        precio = obtener_precio_actual('SOL/USDT')
        mensaje = f'🔷 Precio SOL/USDT: ${precio:.2f}'
    elif query.data == 'grafico_btc':
        await query.edit_message_text(text='Generando gráfico 📊...')
        await enviar_grafico_btc(update, context)
        return  # Ya se mostró el gráfico, no editar texto abajo
    elif query.data == 'ver_senales':
        mensaje = await obtener_senales_activas(context)
    elif query.data == 'variacion_24h':
        precio, variacion = await obtener_variacion_24h()
        mensaje = f"📈 BTC/USDT últimas 24h:\n\n💵 Precio actual: ${precio:.2f}\n📊 Variación: {variacion:.2f}%"
    else:
        mensaje = '⚠️ Opción desconocida'

    if mensaje != query.message.text:
        await query.edit_message_text(text=mensaje)
    else:
        print("Mensaje no modificado, omitiendo actualización.")

# --- ENVÍO DE ALERTAS AUTOMÁTICAS ---
async def enviar_alerta(texto, context: ContextTypes.DEFAULT_TYPE, chat_id):
    await context.bot.send_message(chat_id=chat_id, text=texto)

# --- ANÁLISIS AUTOMÁTICO PERIÓDICO ---
async def auto_monitor_job(context: ContextTypes.DEFAULT_TYPE):
    # Obtener usuarios y monedas que monitorean
    monitored = context.bot_data.get('monitored_users', {})
    if not monitored:
        return

    for user_id, coins in monitored.items():
        for coin in coins:
            try:
                df = get_ohlcv(symbol=coin, limit=50)
                alerta = detectar_cruce_ma(df, coin) or detectar_anomalias(df, coin)
                if alerta:
                    texto = f"Alerta para {coin}:\n{alerta}"
                    await enviar_alerta(texto, context, user_id)
            except Exception as e:
                print(f"Error analizando {coin} para usuario {user_id}: {e}")
                
async def command_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "/start - Inicio del bot\n"
        "/sel - Seleccionar criptomonedas para análisis\n"
        "/capital [monto] - Establecer capital ficticio para backtest\n"
        "/backtest - Iniciar simulación de trading\n"
        "/ver_capital - Ver capital ficticio actual\n"
        "/ver_backtest - Ver estado actual del backtest\n"
        "/fin_backtest - Finalizar simulación y recibir historial\n"
    )
    await update.message.reply_text(texto)
# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sel", sel))  # Nuevo comando para selección múltiple
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(CommandHandler("backtest", command_backtest))
    app.add_handler(CommandHandler("ver_capital", command_ver_capital))
    app.add_handler(CommandHandler("ver_backtest", command_ver_backtest))
    app.add_handler(CommandHandler("fin_backtest", command_fin_backtest))
    app.add_handler(CommandHandler("capital", command_capital))
    app.add_handler(CommandHandler("help", command_help))

    # Job para monitoreo periódico cada 5 minutos
    app.job_queue.run_repeating(auto_monitor_job, interval=300, first=0)

    app.run_polling()

if __name__ == "__main__":
    main()
