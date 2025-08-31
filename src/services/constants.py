TARGET_EXCHANGES: set[str] = {"binance", "bybit", "kucoin"}
MIN_INTERVAL_SEC = 1.6

# Веса для приоритета (можно переопределить из CLI)
W_VOLUME = 0.5
W_MCAP = 0.3
W_EXCH = 0.15
W_CHAINS = 0.05
W_RECENT = 0.0
