import ccxt
import pandas as pd

exchange = ccxt.binance()
symbol = 'BTC/USDT'

def get_ohlcv(symbol=symbol, timeframe='5m', limit=100):
    data = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df
