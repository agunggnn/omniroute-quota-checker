# OmniRoute Quota Checker

CLI lokal untuk membaca snapshot quota OmniRoute, membedakan alias/router dari model nyata, dan merekomendasikan model dengan sisa quota terbanyak.

## Quick start

```bash
uv sync --dev
uv run omni-quota --db "E:\GitHub\OmniRoute\data\storage.sqlite" --purpose coding
```

Jika `--db` tidak diberikan, CLI mencoba `OMNIROUTE_DB`, lalu lokasi default `E:\GitHub\OmniRoute\data\storage.sqlite`.

## Pilihan purpose

- `coding`: prioritaskan model coding/flash
- `reasoning`: prioritaskan model pro/reasoning/thinking
- `general`: urutkan berdasarkan quota tersisa

## Validasi

```bash
uv run pytest
uv run ruff check .
```
