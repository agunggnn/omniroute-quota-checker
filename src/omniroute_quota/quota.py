from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Quota:
    provider: str
    account: str
    model: str
    remaining: float
    exhausted: bool
    reset_at: str | None
    snapshot_at: str

    @property
    def model_id(self) -> str:
        return f"{self.provider}/{self.model}"


_LATEST_ACTIVE_QUOTAS = """
WITH ranked AS (
    SELECT
        q.*,
        ROW_NUMBER() OVER (
            PARTITION BY q.connection_id, q.window_key
            ORDER BY datetime(q.created_at) DESC, q.id DESC
        ) AS rank
    FROM quota_snapshots AS q
)
SELECT
    ranked.provider,
    COALESCE(pc.name, pc.email, ranked.connection_id) AS account,
    ranked.window_key AS model,
    ranked.remaining_percentage AS remaining,
    ranked.is_exhausted AS exhausted,
    ranked.next_reset_at AS reset_at,
    ranked.created_at AS snapshot_at
FROM ranked
LEFT JOIN provider_connections AS pc ON pc.id = ranked.connection_id
WHERE ranked.rank = 1 AND COALESCE(pc.is_active, 1) = 1
ORDER BY ranked.remaining_percentage DESC, ranked.provider, account, model
"""


def load_latest_quotas(path: str | Path) -> list[Quota]:
    database = Path(path).expanduser()
    if not database.is_file():
        raise FileNotFoundError(f"Database OmniRoute tidak ditemukan: {database}")

    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(_LATEST_ACTIVE_QUOTAS).fetchall()
    except sqlite3.Error as error:
        raise RuntimeError(f"Database OmniRoute tidak kompatibel: {error}") from error
    finally:
        connection.close()

    return [
        Quota(
            provider=row["provider"],
            account=row["account"],
            model=row["model"],
            remaining=float(row["remaining"]),
            exhausted=bool(row["exhausted"]),
            reset_at=row["reset_at"],
            snapshot_at=row["snapshot_at"],
        )
        for row in rows
    ]


@dataclass(frozen=True, slots=True)
class Account:
    id: str
    provider: str
    account: str
    auth_type: str | None
    is_active: bool
    test_status: str | None
    error_code: str | None
    last_error: str | None
    last_error_at: str | None
    backoff_level: int
    rate_limited_until: str | None
    last_used_at: str | None
    created_at: str
    updated_at: str


# Deliberately excludes access_token, refresh_token, api_key, id_token, and
# provider_specific_data — this is a read-only visibility query, never a
# credential export.
_ACCOUNTS_QUERY = """
SELECT
    id,
    provider,
    COALESCE(name, email, id) AS account,
    auth_type,
    is_active,
    test_status,
    error_code,
    last_error,
    last_error_at,
    backoff_level,
    rate_limited_until,
    last_used_at,
    created_at,
    updated_at
FROM provider_connections
ORDER BY provider, account
"""


def list_accounts(path: str | Path) -> list[Account]:
    database = Path(path).expanduser()
    if not database.is_file():
        raise FileNotFoundError(f"Database OmniRoute tidak ditemukan: {database}")

    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(_ACCOUNTS_QUERY).fetchall()
    except sqlite3.Error as error:
        raise RuntimeError(f"Database OmniRoute tidak kompatibel: {error}") from error
    finally:
        connection.close()

    return [
        Account(
            id=row["id"],
            provider=row["provider"],
            account=row["account"],
            auth_type=row["auth_type"],
            is_active=bool(row["is_active"]),
            test_status=row["test_status"],
            error_code=row["error_code"],
            last_error=row["last_error"],
            last_error_at=row["last_error_at"],
            backoff_level=int(row["backoff_level"] or 0),
            rate_limited_until=row["rate_limited_until"],
            last_used_at=row["last_used_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


def _is_real_model(quota: Quota) -> bool:
    metadata_windows = {
        "session",
        "session (5h)",
        "weekly (7d)",
        "credit",
        "chat",
        "completions",
        "premium_interactions",
    }
    return quota.model.lower() not in metadata_windows


def _purpose_score(quota: Quota, purpose: str) -> int:
    model = quota.model.lower()
    if purpose == "coding":
        return sum(term in model for term in ("coding", "code", "flash", "sonnet"))
    if purpose == "reasoning":
        return sum(term in model for term in ("reason", "thinking", "pro", "opus"))
    return 0


def recommend_models(quotas: list[Quota], purpose: str = "general", limit: int = 5) -> list[Quota]:
    candidates = [quota for quota in quotas if _is_real_model(quota) and not quota.exhausted]
    return sorted(
        candidates,
        key=lambda quota: (
            -_purpose_score(quota, purpose),
            -quota.remaining,
            quota.provider,
            quota.model,
        ),
    )[:limit]
