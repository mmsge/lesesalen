"""Parsing BookWyrm ActivityPub objects into the five card kinds."""
from __future__ import annotations

import pytest

from app import enrich

HOST = "bookwyrm.social"


def test_review_becomes_a_review_card() -> None:
    parsed = enrich.parse_object(
        {
            "id": "https://bookwyrm.social/user/x/review/1",
            "type": "Review",
            "name": "A quiet triumph",
            "rating": 4.0,
            "content": "<p>Rather good.</p>",
            "inReplyToBook": "https://bookwyrm.social/book/9",
        },
        HOST,
    )
    assert parsed["slag"] == enrich.KIND_REVIEW
    assert parsed["tittel"] == "A quiet triumph"
    assert parsed["vurdering"] == 4.0
    assert parsed["bok_url"] == "https://bookwyrm.social/book/9"


def test_rating_without_prose_is_a_library_slip() -> None:
    parsed = enrich.parse_object(
        {"type": "Rating", "rating": 3.5, "inReplyToBook": "https://bookwyrm.social/book/9"},
        HOST,
    )
    assert parsed["slag"] == enrich.KIND_RATING
    assert parsed["vurdering"] == 3.5


def test_review_with_only_a_rating_is_reclassified() -> None:
    parsed = enrich.parse_object(
        {"type": "Review", "rating": 5, "content": "", "inReplyToBook": "https://bookwyrm.social/book/9"},
        HOST,
    )
    assert parsed["slag"] == enrich.KIND_RATING


def test_quotation_keeps_quote_and_position() -> None:
    parsed = enrich.parse_object(
        {
            "type": "Quotation",
            "quote": "<p>The sea is a library.</p>",
            "position": 143,
            "positionMode": "page",
            "inReplyToBook": "https://bookwyrm.social/book/9",
        },
        HOST,
    )
    assert parsed["slag"] == enrich.KIND_QUOTATION
    assert "library" in parsed["sitat"]
    assert parsed["posisjon"] == 143
    assert parsed["posisjonsmodus"] == "side"


def test_percentage_position_mode() -> None:
    parsed = enrich.parse_object(
        {"type": "Comment", "content": "<p>hm</p>", "position": 40, "positionMode": "pct",
         "inReplyToBook": "https://bookwyrm.social/book/9"},
        HOST,
    )
    assert parsed["posisjonsmodus"] == "prosent"


@pytest.mark.parametrize(
    "phrase,expected",
    [
        ("Markus wants to read <a>Book</a>", "vil-lesa"),
        ("Markus started reading <a>Book</a>", "byrja"),
        ("Markus finished reading <a>Book</a>", "ferdig"),
        ("Markus stopped reading <a>Book</a>", "slutta"),
    ],
)
def test_reading_status_is_read_from_the_generated_prose(phrase: str, expected: str) -> None:
    parsed = enrich.parse_object(
        {
            "type": "GeneratedNote",
            "content": f"<p>{phrase}</p>",
            "tag": [{"type": "Edition", "href": "https://bookwyrm.social/book/9"}],
        },
        HOST,
    )
    assert parsed["slag"] == enrich.KIND_READING_STATUS
    assert parsed["status"] == expected
    assert parsed["bok_url"] == "https://bookwyrm.social/book/9"


def test_unrecognised_reading_prose_degrades_rather_than_breaks() -> None:
    parsed = enrich.parse_object(
        {"type": "GeneratedNote", "content": "<p>Markus har gjort noko rart</p>"}, HOST
    )
    assert parsed["slag"] == enrich.KIND_READING_STATUS
    assert parsed["status"] is None


def test_book_tag_on_another_host_is_ignored() -> None:
    parsed = enrich.parse_object(
        {
            "type": "GeneratedNote",
            "content": "<p>x finished reading y</p>",
            "tag": [{"type": "Edition", "href": "https://evil.example/book/9"}],
        },
        HOST,
    )
    assert parsed["bok_url"] is None


def test_non_book_note_is_not_a_book_post() -> None:
    assert enrich.parse_object({"type": "Note", "content": "<p>hello</p>"}, HOST) is None
    assert enrich.parse_object({"type": "Announce"}, HOST) is None


def test_content_is_sanitised_on_the_way_out() -> None:
    parsed = enrich.parse_object(
        {
            "type": "Comment",
            "content": '<p>hi</p><script>alert(1)</script>',
            "summary": "<b>spoiler</b>",
            "sensitive": True,
            "inReplyToBook": "https://bookwyrm.social/book/9",
        },
        HOST,
    )
    assert "script" not in parsed["innhald"].lower()
    assert parsed["aatvaring"] == "spoiler"
    assert parsed["sensitiv"] is True


def test_out_of_range_ratings_are_dropped() -> None:
    for value in (-1, 6, "many", None, True):
        parsed = enrich.parse_object(
            {"type": "Review", "rating": value, "content": "<p>x</p>",
             "inReplyToBook": "https://bookwyrm.social/book/9"},
            HOST,
        )
        assert parsed["vurdering"] is None


# ── the pure representation, as third parties actually receive it ────────────
#
# These fixtures are the real shapes observed from bookwyrm.social: `type` is
# always "Note", and the object kind is only recoverable from the URI.

PURE_STATUS_URI = "https://bookwyrm.social/user/mvrkws/generatednote/12091719"
PURE_COMMENT_URI = "https://bookwyrm.social/user/mvrkws/comment/11996174"
PURE_REVIEW_URI = "https://bookwyrm.social/user/mvrkws/review/99"
PURE_QUOTE_URI = "https://bookwyrm.social/user/mvrkws/quotation/98"


def test_uri_segment_classifies_when_type_is_a_bare_note() -> None:
    parsed = enrich.parse_object(
        {
            "id": PURE_STATUS_URI,
            "type": "Note",
            "content": '<p>Markus started reading <a href="https://bookwyrm.social/book/2346620">x</a></p>',
            "tag": [{"type": "Edition", "href": "https://bookwyrm.social/book/2346620"}],
        },
        HOST,
        PURE_STATUS_URI,
    )
    assert parsed["slag"] == enrich.KIND_READING_STATUS
    assert parsed["status"] == "byrja"


def test_reading_status_field_beats_the_prose() -> None:
    """`readingStatus` is machine-readable; the regex is only the fallback."""
    parsed = enrich.parse_object(
        {
            "id": PURE_COMMENT_URI.replace("comment", "generatednote"),
            "type": "Note",
            "readingStatus": "stopped-reading",
            "content": "<p>Markus started reading something</p>",
            "inReplyToBook": "https://bookwyrm.social/book/9",
        },
        HOST,
        PURE_STATUS_URI,
    )
    assert parsed["status"] == "slutta"


@pytest.mark.parametrize(
    "field,expected",
    [("to-read", "vil-lesa"), ("reading", "byrja"), ("read", "ferdig"), ("stopped-reading", "slutta")],
)
def test_every_reading_status_field_value_maps(field: str, expected: str) -> None:
    parsed = enrich.parse_object(
        {"type": "Note", "readingStatus": field, "content": "<p>x</p>"}, HOST, PURE_STATUS_URI
    )
    assert parsed["status"] == expected


def test_pure_review_name_yields_the_rating_and_the_real_title() -> None:
    parsed = enrich.parse_object(
        {
            "id": PURE_REVIEW_URI,
            "type": "Note",
            "name": 'Review of "Kransen" (4 stars): Eit år i eit menneskeliv',
            "content": "<p>God.</p>",
            "inReplyToBook": "https://bookwyrm.social/book/9",
        },
        HOST,
        PURE_REVIEW_URI,
    )
    assert parsed["slag"] == enrich.KIND_REVIEW
    assert parsed["vurdering"] == 4.0
    assert parsed["tittel"] == "Eit år i eit menneskeliv"


def test_pure_quotation_promotes_content_to_the_quote() -> None:
    parsed = enrich.parse_object(
        {
            "id": PURE_QUOTE_URI,
            "type": "Note",
            "content": "<p>Havet er eit bibliotek.</p>",
            "inReplyToBook": "https://bookwyrm.social/book/9",
        },
        HOST,
        PURE_QUOTE_URI,
    )
    assert parsed["slag"] == enrich.KIND_QUOTATION
    assert "bibliotek" in parsed["sitat"]


def test_book_link_is_recovered_from_the_prose_when_there_is_no_field() -> None:
    """A reading status carries neither inReplyToBook nor, sometimes, a tag."""
    parsed = enrich.parse_object(
        {
            "type": "Note",
            "content": '<p>x finished <a href="https://bookwyrm.social/book/2346620">y</a></p>',
        },
        HOST,
        PURE_STATUS_URI,
    )
    assert parsed["bok_url"] == "https://bookwyrm.social/book/2346620"


def test_book_link_in_prose_on_another_host_is_still_ignored() -> None:
    parsed = enrich.parse_object(
        {"type": "Note", "content": '<p><a href="https://evil.example/book/1">y</a></p>'},
        HOST,
        PURE_STATUS_URI,
    )
    assert parsed["bok_url"] is None


@pytest.mark.parametrize(
    "uri,expected",
    [
        (PURE_REVIEW_URI, enrich.KIND_REVIEW),
        (PURE_QUOTE_URI, enrich.KIND_QUOTATION),
        (PURE_COMMENT_URI, enrich.KIND_COMMENT),
        (PURE_STATUS_URI, enrich.KIND_READING_STATUS),
        ("https://bookwyrm.social/user/x/rating/1", enrich.KIND_RATING),
        ("https://mastodon.social/users/x/statuses/1", None),
    ],
)
def test_kind_from_uri(uri: str, expected) -> None:
    assert enrich.kind_from_uri(uri) == expected
