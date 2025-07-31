import os
import pandas as pd

def detectar_anomalias(df, symbol):
    # Calcular variación porcentual entre las dos últimas filas
    variacion = (df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2] * 100
    
    # Carpeta y archivo para guardar anomalías
    carpeta = os.path.join('..', 'data')
    if not os.path.exists(carpeta):
        os.makedirs(carpeta)
    archivo = os.path.join(carpeta, f"{symbol}_signals_anomalies.csv")
    
    if variacion > 2:
        mensaje = f'🚀 Subida rápida (+{variacion:.2f}%) en {symbol}'
    elif variacion < -2:
        mensaje = f'📉 Caída rápida ({variacion:.2f}%) en {symbol}'
    else:
        return None  # No hay anomalía, no guardamos nada
    
    # Datos a guardar
    fila = {
        'timestamp': df.index[-1] if hasattr(df.index, 'format') else len(df)-1,
        'close': df['close'].iloc[-1],
        'variacion_pct': variacion,
        'mensaje': mensaje
    }
    
    # Guardar en CSV (append si ya existe)
    df_fila = pd.DataFrame([fila])
    if not os.path.isfile(archivo):
        df_fila.to_csv(archivo, index=False)
    else:
        df_fila.to_csv(archivo, mode='a', header=False, index=False)
    
    print(f"Anomalía guardada en {archivo}: {mensaje}")
    return mensaje
