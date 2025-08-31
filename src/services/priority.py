from typing import Any, Dict


def _norm_rank(rank: int | None, max_rank: int = 100) -> float:
    """
    Нормируем позицию (1..max_rank) в шкалу 0..1: 1 -> ~1.0, max_rank -> ~0.01, None -> 0.0
    """
    if not rank or rank < 1:
        return 0.0
    return 1.0 - (rank - 1) / max_rank


def compute_priority(
    asset: Dict[str, Any],
    w_volume: float,
    w_mcap: float,
    w_recent: float,
    w_exchanges: float,
    w_chains: float,
    target_exchanges_count: int,
) -> float:
    """Счиатем приоритетность по касмтоной формуле"""
    volume_score = _norm_rank(asset.get("volume_rank"))
    mcap_score = _norm_rank(asset.get("market_cap_rank"))
    recent_score = _norm_rank(asset.get("recent_rank"))  # пока None = 0.0
    ex = asset.get("exchanges") or []
    exchange_score = min(len(set(ex)) / max(target_exchanges_count, 1), 1.0)
    chains = asset.get("networks") or []
    chains_score = min(len(set(chains)) / 5.0, 1.0)

    score = (
        w_volume * volume_score
        + w_mcap * mcap_score
        + w_recent * recent_score
        + w_exchanges * exchange_score
        + w_chains * chains_score
    )
    return round(float(score), 4)
