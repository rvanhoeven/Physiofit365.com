#!/usr/bin/env python3
"""Static site generator for PhysioFit365.

Reads content/{en,nl,es}.json and writes the multilingual site to site/<lang>/...
English is the base language (content/en.json); nl and es must have the same keys.

Usage:  python3 build.py            # build into ./site
        BASE_URL=https://example.com python3 build.py
"""
import json
import os
import re
import shutil
import subprocess
from urllib.parse import quote
from html import escape as e
from pathlib import Path

ROOT = Path(__file__).parent
SITE = ROOT / "site"
BASE_URL = os.environ.get("BASE_URL", "https://www.physiofit365.com").rstrip("/")
LANGS = ["en", "nl", "es"]          # en = base language
PAGES = ["home", "about", "services", "faq", "appointment", "contact", "privacy"]
PATHS = {"home": "", "about": "about/", "services": "services/", "faq": "faq/", "appointment": "appointment/", "contact": "contact/", "privacy": "privacy/"}

PHONE_DISPLAY = "+34 686 04 22 00"
PHONE_TEL = "+34686042200"
WHATSAPP = "34686042200"
WHATSAPP_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M17.47 14.38c-.3-.15-1.76-.87-2.03-.97-.27-.1-.47-.15-.67.15-.2.3-.77.97-.94 1.16-.17.2-.35.22-.64.08-.3-.15-1.26-.46-2.39-1.48-.88-.79-1.48-1.76-1.65-2.06-.17-.3-.02-.46.13-.61.13-.13.3-.35.45-.52.15-.17.2-.3.3-.5.1-.2.05-.37-.03-.52-.07-.15-.67-1.61-.91-2.21-.24-.58-.49-.5-.67-.51h-.57c-.2 0-.52.07-.79.37-.27.3-1.04 1.02-1.04 2.48s1.07 2.88 1.22 3.07c.15.2 2.1 3.2 5.08 4.49.71.31 1.26.49 1.69.63.71.23 1.36.2 1.87.12.57-.09 1.76-.72 2-1.41.25-.7.25-1.29.17-1.41-.07-.13-.27-.2-.57-.35zM12.05 21.8h-.01a9.87 9.87 0 0 1-5.03-1.38l-.36-.21-3.74.98 1-3.65-.24-.37a9.86 9.86 0 0 1-1.51-5.26c0-5.45 4.44-9.88 9.89-9.88 2.64 0 5.12 1.03 6.99 2.9a9.82 9.82 0 0 1 2.89 6.99c0 5.45-4.44 9.88-9.88 9.88zm8.41-18.3A11.82 11.82 0 0 0 12.05 0C5.5 0 .16 5.34.16 11.9c0 2.1.55 4.14 1.59 5.94L.06 24l6.3-1.65a11.88 11.88 0 0 0 5.68 1.45h.01c6.55 0 11.89-5.34 11.89-11.9 0-3.18-1.24-6.17-3.48-8.4z"/></svg>'
EMAIL = "info@physiofit365.com"
FACEBOOK = "https://www.facebook.com/physiofit365"
INSTAGRAM = "https://www.instagram.com/physiofit365"

ICONS = {
    "manual": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 11V5.5a1.5 1.5 0 0 1 3 0V10m0-1V4a1.5 1.5 0 0 1 3 0v5m0-3.5a1.5 1.5 0 0 1 3 0V11m0-3a1.5 1.5 0 0 1 3 0v6a7 7 0 0 1-7 7h-1a7 7 0 0 1-5.6-2.8L4 14.5a1.6 1.6 0 0 1 2.5-2L7 13"/></svg>',
    "work": '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M3 13h18"/></svg>',
    "sport": '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="14" cy="4.5" r="2"/><path d="m8 21 3-6 3 2v4M6 12l4-3 3 1 3 3 3 1M10 9l-1 6"/></svg>',
    "check": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>',
    "home": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 11 9-8 9 8M5 10v10h14V10M10 20v-6h4v6"/></svg>',
    "badge": '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="9" r="5.5"/><path d="m9 14 -1.5 7L12 18.5 16.5 21 15 14"/></svg>',
    "team": '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="9" cy="8" r="3.2"/><circle cx="17" cy="9" r="2.4"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6M15.5 14.2c3 .2 5.5 2.4 5.5 5.8"/></svg>',
    "star": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/></svg>',
    "target": '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.2"/></svg>',
    "user": '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8"/></svg>',
    "phone": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z"/></svg>',
    "mail": '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></svg>',
    "pin": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s7-6.2 7-11.5A7 7 0 0 0 5 9.5C5 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/></svg>',
    "surgery": '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="4"/><path d="M12 8v8M8 12h8"/></svg>',
    "elderly": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20s-8-4.7-8-10.5A4.5 4.5 0 0 1 12 7a4.5 4.5 0 0 1 8 2.5C20 15.300 12 20 12 20z"/></svg>',
    "calendar": '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>',
    "clock": '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
}
# Appointment times. Keep in sync with the check on appointment_requests.requested_time in the database.
SLOTS = ["17:30", "18:00", "18:30", "19:00", "19:30", "20:00"]
# Professional registers. "local" is used when that file exists in site/assets/img; until then the college's own logo URL.
REGISTERS = [
    {"key": "physio", "name": "Ilustre Colegio Oficial de Fisioterapeutas de la Comunidad Valenciana", "number": "6.048",
     "url": "https://app.colfisiocv.com/college/collegiatelist/", "local": "colegio-fisioterapeutas.png",
     "logo": "https://www.colfisiocv.com/sites/default/files/prueba_2.png"},
    {"key": "nurse", "name": "Colegio Oficial de Enfermería de Alicante", "number": "18.067",
     "url": "https://www.enferalicante.org/buscar_colegiados.php", "local": "colegio-enfermeria.png",
     "logo": "https://www.enferalicante.org/Images/logoCol.png"},
]
ADV_ICONS = ["user", "home", "badge", "team", "star", "target"]
BENEFIT_ICONS = ["pin", "home", "user", "team"]


def load(lang):
    with open(ROOT / "content" / f"{lang}.json", encoding="utf-8") as f:
        return json.load(f)


def check_keys(base, other, path=""):
    """Fail the build if a translation is missing keys that exist in English."""
    problems = []
    if isinstance(base, dict):
        for k in base:
            if k not in other:
                problems.append(f"{path}/{k}")
            else:
                problems += check_keys(base[k], other[k], f"{path}/{k}")
    elif isinstance(base, list):
        if len(base) != len(other):
            problems.append(f"{path} (list length {len(other)} != {len(base)})")
        else:
            for i, (b, o) in enumerate(zip(base, other)):
                problems += check_keys(b, o, f"{path}[{i}]")
    return problems


class Ctx:
    def __init__(self, lang, page, t):
        self.lang, self.page, self.t = lang, page, t
        depth = 0 if page == "home" else 1
        self.up = "../" * (1 + depth)          # from this page back to site root

    def url(self, page, lang=None):
        return f"{self.up}{lang or self.lang}/{PATHS[page]}"

    def form_url(self):
        """Contact page, scrolled to the form."""
        return self.url("contact") + "#form"

    def form_url_about(self, subject):
        """Contact form with the subject field already filled in (see site.js)."""
        return self.url("contact") + "?subject=" + quote(subject) + "#form"

    def whatsapp_url(self):
        return f"https://wa.me/{WHATSAPP}?text=" + quote(self.t["common"]["whatsapp_text"])

    def asset(self, p):
        return f"{self.up}assets/{p}"


def photo(ctx, mode="lazy"):
    """Mellany's photo. Drop it at site/assets/img/mellany.jpg; until then show a branded placeholder."""
    if (SITE / "assets" / "img" / "mellany.jpg").exists():
        extra = ' fetchpriority="high"' if mode == "eager" else ' loading="lazy"'
        return (f'<img src="{ctx.asset("img/mellany.jpg")}" alt="Mellany Ginny van Hoeven" '
                f'width="1024" height="813"{extra}>')
    return (f'<div class="photo-placeholder" role="img" aria-label="Mellany Ginny van Hoeven">'
            f'<img src="{ctx.asset("img/logo.png")}" alt="" width="260"></div>')


def abs_url(lang, page):
    return f"{BASE_URL}/{lang}/{PATHS[page]}"


def translations_locale(lang):
    return {"en": "en_US", "nl": "nl_NL", "es": "es_ES"}[lang]


def last_modified():
    """Date of the last commit that changed the texts or the page templates."""
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", "content", "build.py"],
                             cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        out = ""
    return out


def json_ld(data):
    text = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/ld+json">{text}</script>'


def structured_data(ctx):
    """Search engine data: the business on home pages, the questions on FAQ pages."""
    t = ctx.t
    business_id = f"{BASE_URL}/#business"
    crumbs = "" if ctx.page == "home" else json_ld({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": t["site_name"], "item": abs_url(ctx.lang, "home")},
            {"@type": "ListItem", "position": 2, "name": t[ctx.page]["title"], "item": abs_url(ctx.lang, ctx.page)},
        ],
    })
    if ctx.page == "home":
        website = json_ld({
            "@context": "https://schema.org",
            "@type": "WebSite",
            "@id": f"{BASE_URL}/#website",
            "name": t["site_name"],
            "url": f"{BASE_URL}/",
            "inLanguage": LANGS,
            "publisher": {"@id": business_id},
        })
        return website + "\n" + json_ld({
            "@context": "https://schema.org",
            "@type": "Physiotherapy",
            "@id": business_id,
            "name": t["site_name"],
            "description": t["home"]["description"],
            "url": abs_url(ctx.lang, "home"),
            "image": f"{BASE_URL}/assets/img/mellany.jpg",
            "logo": f"{BASE_URL}/assets/img/logo.png",
            "telephone": PHONE_TEL,
            "email": EMAIL,
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "Calle Agata Buzón 77",
                "postalCode": "03170",
                "addressLocality": "Rojales",
                "addressRegion": "Alicante",
                "addressCountry": "ES",
            },
            "areaServed": [{"@type": "Place", "name": n} for n in t["home"]["area_towns"]],
            "openingHoursSpecification": {
                "@type": "OpeningHoursSpecification",
                "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                "opens": "15:00",
                "closes": "21:00",
            },
            "availableLanguage": LANGS,
            "sameAs": [FACEBOOK, INSTAGRAM],
            "employee": {"@type": "Person", "name": "Mellany Ginny van Hoeven", "jobTitle": t["about"]["mellany_role"]},
            "hasOfferCatalog": {
                "@type": "OfferCatalog",
                "name": t["services"]["title"],
                "itemListElement": [
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": i["title"], "description": i["short"], "url": f"{abs_url(ctx.lang, 'services')}#{i['id']}"}}
                    for i in t["services"]["items"]
                ],
            },
        })
    if ctx.page == "faq":
        return crumbs + "\n" + json_ld({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": i["q"], "acceptedAnswer": {"@type": "Answer", "text": i["a"]}}
                for i in t["faq"]["items"]
            ],
        })
    return crumbs


def head(ctx, title, description):
    t = ctx.t
    full_title = t[ctx.page]["seo_title"]
    og_alts = "\n".join(
        f'<meta property="og:locale:alternate" content="{translations_locale(l)}">' for l in LANGS if l != ctx.lang
    )
    alts = "\n".join(
        f'<link rel="alternate" hreflang="{l}" href="{abs_url(l, ctx.page)}">' for l in LANGS
    )
    return f"""<!doctype html>
<html lang="{ctx.lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(full_title)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{abs_url(ctx.lang, ctx.page)}">
{alts}
<link rel="alternate" hreflang="x-default" href="{abs_url('en', ctx.page)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{e(t['site_name'])}">
<meta property="og:title" content="{e(full_title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:locale" content="{t['locale']}">
{og_alts}
<meta property="og:url" content="{abs_url(ctx.lang, ctx.page)}">
<meta property="og:image" content="{BASE_URL}/assets/img/mellany.jpg">
<meta property="og:image:width" content="1024">
<meta property="og:image:height" content="813">
<meta property="og:image:alt" content="Mellany Ginny van Hoeven">
<meta name="twitter:card" content="summary_large_image">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="theme-color" content="#fe26ac">
<link rel="icon" href="{ctx.asset('img/favicon.svg')}" type="image/svg+xml">
<link rel="icon" href="{ctx.asset('img/favicon.ico')}" sizes="48x48">
<link rel="apple-touch-icon" href="{ctx.asset('img/apple-touch-icon.png')}">
<link rel="stylesheet" href="{ctx.asset('css/style.css')}">
{structured_data(ctx)}
</head>"""


def cur(cond, val):
    return f' aria-current="{val}"' if cond else ""


def header(ctx):
    t = ctx.t
    nav_items = ["home", "about", "services", "faq"]   # contact lives in the pink button
    links = "".join(
        f'<li><a href="{ctx.url(p)}"{cur(p == ctx.page, "page")}>{e(t["nav"][p])}</a></li>'
        for p in nav_items
    )
    langs = "".join(
        f'<a href="{ctx.url(ctx.page, l)}" hreflang="{l}" lang="{l}"{cur(l == ctx.lang, "true")} '
        f'title="{e(LANG_NAMES[l])}">{l.upper()}</a>'
        for l in LANGS
    )
    return f"""<body>
<a class="skip" href="#main">{e(t['common']['skip'])}</a>
<header class="site-header">
  <div class="wrap bar">
    <a class="brand" href="{ctx.url('home')}" aria-label="{e(t['site_name'])} – {e(t['nav']['home'])}">
      <img src="{ctx.asset('img/logo.png')}" alt="{e(t['site_name'])}" width="132" height="74">
    </a>
    <a class="btn btn-sm btn-appt" href="{ctx.url('appointment')}"{cur(ctx.page == "appointment", "page")}>{ICONS["calendar"]}{e(t['nav']['appointment'])}</a>
    <button class="menu-btn" type="button" aria-expanded="false" aria-controls="nav">
      <span class="sr">{e(t['nav']['menu'])}</span><span class="bars" aria-hidden="true"></span>
    </button>
    <nav id="nav" class="nav" aria-label="{e(t['nav']['menu'])}">
      <ul>{links}</ul>
      <div class="lang" role="group" aria-label="{e(t['nav']['language'])}">{langs}</div>
      <a class="btn btn-sm btn-ghost" href="{ctx.form_url()}"{cur(ctx.page == "contact", "page")}>{e(t['nav']['cta'])}</a>
    </nav>
  </div>
</header>
<main id="main">
"""


def footer(ctx):
    t, c = ctx.t, ctx.t["common"]
    cols = "".join(
        f'<li><a href="{ctx.url(p)}">{e(t["nav"][p])}</a></li>' for p in ["home", "about", "services", "faq", "contact"]
    )
    return f"""</main>
<footer class="site-footer">
  <div class="wrap grid">
    <div>
      <img class="foot-icon" src="{ctx.asset('img/icon-large.jpg')}" alt="" width="64">
      <p class="foot-tag">{e(c['tagline'])}</p>
      <p class="social"><a href="{FACEBOOK}" rel="noopener">Facebook</a> · <a href="{INSTAGRAM}" rel="noopener">Instagram</a></p>
    </div>
    <div>
      <h2>{e(t['nav']['menu'])}</h2>
      <ul class="plain">{cols}</ul>
    </div>
    <div>
      <h2>{e(c['hours_label'])}</h2>
      <p>{e(c['hours'])}<br>{e(c['closed'])}</p>
      <p>{e(c['area'])}</p>
    </div>
    <div>
      <h2>{e(t['nav']['contact'])}</h2>
      <p>{e(c['address'])}</p>
      <p><a href="tel:{PHONE_TEL}">{PHONE_DISPLAY}</a><br><a href="mailto:{EMAIL}">{EMAIL}</a></p>
    </div>
  </div>
  <div class="wrap legal">
    <span>© {2026} PhysioFit365. {e(c['rights'])}</span>
    <a href="{ctx.url('privacy')}">{e(c['privacy'])}</a>
  </div>
</footer>
<a class="wa-float" href="{e(ctx.whatsapp_url())}" target="_blank" rel="noopener" aria-label="{e(c['whatsapp'])}" title="{e(c['whatsapp'])}">{WHATSAPP_ICON}<span>WhatsApp</span></a>
<script src="{ctx.asset('config.js')}" defer></script>
<script src="{ctx.asset('js/site.js')}" defer></script>
</body>
</html>
"""


LANG_NAMES = {"en": "English", "nl": "Nederlands", "es": "Español"}


def ico(name):
    return f'<span class="ico">{ICONS[name]}</span>'


def cta_band(ctx, title, text, label):
    return f"""<section class="band-cta">
  <div class="wrap">
    <h2>{e(title)}</h2>
    <p>{e(text)}</p>
    <a class="btn btn-light" href="{ctx.form_url()}">{e(label)}</a>
  </div>
</section>
"""


def head_photo(ctx):
    """Small framed photo in the pink page header. Decorative, so no alt text."""
    return (f'<figure class="mat" aria-hidden="true"><img src="{ctx.asset("img/head-" + ctx.page + ".jpg")}" alt="" '
            f'width="720" height="542" fetchpriority="high"></figure>')


def registers(ctx, tint=False):
    r = ctx.t["registers"]
    cards = ""
    for x in REGISTERS:
        src = ctx.asset("img/" + x["local"]) if (SITE / "assets" / "img" / x["local"]).exists() else x["logo"]
        cards += f"""<article class="register">
  <a class="register-logo" href="{e(x['url'])}" rel="noopener" target="_blank"><img src="{e(src)}" alt="{e(x['name'])}" loading="lazy" referrerpolicy="no-referrer" onerror="this.style.display='none'"></a>
  <h3>{e(r[x['key'] + '_role'])}</h3>
  <p class="register-no">{e(r['number'])} <strong>{x['number']}</strong></p>
  <p class="register-name">{e(x['name'])}</p>
  <a class="more" href="{e(x['url'])}" rel="noopener" target="_blank">{e(r[x['key'] + '_link'])}</a>
</article>"""
    return f"""<section class="section{' tint' if tint else ''}">
  <div class="wrap">
    <h2 class="section-title">{e(r['title'])}</h2>
    <p class="section-sub">{e(r['sub'])}</p>
    <div class="registers">{cards}</div>
  </div>
</section>
"""


def testimonials(ctx):
    cards = "".join(
        f"""<figure class="quote">
  <blockquote><p>{e(q['quote'])}</p></blockquote>
  <figcaption><strong>{e(q['name'])}</strong><span>{e(q['label'])}</span></figcaption>
</figure>"""
        for q in ctx.t["testimonials"]
    )
    return f"""<section class="section tint">
  <div class="wrap">
    <h2 class="section-title">{e(ctx.t['home']['testimonials_title'])}</h2>
    <div class="quotes">{cards}</div>
  </div>
</section>
"""


# ----------------------------------------------------------------- pages ---

def page_home(ctx):
    t, h = ctx.t, ctx.t["home"]
    badges = "".join(f"<li>{ico('check')}{e(b)}</li>" for b in h["badges"])
    svc_cards = "".join(
        f"""<article class="card">
  {ico(s['id'])}
  <h3>{e(s['title'])}</h3>
  <p>{e(s['short'])}</p>
  <a class="more" href="{ctx.url('services')}#{s['id']}">{e(t['common']['more'])}<span class="sr"> – {e(s['title'])}</span></a>
</article>"""
        for s in t["services"]["items"]
    )
    adv = "".join(
        f"""<li>{ico(ADV_ICONS[i])}<div><h3>{e(a['title'])}</h3><p>{e(a['text'])}</p></div></li>"""
        for i, a in enumerate(h["advantages"])
    )
    benefits = "".join(
        f"""<article class="card">{ico(BENEFIT_ICONS[i])}<h3>{e(b['title'])}</h3><p>{e(b['text'])}</p></article>"""
        for i, b in enumerate(h["benefits"])
    )
    zones = "".join(
        f"""<li><a href="{e(ctx.form_url_about(z['zone']))}"><strong>{e(z['zone'])}</strong><span>{e(z['examples'])}</span></a></li>"""
        for z in h["zones"]
    )
    towns = "".join(f"<li>{e(n)}</li>" for n in h["area_towns"])
    insurers = "".join(
        f'<li><a href="{e(i["url"])}" rel="noopener">{e(i["name"])}</a></li>' for i in load("en")["insurers"]
    )
    body = f"""
<section class="hero">
  <div class="wrap hero-grid">
    <div class="hero-copy">
      <p class="eyebrow">{e(h['eyebrow'])}</p>
      <h1>{e(h['hero_title'])}</h1>
      <p class="lead">{e(h['hero_sub'])}</p>
      <div class="actions">
        <a class="btn" href="{ctx.form_url()}">{e(h['cta_primary'])}</a>
        <a class="btn btn-ghost" href="{ctx.url('services')}">{e(h['cta_secondary'])}</a>
      </div>
      <ul class="badges">{badges}</ul>
    </div>
    <div class="hero-photo">
      <div class="arch">{photo(ctx, 'eager')}</div>
      <p class="chip">{ico('pin')}{e(t['common']['area'])}</p>
    </div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <h2 class="section-title">{e(h['services_title'])}</h2>
    <p class="section-sub">{e(h['services_sub'])}</p>
    <div class="cards five">{svc_cards}</div>
  </div>
</section>

<section class="section tint">
  <div class="wrap">
    <h2 class="section-title">{e(h['benefits_title'])}</h2>
    <p class="section-sub">{e(h['benefits_sub'])}</p>
    <div class="cards four">{benefits}</div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <h2 class="section-title">{e(h['zones_title'])}</h2>
    <p class="section-sub">{e(h['zones_sub'])}</p>
    <ul class="zones">{zones}</ul>
    <p class="zones-note">{e(h['zones_note'])}</p>
  </div>
</section>

<section class="section band-ink">
  <div class="wrap split">
    <div>
      <h2>{e(h['approach_title'])}</h2>
      <p>{e(h['approach_text'])}</p>
    </div>
    <div class="swirl" aria-hidden="true"><img src="{ctx.asset('img/icon-large.jpg')}" alt="" width="150"></div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <h2 class="section-title">{e(h['why_title'])}</h2>
    <ul class="advantages">{adv}</ul>
  </div>
</section>

<section class="section tint">
  <div class="wrap meet">
    <div class="meet-photo">{photo(ctx, 'lazy')}</div>
    <div>
      <h2>{e(h['meet_title'])}</h2>
      <p>{e(h['meet_text'])}</p>
      <a class="btn btn-ghost" href="{ctx.url('about')}">{e(h['meet_cta'])}</a>
    </div>
  </div>
</section>

{registers(ctx)}

{testimonials(ctx)}

<section class="section">
  <div class="wrap two">
    <div>
      <h2>{e(h['area_title'])}</h2>
      <p>{e(h['area_text'])}</p>
      <p class="towns-label">{e(h['area_towns_label'])}</p>
      <ul class="towns">{towns}</ul>
      <p class="muted">{e(t['common']['no_practice'])}</p>
    </div>
    <div>
      <h2>{e(h['insurers_title'])}</h2>
      <ul class="pills">{insurers}</ul>
    </div>
  </div>
</section>

{cta_band(ctx, h['final_title'], h['final_text'], h['final_cta'])}
"""
    return h["title"], h["description"], body


def page_services(ctx):
    s = ctx.t["services"]
    items = ""
    for it in s["items"]:
        pts = "".join(f"<li>{ico('check')}{e(p)}</li>" for p in it["points"])
        items += f"""<article class="service" id="{it['id']}">
  <div class="service-head">{ico(it['id'])}<h2>{e(it['title'])}</h2></div>
  <p>{e(it['body'])}</p>
  <ul class="ticks">{pts}</ul>
</article>"""
    steps = "".join(
        f"<li><span class=\"n\">{i}</span><div><h3>{e(x['title'])}</h3><p>{e(x['text'])}</p></div></li>"
        for i, x in enumerate(s["how"], 1)
    )
    body = f"""
<section class="page-head has-photo"><div class="wrap page-head-grid"><div><h1>{e(s['title'])}</h1><p class="lead">{e(s['intro'])}</p></div>{head_photo(ctx)}</div></section>
<section class="section"><div class="wrap narrow services">{items}</div></section>
<section class="section tint">
  <div class="wrap">
    <h2 class="section-title">{e(s['how_title'])}</h2>
    <ol class="steps">{steps}</ol>
  </div>
</section>
{cta_band(ctx, s['cta_title'], s['cta_text'], s['cta'])}
"""
    return s["title"], s["description"], body


def page_about(ctx):
    a = ctx.t["about"]
    quals = "".join(f"<li>{ico('check')}{e(q)}</li>" for q in a["quals"])
    blocks = "".join(
        f"<div class=\"card flat\"><h3>{e(a[k + '_title'])}</h3><p>{e(a[k])}</p></div>"
        for k in ["vision", "mission", "quality", "care"]
    )
    body = f"""
<section class="page-head has-photo"><div class="wrap page-head-grid"><div><h1>{e(a['title'])}</h1><p class="lead">{e(a['intro'])}</p></div>{head_photo(ctx)}</div></section>

<section class="section">
  <div class="wrap narrow"><h2>{e(a['philosophy_title'])}</h2><p class="big">{e(a['philosophy'])}</p></div>
</section>

<section class="section tint">
  <div class="wrap meet">
    <div class="meet-photo">{photo(ctx, 'lazy')}</div>
    <div>
      <h2>{e(a['mellany_title'])}</h2>
      <p class="role">{e(a['mellany_role'])}</p>
      <p>{e(a['mellany_intro'])}</p>
      <h3>{e(a['education_title'])}</h3><p>{e(a['education'])}</p>
      <h3>{e(a['registration_title'])}</h3><p>{e(a['registration'])}</p>
      <h3>{e(a['career_title'])}</h3><p>{e(a['career'])}</p>
      <h3>{e(a['quals_title'])}</h3><ul class="ticks">{quals}</ul>
      <h3>{e(a['languages_title'])}</h3><p>{e(a['languages'])}</p>
    </div>
  </div>
</section>

{registers(ctx)}

<section class="section tint"><div class="wrap"><div class="cards four">{blocks}</div></div></section>
{cta_band(ctx, ctx.t['home']['final_title'], ctx.t['home']['final_text'], a['cta'])}
"""
    return a["title"], a["description"], body


def page_faq(ctx):
    f = ctx.t["faq"]
    items = "".join(
        f"<details><summary>{e(i['q'])}</summary><p>{e(i['a'])}</p></details>" for i in f["items"]
    )
    body = f"""
<section class="page-head has-photo"><div class="wrap page-head-grid"><div><h1>{e(f['title'])}</h1></div>{head_photo(ctx)}</div></section>
<section class="section"><div class="wrap narrow faq">{items}</div></section>
{cta_band(ctx, ctx.t['services']['cta_title'], ctx.t['services']['cta_text'], ctx.t['services']['cta'])}
"""
    return f["title"], f["description"], body


def page_contact(ctx):
    c, com = ctx.t["contact"], ctx.t["common"]
    opts = "".join(f'<option value="{e(k)}">{e(v)}</option>' for k, v in c["service_options"].items())
    consent = e(c["consent"]).replace(
        "{privacy_link}", f'<a href="{ctx.url("privacy")}">{e(c["privacy_link_text"])}</a>'
    )
    msgs = json.dumps(
        {"sending": c["sending"], "submit": c["submit"], "error": c["error"], "invalid": c["invalid"], "not_configured": c["not_configured"]},
        ensure_ascii=False,
    )
    body = f"""
<section class="page-head has-photo"><div class="wrap page-head-grid"><div><h1>{e(c['title'])}</h1><p class="lead">{e(c['intro'])}</p></div>{head_photo(ctx)}</div></section>
<section class="section">
  <div class="wrap contact-grid">
    <aside class="details">
      <h2>{e(c['details_title'])}</h2>
      <ul class="plain icons">
        <li>{ico('pin')}<span><strong>{e(com['address_label'])}</strong><br>{e(com['address'])}</span></li>
        <li>{ico('phone')}<span><strong>{e(com['phone_label'])}</strong><br><a href="tel:{PHONE_TEL}">{PHONE_DISPLAY}</a></span></li>
        <li><span class="ico wa-ico">{WHATSAPP_ICON}</span><span><strong>WhatsApp</strong><br><a href="{e(ctx.whatsapp_url())}" target="_blank" rel="noopener">{e(com['whatsapp'])}</a></span></li>
        <li>{ico('mail')}<span><strong>{e(com['email_label'])}</strong><br><a href="mailto:{EMAIL}">{EMAIL}</a></span></li>
        <li>{ico('clock')}<span><strong>{e(com['hours_label'])}</strong><br>{e(com['hours'])}<br>{e(com['closed'])}</span></li>
        <li>{ico('home')}<span>{e(com['area'])}<br>{e(com['no_practice'])}</span></li>
      </ul>
    </aside>
    <div class="form-card" id="form">
      <h2>{e(c['form_title'])}</h2>
      <form id="contact-form" novalidate data-lang="{ctx.lang}" data-messages='{e(msgs, quote=True)}'>
        <div class="row">
          <div class="field"><label for="f-first">{e(c['first_name'])} <span class="req">*</span></label>
            <input id="f-first" name="first_name" type="text" autocomplete="given-name" required maxlength="60"></div>
          <div class="field"><label for="f-last">{e(c['last_name'])} <span class="req">*</span></label>
            <input id="f-last" name="last_name" type="text" autocomplete="family-name" required maxlength="59"></div>
        </div>
        <div class="row">
          <div class="field"><label for="f-email">{e(c['email'])} <span class="req">*</span></label>
            <input id="f-email" name="email" type="email" autocomplete="email" required maxlength="254"></div>
          <div class="field"><label for="f-phone">{e(c['phone'])}</label>
            <input id="f-phone" name="phone" type="tel" autocomplete="tel" maxlength="40"></div>
        </div>
        <div class="row">
          <div class="field"><label for="f-town">{e(c['town'])}</label>
            <input id="f-town" name="town" type="text" maxlength="120" aria-describedby="town-hint">
            <small id="town-hint">{e(c['town_hint'])}</small></div>
          <div class="field"><label for="f-service">{e(c['service'])}</label>
            <select id="f-service" name="service">{opts}</select></div>
        </div>
        <div class="field"><label for="f-subject">{e(c['subject'])}</label>
          <input id="f-subject" name="subject" type="text" maxlength="200"></div>
        <div class="field"><label for="f-message">{e(c['message'])} <span class="req">*</span></label>
          <textarea id="f-message" name="message" rows="6" required minlength="5" maxlength="4000"></textarea></div>
        <fieldset class="field reply">
          <legend>{e(c['reply_by'])}</legend>
          <label><input type="radio" name="reply_by" value="email" checked> {e(c['reply_email'])}</label>
          <label><input type="radio" name="reply_by" value="phone"> {e(c['reply_phone'])}</label>
        </fieldset>
        <div class="hp" aria-hidden="true"><label>Website <input type="text" name="website" tabindex="-1" autocomplete="off"></label></div>
        <label class="consent"><input type="checkbox" name="consent" required> <span>{consent} <span class="req">*</span></span></label>
        <p class="status" role="status" aria-live="polite"></p>
        <button class="btn" type="submit">{e(c['submit'])}</button>
      </form>
      <div class="success" hidden>
        <h3>{e(c['success_title'])}</h3><p>{e(c['success'])}</p>
      </div>
    </div>
  </div>
</section>
"""
    return c["title"], c["description"], body


def page_appointment(ctx):
    a, c, com = ctx.t["appointment"], ctx.t["contact"], ctx.t["common"]
    opts = f'<option value="">{e(c["service_options"][""])}</option>' + "".join(
        f'<option value="{e(i["id"])}">{e(i["title"])}</option>' for i in ctx.t["services"]["items"]
    ) + f'<option value="other">{e(c["service_options"]["other"])}</option>'
    consent = e(a["consent"]).replace(
        "{privacy_link}", f'<a href="{ctx.url("privacy")}">{e(c["privacy_link_text"])}</a>'
    )
    msgs = json.dumps(
        {"sending": c["sending"], "submit": a["submit"], "error": c["error"], "invalid": c["invalid"], "not_configured": c["not_configured"],
         "prev": a["prev"], "next": a["next"], "err_date": a["err_date"], "err_time": a["err_time"], "err_full": a["err_full"]},
        ensure_ascii=False,
    )
    slots = "".join(
        f'<label class="slot"><input type="radio" name="time" value="{s}" disabled><span>{s}</span></label>' for s in SLOTS
    )
    body = f"""
<section class="page-head has-photo"><div class="wrap page-head-grid"><div><h1>{e(a['title'])}</h1><p class="lead">{e(a['intro'])}</p></div>{head_photo(ctx)}</div></section>
<section class="section">
  <div class="wrap narrow">
    <div class="plan-note">{ico('clock')}<div><strong>{e(a['notice_title'])}</strong><p>{e(a['notice'])} <a class="nowrap" href="tel:{PHONE_TEL}">{PHONE_DISPLAY}</a></p></div></div>
    <div class="form-card">
      <h2>{e(a['form_title'])}</h2>
      <form id="appointment-form" novalidate data-lang="{ctx.lang}" data-messages='{e(msgs, quote=True)}'>
        <fieldset class="field pick" id="pick-date">
          <legend>1. {e(a['step_date'])} <span class="req">*</span></legend>
          <div class="cal" id="cal"></div>
          <small>{e(a['cal_hint'])}</small>
        </fieldset>
        <fieldset class="field pick" id="pick-time">
          <legend>2. {e(a['step_time'])} <span class="req">*</span></legend>
          <p class="picked" id="picked-date">{e(a['choose_date_first'])}</p>
          <div class="slots">{slots}</div>
          <small>{e(a['time_hint'])}</small>
        </fieldset>
        <h3>3. {e(a['step_details'])}</h3>
        <div class="row">
          <div class="field"><label for="a-first">{e(c['first_name'])} <span class="req">*</span></label>
            <input id="a-first" name="first_name" type="text" autocomplete="given-name" required maxlength="60"></div>
          <div class="field"><label for="a-last">{e(c['last_name'])} <span class="req">*</span></label>
            <input id="a-last" name="last_name" type="text" autocomplete="family-name" required maxlength="59"></div>
        </div>
        <div class="row">
          <div class="field"><label for="a-email">{e(c['email'])} <span class="req">*</span></label>
            <input id="a-email" name="email" type="email" autocomplete="email" required maxlength="254"></div>
          <div class="field"><label for="a-phone">{e(c['phone'])} <span class="req">*</span></label>
            <input id="a-phone" name="phone" type="tel" autocomplete="tel" required minlength="6" maxlength="40"></div>
        </div>
        <div class="row">
          <div class="field"><label for="a-address">{e(a['address'])} <span class="req">*</span></label>
            <input id="a-address" name="address" type="text" autocomplete="street-address" required minlength="3" maxlength="200" aria-describedby="addr-hint">
            <small id="addr-hint">{e(a['address_hint'])}</small></div>
          <div class="field"><label for="a-town">{e(a['town'])} <span class="req">*</span></label>
            <input id="a-town" name="town" type="text" autocomplete="address-level2" required minlength="2" maxlength="120"></div>
        </div>
        <div class="field"><label for="a-service">{e(c['service'])}</label>
          <select id="a-service" name="service">{opts}</select></div>
        <div class="field"><label for="a-message">{e(a['message'])}</label>
          <textarea id="a-message" name="message" rows="4" maxlength="4000"></textarea></div>
        <div class="hp" aria-hidden="true"><label>Website <input type="text" name="website" tabindex="-1" autocomplete="off"></label></div>
        <label class="consent"><input type="checkbox" name="consent" required> <span>{consent} <span class="req">*</span></span></label>
        <p class="status" role="status" aria-live="polite"></p>
        <button class="btn" type="submit">{e(a['submit'])}</button>
      </form>
      <div class="success" hidden tabindex="-1">
        <h3>{e(a['success_title'])}</h3><p>{e(a['success'])}</p>
      </div>
      <noscript><p>{e(c['not_configured'])} <a href="tel:{PHONE_TEL}">{PHONE_DISPLAY}</a></p></noscript>
    </div>
  </div>
</section>
"""
    return a["title"], a["description"], body


def page_privacy(ctx):
    p = ctx.t["privacy"]
    secs = "".join(f"<h2>{e(s['h'])}</h2><p>{e(s['p'])}</p>" for s in p["sections"])
    body = f"""
<section class="page-head has-photo"><div class="wrap page-head-grid"><div><h1>{e(p['title'])}</h1></div>{head_photo(ctx)}</div></section>
<section class="section"><div class="wrap narrow prose">{secs}</div></section>
"""
    return p["title"], p["description"], body


BUILDERS = {"home": page_home, "about": page_about, "services": page_services, "faq": page_faq, "appointment": page_appointment, "contact": page_contact, "privacy": page_privacy}


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main():
    base = load("en")
    translations = {l: load(l) for l in LANGS}
    for l in LANGS[1:]:
        missing = check_keys(base, translations[l])
        if missing:
            raise SystemExit(f"{l}.json is missing keys: {missing}")

    for l in LANGS:
        shutil.rmtree(SITE / l, ignore_errors=True)
    for lang in LANGS:
        t = translations[lang]
        for page in PAGES:
            ctx = Ctx(lang, page, t)
            title, desc, body = BUILDERS[page](ctx)
            write(SITE / lang / PATHS[page] / "index.html", head(ctx, title, desc) + header(ctx) + body + footer(ctx))

    # Root: pick a language from the browser, English is the fallback.
    write(SITE / "index.html", f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>PhysioFit365</title>
<link rel="icon" href="assets/img/favicon.svg" type="image/svg+xml">
<link rel="icon" href="assets/img/favicon.ico" sizes="48x48">
<meta name="description" content="{e(translations['en']['home']['description'])}">
<link rel="canonical" href="{BASE_URL}/en/">
<noscript><meta http-equiv="refresh" content="0; url=en/"></noscript>
<script>
(function () {{
  var l = (navigator.language || "en").slice(0, 2).toLowerCase();
  location.replace(({json.dumps(LANGS)}.indexOf(l) > -1 ? l : "en") + "/");
}})();
</script></head>
<body><p><a href="en/">English</a> · <a href="nl/">Nederlands</a> · <a href="es/">Español</a></p></body></html>
""")
    # GitHub Pages serves this for unknown addresses, with a real 404 status.
    write(SITE / "404.html", f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Page not found | PhysioFit365</title>
<meta name="robots" content="noindex">
<link rel="icon" href="/assets/img/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/assets/css/style.css">
</head>
<body><main id="main"><section class="section"><div class="wrap narrow">
<p><a href="/en/"><img src="/assets/img/logo.png" alt="PhysioFit365" width="132" height="74"></a></p>
<h1>Page not found</h1>
<p><a href="/en/">English</a> · <a href="/nl/" lang="nl">Pagina niet gevonden: naar de homepage</a> · <a href="/es/" lang="es">Página no encontrada: ir al inicio</a></p>
</div></section></main></body></html>
""")
    lastmod = last_modified()
    lastmod_tag = f"<lastmod>{lastmod}</lastmod>" if lastmod else ""
    urls = "".join(
        f"<url><loc>{abs_url(l, p)}</loc>{lastmod_tag}" + "".join(
            f'<xhtml:link rel="alternate" hreflang="{x}" href="{abs_url(x, p)}"/>' for x in LANGS
        ) + f'<xhtml:link rel="alternate" hreflang="x-default" href="{abs_url("en", p)}"/>' + "</url>\n"
        for l in LANGS for p in PAGES
    )
    write(SITE / "sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n{urls}</urlset>\n')
    write(SITE / "robots.txt", f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n")
    print(f"Built {len(LANGS) * len(PAGES)} pages in {SITE}")


if __name__ == "__main__":
    main()
