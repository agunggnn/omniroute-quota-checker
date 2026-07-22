import sqlite3
from pathlib import Path

from omniroute_quota.quota import list_accounts, load_latest_quotas, recommend_models


def make_db(path: Path) -> None:
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE provider_connections (
            id TEXT PRIMARY KEY, provider TEXT, name TEXT, email TEXT, is_active INTEGER,
            auth_type TEXT, test_status TEXT, error_code TEXT, last_error TEXT,
            last_error_at TEXT, backoff_level INTEGER, rate_limited_until TEXT,
            last_used_at TEXT, created_at TEXT, updated_at TEXT
        );
        CREATE TABLE quota_snapshots (
            id INTEGER PRIMARY KEY, provider TEXT, connection_id TEXT, window_key TEXT,
            remaining_percentage REAL, is_exhausted INTEGER, next_reset_at TEXT,
            raw_data TEXT, created_at TEXT
        );
        INSERT INTO provider_connections VALUES
          ('a', 'antigravity', 'primary', 'a@example.com', 1,
           'oauth', 'active', NULL, NULL, NULL, 0, NULL, NULL,
           '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z'),
          ('b', 'codex', 'codex', 'b@example.com', 1,
           'oauth', 'active', NULL, NULL, NULL, 0, NULL, NULL,
           '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z'),
          ('c', 'claude', 'disabled', 'c@example.com', 0,
           'apikey', 'expired', 'unrecoverable_refresh_error',
           'Refresh token consumed', '2026-01-02T00:00:00Z', 0, NULL, NULL,
           '2026-01-01T00:00:00Z', '2026-01-02T00:00:00Z');
        INSERT INTO quota_snapshots VALUES
          (1, 'antigravity', 'a', 'gemini-3.5-flash-high',
           40, 0, NULL, NULL, '2026-01-01T00:00:00Z'),
          (2, 'antigravity', 'a', 'gemini-3.5-flash-high',
           100, 0, NULL, NULL, '2026-01-02T00:00:00Z'),
          (3, 'antigravity', 'a', 'gemini-3.1-pro-high',
           90, 0, NULL, NULL, '2026-01-02T00:00:00Z'),
          (4, 'codex', 'b', 'session',
           20, 0, NULL, NULL, '2026-01-02T00:00:00Z'),
          (5, 'claude', 'c', 'weekly',
           100, 0, NULL, NULL, '2026-01-02T00:00:00Z');
        """
    )
    db.commit()
    db.close()


def test_load_latest_active_quota_snapshots(tmp_path: Path) -> None:
    path = tmp_path / "storage.sqlite"
    make_db(path)

    rows = load_latest_quotas(path)

    assert [(r.provider, r.model, r.remaining) for r in rows] == [
        ("antigravity", "gemini-3.5-flash-high", 100.0),
        ("antigravity", "gemini-3.1-pro-high", 90.0),
        ("codex", "session", 20.0),
    ]


def test_recommend_models_prefers_real_models_and_requested_purpose(tmp_path: Path) -> None:
    path = tmp_path / "storage.sqlite"
    make_db(path)
    rows = load_latest_quotas(path)

    coding = recommend_models(rows, purpose="coding", limit=2)
    reasoning = recommend_models(rows, purpose="reasoning", limit=1)

    assert [r.model for r in coding] == ["gemini-3.5-flash-high", "gemini-3.1-pro-high"]
    assert reasoning[0].model == "gemini-3.1-pro-high"


def test_list_accounts_returns_status_without_credentials(tmp_path: Path) -> None:
    path = tmp_path / "storage.sqlite"
    make_db(path)

    accounts = list_accounts(path)

    assert [(a.provider, a.account, a.is_active) for a in accounts] == [
        ("antigravity", "primary", True),
        ("claude", "disabled", False),
        ("codex", "codex", True),
    ]
    disabled = next(a for a in accounts if a.provider == "claude")
    assert disabled.test_status == "expired"
    assert disabled.error_code == "unrecoverable_refresh_error"
    assert not hasattr(disabled, "access_token")
