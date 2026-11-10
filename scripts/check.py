#!/usr/bin/env python3
"""Site checks: internal links, em dashes, emojis, JSON-LD validity, required meta, feed shape.
Run after build:  python scripts/check.py   (exit code 1 on any failure)
"""
import json
import pathlib
import re
import sys
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKIP = {".git", "scripts", "data", ".claude"}
errors = []


class P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ld, self._in_ld, self.meta, self.title = [], [], False, {}, 0

    def handle_starttag(self, tag, a):
        a = dict(a)
        if tag in ("a", "link") and a.get("href"):
            self.links.append(a["href"])
        if tag in ("img", "script") and a.get("src"):
            self.links.append(a["src"])
        if tag == "script" and a.get("type") == "application/ld+json":
            self._in_ld = True
            self.ld.append("")
        if tag == "meta":
            self.meta[a.get("name") or a.get("property")] = a.get("content")
        if tag == "title":
            self.title += 1

    def handle_endtag(self, tag):
        if tag == "script":
            self._in_ld = False

    def handle_data(self, d):
        if self._in_ld:
            self.ld[-1] += d


def target_exists(href):
    path = href.split("#")[0].split("?")[0]
    if not path:
        return True
    p = ROOT / path.lstrip("/")
    return p.is_file() or (p / "index.html").is_file()


EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
pages = [p for p in ROOT.rglob("*.html") if not (set(p.relative_to(ROOT).parts) & SKIP)]
titles, descs = {}, {}
for f in pages:
    rel = f.relative_to(ROOT).as_posix()
    text = f.read_text(encoding="utf-8")
    if "—" in text:
        errors.append(f"{rel}: em dash")
    if EMOJI.search(text):
        errors.append(f"{rel}: emoji")
    if "G-QX8J421S0J" not in text.split("<meta", 1)[0]:
        errors.append(f"{rel}: GTM snippet not right after <head>")
    p = P()
    p.feed(text)
    for h in p.links:
        if h.startswith(("http://", "https://", "mailto:", "#", "data:")):
            continue
        if not target_exists(h):
            errors.append(f"{rel}: broken link {h}")
    if rel == "404.html":
        continue
    for blob in p.ld:
        try:
            json.loads(blob)
        except ValueError as e:
            errors.append(f"{rel}: bad JSON-LD {e}")
    types = {json.loads(b).get("@type") for b in p.ld}
    for need in ("WebSite", "BreadcrumbList", "Article"):
        if need not in types:
            errors.append(f"{rel}: missing {need} JSON-LD")
    if rel.startswith("reviews/") and rel.count("/") == 2 and "Review" not in types:
        errors.append(f"{rel}: missing Review JSON-LD")
    if rel.startswith("news/") and rel.count("/") == 2 and "NewsArticle" not in types:
        errors.append(f"{rel}: missing NewsArticle JSON-LD")
    for m in ("description", "og:title", "og:image"):
        if not p.meta.get(m):
            errors.append(f"{rel}: missing meta {m}")
    t = re.search(r"<title>(.*?)</title>", text).group(1)
    if t in titles:
        errors.append(f"{rel}: duplicate title with {titles[t]}")
    titles[t] = rel
    d = p.meta.get("description")
    if d in descs:
        errors.append(f"{rel}: duplicate description with {descs[d]}")
    descs[d] = rel

feed = json.loads((ROOT / "news" / "feed.json").read_text(encoding="utf-8"))
if feed.get("version") != "https://jsonfeed.org/version/1.1":
    errors.append("feed.json: wrong version")
for it in feed["items"]:
    for k in ("id", "title", "url", "date_published", "summary", "image", "tags"):
        if not it.get(k):
            errors.append(f"feed.json: item {it.get('id')} missing {k}")
    img = it["image"].replace("https://streaming.samcbarth.com", "")
    if not target_exists(img):
        errors.append(f"feed.json: missing image file {img}")
for f in ("sitemap.xml", "robots.txt", "rss.xml", "llms.txt", "CNAME"):
    if not (ROOT / f).is_file():
        errors.append(f"missing {f}")

print(f"Checked {len(pages)} HTML pages.")
if errors:
    print("\n".join(errors))
    sys.exit(1)
print("All checks passed.")
