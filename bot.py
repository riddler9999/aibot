import time
import pandas as pd
import numpy as np
import os
from binance.client import Client
from binance.enums import *

# === API Keys ===
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")
client = Client(API_KEY, API_SECRET)
client.FUTURES_URL = 'https://fapi.binance.com/fapi'

# === Settings ===
SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', '1000PEPEUSDT', 'MYXUSDT', 'FARTCOINUSDT']
INTERVAL = '5m'
USD_PER_TRADE = 10
TRADE_COOLDOWN = 60 * 5  # 5 minutes
STOP_LOSS_PERCENT = 3  # 3% stop loss
last_trade_times = {symbol: 0 for symbol in SYMBOLS}

# === Functions ===

def get_klines(symbol, interval, limit=100):
    data = client.futures_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])
    df['close'] = df['close'].astype(float)
    return df

def bollinger_signal(df):
    df['MA20'] = df['close'].rolling(window=20).mean()
    df['STD'] = df['close'].rolling(window=20).std()
    df['Upper'] = df['MA20'] + (2 * df['STD'])
    df['Lower'] = df['MA20'] - (2 * df['STD'])

    price = df['close'].iloc[-1]
    upper = df['Upper'].iloc[-1]
    lower = df['Lower'].iloc[-1]

    if price <= lower:
        return 'BUY'
    elif price >= upper:
        return 'SELL'
    else:
        return 'HOLD'

def get_price(symbol):
    ticker = client.futures_symbol_ticker(symbol=symbol)
    return float(ticker['price'])

def get_symbol_precision(symbol):
    try:
        exchange_info = client.futures_exchange_info()
        for s in exchange_info['symbols']:
            if s['symbol'] == symbol:
                for f in s['filters']:
                    if f['filterType'] == 'LOT_SIZE':
                        step_size = float(f['stepSize'])
                        precision = abs(int(round(-np.log10(step_size))))
                        return precision
    except Exception as e:
        print(f"Error fetching precision for {symbol}: {e}")
    return 2  # fallback

def place_market_order(symbol, side, quantity):
    try:
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type='MARKET',
            quantity=quantity
        )
        print(f"{side} order placed for {symbol} (Qty: {quantity}) | Order ID: {order['orderId']}")
        return order
    except Exception as e:
        print(f"Error placing {side} order for {symbol}: {e}")
        return None

def place_stop_loss(symbol, side, entry_price, quantity, sl_percent):
    try:
        if side == SIDE_BUY:
            stop_price = round(entry_price * (1 - sl_percent / 100), 4)
            sl_side = SIDE_SELL
        else:
            stop_price = round(entry_price * (1 + sl_percent / 100), 4)
            sl_side = SIDE_BUY

        client.futures_create_order(
            symbol=symbol,
            side=sl_side,
            type=ORDER_TYPE_STOP_MARKET,
            stopPrice=stop_price,
            quantity=quantity,
            timeInForce=TIME_IN_FORCE_GTC
        )
        print(f"Stop loss set at {stop_price} for {symbol}")
    except Exception as e:
        print(f"Failed to set stop loss for {symbol}: {e}")

# === Main Loop ===
while True:
    for symbol in SYMBOLS:
        try:
            df = get_klines(symbol, INTERVAL)
            signal = bollinger_signal(df)
            print(f"[{symbol}] Signal: {signal}")

            current_time = time.time()

            if signal in ['BUY', 'SELL'] and (current_time - last_trade_times[symbol]) > TRADE_COOLDOWN:
                price = get_price(symbol)
                precision = get_symbol_precision(symbol)
                quantity = round(USD_PER_TRADE / price, precision)
                side = SIDE_BUY if signal == 'BUY' else SIDE_SELL

                order = place_market_order(symbol, side, quantity)
                if order:
                    entry_price = price
                    place_stop_loss(symbol, side, entry_price, quantity, STOP_LOSS_PERCENT)
                    last_trade_times[symbol] = current_time

        except Exception as e:
            print(f"Error processing {symbol}: {e}")

    time.sleep(60)
