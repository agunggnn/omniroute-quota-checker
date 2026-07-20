from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .quota import Quota, load_latest_quotas, recommend_models

DEFAULT_DB = Path(r"E:\GitHub\OmniRoute\data\storage.sqlite")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Cek quota model OmniRoute dan rekomendasikan model yang masih longgar."
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path(os.environ.get("OMNIROUTE_DB", DEFAULT_DB)),
        help="Path storage.sqlite OmniRoute",
    )
    parser.add_argument(
        "--purpose",
        choices=("general", "coding", "reasoning"),
        default="general",
        help="Jenis pekerjaan untuk rekomendasi",
    )
    parser.add_argument("--limit", type=int, default=5, help="Jumlah rekomendasi")
    parser.add_argument(
        "--all", action="store_true", help="Tampilkan semua window quota, termasuk metadata akun"
    )
    return parser


def _line(quota: Quota) -> str:
    reset = quota.reset_at or "-"
    return f"{quota.remaining:6.2f}%  {quota.model_id:<48} reset {reset}"


def run(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.limit < 1:
        print("error: --limit minimal 1", file=sys.stderr)
        return 2

    try:
        quotas = load_latest_quotas(args.db)
    except (FileNotFoundError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"Database: {args.db}")
    print(f"Snapshot terbaru: {max((q.snapshot_at for q in quotas), default='-')}")

    if args.all:
        print("\nSemua quota aktif:")
        for quota in quotas:
            print(_line(quota))

    recommendations = recommend_models(quotas, args.purpose, args.limit)
    print(f"\nRekomendasi {args.purpose}:")
    if not recommendations:
        print("Tidak ada model aktif dengan snapshot quota yang dapat direkomendasikan.")
        return 1
    for index, quota in enumerate(recommendations, start=1):
        print(f"{index}. {_line(quota)}")
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
