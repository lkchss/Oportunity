"""Shared pytest fixtures for the law suite.

Deliberately minimal: the law product is pure stdlib + Flask + committed JSON
data — no LLM SDKs, no network at test time. (The monorepo this was extracted
from carried ship-product SDK stubs and platformdirs isolation here; none of
that applies to any law test, so it did not come along.)
"""
