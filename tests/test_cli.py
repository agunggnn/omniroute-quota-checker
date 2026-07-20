from pathlib import Path

from test_quota import make_db

from omniroute_quota.cli import run


def test_cli_prints_ranked_models(tmp_path: Path, capsys) -> None:
    path = tmp_path / "storage.sqlite"
    make_db(path)

    exit_code = run(["--db", str(path), "--purpose", "coding", "--limit", "2"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "100.00%" in output
    assert "antigravity/gemini-3.5-flash-high" in output
    assert "Rekomendasi coding" in output
