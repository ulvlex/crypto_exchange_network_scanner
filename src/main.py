import argparse
import csv
import json
import logging

from src.services.asset_service import AssetService
from src.services.utils import normalize_for_csv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Crypto assets collector (CoinGecko only)")
    parser.add_argument("--limit", type=int, default=10, help="Сколько активов взять из топа по объёму")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Формат вывода")
    parser.add_argument("--out", type=str, default="out.json", help="Файл для сохранения")
    parser.add_argument("--w-volume", type=float, default=0.7, help="Вес объёма")
    parser.add_argument("--w-mcap", type=float, default=0.3, help="Вес рыночной капитализации")
    parser.add_argument("--w-recent", type=float, default=0.0, help="Вес новизны (сейчас 0)")
    parser.add_argument("--w-exchanges", type=float, default=0.2, help="Вес покрытых целевых бирж")
    parser.add_argument("--w-chains", type=float, default=0.1, help="Вес сети/мультичейна")
    parser.add_argument(
        "--alt",
        action="store_true",
        help="Собирать альтернативные биржи (по умолчанию выключено — только целевые)",
    )

    args = parser.parse_args()

    svc = AssetService()
    assets = svc.get_enriched_assets(
        limit=args.limit,
        w_volume=args.w_volume,
        w_mcap=args.w_mcap,
        w_recent=args.w_recent,
        w_exchanges=args.w_exchanges,
        w_chains=args.w_chains,
        include_alternatives=args.alt,
    )

    if args.format == "json":
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(assets, f, ensure_ascii=False, indent=2)
        logger.info("Сохранено %s активов в %s (json)", len(assets), args.out)
    else:
        if assets:
            fieldnames = sorted({k for a in assets for k in a.keys()})
            with open(args.out, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=fieldnames)
                w.writeheader()
                for a in assets:
                    w.writerow(normalize_for_csv(a))
            logger.info("Сохранено %s активов в %s (csv)", len(assets), args.out)


if __name__ == "__main__":
    main()
