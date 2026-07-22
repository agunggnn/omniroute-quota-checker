"""OmniRoute Quota Checker — MCP server.

Exposes the quota inspector as an MCP (Model Context Protocol) server so
Hermes can call it as a tool. The CLI already lives in ``cli.py``; this
module reuses the same core (``load_latest_quotas`` / ``recommend_models``
from :mod:`omniroute_quota.quota`) and returns structured JSON instead of
human text.

Run it inside the ``omniroute-quota-mcp`` Docker image:

    python -m omniroute_quota.mcp_server

It speaks the MCP stdio transport (JSON-RPC 2.0) using the ``mcp`` SDK's
``FastMCP`` helper. Two environment overrides:

    OMNIROUTE_DB   path to the OmniRoute storage.sqlite (default:
                   E:\\GitHub\\OmniRoute\\data\\storage.sqlite, which the
                   Docker image overrides to /app/data/storage.sqlite)
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .quota import Account, Quota, list_accounts, load_latest_quotas, recommend_models

DEFAULT_DB = Path(r"E:\GitHub\OmniRoute\data\storage.sqlite")

mcp = FastMCP("omniroute-quota")


def _resolve_db() -> Path:
    raw = os.environ.get("OMNIROUTE_DB")
    if raw:
        return Path(raw).expanduser()
    return DEFAULT_DB


def _quota_to_dict(quota: Quota) -> dict:
    return {
        "provider": quota.provider,
        "account": quota.account,
        "model": quota.model,
        "model_id": quota.model_id,
        "remaining_pct": round(quota.remaining, 2),
        "exhausted": quota.exhausted,
        "reset_at": quota.reset_at,
        "snapshot_at": quota.snapshot_at,
    }


def _account_to_dict(account: Account) -> dict:
    return {
        "id": account.id,
        "provider": account.provider,
        "account": account.account,
        "auth_type": account.auth_type,
        "is_active": account.is_active,
        "test_status": account.test_status,
        "error_code": account.error_code,
        "last_error": account.last_error,
        "last_error_at": account.last_error_at,
        "backoff_level": account.backoff_level,
        "rate_limited_until": account.rate_limited_until,
        "last_used_at": account.last_used_at,
        "created_at": account.created_at,
        "updated_at": account.updated_at,
    }


@mcp.tool()
def omni_quota_check(
    purpose: str = "general",
    limit: int = 5,
    db: str | None = None,
    include_all: bool = False,
) -> str:
    """Inspect OmniRoute quota snapshots and recommend models with quota left.

    Reads the latest quota snapshot from the OmniRoute SQLite database,
    distinguishes real models from router/alias/account metadata windows,
    and returns the recommended models with the most remaining quota for a
    given work purpose.

    Args:
        purpose: Work type for ranking — one of "general", "coding"
            (prefers coding/flash/sonnet models), or "reasoning"
            (prefers reasoning/thinking/pro/opus models). Default "general".
        limit: How many recommended models to return (1-50). Default 5.
        db: Optional path to OmniRoute storage.sqlite. Defaults to
            OMNIROUTE_DB env, then the image default
            /app/data/storage.sqlite.
        include_all: When true, also return the full list of all active
            quota windows (including account metadata) under the
            "all_quotas" key.

    Returns:
        JSON string with keys: database, snapshot_at, purpose, limit,
        recommendations (list of model dicts), and optionally all_quotas.
        On error, a JSON object with an "error" key.
    """
    if purpose not in ("general", "coding", "reasoning"):
        return json.dumps(
            {"error": f"invalid purpose '{purpose}'; expected general|coding|reasoning"}
        )
    if limit < 1:
        limit = 1
    if limit > 50:
        limit = 50

    db_path = Path(db).expanduser() if db else _resolve_db()

    try:
        quotas = load_latest_quotas(db_path)
    except (FileNotFoundError, RuntimeError) as error:
        return json.dumps({"error": str(error), "database": str(db_path)})

    snapshot_at = max((q.snapshot_at for q in quotas), default=None)
    recommendations = recommend_models(quotas, purpose, limit)

    result: dict = {
        "database": str(db_path),
        "snapshot_at": snapshot_at,
        "purpose": purpose,
        "limit": limit,
        "recommendations": [_quota_to_dict(q) for q in recommendations],
    }

    if include_all:
        result["all_quotas"] = [_quota_to_dict(q) for q in quotas]

    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def omni_account_status(
    db: str | None = None,
    active_only: bool = False,
) -> str:
    """List OmniRoute provider account connections and their health status.

    Read-only visibility into the accounts/connections OmniRoute has
    configured — which provider they belong to, whether they're active,
    and their last known test/error state. Never returns credentials
    (access tokens, refresh tokens, API keys are excluded from the query
    entirely). This tool cannot enable, disable, add, or remove accounts.

    Args:
        db: Optional path to OmniRoute storage.sqlite. Defaults to
            OMNIROUTE_DB env, then the image default
            /app/data/storage.sqlite.
        active_only: When true, only return accounts where is_active is
            true. Default false (returns all accounts).

    Returns:
        JSON string with keys: database, accounts (list of account status
        dicts). On error, a JSON object with an "error" key.
    """
    db_path = Path(db).expanduser() if db else _resolve_db()

    try:
        accounts = list_accounts(db_path)
    except (FileNotFoundError, RuntimeError) as error:
        return json.dumps({"error": str(error), "database": str(db_path)})

    if active_only:
        accounts = [a for a in accounts if a.is_active]

    result = {
        "database": str(db_path),
        "accounts": [_account_to_dict(a) for a in accounts],
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
