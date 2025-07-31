from bot import get_ohlcv
from telegram.ext import ContextTypes
import asyncio

from patterns.anomalies import detectar_anomalias
from patterns.cruce_ma import detectar_cruce_ma

estado_anterior = {}

async def analizar_moneda(symbol):
    df = get_ohlcv(symbol=symbol, limit=50)
    senales = []

    cruce = detectar_cruce_ma(df, symbol)  # lista o None
    if cruce:
        senales.extend(cruce)

    anomalia = detectar_anomalias(df, symbol)  # string o None
    if anomalia:
        senales.append(anomalia)

    return senales

def detectar_senales_completas(df, symbol):
    señales = []

    # Detector de cruces de medias
    cruces = detectar_cruce_ma(df, symbol)
    if cruces:
        señales.extend([s for s in cruces if s in ('compra', 'venta')])

    # Detector de anomalías
    anomalia = detectar_anomalias(df, symbol)
    if anomalia:
        señales.append('compra')  # Se trata como señal de compra

    return señales, anomalia


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
