#!/usr/bin/env python3
"""Static build for streaming.samcbarth.com (Streaming Price Check).

Sources of truth:
  data/services.json   service plans, prices, facts (+ "checked" date)
  data/compare.json    X vs Y pages
  data/best.json       "best streaming service for ..." pages
  data/devices.json    streaming device guides
  news/stories/*.json  one file per news story

Run:  python build.py      (regenerates every page, feeds, sitemap, images)
Ad / affiliate ids live in assets/config.js and are applied in the browser, so no rebuild is needed for those.
"""
import datetime as dt
import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
BASE = "https://streaming.samcbarth.com"
SITE = "Streaming Price Check"
NEWS_BRAND = "The Stream Desk"
AUTHOR = {"@type": "Person", "name": "Sam Barth", "url": "https://samcbarth.com"}
LAUNCH = "2026-11-09"

GTM = '''<script async src="https://www.googletagmanager.com/gtag/js?id=G-QX8J421S0J"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-QX8J421S0J');
</script>
<!-- monetag -->
<script src="https://5gvci.com/act/files/tag.min.js?z=12242938" data-cfasync="false" async></script>
<script>(function(s){s.dataset.zone='12242939',s.src='https://nap5k.com/tag.min.js'})([document.documentElement, document.body].filter(Boolean).pop().appendChild(document.createElement('script')))</script>
<script>(function(s){s.dataset.zone='12242940',s.src='https://n6wxm.com/vignette.min.js'})([document.documentElement, document.body].filter(Boolean).pop().appendChild(document.createElement('script')))</script>'''

NETWORK = [
    ("realestate", "Real Estate"), ("tools", "Tools"), ("games", "Games"), ("streaming", "Streaming"),
    ("homerepair", "Home Repair"), ("deals", "Deals"), ("news", "News"),
]
NAV = [("/reviews/", "Reviews"), ("/compare/", "Compare"), ("/best/", "Best of"),
       ("/calculator/", "Calculator"), ("/devices/", "Devices"), ("/news/", "News")]


def load(name):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


SVC_DATA = load("services.json")
CHECKED = SVC_DATA["checked"]
SERVICES = SVC_DATA["services"]
SVC = {s["slug"]: s for s in SERVICES}
PAIRS = load("compare.json")["pairs"]
BEST = load("best.json")["pages"]
DEVICES = load("devices.json")["devices"]
STORIES = sorted(
    (json.loads(p.read_text(encoding="utf-8")) for p in (ROOT / "news" / "stories").glob("*.json")),
    key=lambda s: s["date_published"], reverse=True,
)

esc = html.escape
PAGES = []  # (url_path, lastmod) for the sitemap


def human_date(iso):
    d = dt.date.fromisoformat(iso)
    return f"{d.strftime('%B')} {d.day}, {d.year}"


CHECKED_H = human_date(CHECKED)
MONTH_YEAR = dt.date.fromisoformat(CHECKED).strftime("%B %Y")


def money(x):
    if x is None:
        return "n/a"
    return f"${x:,.0f}" if float(x).is_integer() else f"${x:,.2f}"


def pair_slug(p):
    return f"{p['a']}-vs-{p['b']}"


# ---------------------------------------------------------------- images
def ensure_images():
    """Flat WebP share cards (1200x630). Generated once; delete a file to regenerate it."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow not installed; skipping image generation")
        return
    out = ROOT / "assets" / "img"
    out.mkdir(parents=True, exist_ok=True)

    def font(size, bold=True):
        for f in (["arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold else ["arial.ttf", "DejaVuSans.ttf"]):
            try:
                return ImageFont.truetype(f, size)
            except OSError:
                continue
        return ImageFont.load_default()

    def card(name, title, kicker, color):
        path = out / f"{name}.webp"
        if path.exists():
            return
        im = Image.new("RGB", (1200, 630), (0, 0, 0))
        d = ImageDraw.Draw(im)
        for x in range(1200):
            t = x / 1199
            d.line([(x, 0), (x, 559)], fill=(int(154 * t * color), 0, int(255 * t * color)))
        d.rectangle([0, 560, 1200, 630], fill=(25, 25, 25))
        d.rectangle([0, 558, 1200, 560], fill=(154, 0, 255))
        d.text((60, 70), kicker.upper(), font=font(30), fill=(255, 255, 255))
        words, lines, cur = title.split(), [], ""
        f = font(70)
        for w in words:
            test = (cur + " " + w).strip()
            if d.textlength(test, font=f) > 1080:
                lines.append(cur)
                cur = w
            else:
                cur = test
        lines.append(cur)
        y = 150
        for ln in lines[:5]:
            d.text((60, y), ln, font=f, fill=(255, 255, 255))
            y += 84
        d.text((60, 578), "streaming.samcbarth.com", font=font(28, False), fill=(220, 220, 230))
        im.save(path, "WEBP", quality=80)

    card("og-default", "Streaming prices, plans and picks", SITE, 1.0)
    for s in SERVICES:
        card(f"svc-{s['slug']}", f"{s['name']} review: plans and prices", f"Checked {CHECKED_H}", 1.0)
    for p in PAIRS:
        card(f"cmp-{pair_slug(p)}", f"{SVC[p['a']]['name']} vs {SVC[p['b']]['name']}", "Comparison", 0.85)
    for b in BEST:
        card(f"best-{b['slug']}", b["title"], SITE, 0.9)
    for d in DEVICES:
        card(f"dev-{d['slug']}", f"{d['name']} guide", "Streaming devices", 0.8)
    for s in STORIES:
        card(f"news-{s['slug']}", s["title"], f"{NEWS_BRAND} | {human_date(s['date_published'])}", 0.95)
    card("calc", "Cord-cutting cost calculator", SITE, 0.9)


def img(name):
    return f"/assets/img/{name}.webp"


# ---------------------------------------------------------------- layout
def ld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False) + "</script>"


def breadcrumbs_ld(crumbs):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": BASE + u} for i, (n, u) in enumerate(crumbs)]}


def crumbs_html(crumbs):
    if len(crumbs) < 2:
        return ""
    parts = [f'<a href="{u}">{esc(n)}</a>' for n, u in crumbs[:-1]] + [esc(crumbs[-1][0])]
    return '<nav class="crumbs" aria-label="Breadcrumb">' + " / ".join(parts) + "</nav>"


def page(path, title, desc, body, crumbs, *, image=None, ld_extra=(), published=LAUNCH, modified=None,
         og_type="article", section=None):
    url = BASE + path
    image = image or img("og-default")
    modified = modified or CHECKED
    full_title = title if path == "/" else f"{title} | {SITE}"
    lds = [
        {"@context": "https://schema.org", "@type": "WebSite", "name": SITE, "url": BASE + "/",
         "publisher": {"@type": "Organization", "name": SITE, "url": BASE + "/"}},
        breadcrumbs_ld(crumbs),
        {"@context": "https://schema.org", "@type": "Article", "headline": title[:110], "description": desc,
         "url": url, "mainEntityOfPage": url, "image": BASE + image, "datePublished": published,
         "dateModified": modified, "author": AUTHOR,
         "publisher": {"@type": "Organization", "name": SITE, "url": BASE + "/"}},
        *ld_extra,
    ]
    nav = "".join(
        f'<a href="{u}"{" aria-current=\"page\"" if (section == u) else ""}>{n}</a>' for u, n in NAV)
    net = "".join(
        f'<a href="https://{s}.samcbarth.com/"{" aria-current=\"true\"" if s == "streaming" else ""}>{n}</a>'
        for s, n in NETWORK)
    doc = f"""<!doctype html>
<html lang="en">
<head>
{GTM}
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{SITE}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}{image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="color-scheme" content="dark">
<meta name="theme-color" content="#000000">
<link rel="icon" href="/assets/img/favicon.svg" type="image/svg+xml">
<link rel="alternate" type="application/rss+xml" title="{NEWS_BRAND} RSS" href="/rss.xml">
<link rel="alternate" type="application/feed+json" title="{NEWS_BRAND} JSON Feed" href="/news/feed.json">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700&family=Barlow:wght@900&family=Inter:wght@400;500;700&display=swap">
<link rel="stylesheet" href="/assets/style.css">
{"".join(ld(o) for o in lds)}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-head"><div class="wrap head-row">
<a class="brand" href="/"><span class="dot" aria-hidden="true"></span>Streaming Price Check</a>
<nav class="nav" aria-label="Main">{nav}</nav>
</div><div class="sb-band" aria-hidden="true"></div></header>
<main id="main"><div class="wrap">
{crumbs_html(crumbs)}
{body}
</div></main>
<footer class="site-foot"><div class="sb-band" aria-hidden="true"></div><div class="wrap">
<div class="foot-links">
<a href="/about/">About</a><a href="/how-we-research/">How we research</a><a href="/contact/">Contact</a>
<a href="/affiliate-disclosure/">Affiliate disclosure</a><a href="/privacy/">Privacy</a><a href="/terms/">Terms</a>
<a href="/news/feed.json">JSON Feed</a><a href="/rss.xml">RSS</a>
</div>
<p>Prices change often. Every price on this site links to the official page it came from and shows the date it was last checked. Always confirm on the provider's site before you subscribe.</p>
<nav class="network" aria-label="samcbarth.com network"><strong>Network:</strong>{net}</nav>
</div></footer>
<script src="/assets/config.js"></script>
<script src="/assets/site.js" defer></script>
</body>
</html>
"""
    if "—" in doc:
        raise SystemExit(f"Em dash found in {path}; remove it.")
    out = ROOT / path.strip("/") / "index.html" if path != "/" else ROOT / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    PAGES.append((path, modified))


# ---------------------------------------------------------------- fragments
DISCLOSE = ('<p class="disclose">Disclosure: some buttons on this page may become affiliate links. If you sign up '
            'or buy through one, this site may earn a commission at no extra cost to you. It never changes the '
            'prices or facts we list. <a href="/affiliate-disclosure/">Read the affiliate disclosure</a>.</p>')


def svc_btn(s, label=None, ghost=False):
    return (f'<a class="btn{" ghost" if ghost else ""}" data-aff="{s["slug"]}" href="{s["official"]}" '
            f'target="_blank" rel="noopener">{esc(label or "Visit " + s["name"])}</a>')


def amazon_btn(q):
    if not q:
        return ""
    return f'<a class="btn ghost" data-amazon="{esc(q)}" href="#" hidden target="_blank">Check price on Amazon</a>'


def checked_line(s):
    return (f'<p class="source">Prices last checked {CHECKED_H} on '
            f'<a href="{s["pricing_url"]}" target="_blank" rel="noopener">{esc(s["pricing_source"])}</a>. '
            f'Taxes and promotional offers not included.</p>')


def plans_table(s):
    rows = "".join(f'<tr><td>{esc(p["name"])}</td><td class="num">{money(p["monthly"])}/mo</td>'
                   f'<td>{esc(p["note"])}</td></tr>' for p in s["plans"])
    return (f'<div class="tbl-wrap"><table><thead><tr><th>Plan</th><th>Price</th><th>Notes</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>')


def facts_rows(s):
    return [("Cheapest plan", money(s["cheapest"]) + "/mo"),
            ("Ad-free from", money(s["adfree"]) + "/mo" if s["adfree"] else "No ad-free option (live TV)"),
            ("4K", s["four_k"]), ("Live sports", s["live_sports"]), ("Kids and family", s["kids"]),
            ("Local channels", s["locals"]), ("Free trial", s["trial"])]


def svc_card(s, extra=""):
    return (f'<div class="card"><h3><a href="/reviews/{s["slug"]}/">{esc(s["name"])}</a></h3>'
            f'<p>From <span class="price">{money(s["cheapest"])}/mo</span>'
            f'{" &middot; ad-free " + money(s["adfree"]) if s["adfree"] else ""}</p>'
            f'<p>{esc(extra or s["best_for"][0])}</p></div>')


def story_item(s):
    return (f'<li><a href="/news/{s["slug"]}/">{esc(s["title"])}</a>'
            f'<div class="meta">{human_date(s["date_published"])} &middot; Source: {esc(s["source"]["name"])}</div>'
            f'<p>{esc(s["summary"])}</p></li>')


def related_links(links):
    names = {f"/reviews/{s['slug']}/": f"{s['name']} review" for s in SERVICES}
    names.update({f"/compare/{pair_slug(p)}/": f"{SVC[p['a']]['name']} vs {SVC[p['b']]['name']}" for p in PAIRS})
    names.update({f"/best/{b['slug']}/": b["title"] for b in BEST})
    names.update({f"/devices/{d['slug']}/": f"{d['name']} guide" for d in DEVICES})
    return "".join(f'<li><a href="{u}">{esc(names.get(u, u))}</a></li>' for u in links)


METHOD = ('<h2>How was this researched?</h2><p>This page is research-based, not a hands-on test. Prices and plan '
          'details come from each provider\'s own pricing or help pages, checked on the date shown. Feature and '
          'sports details come from provider pages and published news reports, which are linked. We do not '
          'assign star ratings. <a href="/how-we-research/">Read how we research</a>.</p>')


# ---------------------------------------------------------------- pages
def build_reviews():
    for s in SERVICES:
        path = f"/reviews/{s['slug']}/"
        pairs = [p for p in PAIRS if s["slug"] in (p["a"], p["b"])]
        bests = [b for b in BEST if any(pk["slug"] == s["slug"] for pk in b["picks"])]
        news = [st for st in STORIES if path in st["related"]]
        facts = "".join(f"<tr><th scope=\"row\">{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in facts_rows(s))
        related = related_links([f"/compare/{pair_slug(p)}/" for p in pairs] + [f"/best/{b['slug']}/" for b in bests])
        news_html = ("<h2>Recent news</h2><ul class=\"story-list\">" + "".join(story_item(x) for x in news) + "</ul>") if news else ""
        title = f"{s['name']} review ({MONTH_YEAR}): plans, prices and who it is for"
        body = f"""<article class="two"><div>
<h1>{esc(s['name'])} review: plans, prices and who it is for</h1>
<p class="meta">By Sam Barth &middot; Updated {CHECKED_H} &middot; Research-based review</p>
<p class="answer">{esc(s['answer'])}</p>
{DISCLOSE}
<h2>How much does {esc(s['name'])} cost?</h2>
{plans_table(s)}
{checked_line(s)}
{f"<p>{esc(s['extras'])}</p>" if s['extras'] else ""}
<h2>Who is {esc(s['name'])} best for?</h2>
<ul class="clean pros">{"".join(f"<li>{esc(x)}</li>" for x in s['best_for'])}</ul>
<h3>Who should skip it?</h3>
<ul class="clean cons">{"".join(f"<li>{esc(x)}</li>" for x in s['not_for'])}</ul>
<h2>What do you get with {esc(s['name'])}?</h2>
<div class="tbl-wrap"><table><tbody>{facts}</tbody></table></div>
<h2>What should you know before subscribing?</h2>
{"".join(f"<p>{esc(x)}</p>" for x in s['detail'])}
<p>{svc_btn(s)}</p>
{METHOD}
{news_html}
<h2>Related pages</h2><ul>{related}<li><a href="/calculator/">Cord-cutting cost calculator</a></li></ul>
</div>
<aside><div class="card"><h3>{esc(s['name'])} at a glance</h3>
<p>From <span class="price">{money(s['cheapest'])}/mo</span></p>
{f"<p>Ad-free from {money(s['adfree'])}/mo</p>" if s['adfree'] else ""}
<p>Checked {CHECKED_H}</p>
{svc_btn(s, "See plans on " + s['name'])}
</div></aside></article>"""
        review_ld = {
            "@context": "https://schema.org", "@type": "Review", "name": title,
            "author": AUTHOR, "datePublished": LAUNCH, "dateModified": CHECKED,
            "reviewBody": s["answer"],
            "publisher": {"@type": "Organization", "name": SITE},
            "itemReviewed": {"@type": "Service", "name": s["name"], "url": s["official"],
                             "provider": {"@type": "Organization", "name": s["company"]},
                             "offers": [{"@type": "Offer", "name": p["name"], "price": f"{p['monthly']:.2f}",
                                         "priceCurrency": "USD", "url": s["pricing_url"]} for p in s["plans"]]},
        }
        page(path, title,
             f"{s['name']} plans and prices as of {CHECKED_H}, what it is best for, and who should skip it. Research-based, with links to official pricing.",
             body, [("Home", "/"), ("Reviews", "/reviews/"), (s["name"], path)],
             image=img(f"svc-{s['slug']}"), ld_extra=[review_ld], section="/reviews/")

    def grid(kind):
        return '<div class="grid">' + "".join(svc_card(s) for s in SERVICES if s["kind"] == kind) + "</div>"
    body = f"""<h1>Streaming service reviews</h1>
<p class="answer">Every major US streaming service, with current plans and prices pulled from official pages (last checked {CHECKED_H}), what each is best for, and who should skip it.</p>
<h2>On-demand services</h2>{grid("on-demand")}
<h2>Live TV services</h2>{grid("live")}
{METHOD}"""
    page("/reviews/", "Streaming service reviews", f"Research-based reviews of {len(SERVICES)} US streaming services with plans and prices checked {CHECKED_H}.",
         body, [("Home", "/"), ("Reviews", "/reviews/")], section="/reviews/")


def compare_table(a, b):
    rows = [("Cheapest plan", money(a["cheapest"]) + "/mo", money(b["cheapest"]) + "/mo"),
            ("Ad-free from", money(a["adfree"]) + "/mo" if a["adfree"] else "n/a", money(b["adfree"]) + "/mo" if b["adfree"] else "n/a")]
    rows += [(k, va, vb) for (k, va), (_, vb) in zip(facts_rows(a)[2:], facts_rows(b)[2:])]
    r = "".join(f"<tr><th scope=\"row\">{esc(k)}</th><td>{esc(x)}</td><td>{esc(y)}</td></tr>" for k, x, y in rows)
    return (f'<div class="tbl-wrap"><table><thead><tr><th></th><th>{esc(a["name"])}</th><th>{esc(b["name"])}</th>'
            f'</tr></thead><tbody>{r}</tbody></table></div>')


def build_compare():
    for p in PAIRS:
        a, b = SVC[p["a"]], SVC[p["b"]]
        path = f"/compare/{pair_slug(p)}/"
        title = f"{a['name']} vs {b['name']} ({MONTH_YEAR}): price, plans and which to pick"
        news = [st for st in STORIES if path in st["related"] or f"/reviews/{a['slug']}/" in st["related"] or f"/reviews/{b['slug']}/" in st["related"]]
        body = f"""<h1>{esc(a['name'])} vs {esc(b['name'])}: which should you pick?</h1>
<p class="meta">By Sam Barth &middot; Prices checked {CHECKED_H}</p>
<p class="answer">{esc(p['answer'])}</p>
{DISCLOSE}
<h2>How do {esc(a['name'])} and {esc(b['name'])} compare?</h2>
{compare_table(a, b)}
{checked_line(a)}{checked_line(b)}
<h2>What are the key differences?</h2>
<ul class="clean">{"".join(f"<li>{esc(x)}</li>" for x in p['points'])}</ul>
<h2>Which one should you choose?</h2>
<div class="grid">
<div class="card"><h3>Choose {esc(a['name'])} if you want</h3><ul class="clean pros">{"".join(f"<li>{esc(x)}</li>" for x in a['best_for'])}</ul>{svc_btn(a)}</div>
<div class="card"><h3>Choose {esc(b['name'])} if you want</h3><ul class="clean pros">{"".join(f"<li>{esc(x)}</li>" for x in b['best_for'])}</ul>{svc_btn(b)}</div>
</div>
<h2>Can you have both?</h2>
<p>Together they cost {money(a['cheapest'] + b['cheapest'])} a month on the cheapest plans. Try the <a href="/calculator/">cord-cutting calculator</a> to see how that compares to a cable bill.</p>
{METHOD}
{("<h2>Related news</h2><ul class=\"story-list\">" + "".join(story_item(x) for x in news[:3]) + "</ul>") if news else ""}
<h2>Full reviews</h2><ul><li><a href="/reviews/{a['slug']}/">{esc(a['name'])} review</a></li><li><a href="/reviews/{b['slug']}/">{esc(b['name'])} review</a></li><li><a href="/compare/">All comparisons</a></li></ul>"""
        page(path, title, f"{a['name']} vs {b['name']}: prices checked {CHECKED_H}, plan differences, and a direct answer on which to choose.",
             body, [("Home", "/"), ("Compare", "/compare/"), (f"{a['name']} vs {b['name']}", path)],
             image=img(f"cmp-{pair_slug(p)}"), section="/compare/")
    cards = "".join(f'<div class="card"><h3><a href="/compare/{pair_slug(p)}/">{esc(SVC[p["a"]]["name"])} vs {esc(SVC[p["b"]]["name"])}</a></h3><p>{esc(p["answer"].split(". ")[0])}.</p></div>' for p in PAIRS)
    page("/compare/", "Streaming service comparisons", "Head-to-head streaming comparisons with current prices: Netflix vs Hulu, YouTube TV vs Sling and more.",
         f'<h1>Streaming comparisons</h1><p class="answer">Side-by-side comparisons of popular streaming services, each with a direct answer, a price table checked {CHECKED_H}, and links to official pricing.</p><div class="grid">{cards}</div>',
         [("Home", "/"), ("Compare", "/compare/")], section="/compare/")


def build_best():
    for b in BEST:
        path = f"/best/{b['slug']}/"
        items = ""
        for i, pk in enumerate(b["picks"], 1):
            s = SVC[pk["slug"]]
            items += (f'<div class="card"><h3>{i}. <a href="/reviews/{s["slug"]}/">{esc(s["name"])}</a></h3>'
                      f'<p>From <span class="price">{money(s["cheapest"])}/mo</span></p><p>{esc(pk["why"])}</p>{svc_btn(s, ghost=True)}</div>')
        rows = "".join(f'<tr><td><a href="/reviews/{SVC[pk["slug"]]["slug"]}/">{esc(SVC[pk["slug"]]["name"])}</a></td>'
                       f'<td class="num">{money(SVC[pk["slug"]]["cheapest"])}</td><td>{esc(SVC[pk["slug"]]["live_sports"] if b["slug"] == "sports" else SVC[pk["slug"]]["kids"] if b["slug"] == "kids" else SVC[pk["slug"]]["locals"])}</td></tr>'
                       for pk in b["picks"])
        col = {"sports": "Sports", "kids": "Family content"}.get(b["slug"], "Local channels")
        itemlist = {"@context": "https://schema.org", "@type": "ItemList", "name": b["title"],
                    "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"{BASE}/reviews/{pk['slug']}/",
                                         "name": SVC[pk["slug"]]["name"]} for i, pk in enumerate(b["picks"])]}
        body = f"""<h1>{esc(b['title'])} ({MONTH_YEAR})</h1>
<p class="meta">By Sam Barth &middot; Prices checked {CHECKED_H}</p>
<h2>{esc(b['question'])}</h2>
<p class="answer">{esc(b['answer'])}</p>
{DISCLOSE}
<h2>Top picks</h2>
<div class="grid">{items}</div>
<h2>How do the picks compare?</h2>
<div class="tbl-wrap"><table><thead><tr><th>Service</th><th>From</th><th>{col}</th></tr></thead><tbody>{rows}</tbody></table></div>
<p>{esc(b['notes'])}</p>
{METHOD}
<h2>More guides</h2><ul>{related_links([f"/best/{x['slug']}/" for x in BEST if x is not b])}<li><a href="/calculator/">Cord-cutting cost calculator</a></li></ul>"""
        page(path, f"{b['title']} ({MONTH_YEAR})", f"{b['answer'][:150]}",
             body, [("Home", "/"), ("Best of", "/best/"), (b["title"], path)],
             image=img(f"best-{b['slug']}"), ld_extra=[itemlist], section="/best/")
    cards = "".join(f'<div class="card"><h3><a href="/best/{b["slug"]}/">{esc(b["title"])}</a></h3><p>{esc(b["answer"].split(". ")[0])}.</p></div>' for b in BEST)
    page("/best/", "Best streaming services by need", "The best streaming service for sports, kids, live TV and tight budgets, with current prices.",
         f'<h1>Best streaming services by need</h1><p class="answer">Short, sourced answers to the most common streaming questions, ranked from published lineups and prices checked {CHECKED_H}.</p><div class="grid">{cards}</div>',
         [("Home", "/"), ("Best of", "/best/")], section="/best/")


def build_devices():
    for d in DEVICES:
        path = f"/devices/{d['slug']}/"
        models = "".join(f'<div class="model"><p><strong>{esc(m["name"])}</strong><br>{esc(m["specs"])}</p>{amazon_btn(m["q"])}</div>' for m in d["models"])
        itemlist = {"@context": "https://schema.org", "@type": "ItemList", "name": f"{d['name']} models",
                    "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": m["name"]} for i, m in enumerate(d["models"])]}
        news = [st for st in STORIES if path in st["related"]]
        body = f"""<h1>{esc(d['name'])} guide: models, strengths and who should buy one</h1>
<p class="meta">By Sam Barth &middot; Updated {CHECKED_H} &middot; Research-based guide</p>
<p class="answer">{esc(d['answer'])}</p>
{DISCLOSE}
<h2>Which {esc(d['name'])} model should you buy?</h2>
{models}
<p class="source">Specs from the <a href="{d['official']}" target="_blank" rel="noopener">{esc(d['official_label'])}</a>, checked {CHECKED_H}. We do not show Amazon prices or ratings here because they change constantly; use the button to see the current price.</p>
<h2>What is good about {esc(d['name'])}?</h2>
<ul class="clean pros">{"".join(f"<li>{esc(x)}</li>" for x in d['good'])}</ul>
<h2>What should you watch out for?</h2>
<ul class="clean cons">{"".join(f"<li>{esc(x)}</li>" for x in d['watch'])}</ul>
<h2>Who is it best for?</h2><p>{esc(d['best_for'])}</p>
<h2>How was this guide researched?</h2><p>This guide is based on manufacturer specifications and published reviews, not hands-on testing. <a href="/how-we-research/">How we research</a>.</p>
{("<h2>Related news</h2><ul class=\"story-list\">" + "".join(story_item(x) for x in news) + "</ul>") if news else ""}
<h2>Other devices</h2><ul>{related_links([f"/devices/{x['slug']}/" for x in DEVICES if x is not d])}</ul>"""
        page(path, f"{d['name']} guide ({MONTH_YEAR}): which model to buy", d["answer"][:155],
             body, [("Home", "/"), ("Devices", "/devices/"), (d["name"], path)],
             image=img(f"dev-{d['slug']}"), ld_extra=[itemlist], section="/devices/")
    cards = "".join(f'<div class="card"><h3><a href="/devices/{d["slug"]}/">{esc(d["name"])}</a></h3><p>{esc(d["best_for"])}</p></div>' for d in DEVICES)
    body = f"""<h1>Streaming device guides</h1>
<p class="answer">Which streaming device should you buy? Roku is the simplest, Fire TV fits Prime and Alexa homes, Apple TV 4K is the premium pick for iPhone users, and the Google TV Streamer suits Android and Google Home users.</p>
<div class="grid">{cards}</div>"""
    page("/devices/", "Streaming device guides: Roku, Fire TV, Apple TV, Google TV",
         "Which streaming device to buy: Roku, Fire TV, Apple TV 4K or Google TV Streamer, with model-by-model guidance.",
         body, [("Home", "/"), ("Devices", "/devices/")], section="/devices/")


def build_calculator():
    opts = ""
    for s in SERVICES:
        o = "".join(f'<option value="{p["monthly"]:.2f}">{esc(p["name"])} ({money(p["monthly"])})</option>' for p in s["plans"])
        opts += f'<label>{esc(s["name"])}<select data-svc="{s["slug"]}"><option value="0">None</option>{o}</select></label>'
    body = f"""<h1>Cord-cutting cost calculator</h1>
<p class="answer">How much can you save by cutting cable? Enter your current TV bill, pick the streaming plans you would replace it with, and the calculator shows your monthly and first-year savings using prices checked {CHECKED_H}.</p>
<form class="calc" id="calc" onsubmit="return false">
<div>
<label for="bill">Current cable or satellite TV bill (per month, $)</label>
<input id="bill" type="number" min="0" step="0.01" inputmode="decimal" placeholder="e.g. 120">
<label for="internet">Extra internet cost after cutting cable (per month, $)</label>
<input id="internet" type="number" min="0" step="0.01" inputmode="decimal" value="0">
<label for="device">One-time cost for streaming devices ($)</label>
<input id="device" type="number" min="0" step="0.01" inputmode="decimal" value="0">
<h2>Pick your streaming plans</h2>
<div class="svc-pick">{opts}</div>
</div>
<div class="result" aria-live="polite">
<h2 style="margin-top:0">Your estimate</h2>
<dl>
<dt>Streaming subscriptions</dt><dd id="r-subs">$0.00</dd>
<dt>New monthly total</dt><dd id="r-new">$0.00</dd>
<dt>Monthly savings</dt><dd id="r-month" class="big">$0.00</dd>
<dt>First-year savings (after devices)</dt><dd id="r-year">$0.00</dd>
</dl>
<p id="r-msg" class="meta"></p>
</div>
</form>
<h2>How does the calculator work?</h2>
<p>Monthly savings = your current TV bill minus (the streaming plans you pick + any extra internet cost). First-year savings = monthly savings x 12 minus one-time device costs. Prices exclude taxes and promotional discounts.</p>
<h2>How can you lower the total?</h2>
<ul class="clean"><li>Use an over-the-air antenna for local channels instead of a live TV service.</li><li>Rotate on-demand services month to month instead of keeping all of them.</li><li>Check bundles: the <a href="/reviews/disney-plus/">Disney+, Hulu bundle</a> costs 50 cents more than either service alone with ads.</li><li>See the <a href="/best/cheapest/">cheapest streaming services</a>.</li></ul>
<p class="source">Plan prices come from each provider's official page; see the <a href="/reviews/">reviews</a> for sources.</p>"""
    app = {"@context": "https://schema.org", "@type": "WebApplication", "name": "Cord-cutting cost calculator",
           "applicationCategory": "FinanceApplication", "operatingSystem": "Any", "url": BASE + "/calculator/",
           "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}}
    page("/calculator/", "Cord-cutting cost calculator", "Free calculator: compare your cable bill with streaming plans priced as of " + CHECKED_H + " and see monthly and yearly savings.",
         body, [("Home", "/"), ("Calculator", "/calculator/")], image=img("calc"), ld_extra=[app], section="/calculator/")


def build_news():
    for s in STORIES:
        path = f"/news/{s['slug']}/"
        body = f"""<article>
<p class="meta">{NEWS_BRAND} &middot; {human_date(s['date_published'])} &middot; By Sam Barth</p>
<h1>{esc(s['title'])}</h1>
<p class="answer">{esc(s['summary'])}</p>
<img src="{img('news-' + s['slug'])}" width="1200" height="630" alt="{esc(s['title'])}" loading="lazy" decoding="async">
{"".join(f"<p>{esc(x)}</p>" for x in s['body'])}
<p class="source">Source: <a href="{s['source']['url']}" target="_blank" rel="noopener">{esc(s['source']['name'])}</a>. This is an original summary; read the source for full details.</p>
<p>{"".join(f'<span class="tag">{esc(t)}</span>' for t in s['tags'])}</p>
<h2>Related guides</h2><ul>{related_links(s['related'])}</ul>
<p><a href="/news/">More from {NEWS_BRAND}</a></p>
</article>"""
        news_ld = {"@context": "https://schema.org", "@type": "NewsArticle", "headline": s["title"][:110],
                   "description": s["summary"], "datePublished": s["date_published"], "dateModified": s["date_published"],
                   "image": [BASE + img("news-" + s["slug"])], "author": AUTHOR, "url": BASE + path,
                   "publisher": {"@type": "Organization", "name": SITE, "url": BASE + "/"},
                   "isBasedOn": s["source"]["url"]}
        page(path, s["title"], s["summary"], body,
             [("Home", "/"), ("News", "/news/"), (s["title"], path)],
             image=img("news-" + s["slug"]), ld_extra=[news_ld], published=s["date_published"],
             modified=s["date_published"], section="/news/")
    body = f"""<h1>{NEWS_BRAND}: streaming news</h1>
<p class="answer">Short, sourced write-ups on streaming price changes, new services and sports rights, with what each change means for your monthly bill. Every story links to its source.</p>
<ul class="story-list">{"".join(story_item(s) for s in STORIES)}</ul>
<p class="source">Follow via <a href="/news/feed.json">JSON Feed</a> or <a href="/rss.xml">RSS</a>.</p>"""
    page("/news/", f"{NEWS_BRAND}: streaming news", "Streaming news: price increases, new services and sports rights, each with a source link and what it means for you.",
         body, [("Home", "/"), ("News", "/news/")], modified=STORIES[0]["date_published"] if STORIES else CHECKED,
         og_type="website", section="/news/")

    feed = {
        "version": "https://jsonfeed.org/version/1.1",
        "title": f"{NEWS_BRAND} ({SITE})",
        "home_page_url": BASE + "/news/",
        "feed_url": BASE + "/news/feed.json",
        "description": "Streaming price changes, new services and sports rights.",
        "language": "en-US",
        "icon": BASE + img("og-default"),
        "authors": [{"name": "Sam Barth", "url": "https://samcbarth.com"}],
        "items": [{
            "id": BASE + f"/news/{s['slug']}/",
            "url": BASE + f"/news/{s['slug']}/",
            "title": s["title"],
            "summary": s["summary"],
            "content_text": "\n\n".join(s["body"]),
            "image": BASE + img("news-" + s["slug"]),
            "date_published": s["date_published"] + "T12:00:00-06:00",
            "tags": s["tags"],
            "external_url": s["source"]["url"],
        } for s in STORIES],
    }
    (ROOT / "news" / "feed.json").write_text(json.dumps(feed, indent=2, ensure_ascii=False), encoding="utf-8")

    def rfc822(iso):
        return dt.datetime.fromisoformat(iso + "T12:00:00-06:00").strftime("%a, %d %b %Y %H:%M:%S %z")
    items = "".join(f"""<item><title>{esc(s['title'])}</title><link>{BASE}/news/{s['slug']}/</link><guid>{BASE}/news/{s['slug']}/</guid><pubDate>{rfc822(s['date_published'])}</pubDate><description>{esc(s['summary'])}</description></item>""" for s in STORIES)
    (ROOT / "rss.xml").write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>{NEWS_BRAND} ({SITE})</title><link>{BASE}/news/</link><description>Streaming price changes, new services and sports rights.</description><language>en-us</language>{items}</channel></rss>
""", encoding="utf-8")


def build_home():
    rows = "".join(f'<tr><td><a href="/reviews/{s["slug"]}/">{esc(s["name"])}</a></td><td class="num">{money(s["cheapest"])}</td>'
                   f'<td class="num">{money(s["adfree"]) if s["adfree"] else "n/a"}</td><td>{esc(s["best_for"][0])}</td></tr>' for s in SERVICES)
    best = "".join(f'<div class="card"><h3><a href="/best/{b["slug"]}/">{esc(b["title"])}</a></h3><p>{esc(b["answer"].split(". ")[0])}.</p></div>' for b in BEST)
    cmp_links = "".join(f'<li><a href="/compare/{pair_slug(p)}/">{esc(SVC[p["a"]]["name"])} vs {esc(SVC[p["b"]]["name"])}</a></li>' for p in PAIRS)
    dev = "".join(f'<div class="card"><h3><a href="/devices/{d["slug"]}/">{esc(d["name"])}</a></h3><p>{esc(d["best_for"])}</p></div>' for d in DEVICES)
    cheapest_adfree = min((s for s in SERVICES if s["adfree"]), key=lambda s: s["adfree"])
    body = f"""<h1>Streaming prices, plans and picks, checked against official pages</h1>
<p class="lede">Plain answers on which streaming services are worth paying for, what they cost right now, and which device to watch them on.</p>
<h2>How much does streaming cost in {MONTH_YEAR}?</h2>
<p class="answer">Most major on-demand services start at $8.99 to $12.49 a month with ads; ad-free plans run from {money(cheapest_adfree['adfree'])} ({esc(cheapest_adfree['name'])}) to about $21.49. Live TV services that replace cable cost $25 (Philo) to $82.99 (YouTube TV) and up.</p>
<div class="tbl-wrap"><table><thead><tr><th>Service</th><th>From (with ads)</th><th>Ad-free from</th><th>Best for</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="source">All prices checked {CHECKED_H} on each provider's official pricing page (linked from every review). Monthly US prices before tax.</p>
<h2>Which streaming service is best for you?</h2>
<div class="grid">{best}</div>
<h2>Will cutting cable save you money?</h2>
<p>Usually, if you keep your streaming list short. The <a href="/calculator/">cord-cutting cost calculator</a> compares your current bill with the exact plans you would pick.</p>
<h2>Popular comparisons</h2><ul class="clean">{cmp_links}</ul>
<h2>Which streaming device should you buy?</h2>
<div class="grid">{dev}</div>
<h2>Latest from {NEWS_BRAND}</h2>
<ul class="story-list">{"".join(story_item(s) for s in STORIES[:4])}</ul>
<p><a href="/news/">All streaming news</a></p>"""
    page("/", f"{SITE}: streaming service reviews, prices and comparisons",
         f"Current US streaming prices checked {CHECKED_H}: Netflix, Hulu, Disney+, HBO Max, YouTube TV and more, plus comparisons, a cord-cutting calculator and device guides.",
         body, [("Home", "/")], og_type="website")


def build_static():
    S = lambda p, t, d, b, n: page(p, t, d, b, [("Home", "/"), (n, p)])
    S("/about/", "About Streaming Price Check", "Who runs Streaming Price Check, what it covers, and how it is funded.",
      f"""<h1>About {SITE}</h1>
<p class="answer">{SITE} is an independent guide to US streaming services and devices, run by Sam Barth as part of the samcbarth.com network of sites.</p>
<h2>What does this site do?</h2><p>It tracks the plans and prices of the major streaming services, compares them head to head, explains which service fits which kind of viewer, and covers streaming news that affects what you pay.</p>
<h2>How is it funded?</h2><p>The site may earn commissions from affiliate links to streaming services and devices. Those commissions never change which services we list, the prices we show, or the order of our picks. See the <a href="/affiliate-disclosure/">affiliate disclosure</a>.</p>
<h2>How is content researched?</h2><p>Reviews are research-based: official pricing pages, provider help centers and published reporting, all linked. Read <a href="/how-we-research/">how we research</a>.</p>""", "About")
    S("/how-we-research/", "How we research streaming services", "How Streaming Price Check gathers prices, checks facts and makes recommendations.",
      f"""<h1>How we research</h1>
<p class="answer">Every price on this site comes from the provider's own pricing or help page and shows the date it was last checked. We do not invent ratings, test results or user reviews.</p>
<h2>Where do prices come from?</h2><p>From each service's official plan, sign-up or help-center page, linked next to every price table. The current data set was checked on {CHECKED_H}. Promotional and introductory prices are noted where the provider showed them.</p>
<h2>Are the reviews hands-on?</h2><p>No. Reviews and device guides are research-based: they summarize official specifications, plan details and published reporting. When a fact comes from a news report, the report is linked.</p>
<h2>How are picks chosen?</h2><p>Picks match a service's published lineup and price to a specific need, such as sports or kids. Affiliate relationships do not affect picks.</p>
<h2>How do you handle news?</h2><p>{NEWS_BRAND} stories are original short summaries of real events. Each one links its source, and we leave out anything we cannot verify.</p>
<h2>Found an error?</h2><p>Prices change often. If something is out of date, please <a href="/contact/">contact us</a>.</p>""", "How we research")
    S("/contact/", "Contact", "Contact Streaming Price Check about corrections, price changes or partnerships.",
      """<h1>Contact</h1>
<p class="answer">Spotted an outdated price or a mistake? Corrections are the most useful message you can send.</p>
<div id="contact-box" class="card"><p>The contact form is being set up. Please check back soon.</p></div>
<p>For corrections, include the page address and a link to the official source showing the new information.</p>""", "Contact")
    S("/affiliate-disclosure/", "Affiliate disclosure", "How Streaming Price Check uses affiliate links and what that means for you.",
      f"""<h1>Affiliate disclosure</h1>
<p class="answer">Some links on {SITE} may be affiliate links. If you sign up for a service or buy a device through one, this site may earn a commission at no extra cost to you.</p>
<h2>Which links are affiliate links?</h2><p>Buttons that send you to a streaming service (for example "Visit Netflix") and "Check price on Amazon" buttons may carry affiliate tracking. Affiliate links are marked with <code>rel="sponsored"</code>. A disclosure line appears above the first such button on every page that has them.</p>
<h2>Amazon Associates</h2><p>As an Amazon Associate, this site earns from qualifying purchases once enrolled in the program. We do not display Amazon prices or ratings because they change constantly; the button takes you to Amazon to see the current price.</p>
<h2>Does this affect recommendations?</h2><p>No. Prices come from official provider pages, and picks are based on published lineups and prices. A service without an affiliate program is listed exactly the same way.</p>""", "Affiliate disclosure")
    S("/privacy/", "Privacy policy", "Privacy policy for Streaming Price Check: cookies, analytics, Google ads and affiliate links.",
      f"""<h1>Privacy policy</h1>
<p class="meta">Last updated {human_date(LAUNCH)}</p>
<p class="answer">{SITE} does not ask you to create an account. It uses cookies and similar technologies for analytics, advertising and affiliate tracking, as described below.</p>
<h2>What data is collected?</h2><p>Standard analytics data such as pages viewed, approximate location, device and browser type, collected through Google Tag Manager and Google Analytics. If you use the contact form, we receive the details you submit.</p>
<h2>Cookies and Google ads</h2><p>Third-party vendors, including Google, may use cookies to serve ads based on your prior visits to this and other websites. Google's use of advertising cookies enables it and its partners to serve ads based on your visits. You can opt out of personalized advertising at <a href="https://adssettings.google.com/" target="_blank" rel="noopener">Google Ads Settings</a> or <a href="https://www.aboutads.info/" target="_blank" rel="noopener">aboutads.info</a>.</p>
<h2>Affiliate links</h2><p>When you click an affiliate link, the destination site or affiliate network (such as Amazon, Impact or CJ) may set a cookie to credit the referral. Their privacy policies apply on their sites.</p>

<h2>Your choices</h2><p>You can block or delete cookies in your browser settings. The site works without them.</p>
<h2>Contact</h2><p>Questions about privacy: use the <a href="/contact/">contact page</a>.</p>""", "Privacy")
    S("/terms/", "Terms of use", "Terms of use for Streaming Price Check.",
      f"""<h1>Terms of use</h1>
<p class="meta">Last updated {human_date(LAUNCH)}</p>
<p class="answer">{SITE} provides general information about streaming services for free. Prices and plans change often, so always confirm details on the provider's site before you buy.</p>
<h2>Accuracy</h2><p>We check prices against official sources and show the date checked, but we cannot guarantee that information is current or complete. Nothing here is financial advice.</p>
<h2>Third-party sites</h2><p>Links to other sites are provided for convenience. We are not responsible for their content, prices or policies.</p>
<h2>Trademarks</h2><p>Service and product names are trademarks of their owners and are used only to identify them. This site is not affiliated with or endorsed by any streaming service.</p>
<h2>Content use</h2><p>You may quote short passages with a link back. Do not republish full pages without permission.</p>""", "Terms")


def build_meta_files():
    (ROOT / "404.html").write_text(f"""<!doctype html><html lang="en"><head>{GTM}<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Page not found | {SITE}</title><meta name="robots" content="noindex"><link rel="stylesheet" href="/assets/style.css"></head>
<body><main><div class="wrap"><h1>Page not found</h1><p>That page does not exist. Try the <a href="/">home page</a>, <a href="/reviews/">reviews</a> or <a href="/news/">news</a>.</p></div></main></body></html>
""", encoding="utf-8")
    urls = "".join(f"<url><loc>{BASE}{p}</loc><lastmod>{m}</lastmod></url>" for p, m in PAGES)
    (ROOT / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n', encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n", encoding="utf-8")
    (ROOT / "CNAME").write_text("streaming.samcbarth.com\n", encoding="utf-8")
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")
    fav = ROOT / "assets" / "img" / "favicon.svg"
    fav.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#000"/><circle cx="32" cy="32" r="22" fill="#9a00ff"/><path d="M24 18l24 14-24 14z" fill="#fff"/></svg>\n', encoding="utf-8")
    ico = ROOT / "favicon.ico"
    if not ico.exists():
        try:
            from PIL import Image, ImageDraw
            im = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            d.rounded_rectangle([0, 0, 63, 63], radius=14, fill=(0, 0, 0)); d.ellipse([10, 10, 54, 54], fill=(154, 0, 255))
            d.polygon([(24, 18), (48, 32), (24, 46)], fill=(255, 255, 255))
            im.save(ico, sizes=[(16, 16), (32, 32), (48, 48)])
        except ImportError:
            pass
    svc_lines = "\n".join(f"- [{s['name']} review]({BASE}/reviews/{s['slug']}/): {s['answer']}" for s in SERVICES)
    llms = f"""# {SITE}

> Independent, research-based guide to US streaming services and devices at {BASE}. Prices come from official provider pages and were last checked {CHECKED_H}. No invented ratings or hands-on claims.

## Reviews
{svc_lines}

## Guides
""" + "\n".join(f"- [{b['title']}]({BASE}/best/{b['slug']}/): {b['answer']}" for b in BEST) + "\n" + \
        "\n".join(f"- [{SVC[p['a']]['name']} vs {SVC[p['b']]['name']}]({BASE}/compare/{pair_slug(p)}/)" for p in PAIRS) + "\n" + \
        "\n".join(f"- [{d['name']} guide]({BASE}/devices/{d['slug']}/)" for d in DEVICES) + f"""
- [Cord-cutting cost calculator]({BASE}/calculator/)

## News
- [{NEWS_BRAND}]({BASE}/news/), JSON Feed: {BASE}/news/feed.json
"""
    (ROOT / "llms.txt").write_text(llms, encoding="utf-8")


def main():
    ensure_images()
    build_home()
    build_reviews()
    build_compare()
    build_best()
    build_devices()
    build_calculator()
    build_news()
    build_static()
    build_meta_files()
    print(f"Built {len(PAGES)} pages, {len(STORIES)} news stories.")


if __name__ == "__main__":
    main()
