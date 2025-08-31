import logging
import time
from typing import Any, Dict, Iterable, List, Tuple

logger = logging.getLogger(__name__)


def throttle(last_call_t: float, min_interval_sec: float) -> float:
    """Простой троттлинг между API-вызовами"""
    now = time.monotonic()
    dt = now - last_call_t
    if dt < min_interval_sec:
        time.sleep(min_interval_sec - dt)
        now = time.monotonic()
    return now


def is_ticker_ok(t: Dict[str, Any]) -> bool:
    """
    Фильтр мусорных тикеров: должен быть market
    """
    if not isinstance(t, dict):
        return False
    market = t.get("market") or {}
    if not market:
        return False
    return True


def clean_exchange_id(market: Dict[str, Any]) -> str:
    """Достаём нормализованный идентификатор биржи: identifier или name"""
    if not isinstance(market, dict):
        return ""
    ex = market.get("identifier") or market.get("name") or ""
    return ex.strip().lower()


def uniq_keep_order(items: Iterable[str]) -> List[str]:
    """Уникальные элементы, сохраняя порядок"""
    seen, out = set(), []
    for x in items:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out


def normalize_for_csv(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Нормализация записи для CSV: списки -> 'a;b;c', None -> ''"""
    row = {}
    for k, v in obj.items():
        if isinstance(v, list):
            row[k] = ";".join(map(str, v))
        elif v is None:
            row[k] = ""
        else:
            row[k] = v
    return row
