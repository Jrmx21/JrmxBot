from bot import get_ohlcv
from telegram.ext import ContextTypes

from ta.momentum import RSIIndicator
estado_anterior = {}

def detectar_cruce_ma(df, symbol):
    df = df.copy()
    df['ma9'] = df['close'].rolling(window=9).mean()
    df['ma21'] = df['close'].rolling(window=21).mean()
    df['rsi'] = RSIIndicator(close=df['close'], window=14).rsi()
    
    # Estado previo para simular cambio
    estado_anterior = 'ninguno'
    senales = []
    
    for i in range(1, len(df)):
        cruce_alcista = df['ma9'].iloc[i-1] < df['ma21'].iloc[i-1] and df['ma9'].iloc[i] > df['ma21'].iloc[i]
        cruce_bajista = df['ma9'].iloc[i-1] > df['ma21'].iloc[i-1] and df['ma9'].iloc[i] < df['ma21'].iloc[i]
        diferencia = abs(df['ma9'].iloc[i] - df['ma21'].iloc[i])
        umbral_diferencia = df['close'].iloc[i] * 0.002
        rsi = df['rsi'].iloc[i]
        
        señal = 'ninguno'
        if cruce_alcista and diferencia > umbral_diferencia and rsi < 70:
            if estado_anterior != 'compra':
                señal = 'compra'
                estado_anterior = 'compra'
        elif cruce_bajista and diferencia > umbral_diferencia and rsi > 30:
            if estado_anterior != 'venta':
                señal = 'venta'
                estado_anterior = 'venta'
        senales.append(señal)
    
    # Ajustamos para que la lista tenga la misma longitud que df (rellenando el primero)
    return ['ninguno'] + senales


def detectar_anomalias(df, symbol):
    variacion = (df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2] * 100
    if variacion > 2:
        return f'🚀 Subida rápida (+{variacion:.2f}%) en {symbol}'
    elif variacion < -2:
        return f'📉 Caída rápida ({variacion:.2f}%) en {symbol}'
    return None
import asyncio

async def analizar_moneda(symbol):
    df = get_ohlcv(symbol=symbol)
    senales = []

    cruce = detectar_cruce_ma(df, symbol)  # Puede devolver lista de strings
    if cruce:
        # Si devuelve lista, extiéndela, no añadas la lista completa
        senales.extend([s for s in cruce if s != 'ninguno'])

    anomalia = detectar_anomalias(df, symbol)  # Devuelve string o None
    if anomalia:
        senales.append(anomalia)

    return senales


async def obtener_senales_activas(context: ContextTypes.DEFAULT_TYPE):
    monedas = context.user_data.get('selected_coins', [])
    if not monedas:
        return "⚠️ No tienes criptomonedas seleccionadas para monitorizar. Usa /sel para seleccionar."

    # Ejecuta todos los análisis en paralelo
    resultados = await asyncio.gather(*(analizar_moneda(coin) for coin in monedas))

    senales = [senal for sublista in resultados for senal in sublista]

    return "\n".join(senales) if senales else "✅ No hay señales activas en este momento para tus criptomonedas seleccionadas."


async def obtener_variacion_24h(symbol='BTC/USDT'):
    df = get_ohlcv(symbol=symbol, timeframe='1h', limit=24)  # 24 velas de 1h = 24h
    precio_inicial = df['close'].iloc[0]
    precio_final = df['close'].iloc[-1]
    variacion = ((precio_final - precio_inicial) / precio_inicial) * 100
    return precio_final, variacion
