from __future__ import annotations

from apps.sip.collector.mapping import map_article, map_articles, parse_published_at

RUN_ID = "11111111-1111-1111-1111-111111111111"


def _article(**overrides: object) -> dict:
    base = {
        "title": "India, NZ discuss FTA next steps",
        "description": "Officials met to progress trade talks.",
        "url": "https://example.com/article",
        "source": "RNZ Business",
        "published": "2026-07-21 19:32:00+00:00",
        "score": 34,
        "nz_relevance_score": 15,
        "sectors": "Trade and FTA",
    }
    base.update(overrides)
    return base


# ---------- parse_published_at ----------


def test_parse_published_at_handles_rss_style_str_datetime() -> None:
    assert parse_published_at("2026-07-21 19:32:00+00:00") == "2026-07-21T19:32:00+00:00"


def test_parse_published_at_handles_gdelt_seendate() -> None:
    assert parse_published_at("20260721T193200Z") == "2026-07-21T19:32:00+00:00"


def test_parse_published_at_handles_gdelt_compact_no_z() -> None:
    assert parse_published_at("20260721193200") == "2026-07-21T19:32:00"


def test_parse_published_at_returns_none_for_empty() -> None:
    assert parse_published_at("") is None
    assert parse_published_at(None) is None
    assert parse_published_at("   ") is None


def test_parse_published_at_returns_none_for_unrecognised_value() -> None:
    assert parse_published_at("not a date") is None


def test_parse_published_at_returns_none_for_non_string_input() -> None:
    # The agent's output is untrusted external data - a wrong-typed value (e.g. an int from a
    # malformed article) must not raise, just be treated as unparseable.
    assert parse_published_at(20260721193200) is None
    assert parse_published_at(["2026-07-21"]) is None
    assert parse_published_at({"date": "2026-07-21"}) is None


# ---------- map_article ----------


def test_map_article_maps_core_fields() -> None:
    mapped = map_article(_article(), RUN_ID)

    assert mapped.candidate.run_id == RUN_ID
    assert mapped.candidate.headline == "India, NZ discuss FTA next steps"
    assert mapped.candidate.summary == "Officials met to progress trade talks."
    assert mapped.candidate.url == "https://example.com/article"
    assert mapped.candidate.published_at == "2026-07-21T19:32:00+00:00"
    assert mapped.candidate.in_coverage_window is True
    assert mapped.source_name == "RNZ Business"


def test_map_article_leaves_source_id_unset_without_lookup() -> None:
    mapped = map_article(_article(), RUN_ID)
    assert mapped.candidate.source_id is None


def test_map_article_resolves_source_id_from_lookup() -> None:
    lookup = {"RNZ Business": "22222222-2222-2222-2222-222222222222"}
    mapped = map_article(_article(), RUN_ID, source_name_lookup=lookup)
    assert mapped.candidate.source_id == "22222222-2222-2222-2222-222222222222"


def test_map_article_leaves_unmatched_source_unresolved() -> None:
    lookup = {"Some Other Source": "22222222-2222-2222-2222-222222222222"}
    mapped = map_article(_article(), RUN_ID, source_name_lookup=lookup)
    assert mapped.candidate.source_id is None


def test_map_article_does_not_score_or_route() -> None:
    mapped = map_article(_article(), RUN_ID)

    assert mapped.candidate.nz_relevance is None
    assert mapped.candidate.india_relevance is None
    assert mapped.candidate.member_relevance is None
    assert mapped.candidate.signal is None
    assert mapped.candidate.confidence is None
    assert mapped.candidate.duplicate_of is None
    assert mapped.candidate.included is None
    assert mapped.candidate.reason is None
    assert mapped.candidate.proposed_routing is None


def test_map_article_treats_blank_url_and_description_as_absent() -> None:
    mapped = map_article(_article(url="", description=""), RUN_ID)
    assert mapped.candidate.url is None
    assert mapped.candidate.summary is None


def test_map_articles_maps_each_item_in_order() -> None:
    articles = [_article(title="First"), _article(title="Second")]
    mapped = map_articles(articles, RUN_ID)

    assert [item.candidate.headline for item in mapped] == ["First", "Second"]
