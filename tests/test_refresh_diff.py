"""
Unit tests for law/data/refresh.py — diff-report logic only.

All tests operate on in-memory dataset dicts; no file I/O, no network.
"""

import pytest
from law.data.refresh import compute_diff


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_dataset(*schools: dict) -> dict:
    return {"schools": list(schools)}


def _school(sid: str, **fields) -> dict:
    base: dict = {
        "id": sid,
        "name": f"School {sid}",
        "lsat_50": 160,
        "acceptance_rate": 0.3,
    }
    base.update(fields)
    return base


# ---------------------------------------------------------------------------
# schools_added / schools_removed
# ---------------------------------------------------------------------------

class TestSchoolsAddedRemoved:
    def test_identical_datasets_no_adds_or_removes(self):
        s = _school("alpha")
        d = _make_dataset(s)
        diff = compute_diff(d, d)
        assert diff["schools_added"] == []
        assert diff["schools_removed"] == []

    def test_school_added(self):
        before = _make_dataset(_school("alpha"))
        after = _make_dataset(_school("alpha"), _school("beta"))
        diff = compute_diff(before, after)
        assert diff["schools_added"] == ["beta"]
        assert diff["schools_removed"] == []

    def test_school_removed(self):
        before = _make_dataset(_school("alpha"), _school("beta"))
        after = _make_dataset(_school("alpha"))
        diff = compute_diff(before, after)
        assert diff["schools_added"] == []
        assert diff["schools_removed"] == ["beta"]

    def test_school_added_and_removed(self):
        before = _make_dataset(_school("alpha"), _school("old"))
        after = _make_dataset(_school("alpha"), _school("new"))
        diff = compute_diff(before, after)
        assert diff["schools_added"] == ["new"]
        assert diff["schools_removed"] == ["old"]

    def test_added_ids_are_sorted(self):
        before = _make_dataset()
        after = _make_dataset(_school("z-school"), _school("a-school"), _school("m-school"))
        diff = compute_diff(before, after)
        assert diff["schools_added"] == ["a-school", "m-school", "z-school"]

    def test_empty_before_all_added(self):
        before = _make_dataset()
        after = _make_dataset(_school("x"), _school("y"))
        diff = compute_diff(before, after)
        assert set(diff["schools_added"]) == {"x", "y"}
        assert diff["schools_removed"] == []

    def test_empty_after_all_removed(self):
        before = _make_dataset(_school("x"), _school("y"))
        after = _make_dataset()
        diff = compute_diff(before, after)
        assert diff["schools_added"] == []
        assert set(diff["schools_removed"]) == {"x", "y"}


# ---------------------------------------------------------------------------
# field_change_counts
# ---------------------------------------------------------------------------

class TestFieldChangeCounts:
    def test_no_changes(self):
        s = _school("alpha", lsat_50=160)
        diff = compute_diff(_make_dataset(s), _make_dataset(s.copy()))
        assert diff["field_change_counts"] == {}

    def test_single_field_changed_single_school(self):
        before = _make_dataset(_school("alpha", lsat_50=160))
        after = _make_dataset(_school("alpha", lsat_50=162))
        diff = compute_diff(before, after)
        assert diff["field_change_counts"]["lsat_50"] == 1

    def test_multiple_schools_same_field_changed(self):
        before = _make_dataset(_school("a", lsat_50=155), _school("b", lsat_50=160))
        after = _make_dataset(_school("a", lsat_50=156), _school("b", lsat_50=161))
        diff = compute_diff(before, after)
        assert diff["field_change_counts"]["lsat_50"] == 2

    def test_field_added_to_school(self):
        """A field present in after but absent in before counts as a change."""
        before = _make_dataset(_school("alpha"))
        after = _make_dataset(_school("alpha", new_field=42))
        diff = compute_diff(before, after)
        assert "new_field" in diff["field_change_counts"]

    def test_field_removed_from_school(self):
        """A field present in before but absent in after counts as a change."""
        before = _make_dataset(_school("alpha", old_field=99))
        after = _make_dataset(_school("alpha"))
        diff = compute_diff(before, after)
        assert "old_field" in diff["field_change_counts"]

    def test_notable_fields_excluded(self):
        """notable_alumni, notable_faculty, wiki_title must never appear in diff."""
        before = _make_dataset(_school("alpha", notable_alumni=[], notable_faculty=[]))
        after = _make_dataset(_school("alpha", notable_alumni=[{"name": "X"}], notable_faculty=[]))
        diff = compute_diff(before, after)
        assert "notable_alumni" not in diff["field_change_counts"]
        assert "notable_faculty" not in diff["field_change_counts"]
        assert "wiki_title" not in diff["field_change_counts"]

    def test_newly_added_schools_not_counted_in_field_changes(self):
        """Schools that are new (not in before) should not inflate field_change_counts."""
        before = _make_dataset(_school("alpha"))
        after = _make_dataset(_school("alpha"), _school("beta", lsat_50=170))
        diff = compute_diff(before, after)
        # beta is new — its fields should NOT appear in field_change_counts
        # (they appear in schools_added instead)
        assert diff["schools_added"] == ["beta"]
        # lsat_50 only changed on common schools (none for 'beta' since it's new)
        assert "lsat_50" not in diff["field_change_counts"]


# ---------------------------------------------------------------------------
# field_examples
# ---------------------------------------------------------------------------

class TestFieldExamples:
    def test_examples_contain_before_and_after(self):
        before = _make_dataset(_school("alpha", lsat_50=160))
        after = _make_dataset(_school("alpha", lsat_50=162))
        diff = compute_diff(before, after)
        ex = diff["field_examples"]["lsat_50"]
        assert len(ex) == 1
        assert ex[0]["id"] == "alpha"
        assert ex[0]["before"] == 160
        assert ex[0]["after"] == 162

    def test_examples_capped_at_max_examples(self):
        n = 10
        before = _make_dataset(*[_school(f"s{i}", lsat_50=160) for i in range(n)])
        after = _make_dataset(*[_school(f"s{i}", lsat_50=161) for i in range(n)])
        diff = compute_diff(before, after, max_examples=3)
        assert len(diff["field_examples"]["lsat_50"]) == 3

    def test_custom_max_examples_zero(self):
        before = _make_dataset(_school("a", lsat_50=160))
        after = _make_dataset(_school("a", lsat_50=161))
        diff = compute_diff(before, after, max_examples=0)
        assert diff["field_examples"].get("lsat_50", []) == []

    def test_no_examples_when_no_changes(self):
        s = _school("alpha")
        diff = compute_diff(_make_dataset(s), _make_dataset(s.copy()))
        assert diff["field_examples"] == {}


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_both_empty_datasets(self):
        diff = compute_diff(_make_dataset(), _make_dataset())
        assert diff["schools_added"] == []
        assert diff["schools_removed"] == []
        assert diff["field_change_counts"] == {}

    def test_none_values_handled(self):
        """None is a valid field value; None -> 42 is a change."""
        before = _make_dataset(_school("alpha", bar_pass=None))
        after = _make_dataset(_school("alpha", bar_pass=0.85))
        diff = compute_diff(before, after)
        assert diff["field_change_counts"]["bar_pass"] == 1

    def test_value_unchanged_none_to_none(self):
        before = _make_dataset(_school("alpha", bar_pass=None))
        after = _make_dataset(_school("alpha", bar_pass=None))
        diff = compute_diff(before, after)
        assert "bar_pass" not in diff["field_change_counts"]

    def test_custom_notable_fields_excluded(self):
        """Caller can extend the excluded set."""
        before = _make_dataset(_school("alpha", custom_scraped="old"))
        after = _make_dataset(_school("alpha", custom_scraped="new"))
        diff_default = compute_diff(before, after)
        assert "custom_scraped" in diff_default["field_change_counts"]

        diff_excluded = compute_diff(
            before, after,
            notable_fields=frozenset({"custom_scraped"})
        )
        assert "custom_scraped" not in diff_excluded["field_change_counts"]
