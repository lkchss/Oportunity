"""Tests for mvp/lists.py — unified list CLI (ingest, dedupe, status, regrade)."""
import json
import sqlite3
from pathlib import Path

import pytest

from mvp import lists
from mvp.lists import ListCfg, connect, infer_status, ingest, norm_url, regrade


@pytest.fixture()
def cfg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ListCfg:
    monkeypatch.setattr(lists, "INGESTED_DIR", tmp_path / "ingested")
    return ListCfg(
        "jobs", tmp_path / "t.db", tmp_path / "t.csv", "job", "jobs", "Jobs",
        lists.LISTS["jobs"].csv_header,
    )


def _ingest(cfg: ListCfg, conn: sqlite3.Connection, items: list[dict],
            tmp_path: Path, name: str = "b.json", **kw) -> None:
    p = tmp_path / name
    p.write_text(json.dumps(items), encoding="utf-8")
    ingest(cfg, conn, p, **kw)


class TestNormUrl:
    def test_strips_tracking_params_fragment_and_slash(self):
        assert norm_url("HTTPS://Example.COM/a/b/?utm_campaign=z&q=1#frag") == \
            "https://example.com/a/b?q=1"

    def test_equivalent_urls_collapse(self):
        variants = [
            "https://example.com/x",
            "https://EXAMPLE.com/x/",
            "https://example.com/x?utm_source=tw",
            "https://example.com/x#section",
        ]
        assert len({norm_url(u) for u in variants}) == 1

    def test_real_query_params_kept(self):
        assert "id=7" in norm_url("https://example.com/x?id=7&utm_medium=m")


class TestInferStatus:
    def test_explicit_wins(self):
        assert infer_status("Rolling", "passed") == "passed"

    def test_heuristics(self):
        assert infer_status("Passed (~Apr 30; annual)") == "passed"
        assert infer_status("Rolling (city cohorts)") == "rolling"
        assert infer_status("Sep 7, 2026") == "open"
        assert infer_status("") == "unknown"
        assert infer_status(None) == "unknown"


class TestIngest:
    def test_grade_at_ingest_and_dedupe(self, cfg, tmp_path):
        conn = connect(cfg)
        _ingest(cfg, conn, [
            {"title": "A", "url": "https://x.com/a", "fit_grade": "A+",
             "deadline": "Rolling", "category": "VC"},
            {"title": "A dup", "url": "https://X.com/a/?utm_source=s"},
        ], tmp_path)
        rows = conn.execute(
            "SELECT title, fit_grade, status, kind FROM opportunities").fetchall()
        assert rows == [("A", "A+", "rolling", "job")]

    def test_bad_grade_stored_ungraded(self, cfg, tmp_path):
        conn = connect(cfg)
        _ingest(cfg, conn, [{"title": "B", "url": "https://x.com/b",
                             "fit_grade": "Z+"}], tmp_path)
        assert conn.execute("SELECT fit_grade FROM opportunities").fetchone() == ("",)

    def test_search_log_and_archive(self, cfg, tmp_path):
        conn = connect(cfg)
        _ingest(cfg, conn, [{"title": "C", "url": "https://x.com/c"}],
                tmp_path, bucket="vc")
        assert conn.execute(
            "SELECT bucket, n_found, n_new FROM search_log").fetchone() == ("vc", 1, 1)
        assert not (tmp_path / "b.json").exists()
        assert (tmp_path / "ingested" / "b.json").exists()


class TestRegrade:
    def test_updates_and_warns_unmatched(self, cfg, tmp_path, capsys):
        conn = connect(cfg)
        _ingest(cfg, conn, [{"title": "D", "url": "https://x.com/d"}], tmp_path)
        rg = tmp_path / "rg.json"
        rg.write_text(json.dumps({"D": ["B+", "Passed (annual)"],
                                  "Ghost": ["A", "x"]}), encoding="utf-8")
        regrade(conn, rg)
        assert conn.execute(
            "SELECT fit_grade, status FROM opportunities").fetchone() == ("B+", "passed")
        assert "Ghost" in capsys.readouterr().out


class TestStatusBackfill:
    def test_legacy_db_gets_status_column_backfilled(self, tmp_path, cfg):
        legacy = sqlite3.connect(cfg.db)
        legacy.execute("CREATE TABLE opportunities (url TEXT PRIMARY KEY, title TEXT, "
                       "summary TEXT, why_match TEXT, category TEXT, found_at TEXT, "
                       "fit_grade TEXT, deadline TEXT, kind TEXT)")
        legacy.execute("INSERT INTO opportunities (url, title, deadline) VALUES "
                       "('https://x.com/e', 'E', 'Passed (~Jun 1; annual)')")
        legacy.commit()
        legacy.close()
        conn = connect(cfg)
        assert conn.execute("SELECT status FROM opportunities").fetchone() == ("passed",)
