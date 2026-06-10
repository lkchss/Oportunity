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


class TestRefreshOnReingest:
    def test_known_url_with_new_deadline_refreshes_row(self, cfg, tmp_path):
        conn = connect(cfg)
        _ingest(cfg, conn, [{"title": "F", "url": "https://x.com/f",
                             "fit_grade": "B", "deadline": "Passed (~Mar 1)"}],
                tmp_path, name="b1.json")
        _ingest(cfg, conn, [{"title": "F", "url": "https://x.com/f/",
                             "fit_grade": "A", "deadline": "Mar 1, 2027"}],
                tmp_path, name="b2.json")
        rows = conn.execute(
            "SELECT fit_grade, deadline, status FROM opportunities").fetchall()
        assert rows == [("A", "Mar 1, 2027", "open")]

    def test_known_url_unchanged_is_skipped_not_refreshed(self, cfg, tmp_path, capsys):
        conn = connect(cfg)
        items = [{"title": "G", "url": "https://x.com/g", "deadline": "Rolling"}]
        _ingest(cfg, conn, items, tmp_path, name="b1.json")
        capsys.readouterr()
        _ingest(cfg, conn, items, tmp_path, name="b2.json")
        assert "0 new, 0 refreshed" in capsys.readouterr().out

    def test_status_only_change_refreshes(self, cfg, tmp_path):
        conn = connect(cfg)
        _ingest(cfg, conn, [{"title": "I", "url": "https://x.com/i",
                             "deadline": "Rolling"}], tmp_path, name="b1.json")
        _ingest(cfg, conn, [{"title": "I", "url": "https://x.com/i",
                             "status": "passed"}], tmp_path, name="b2.json")
        row = conn.execute(
            "SELECT status, deadline FROM opportunities").fetchone()
        assert row == ("passed", "Rolling")  # empty deadline must not clobber

    def test_refresh_prints_old_to_new(self, cfg, tmp_path, capsys):
        conn = connect(cfg)
        _ingest(cfg, conn, [{"title": "J", "url": "https://x.com/j",
                             "deadline": "Passed (~Mar 1)"}], tmp_path,
                name="b1.json")
        capsys.readouterr()
        _ingest(cfg, conn, [{"title": "J", "url": "https://x.com/j",
                             "deadline": "Mar 1, 2027"}], tmp_path, name="b2.json")
        out = capsys.readouterr().out
        assert "Passed (~Mar 1)" in out and "Mar 1, 2027" in out


class TestRecheck:
    def test_old_unverified_open_item_flagged(self, cfg, tmp_path, capsys):
        conn = connect(cfg)
        _ingest(cfg, conn, [
            {"title": "Old", "url": "https://x.com/old", "deadline": "Rolling"},
            {"title": "Gone", "url": "https://x.com/gone",
             "deadline": "Passed (~Jan 1)"},
        ], tmp_path)
        conn.execute("UPDATE opportunities SET found_at='2020-01-01T00:00:00', "
                     "checked_at=NULL")
        conn.commit()
        capsys.readouterr()
        lists.recheck(conn, age_days=180)
        out = capsys.readouterr().out
        assert "Old" in out
        assert "Gone" not in out  # passed items belong to --stale, not recheck

    def test_regrade_counts_as_verification(self, cfg, tmp_path, capsys):
        conn = connect(cfg)
        _ingest(cfg, conn, [{"title": "H", "url": "https://x.com/h",
                             "deadline": "Rolling"}], tmp_path)
        conn.execute("UPDATE opportunities SET found_at='2020-01-01T00:00:00', "
                     "checked_at=NULL")
        conn.commit()
        rg = tmp_path / "rg.json"
        rg.write_text(json.dumps({"H": ["A", "Rolling"]}), encoding="utf-8")
        regrade(conn, rg)
        capsys.readouterr()
        lists.recheck(conn, age_days=180)
        assert "Nothing unverified" in capsys.readouterr().out


class TestDryStreak:
    def test_dry_warning_after_streak(self, cfg, tmp_path, capsys):
        conn = connect(cfg)
        _ingest(cfg, conn, [{"title": "S", "url": "https://x.com/s"}],
                tmp_path, name="b0.json", bucket="vc")
        for i in range(lists.DRY_STREAK):
            _ingest(cfg, conn, [{"title": "S", "url": "https://x.com/s"}],
                    tmp_path, name=f"b{i + 1}.json", bucket="vc")
        assert "looks DRY" in capsys.readouterr().out
        capsys.readouterr()
        lists.stats(conn)
        assert "DRY" in capsys.readouterr().out

    def test_no_warning_at_streak_minus_one(self, cfg, tmp_path, capsys):
        conn = connect(cfg)
        _ingest(cfg, conn, [{"title": "S", "url": "https://x.com/s"}],
                tmp_path, name="b0.json", bucket="vc")
        for i in range(lists.DRY_STREAK - 1):
            _ingest(cfg, conn, [{"title": "S", "url": "https://x.com/s"}],
                    tmp_path, name=f"b{i + 1}.json", bucket="vc")
        assert "looks DRY" not in capsys.readouterr().out

    def test_refresh_only_batches_are_not_dry(self, cfg, tmp_path, capsys):
        conn = connect(cfg)
        _ingest(cfg, conn, [{"title": "S", "url": "https://x.com/s",
                             "deadline": "Mar 1, 2026"}],
                tmp_path, name="b0.json", bucket="vc")
        for i in range(lists.DRY_STREAK + 1):
            _ingest(cfg, conn, [{"title": "S", "url": "https://x.com/s",
                                 "deadline": f"Mar 1, {2027 + i}"}],
                    tmp_path, name=f"b{i + 1}.json", bucket="vc")
        out = capsys.readouterr().out
        assert "looks DRY" not in out
        capsys.readouterr()
        lists.stats(conn)
        assert "DRY" not in capsys.readouterr().out


class TestQueriesLog:
    def test_queries_stored_and_reported(self, cfg, tmp_path, capsys):
        conn = connect(cfg)
        _ingest(cfg, conn, [{"title": "Q", "url": "https://x.com/q"}],
                tmp_path, bucket="vc", queries="fellowship 2026 | open call vc")
        capsys.readouterr()
        lists.batches(conn)
        out = capsys.readouterr().out
        assert "fellowship 2026" in out
        assert "open call vc" in out


class TestTitlesFilter:
    def test_category_substring_filter(self, cfg, tmp_path, capsys):
        conn = connect(cfg)
        _ingest(cfg, conn, [
            {"title": "V", "url": "https://x.com/v", "category": "VC/Startup"},
            {"title": "P", "url": "https://x.com/p", "category": "Policy"},
        ], tmp_path)
        capsys.readouterr()
        lists.dump_titles(conn, category="VC")
        out = capsys.readouterr().out
        assert "V" in out and "https://x.com/p" not in out


class TestSources:
    def test_seed_list_and_check(self, cfg, tmp_path, capsys):
        conn = connect(cfg)
        lists.seed_sources(cfg, conn)
        capsys.readouterr()
        lists.list_sources(conn)
        out = capsys.readouterr().out
        assert "80,000 Hours" in out and "NEVER" in out
        lists.mark_checked(conn, ["https://jobs.80000hours.org/"])
        capsys.readouterr()
        lists.list_sources(conn)
        out = capsys.readouterr().out
        assert out.count("NEVER") == len(lists.SEED_SOURCES["jobs"]) - 1

    def test_seed_idempotent(self, cfg, tmp_path):
        conn = connect(cfg)
        lists.seed_sources(cfg, conn)
        lists.seed_sources(cfg, conn)
        n = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        assert n == len(lists.SEED_SOURCES["jobs"])

    def test_mark_checked_unknown_url_warns(self, cfg, tmp_path, capsys):
        conn = connect(cfg)
        lists.mark_checked(conn, ["https://nope.example.com/"])
        out = capsys.readouterr().out
        assert "no source" in out and "0 source(s)" in out

    def test_reregister_source_preserves_last_checked(self, cfg, tmp_path):
        conn = connect(cfg)
        lists.add_source(conn, "https://hub.example.com/", "Hub", "", "aggregator", "")
        lists.mark_checked(conn, ["https://hub.example.com/"])
        lists.add_source(conn, "https://hub.example.com/", "Hub v2", "", "x", "")
        label, last = conn.execute(
            "SELECT label, last_checked FROM sources").fetchone()
        assert label == "Hub v2" and last is not None


class TestCanaries:
    def test_recall_hit_and_miss(self, cfg, tmp_path, capsys):
        conn = connect(cfg)
        _ingest(cfg, conn, [{"title": "Found", "url": "https://x.com/found"}],
                tmp_path)
        lists.canary_add(conn, "https://x.com/found/?utm_source=nl", "Found",
                         "newsletter")
        lists.canary_add(conn, "https://x.com/missed", "Missed", "friend")
        capsys.readouterr()
        lists.canary_check(conn)
        out = capsys.readouterr().out
        assert "Recall: 1/2" in out and "Missed" in out

    def test_found_at_sticks(self, cfg, tmp_path, capsys):
        conn = connect(cfg)
        _ingest(cfg, conn, [{"title": "Found", "url": "https://x.com/found"}],
                tmp_path)
        lists.canary_add(conn, "https://x.com/found", "Found", "nl")
        lists.canary_check(conn)
        capsys.readouterr()
        lists.canary_check(conn)
        assert "Recall: 1/1" in capsys.readouterr().out


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
