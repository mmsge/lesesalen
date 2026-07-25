"""The guards that stop /api/berik being an open proxy and an XSS delivery route.

These are the tests worth having. If one of them starts failing, something in
the security model has been undone rather than merely refactored.
"""
from __future__ import annotations

import ipaddress

import pytest

from app import netfetch, sanitise


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.5",
        "172.18.0.1",          # the box's own Docker bridge gateway
        "192.168.1.1",
        "169.254.169.254",     # cloud metadata, the classic SSRF payoff
        "100.64.0.1",          # CGNAT
        "0.0.0.0",
        "::1",
        "fd00::1",
        "fe80::1",
        "::ffff:127.0.0.1",    # IPv4-mapped loopback
    ],
)
def test_private_addresses_are_refused(address: str) -> None:
    assert netfetch.address_is_public(ipaddress.ip_address(address)) is False


@pytest.mark.parametrize("address", ["1.1.1.1", "157.180.66.111", "2606:4700::1111"])
def test_public_addresses_are_allowed(address: str) -> None:
    assert netfetch.address_is_public(ipaddress.ip_address(address)) is True


@pytest.mark.parametrize(
    "value",
    [
        "127.0.0.1",
        "192.168.0.1",
        "localhost",           # no dot: not a public DNS name
        "bookwyrm.social:8080",
        "[::1]",
        "",
        "   ",
        "-bad.example",
        "a" * 300 + ".example",
    ],
)
def test_bad_domains_are_rejected(value: str) -> None:
    assert netfetch.normalise_domain(value) is None


def test_good_domains_normalise() -> None:
    assert netfetch.normalise_domain("BookWyrm.Social") == "bookwyrm.social"
    assert netfetch.normalise_domain("https://bookwyrm.social/user/x") == "bookwyrm.social"
    assert netfetch.normalise_domain("example.co.uk.") == "example.co.uk"


def test_url_must_be_https_and_allowlisted() -> None:
    allowed = {"bookwyrm.social"}
    assert netfetch._check_url("https://bookwyrm.social/x", allowed) == "bookwyrm.social"
    for bad in [
        "http://bookwyrm.social/x",          # plaintext
        "https://evil.example/x",            # not on the allowlist
        "https://bookwyrm.social:8443/x",    # non-default port
        "file:///etc/passwd",
        "https://127.0.0.1/x",
    ]:
        with pytest.raises(netfetch.BlockedError):
            netfetch._check_url(bad, allowed)


# ── sanitising ───────────────────────────────────────────────────────────────

def test_script_and_event_handlers_are_stripped() -> None:
    dirty = '<p onclick="steal()">hi</p><script>alert(1)</script>'
    clean = sanitise.clean_html(dirty)
    assert "script" not in clean.lower()
    assert "onclick" not in clean.lower()
    assert "hi" in clean


@pytest.mark.parametrize(
    "dirty",
    [
        '<svg onload="alert(1)"></svg>',
        '<math><mtext><script>alert(1)</script></mtext></math>',
        '<iframe src="https://evil.example"></iframe>',
        '<object data="x"></object>',
        '<embed src="x">',
        '<form action="https://evil.example"><input name="a"></form>',
        '<style>body{display:none}</style>',
        '<img src="x" onerror="alert(1)">',
    ],
)
def test_dangerous_elements_are_excluded(dirty: str) -> None:
    clean = sanitise.clean_html(dirty).lower()
    for tag in ("<svg", "<math", "<iframe", "<object", "<embed", "<form", "<style", "<img"):
        assert tag not in clean
    assert "alert(1)" not in clean


@pytest.mark.parametrize(
    "scheme", ["javascript:alert(1)", "data:text/html,<script>x</script>", "vbscript:msgbox"]
)
def test_dangerous_url_schemes_are_dropped(scheme: str) -> None:
    clean = sanitise.clean_html(f'<a href="{scheme}">click</a>')
    assert "javascript:" not in clean.lower()
    assert "vbscript:" not in clean.lower()
    assert "data:text/html" not in clean.lower()


def test_links_are_forced_safe_and_mastodon_classes_survive() -> None:
    clean = sanitise.clean_html(
        '<p><a href="https://example.com" class="mention">@x</a> '
        '<span class="invisible">https://</span></p>'
    )
    assert 'rel="nofollow noopener noreferrer"' in clean
    assert 'class="mention"' in clean
    assert 'class="invisible"' in clean


def test_clean_text_returns_real_text_not_markup() -> None:
    assert sanitise.clean_text("<b>Tom &amp; Jerry</b>") == "Tom & Jerry"
    assert sanitise.clean_text("<script>alert(1)</script>hei") == "hei"
    assert sanitise.clean_text(None) == ""
