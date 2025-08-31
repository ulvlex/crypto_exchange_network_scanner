# crypto_exchange_network_scanner

Скрипт на Python, который:

Получает топ активов по суточному объёму (CoinGecko /coins/markets).

Для каждого актива проверяет наличие на целевых биржах {binance, bybit, kucoin} и, по желанию, собирает альтернативные биржи.

Определяет, в каких блокчейн-сетях доступен токен (поле platforms из /coins/{id}).

Выгружает результат в JSON или CSV.

Считает приоритет добавления актива (взвешенная модель по объёму, капитализации, покрытию бирж и мультичейну).

# Почему нет “топ-100 по дате листинга”
Публичный CoinGecko не даёт сортировки по дате листинга/дате добавления на биржи. Аналогичное поле (date_added) есть у CoinMarketCap, но для него нужен CMC API key. Получить его не удалось.

# Требования

Python 3.10+

Зависимости (см. requirements.txt)

# Переменные окружения

Создай .env :

CG_API_KEY=


# Установка и запуск
git clone https://github.com/<you>/crypto_exchange_network_scanner.git

cd crypto_exchange_network_scanner

python3 -m venv .venv

source .venv/bin/activate           

для Windows: .venv\Scripts\activate

pip install -r requirements.txt

# Настройка весов модели приоритета
python -m src.main \
  --limit 15 \
  --w-volume 0.5 --w-mcap 0.3 --w-exchanges 0.15 --w-chains 0.05 --w-recent 0.0 \
  --format json --out assets.json

# CLI-параметры

--limit — сколько активов взять из топа по объёму (по умолчанию 10).

--format — json | csv (по умолчанию json).

--out — путь к файлу выгрузки.

Веса модели приоритета:

--w-volume — вес объёма торгов (default 0.5).

--w-mcap — вес рыночной капитализации (default 0.3).

--w-exchanges — вес покрытия целевых бирж (default 0.15).

--w-chains — вес мультичейна (default 0.05).

--w-recent — вес «новизны» (сейчас 0.0).

--alt — собирать альтернативные биржи (дороже по запросам). По умолчанию выключено.

# Формат результата

Для каждого актива:

id, symbol, name

total_volume, market_cap_rank

exchanges — целевые биржи, где есть актив (binance, bybit, kucoin)

exchanges_alt — альтернативные биржи (если включено --alt)

networks — список сетей (ключи из platforms, например ethereum, bnb-smart-chain, solana…)

volume_rank, recent_rank (сейчас recent_rank=None)

priority_score — итоговая приоритизация (0..1), взвешенная сумма нормализованных факторов

# Модель приоритета (кратко)

priority_score = w_volume*volume_score + w_mcap*mcap_score + w_exchanges*exch_score + w_chains*chains_score + w_recent*recent_score

volume_score — нормализованный volume_rank.

mcap_score — нормализованный market_cap_rank.

exch_score — доля покрытых целевых бирж.

chains_score — нормализация по кол-ву сетей (мультичейн).

recent_score — сейчас не используется (нет публичной «даты листинга» у CG).

Веса выставляются через CLI или в constants.py.


# Дальнейшие улучшения 

Топ по дате листинга (CMC)

Контейнеризация
Написать Dockerfile и docker-compose.yml (проброс .env).

Тесты (pytest)

Юнит-тесты для priority.py, utils.py.


Код-стайл и качество
ruff/flake8, black, mypy, pre-commit.

CI (GitHub Actions): линт + тесты.


#  Примеры запуска
# Быстрый прогон (минимум запросов):
python -m src.main --limit 5 --format json --out assets.json

# С альтернативными биржами:
python -m src.main --limit 10 --alt --format csv --out assets.csv

# С изменёнными весами приоритета:
python -m src.main --limit 15 --w-volume 0.4 --w-mcap 0.4 --w-exchanges 0.15 --w-chains 0.05
