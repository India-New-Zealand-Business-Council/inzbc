from __future__ import annotations

from apps.sip.collector.dedupe import find_duplicate_of, normalize_title, normalize_url


def test_normalize_url_lowercases_strips_and_drops_trailing_slash() -> None:
    assert normalize_url("  HTTPS://Example.com/Article/  ") == "https://example.com/article"


def test_normalize_url_none_for_empty() -> None:
    assert normalize_url(None) is None
    assert normalize_url("") is None


def test_normalize_title_collapses_whitespace_and_lowercases() -> None:
    assert normalize_title("  India,  NZ   discuss FTA \n next steps ") == "india, nz discuss fta next steps"


def test_find_duplicate_of_matches_by_url() -> None:
    existing = [{"id": "existing-1", "url": "https://example.com/a", "headline": "Old headline"}]
    article = {"url": "https://example.com/a/", "title": "Different headline entirely"}

    assert find_duplicate_of(article, existing) == "existing-1"


def test_find_duplicate_of_falls_back_to_title_when_no_url_match() -> None:
    existing = [{"id": "existing-2", "url": "https://example.com/other", "headline": "Same story here"}]
    article = {"url": "https://example.com/different", "title": "Same story here"}

    assert find_duplicate_of(article, existing) == "existing-2"


def test_find_duplicate_of_returns_none_when_nothing_matches() -> None:
    existing = [{"id": "existing-3", "url": "https://example.com/x", "headline": "Unrelated"}]
    article = {"url": "https://example.com/y", "title": "Also unrelated"}

    assert find_duplicate_of(article, existing) is None


def test_find_duplicate_of_handles_empty_existing_list() -> None:
    article = {"url": "https://example.com/a", "title": "Title"}
    assert find_duplicate_of(article, []) is None
