import asyncio
import csv
import datetime
from io import StringIO
from telegram import Update, InputFile
from telegram.ext import ContextTypes
from analysis import detectar_cruce_ma, detectar_anomalias
from bot import get_ohlcv
import os

backtest_sessions = {}


def guardar_csv_backtest(history, user_id):
    folder = "backtests"
    os.makedirs(folder, exist_ok=True)

    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename_local = os.path.join(folder, f"backtest_{user_id}.csv")  # Fijo el nombre para ir sobreescribiendo

    with open(filename_local, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'coin', 'precio', 'senal', 'detalle', 'balance'])
        for evento in history:
            writer.writerow([
                evento['timestamp'],
                evento['coin'],
                f"{evento['precio']:.2f}",
                evento['senal'],
                evento['detalle'],
                f"{evento.get('balance', 0):.2f}"
            ])

    return filename_local
# Mostrar capital ficticio actual
async def command_ver_capital(update: Update, context: ContextTypes.DEFAULT_TYPE):
    capital = context.user_data.get('capital', 1000.0)
    await update.message.reply_text(f"Tu capital ficticio actual es: ${capital:.2f}")

# Mostrar estado actual del backtest
async def command_ver_backtest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in backtest_sessions:
        await update.message.reply_text("No tienes ningún backtest en curso.")
        return

    session = backtest_sessions[user_id]
    capital = session.get('balance', 0)
    history = session.get('history', [])

    texto = f"📊 Estado actual del backtest:\nCapital disponible: ${capital:.2f}\n"

    if not history:
        texto += "No hay operaciones realizadas aún."
    else:
        texto += "Últimas operaciones:\n"
        ultimas = history[-5:]  # últimas 5
        for evento in ultimas:
            texto += (f"{evento['timestamp']} - {evento['coin']} - "
                      f"{evento['senal'].capitalize()} a ${evento['precio']:.2f} "
                      f"({evento['detalle']})\n")

    await update.message.reply_text(texto)

# Iniciar backtest
async def command_backtest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in backtest_sessions and backtest_sessions[user_id].get('activo', False):
        await update.message.reply_text("Ya tienes un backtest corriendo. Usa /fin_backtest para terminarlo antes.")
        return

    capital = context.user_data.get('capital', 1000.0)
    coins = context.user_data.get('selected_coins', ['BTC/USDT'])  # Ajusta las monedas por defecto o seleccionadas

    session = {
        'capital': capital,
        'coins': coins,
        'balance': capital,
        'positions': {},
        'history': [],
        'activo': True,
        'chat_id': update.effective_chat.id,
        'context': context
    }
    backtest_sessions[user_id] = session

    await update.message.reply_text(f"Backtest iniciado con capital ficticio ${capital:.2f} para {', '.join(coins)}.")

    async def backtest_loop():
        while session['activo']:
            for coin in coins:
                df = get_ohlcv(symbol=coin, limit=50)
                señales = detectar_cruce_ma(df, coin)
                señal_actual = señales[-1]
                precio_actual = df['close'].iloc[-1]
                position = session['positions'].get(coin)

                detalle = None
                msg = None

                if señal_actual == 'compra' and not position:
                    cantidad = session['balance'] / precio_actual
                    session['positions'][coin] = {'cantidad': cantidad, 'precio': precio_actual}
                    session['balance'] = 0.0
                    detalle = f"Compra {cantidad:.6f} {coin} a ${precio_actual:.2f}"
                    msg = f"💰 {detalle}"

                elif señal_actual == 'venta' and position:
                    cantidad = position['cantidad']
                    ganancia = cantidad * precio_actual
                    session['balance'] += ganancia
                    del session['positions'][coin]  # borrar la posición correctamente
                    detalle = f"Venta {cantidad:.6f} {coin} a ${precio_actual:.2f}, balance ${session['balance']:.2f}"
                    msg = f"📉 {detalle}"

                anomalia = detectar_anomalias(df, coin)
                if anomalia:
                    msg = f"⚠️ {anomalia}"

                if detalle or anomalia:
                    session['history'].append({
                        'timestamp': datetime.datetime.now().isoformat(sep=' ', timespec='seconds'),
                        'coin': coin,
                        'precio': precio_actual,
                        'senal': señal_actual if detalle else 'ninguno',
                        'detalle': detalle or anomalia,
                        'balance': session['balance']
                    })
                    guardar_csv_backtest(session['history'], user_id)
                if msg:
                    # Enviar mensaje al chat
                    await context.bot.send_message(chat_id=session['chat_id'], text=msg)

            await asyncio.sleep(5)  # Espera entre iteraciones

    context.application.create_task(backtest_loop())

# Establecer capital ficticio
async def command_capital(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args

    if not args:
        await update.message.reply_text("Por favor, usa: /capital <monto> para establecer el capital ficticio.")
        return

    try:
        capital = float(args[0])
        if capital <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Monto inválido. Usa un número positivo, por ejemplo: /capital 1000")
        return

    context.user_data['capital'] = capital

    # También actualizar si hay sesión activa
    if user_id in backtest_sessions:
        backtest_sessions[user_id]['capital'] = capital
        backtest_sessions[user_id]['balance'] = capital

    await update.message.reply_text(f"Capital establecido en ${capital:.2f} para el backtest.")

# Finalizar backtest y enviar CSV
async def command_fin_backtest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in backtest_sessions or not backtest_sessions[user_id].get('activo', False):
        await update.message.reply_text("No tienes ningún backtest en curso para finalizar.")
        return

    session = backtest_sessions[user_id]
    history = session.get('history', [])

    if not history:
        await update.message.reply_text("No hay datos para guardar del backtest.")
        return

    # Crear CSV en memoria
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['timestamp', 'coin', 'precio', 'senal', 'detalle', 'balance'])

    for evento in history:
        writer.writerow([
            evento['timestamp'],
            evento['coin'],
            f"{evento['precio']:.2f}",
            evento['senal'],
            evento['detalle'],
            f"{evento.get('balance', 0):.2f}"
        ])

    output.seek(0)

    # Enviar CSV al usuario
    await context.bot.send_document(chat_id=update.effective_chat.id,
                                    document=InputFile(output, filename="backtest_resultados.csv"))

    # Limpiar sesión
    del backtest_sessions[user_id]

    await update.message.reply_text("Backtest finalizado y archivo enviado. Sesión eliminada.")
