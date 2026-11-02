#!/usr/bin/env python3
"""Adapts the built valkey.io site for this repository's GitHub Pages project site. Not part of the proposed change.

Usage: adapt-build.py <site-dir> <path-prefix>    e.g. website/public /valkey-site-search-preview

The build already uses the preview's base_url, so every get_url() link is right. This step:

1. Prefixes root-relative URLs ("/img/Valkey-logo.svg", "/clients/") in HTML and CSS with the project path, because
   the templates write them for a site at the domain root. That covers attributes (where Zola often writes "/" as
   "&#x2F;"), CSS url() and @import, and the inline fetch("/command-list/") and fetch("/topics-list/") on command
   and docs pages.
2. Points the search box at the index under the project path. Pagefind's component UI otherwise looks for it at
   /pagefind/, which is right on valkey.io but not here.
3. Removes Google Tag Manager, Osano, and the Scarf pixel, so the preview doesn't send page views to the Valkey
   project's analytics.
4. Adds <meta name="robots" content="noindex"> to every page, so the preview doesn't compete with valkey.io in search
   results. robots.txt only counts at the host root, which a project site doesn't control.

It fails if a step finds nothing to change where it expects to, or if a page still mentions a tracker or lacks the
noindex tag afterwards, so a change to the site can't silently undo the adaptation.
"""
import pathlib
import re
import sys

site_dir = pathlib.Path(sys.argv[1])
prefix = sys.argv[2].rstrip("/")

TRACKERS = re.compile(
    r"<script\b[^>]*>(?:(?!</script>).)*?googletagmanager\.com(?:(?!</script>).)*?</script>"
    r"|<script\b[^>]*\bsrc=\"https://cmp\.osano\.com/[^\"]*\"[^>]*>\s*</script>"
    r"|<noscript\b[^>]*>\s*<iframe\b[^>]*googletagmanager\.com[^>]*>\s*</iframe>\s*</noscript>"
    r"|<img\b[^>]*\bsrc=\"https://static\.scarf\.sh/[^\"]*\"[^>]*>",
    re.DOTALL,
)
TRACKER_HOSTS = ("googletagmanager.com", "osano.com", "scarf.sh")

# Zola escapes "/" as "&#x2F;" in values it inserts with {{ }}, so a slash may come in either form.
SLASH = r"(?:/|&#x2F;)"
PREFIX_NAME = re.escape(prefix.lstrip("/"))
# A root-relative URL: one leading slash, not two (protocol-relative), and not already under the prefix.
ROOT_RELATIVE = rf"{SLASH}(?!{SLASH})(?!{PREFIX_NAME}{SLASH})"
ATTRIBUTE = re.compile(rf"(\b(?:href|src|action|poster|srcset|content)=)([\"'])({ROOT_RELATIVE})")
# srcset lists several URLs: "a.png 1x, /b.png 2x".
SRCSET_ITEM = re.compile(rf"(,\s*)({ROOT_RELATIVE})")
CSS_URL = re.compile(rf"(url\(\s*[\"']?)({ROOT_RELATIVE})")
CSS_IMPORT = re.compile(rf"(@import\s+[\"'])({ROOT_RELATIVE})")
REFRESH = re.compile(rf"(content=[\"']\d+;\s*url=)({ROOT_RELATIVE})", re.IGNORECASE)
FETCH = re.compile(rf"(\bfetch\(\s*[\"'])({ROOT_RELATIVE})")

HEAD_OPEN = re.compile(r"<head\b[^>]*>", re.IGNORECASE)
# Zola's redirect pages (aliases) have no <head>; a <meta> right after the doctype still belongs to the implied head.
DOCTYPE = re.compile(r"<!doctype html>", re.IGNORECASE)
NOINDEX = '<meta name="robots" content="noindex">'


def is_fragment(text):
    # /command-list/ and /topics-list/ are bare lists that command and docs pages fetch and insert: not pages.
    return not (HEAD_OPEN.search(text) or DOCTYPE.search(text))


def add_noindex(text):
    if HEAD_OPEN.search(text):
        return HEAD_OPEN.sub(lambda m: m[0] + NOINDEX, text, count=1)
    return DOCTYPE.sub(lambda m: m[0] + NOINDEX, text, count=1)


def adapt_css(text):
    text = CSS_URL.sub(lambda m: m[1] + prefix + m[2], text)
    return CSS_IMPORT.sub(lambda m: m[1] + prefix + m[2], text)


def adapt_html(text):
    text = TRACKERS.sub("", text)
    text = REFRESH.sub(lambda m: m[1] + prefix + m[2], text)
    text = ATTRIBUTE.sub(lambda m: m[1] + m[2] + prefix + m[3], text)
    text = re.sub(r"srcset=\"[^\"]*\"", lambda m: SRCSET_ITEM.sub(lambda n: n[1] + prefix + n[2], m[0]), text)
    text = adapt_css(text)
    text = FETCH.sub(lambda m: m[1] + prefix + m[2], text)
    return text if is_fragment(text) else add_noindex(text)


def point_search_at_index():
    """Returns a problem, or None. The index stays where Pagefind built it; only the search box's setting changes."""
    search_js = site_dir / "assets/js/search.js"
    text = search_js.read_text(encoding="utf-8")
    call = "configureInstance('default', {"
    if call not in text:
        return f"{search_js.relative_to(site_dir)}: no {call} to add the bundle path to"
    search_js.write_text(text.replace(call, f"{call} bundlePath: '{prefix}/pagefind/',", 1), encoding="utf-8")
    return None


changed = 0
problems = []
for path in sorted(site_dir.rglob("*")):
    if not path.is_file() or path.suffix not in (".html", ".css"):
        continue
    text = path.read_text(encoding="utf-8", errors="surrogateescape")
    new = adapt_html(text) if path.suffix == ".html" else adapt_css(text)
    if new != text:
        path.write_text(new, encoding="utf-8", errors="surrogateescape")
        changed += 1
    if path.suffix == ".html":
        name = path.relative_to(site_dir)
        if NOINDEX not in new and not is_fragment(new):
            problems.append(f"{name}: no noindex tag")
        problems += [f"{name}: still mentions {host}" for host in TRACKER_HOSTS if host in new]


search_problem = point_search_at_index()
if search_problem:
    problems.append(search_problem)

print(f"{site_dir}: adapted {changed} files for {prefix}/")
if problems:
    print("\n".join(problems), file=sys.stderr)
    sys.exit(1)
