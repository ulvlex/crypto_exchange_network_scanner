import logging
import os
import time
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

RETRYABLE_5XX = {500, 502, 503, 504}


class CoinGeckoClient:
    """
    Клиент для работы с CoinGecko
    """

    def __init__(
        self,
        timeout: Optional[int] = 30,
        max_retries_5xx: int = 5,
        retry_after_cap: float = 100.0,  # верхний предел ожидания по Retry-After (сек)
        fallback_429_waits: tuple[float, float, float] = (20.0, 20.0, 20.0),
    ):
        self.api_key = os.getenv("CG_API_KEY")
        self.base_url = "https://api.coingecko.com/api/v3"
        self.timeout = timeout
        self.max_retries_5xx = max_retries_5xx
        self.retry_after_cap = retry_after_cap
        self.fallback_429_waits = fallback_429_waits

    def _default_headers(self) -> dict:
        headers = {
            "Accept": "application/json",
            "User-Agent": "cg-client-simple/1.0",
        }
        if self.api_key:
            headers["x-cg-demo-api-key"] = self.api_key
        return headers

    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """
        Простой цикл ретраев:
            retry на Timeout/ConnectionError
            retry на HTTP 429/5xx
            Retry-After, если есть
            экспонента 1,2,4,8,16 (сек)
        """
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop("headers", {})
        headers.update(self._default_headers())

        tries_5xx = 0
        waits_5xx = 1.0  # старт экспоненты
        tries_429_fallback = 0

        while True:
            try:
                resp = requests.request(method, url, headers=headers, timeout=self.timeout, **kwargs)

                # успех
                if resp.status_code < 400:
                    try:
                        return resp.json()
                    except ValueError:
                        logger.error("Invalid JSON from %s: %s", url, resp.text[:300])
                        raise

                # 429 (rate limit)
                if resp.status_code == 429:
                    ra = resp.headers.get("Retry-After")
                    if ra:
                        try:
                            sec = float(ra)
                            if sec > 0:
                                sleep_for = min(sec, self.retry_after_cap)
                                logger.warning("HTTP 429 %s — Retry-After=%.1fs (waiting)", url, sleep_for)
                                time.sleep(sleep_for)

                                continue
                        except Exception:
                            pass

                    # без Retry-After — 3 фикспаузы по 20с
                    if tries_429_fallback >= len(self.fallback_429_waits):
                        logger.error("HTTP 429 on %s %s: %s", method, url, resp.text[:300])
                        resp.raise_for_status()
                    wait = self.fallback_429_waits[tries_429_fallback]
                    logger.warning("HTTP 429 %s — no Retry-After, sleeping %.1fs", url, wait)
                    time.sleep(wait)
                    tries_429_fallback += 1
                    continue

                # 5xx — экспоненциальный ретрай
                if resp.status_code in RETRYABLE_5XX:
                    if tries_5xx >= self.max_retries_5xx:
                        logger.error("HTTP %s on %s %s: %s", resp.status_code, method, url, resp.text[:300])
                        resp.raise_for_status()
                    logger.warning(
                        "HTTP %s %s — retry %d/%d in %.1fs",
                        resp.status_code,
                        url,
                        tries_5xx + 1,
                        self.max_retries_5xx,
                        waits_5xx,
                    )
                    time.sleep(waits_5xx)
                    tries_5xx += 1
                    waits_5xx = min(waits_5xx * 2.0, 60.0)
                    continue

                # прочие 4xx — без ретраев
                logger.error("HTTP %s on %s %s: %s", resp.status_code, method, url, resp.text[:400])
                resp.raise_for_status()

            except (requests.Timeout, requests.ConnectionError) as e:
                # сеть — как 5xx
                if tries_5xx >= self.max_retries_5xx:
                    logger.error("Network error on %s %s: %s (no more retries)", method, url, e)
                    raise
                logger.warning(
                    "Network error on %s %s — retry %d/%d in %.1fs",
                    method,
                    url,
                    tries_5xx + 1,
                    self.max_retries_5xx,
                    waits_5xx,
                )
                time.sleep(waits_5xx)
                tries_5xx += 1
                waits_5xx = min(waits_5xx * 2.0, 60.0)

    def top_by_volume(self, limit: int = 100, vs_currency: str = "usd"):
        """
        GET /coins/markets?order=volume_desc
        Возвращает список словарей, каждый словарь описывает один актив (монету/токен)
        Топ-100 монет по объёму торгов за сутки
        """
        params = {
            "vs_currency": vs_currency,
            "order": "volume_desc",
            "per_page": limit,
            "page": 1,
        }
        return self._request("GET", "/coins/markets", params=params)

    def coin_platforms(self, coin_id: str):
        """
        GET /coins/{id} -> поле platforms: {network_name: contract_address}
        Возвращает словарь с описанием монеты, поле platforms - сети, где доступен актив
        """
        params = {
            "localization": "false",
            "tickers": "false",
            "market_data": "false",
            "community_data": "false",
            "developer_data": "false",
            "sparkline": "false",
        }
        data = self._request("GET", f"/coins/{coin_id}", params=params)
        return data.get("platforms") or {}

    def coin_tickers(self, coin_id: str, exchange_ids: Optional[List[str]] = None, page: int = 1):
        """
        GET /coins/{id}/tickers[?exchange_ids=binance,bybit,kucoin]&page=N
        Возвращает список бирж, где доступен актив
        """
        params: Dict[str, Any] = {"page": page}
        if exchange_ids:
            params["exchange_ids"] = ",".join(exchange_ids)

        return self._request("GET", f"/coins/{coin_id}/tickers", params=params)
