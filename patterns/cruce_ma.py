import os
import pandas as pd
from ta.momentum import RSIIndicator

def detectar_cruce_ma(df, symbol):
    print(f"Analizando {symbol} para cruces de medias móviles...")
    df = df.copy()
    df['ma9'] = df['close'].rolling(window=9).mean()
    df['ma21'] = df['close'].rolling(window=21).mean()
    df['rsi'] = RSIIndicator(close=df['close'], window=14).rsi()
    
    estado_anterior = 'ninguno'
    senales = []

    ##CSV
    # Carpeta y archivo para guardar señales
    carpeta = os.path.join('..', 'data')
    if not os.path.exists(carpeta):
        os.makedirs(carpeta)
    archivo = os.path.join(carpeta, f"{symbol}_signals_cruces_ma.csv")

    # Para guardar solo filas con señales reales
    filas_a_guardar = []

    ##CSV
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
        #CSV
    if señal != 'ninguno':
            fila = {
                'timestamp': df.index[i] if hasattr(df.index, 'format') else i,
                'close': df['close'].iloc[i],
                'ma9': df['ma9'].iloc[i],
                'ma21': df['ma21'].iloc[i],
                'rsi': rsi,
                'señal': señal
            }
            filas_a_guardar.append(fila)
    
     # Guardar solo si hay señales reales
    if filas_a_guardar:
        df_senal = pd.DataFrame(filas_a_guardar)
        # Si el archivo no existe, crea con header, si existe, añade sin header
        if not os.path.isfile(archivo):
            df_senal.to_csv(archivo, index=False)
        else:
            df_senal.to_csv(archivo, mode='a', header=False, index=False)
        print(f"Se guardaron {len(filas_a_guardar)} señales en {archivo}")

    #CSV
    
    # Si no hay señales relevantes, devuelve None
    if all(s == 'ninguno' for s in senales):
        return None
    
    # Devolver lista con señales (con longitud len(df)-1)
    return senales
