"""Dashboard front-end assets: every module and stylesheet the page loads exists, and the shell keeps its contract."""

from __future__ import annotations

import re
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"
IMPORT_RE = re.compile(r"""from\s+['"](\.{1,2}/[^'"]+)['"]""")


def test_every_imported_module_exists():
    for js in WEB.rglob("*.js"):
        for rel in IMPORT_RE.findall(js.read_text(encoding="utf-8")):
            assert (js.parent / rel).resolve().is_file(), f"{js.relative_to(WEB)} imports missing {rel}"


def test_index_references_existing_assets():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    for href in re.findall(r'(?:href|src)="((?:css|js)/[^"]+)"', html):
        assert (WEB / href).is_file(), href


def test_shell_contract():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    for needle in ('id="loader"', 'id="landing"', 'id="landing-tpl"', 'id="app"', 'id="sb-toggle"', 'id="sidebar-nav"',
                   'id="sidebar-foot"', 'class="skip-link"', 'name="viewport"', 'lang="en"'):
        assert needle in html, needle
    assert html.count("<h1") == 1                      # one h1 in the document: the landing template's (pages add their own)


def test_themes_define_the_same_tokens():
    tokens = (WEB / "css" / "tokens.css").read_text(encoding="utf-8")
    light = tokens.split(':root[data-theme="dark"]')[0]
    dark = tokens.split(':root[data-theme="dark"]')[1].split("}")[0]
    names = set(re.findall(r"(--cv-[a-z-]+):", light))
    assert names and names <= set(re.findall(r"(--cv-[a-z-]+):", dark)), "dark theme is missing canvas tokens"
    for must in ("--ground", "--surface", "--text", "--muted", "--border", "--data", "--primary"):
        assert must in light and must in dark


def test_no_external_requests_in_the_front_end():
    for f in list(WEB.rglob("*.js")) + list(WEB.rglob("*.css")) + [WEB / "index.html"]:
        text = f.read_text(encoding="utf-8")
        for url in re.findall(r"""(?:src|href|url\()\s*=?\s*["']?(https?://[^"')\s>]+)""", text):
            assert (
                "github.com/shrirajagarkar30/graphpulse" in url
                or "w3.org" in url
                or "unpkg.com" in url
                or "openstreetmap.org" in url
            ), f"{f.name}: external request {url}"
