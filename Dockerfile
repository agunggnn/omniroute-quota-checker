# OmniRoute Quota Checker — MCP server image
#
# Runs the quota inspector as an MCP (stdio) server so Hermes can call it
# as a tool. The OmniRoute SQLite DB is mounted read-only from the host
# (same bind mount the `omniroute` container uses: E:\GitHub\OmniRoute\data).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    OMNIROUTE_DB=/app/data/storage.sqlite

WORKDIR /app

# Copy metadata + source first (hatchling build needs README.md & src)
COPY pyproject.toml uv.lock README.md ./
COPY src ./src

# Install dependencies (better layer caching after the COPY above)
RUN pip install --no-cache-dir uv \
    && uv sync --no-dev --frozen

# The MCP server speaks stdio JSON-RPC. Hermes launches it via:
#   docker run --rm -i -v "E:\GitHub\OmniRoute\data:/app/data:ro" omniroute-quota-mcp
#
# Invoke the venv's python directly rather than `uv run` — `uv run` re-syncs
# against uv.lock (including the dev dependency group) on every start, which
# re-downloads ruff/pygments over the network and adds ~20-30s per call.
ENTRYPOINT [".venv/bin/python", "-m", "omniroute_quota.mcp_server"]
