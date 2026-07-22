# OmniRoute Quota Checker

CLI lokal (dan sekarang MCP server) untuk membaca snapshot quota OmniRoute,
membedakan alias/router dari model nyata, dan merekomendasikan model dengan
sisa quota terbanyak.

Ada dua cara pakai:

1. **CLI** — jalan langsung via `uv`.
2. **MCP server (Docker)** — di-container, lalu didaftarkan ke Hermes sebagai
   tool yang bisa dipanggil langsung.

## 1. CLI (uv)

```bash
uv sync --dev
uv run omni-quota --db "E:\GitHub\OmniRoute\data\storage.sqlite" --purpose coding
```

Jika `--db` tidak diberikan, CLI mencoba `OMNIROUTE_DB`, lalu lokasi default
`E:\GitHub\OmniRoute\data\storage.sqlite`.

### Pilihan purpose

- `coding`: prioritaskan model coding/flash
- `reasoning`: prioritaskan model pro/reasoning/thinking
- `general`: urutkan berdasarkan quota tersisa

```bash
uv run omni-quota --purpose coding --limit 5
uv run omni-quota --purpose reasoning --limit 3
uv run omni-quota --all
```

## 2. MCP server (Docker + Hermes)

Build image:

```bash
docker build -t omniroute-quota-mcp .
# atau: docker compose build
```

Jalankan manual (stdio) untuk verifikasi:

```bash
docker run --rm -i -v "E:\GitHub\OmniRoute\data:/app/data:ro" omniroute-quota-mcp
```

Daftarkan ke Hermes (`config.yaml` → `mcp_servers`):

```yaml
mcp_servers:
  omni-quota:
    enabled: true
    command: docker
    args:
      - run
      - --rm
      - -i
      - -v
      - "E:\\GitHub\\OmniRoute\\data:/app/data:ro"
      - omniroute-quota-mcp
    env: {}
```

Setelah itu Hermes punya dua tool:

- `omni_quota_check` — parameter `purpose` (general|coding|reasoning), `limit`,
  `db`, dan `include_all`.
- `omni_account_status` — visibilitas read-only ke akun/koneksi provider
  OmniRoute (aktif/nonaktif, status test, error terakhir). Parameter `db` dan
  `active_only`. Tidak pernah mengembalikan token/API key, dan tidak bisa
  mengaktifkan/menonaktifkan/menambah/menghapus akun.

## Validasi (dev)

```bash
uv run pytest
uv run ruff check .
```
