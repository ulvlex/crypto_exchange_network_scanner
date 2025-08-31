import logging
from typing import Any, Dict, List, Tuple

from src.external.coingecko_client import CoinGeckoClient
from src.services.constants import (
    MIN_INTERVAL_SEC,
    TARGET_EXCHANGES,
    W_CHAINS,
    W_EXCH,
    W_MCAP,
    W_RECENT,
    W_VOLUME,
)
from src.services.priority import compute_priority
from src.services.utils import (
    clean_exchange_id,
    is_ticker_ok,
    throttle,
    uniq_keep_order,
)

logger = logging.getLogger(__name__)


class AssetService:
    """
    Сервис для получения и обработки информации об активах
    """

    def __init__(self):
        self.client = CoinGeckoClient()

    def get_volume_top_assets(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Топ активов по 24h объёму (CoinGecko)
        """
        try:
            rows = self.client.top_by_volume(limit=limit)
            out: List[Dict[str, Any]] = []
            for i, r in enumerate(rows, start=1):
                out.append(
                    {
                        "id": r.get("id"),
                        "symbol": (r.get("symbol") or "").upper(),
                        "name": r.get("name"),
                        "total_volume": r.get("total_volume"),
                        "market_cap_rank": r.get("market_cap_rank"),
                        "volume_rank": i,
                        "recent_rank": None,  # пока нет
                    }
                )
            logger.info("Получено %s активов (топ по объёму)", len(out))
            return out
        except Exception as e:
            logger.error("Не удалось получить топ активов: %s", e)
            return []

    def get_date_listing_top_assets(self, limit: int = 100):
        """
        Получаем топ-100 активов по дате листинга
        """
        logger.info("Топ по дате листинга пропущен (нет публичного эндпоинта в CoinGecko)")
        return []

    def _collect_networks(self, coin_id: str) -> List[str]:
        """Сети всегда тянем из /coins/{id} keys(platforms)"""
        try:
            platforms = self.client.coin_platforms(coin_id) or {}
            nets = list(platforms.keys())
            if nets:
                logger.info("Сети %s: %d", coin_id, len(nets))
            else:
                logger.info("Сети %s: platforms пуст (нативная монета или нет данных)", coin_id)
            return nets
        except Exception as e:
            logger.warning("Сети: ошибка для %s: %s", coin_id, e)
            return []

    def _collect_exchanges(self, coin_id: str, include_alternatives: bool) -> Tuple[List[str], List[str]]:
        """Биржи: целевые через фильтр; альтернативы — опционально (1 страница)."""
        targets: List[str] = []
        alts: List[str] = []

        # целевые
        try:
            data = self.client.coin_tickers(coin_id, exchange_ids=list(TARGET_EXCHANGES))
            tickers = data.get("tickers", []) if isinstance(data, dict) else []
            seen_t = set()
            for t in tickers:
                if not is_ticker_ok(t):
                    continue
                ex = clean_exchange_id(t.get("market"))
                if ex and ex in TARGET_EXCHANGES and ex not in seen_t:
                    targets.append(ex)
                    seen_t.add(ex)
        except Exception as e:
            logger.warning("Биржи(целевые) %s: %s", coin_id, e)

        # альтернативы
        if include_alternatives:
            try:
                data = self.client.coin_tickers(coin_id, page=1)
                tickers = data.get("tickers", []) if isinstance(data, dict) else []
                seen_a = set()
                for t in tickers:
                    if not is_ticker_ok(t):
                        continue
                    ex = clean_exchange_id(t.get("market"))
                    if ex and ex not in TARGET_EXCHANGES and ex not in seen_a:
                        alts.append(ex)
                        seen_a.add(ex)
            except Exception as e:
                logger.warning("Биржи(альтернативы) %s: %s", coin_id, e)

        logger.info("Биржи %s: целевые=%d, альтернативные=%d", coin_id, len(targets), len(alts))
        return targets, alts

    def get_enriched_assets(
        self,
        limit: int = 10,
        w_volume: float = W_VOLUME,
        w_mcap: float = W_MCAP,
        w_recent: float = W_RECENT,
        w_exchanges: float = W_EXCH,
        w_chains: float = W_CHAINS,
        include_alternatives: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Главный метод:
            берём топ по объёму
            сети: /coins/{id} с tickers=false (только platforms) — для токенов
            биржи: /coins/{id}/tickers?exchange_ids=... (целевые). Альтернативы — опционально page=1
            считаем priority_score
            сортируем по приоритету
        """
        assets = self.get_volume_top_assets(limit=limit)
        enriched: List[Dict[str, Any]] = []

        last_call_t = 0.0
        for a in assets:
            coin_id = a.get("id")
            if not coin_id:
                logger.warning("Пропуск актива без id: %s", a)
                continue

            # тикеры (целевые и, по запросу, альтернативные)
            last_call_t = throttle(last_call_t, MIN_INTERVAL_SEC)
            exchanges, exchanges_alt = self._collect_exchanges(coin_id, include_alternatives=include_alternatives)

            # сети
            last_call_t = throttle(last_call_t, MIN_INTERVAL_SEC)
            networks = self._collect_networks(coin_id)

            item = {
                "id": coin_id,
                "symbol": a.get("symbol") or "",
                "name": a.get("name") or "",
                "total_volume": a.get("total_volume"),
                "market_cap_rank": a.get("market_cap_rank"),
                "exchanges": uniq_keep_order(exchanges),
                "exchanges_alt": uniq_keep_order(exchanges_alt),
                "networks": uniq_keep_order(networks),
                "volume_rank": a.get("volume_rank"),
                "recent_rank": a.get("recent_rank"),
            }

            item["priority_score"] = compute_priority(
                item,
                w_volume=w_volume,
                w_mcap=w_mcap,
                w_recent=w_recent,
                w_exchanges=w_exchanges,
                w_chains=w_chains,
                target_exchanges_count=len(TARGET_EXCHANGES),
            )
            enriched.append(item)

        enriched.sort(key=lambda x: x.get("priority_score") or 0.0, reverse=True)
        logger.info("Готово: рассмотрено %s активов", len(enriched))
        return enriched
