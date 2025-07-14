# Multi-Coin Binance Futures Trading Bot (Render Deploy)

Trades BTCUSDT, ETHUSDT, XRPUSDT, and 1000PEPEUSDT using Bollinger Band strategy on 15m timeframe.

## ⚙️ Features

- Auto-calculates quantity based on $10/trade
- Executes BUY or SELL based on Bollinger Band signals
- Runs every 60 seconds
- Keeps trade cooldown (15 minutes per coin)
- Secure API key via environment variables

## 🚀 Deployment (on Render)

1. Go to https://render.com
2. Create new **Background Worker**
3. Connect this project (via GitHub or upload manually)
4. Set `Start Command` to:
   ```
   python bot.py
   ```
5. Add **Environment Variables**:
   - `BINANCE_API_KEY`: your Binance API key
   - `BINANCE_API_SECRET`: your Binance API secret

## ✅ Notes

- For test trading, use Binance Testnet: https://testnet.binancefuture.com
- Do NOT enable withdrawals in your API key
- Monitor logs to see trade activity
