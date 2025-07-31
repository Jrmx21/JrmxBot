from io import BytesIO
from matplotlib import pyplot as plt
from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes
)

from analysis import obtener_senales_activas, obtener_variacion_24h
from bot import get_ohlcv
from config import ALL_COINS

# Función para obtener precio actual
def obtener_precio_actual(symbol='BTC/USDT'):
    df = get_ohlcv(symbol=symbol, limit=1)
    return df['close'].iloc[-1]

# Función para enviar gráfico de BTC últimas 8 horas
async def enviar_grafico_btc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    df = get_ohlcv(symbol='BTC/USDT', timeframe='15m', limit=32)  # 8h

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


# Comando /sel para selección múltiple
async def sel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    
    # Inicializar si no existe
    if 'selected_coins' not in user_data:
        user_data['selected_coins'] = []

    keyboard = []
    for coin in ALL_COINS:
        marcado = "✅" if coin in user_data['selected_coins'] else "⬜"
        keyboard.append([InlineKeyboardButton(f"{marcado} {coin}", callback_data=f"sel_{coin}")])

    keyboard.append([
        InlineKeyboardButton("Marcar / Desmarcar todos 🔄", callback_data="sel_toggle_all")
    ])
    keyboard.append([InlineKeyboardButton("Confirmar selección ✅", callback_data="sel_confirm")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(
            "Selecciona las criptomonedas para monitorear",
            reply_markup=reply_markup
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            "Selecciona las criptomonedas para monitorear:",
            reply_markup=reply_markup
        )

# Callback para selección múltiple
async def sel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_data = context.user_data
    if 'selected_coins' not in user_data:
        user_data['selected_coins'] = []

    data = query.data

    if data == 'sel_toggle_all':
        # Si hay alguna moneda sin marcar, marcar todas. Si todas marcadas, desmarcar todas
        if set(user_data['selected_coins']) == set(ALL_COINS):
            user_data['selected_coins'] = []
        else:
            user_data['selected_coins'] = ALL_COINS.copy()

    elif data.startswith('sel_') and data != 'sel_confirm':
        coin = data[4:]
        if coin in user_data['selected_coins']:
            user_data['selected_coins'].remove(coin)
        else:
            user_data['selected_coins'].append(coin)

    if data == 'sel_confirm':
        # Guardar selección definitiva en bot_data para monitoreo global
        if 'monitored_users' not in context.bot_data:
            context.bot_data['monitored_users'] = {}
        context.bot_data['monitored_users'][query.from_user.id] = user_data['selected_coins']

        await query.edit_message_text(f"Selección guardada:\n{', '.join(user_data['selected_coins']) or 'Nada seleccionado'}")
        return

    # Actualizar teclado con la selección actualizada
    keyboard = []
    for c in ALL_COINS:
        marcado = "✅" if c in user_data['selected_coins'] else "⬜"
        keyboard.append([InlineKeyboardButton(f"{marcado} {c}", callback_data=f"sel_{c}")])
    keyboard.append([InlineKeyboardButton("Marcar / Desmarcar todos 🔄", callback_data="sel_toggle_all")])
    keyboard.append([InlineKeyboardButton("Confirmar selección ✅", callback_data="sel_confirm")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_reply_markup(reply_markup=reply_markup)

# Enviar precio actual de una moneda específica
async def enviar_precio_actual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = 'BTC/USDT'  # Puedes cambiar esto a cualquier otra moneda
    if context.args:
        symbol = context.args[0].upper()
    if symbol.upper() not in ALL_COINS:
        await update.message.reply_text(f"⚠️ Moneda no válida. Usa una de las siguientes: {', '.join(ALL_COINS)}")
        return
    if '/' not in symbol:
        symbol += '/USDT'
    
    precio = obtener_precio_actual(symbol)
    await update.message.reply_text(f"💰 Precio actual de {symbol}: ${precio:.2f}")
    
    from telegram import BotCommand
async def set_bot_commands(app: ApplicationBuilder):
    commands = [
        BotCommand("start", "Iniciar el bot"),
        BotCommand("sel", "Seleccionar criptomonedas para monitoreo"),
        BotCommand("backtest", "Iniciar un backtest con capital ficticio"),
        BotCommand("capital", "Ver capital ficticio actual"),
        BotCommand("fin_backtest", "Finalizar el backtest actual"),
        BotCommand("ver_backtest", "Ver estado del backtest actual"),
        BotCommand("ver_capital", "Ver capital ficticio actual"),
        BotCommand("grafico_btc", "Enviar gráfico de BTC/USDT (últimas 8 horas)"),
        BotCommand("precio", "Enviar precio actual de una moneda específica")
    ]
# Callback principal para botones
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith('sel_') or query.data == 'sel_confirm' or query.data == 'sel_command':
        # Delegar a función de selección múltiple
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
        return
    elif query.data == 'ver_senales':
        mensaje = await obtener_senales_activas(context)
    else:
        mensaje = '⚠️ Opción desconocida'

    if mensaje != query.message.text:
        await query.edit_message_text(text=mensaje)

# Enviar alerta automática
async def enviar_alerta(texto, context: ContextTypes.DEFAULT_TYPE, chat_id):
    await context.bot.send_message(chat_id=chat_id, text=texto)

#help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🆘 Comandos disponibles:\n"
        "/start - Iniciar el bot\n"
        "/sel - Seleccionar criptomonedas para monitoreo\n"
        "/backtest - Iniciar un backtest con capital ficticio\n"
        "/capital - Ver capital ficticio actual\n"
        "/fin_backtest - Finalizar el backtest actual\n"
        "/ver_backtest - Ver estado del backtest actual\n"
        "/ver_capital - Ver capital ficticio actual\n"
        "/grafico_btc - Enviar gráfico de BTC/USDT (últimas 8 horas)\n"
        "/precio [moneda] - Enviar precio actual de una moneda específica (ej. /precio ETH/USDT)"
    )
    await update.message.reply_text(help_text)