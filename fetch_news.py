import feedparser
import requests
from bs4 import BeautifulSoup, Comment
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
import html
import re
import json
import time

# ── Feeds om te volgen ────────────────────────────────────────────────────────
FEEDS = [
    {"name": "Hacker News",  "url": "https://news.ycombinator.com/rss",          "emoji": "🔶"},
    {"name": "AWS Blog",     "url": "https://aws.amazon.com/blogs/aws/feed/",     "emoji": "☁️"},
    {"name": "Kubernetes",   "url": "https://kubernetes.io/feed.xml",             "emoji": "⚙️"},
    {"name": "CNCF",         "url": "https://www.cncf.io/feed/",                  "emoji": "🌐"},
    {"name": "HashiCorp",    "url": "https://www.hashicorp.com/blog/feed.xml",    "emoji": "🔷"},
    {"name": "The Register", "url": "https://www.theregister.com/headlines.atom", "emoji": "📰"},
    {"name": "Docker",       "url": "https://www.docker.com/feed/",               "emoji": "🐳"},
    {"name": "Google Cloud", "url": "https://cloudblog.withgoogle.com/rss/",      "emoji": "🔵"},
]

MAX_PER_FEED = 5
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; TechDigestBot/1.0)"}

# Tags die we willen bewaren in de reader
ALLOWED_TAGS = {
    "p", "br", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "blockquote", "pre", "code",
    "strong", "b", "em", "i", "a", "img",
    "figure", "figcaption", "picture", "source",
    "table", "thead", "tbody", "tr", "th", "td",
}

def make_absolute(tag, attr, base_url):
    """Maak een relatieve URL absoluut."""
    val = tag.get(attr)
    if val and not val.startswith(("http", "data:", "//")):
        tag[attr] = urljoin(base_url, val)
    elif val and val.startswith("//"):
        tag[attr] = "https:" + val

def clean_html_text(raw: str) -> str:
    """Haal plain text uit HTML (voor de kaart-samenvatting)."""
    if not raw:
        return ""
    soup = BeautifulSoup(raw, "html.parser")
    text = soup.get_text(separator=" ")
    return re.sub(r'\s+', ' ', text).strip()

def fetch_full_article(url: str) -> str:
    """
    Haal het volledige artikel op en geef nette HTML terug,
    inclusief afbeeldingen en opmaak.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        base_url = url

        # Verwijder rommel
        for tag in soup(["nav", "header", "footer", "aside", "script",
                          "style", "form", "iframe", "button", "input",
                          "select", "textarea", "noscript"]):
            tag.decompose()
        # Verwijder HTML-commentaar
        for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
            comment.extract()

        # Zoek de hoofd-inhoud
        content = (
            soup.find("article") or
            soup.find(attrs={"role": "main"}) or
            soup.find("main") or
            soup.find(class_=re.compile(
                r"(post|article|entry|content|body)[-_]?(content|body|text|main)?", re.I
            )) or
            soup.find("body")
        )
        if not content:
            return ""

        # Maak URLs absoluut
        for img in content.find_all("img"):
            make_absolute(img, "src", base_url)
            make_absolute(img, "data-src", base_url)
            # Lazy-loaded afbeeldingen
            if img.get("data-src") and not img.get("src", "").startswith("http"):
                img["src"] = img["data-src"]
            img["loading"] = "lazy"
            img["style"]   = "max-width:100%;height:auto;border-radius:8px;margin:1rem 0;"
            # Verwijder overbodige attributen
            for attr in ["class", "id", "width", "height", "srcset", "sizes", "data-src"]:
                if attr in img.attrs:
                    del img[attr]

        for a in content.find_all("a"):
            make_absolute(a, "href", base_url)
            a["target"] = "_blank"
            a["rel"]    = "noopener"
            for attr in ["class", "id", "style"]:
                if attr in a.attrs:
                    del a[attr]

        # Verwijder alle niet-toegestane tags maar bewaar hun inhoud
        for tag in content.find_all(True):
            if tag.name not in ALLOWED_TAGS:
                tag.unwrap()

        # Verwijder lege class/id/style van overgebleven tags
        for tag in content.find_all(True):
            for attr in ["class", "id", "style", "data-*"]:
                tag.attrs = {k: v for k, v in tag.attrs.items()
                             if k in ("src", "href", "alt", "target",
                                      "rel", "loading", "colspan", "rowspan")}

        result = str(content)
        # Verwijder meerdere lege regels
        result = re.sub(r'\n{3,}', '\n\n', result)
        return result

    except Exception as e:
        print(f"      [WARN] Kon artikel niet ophalen: {e}")
        return ""

def fetch_feed(feed_info: dict) -> list:
    """Haal artikelen op uit één RSS feed."""
    try:
        parsed = feedparser.parse(feed_info["url"])
        articles = []
        for entry in parsed.entries[:MAX_PER_FEED]:
            title    = html.unescape(entry.get("title", "Geen titel"))
            link     = entry.get("link", "#")
            raw_sum  = entry.get("summary", entry.get("description", ""))
            summary  = clean_html_text(raw_sum)
            short    = summary[:280] + ("…" if len(summary) > 280 else "")

            pub = entry.get("published_parsed") or entry.get("updated_parsed")
            date_str = datetime(*pub[:6], tzinfo=timezone.utc).strftime("%-d %b %Y") if pub else "–"

            print(f"    📄 {title[:65]}")
            full_html = fetch_full_article(link)
            if not full_html:
                # Fallback: gebruik RSS-beschrijving als HTML
                full_html = f"<p>{summary}</p>"
            time.sleep(0.4)

            articles.append({
                "title":     title,
                "link":      link,
                "summary":   short,
                "full_html": full_html,
                "date":      date_str,
                "source":    feed_info["name"],
                "emoji":     feed_info["emoji"],
            })
        return articles
    except Exception as e:
        print(f"  [WARN] Feed mislukt ({feed_info['name']}): {e}")
        return []

def generate_html(all_articles: list) -> str:
    now = datetime.now().strftime("%-d %B %Y, %H:%M")

    articles_json = json.dumps([{
        "title":     a["title"],
        "link":      a["link"],
        "full_html": a["full_html"],
        "date":      a["date"],
        "source":    a["source"],
        "emoji":     a["emoji"],
    } for a in all_articles], ensure_ascii=False)

    cards_html = ""
    for i, a in enumerate(all_articles):
        cards_html += f"""
        <article class="card" data-source="{a['source']}" data-index="{i}" onclick="openReader({i})">
          <div class="card-header">
            <span class="source">{a["emoji"]} {a["source"]}</span>
            <span class="date">{a["date"]}</span>
          </div>
          <h2 class="title">{a["title"]}</h2>
          <p class="summary">{a["summary"]}</p>
          <span class="read-more">Lees verder →</span>
        </article>"""

    return f"""<!DOCTYPE html>
<html lang="nl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Tech Digest</title>
  <style>
    :root {{
      --bg:      #0f1117;
      --surface: #1a1d27;
      --border:  #2a2d3a;
      --accent:  #5b8af7;
      --text:    #e2e8f0;
      --muted:   #8892a4;
      --r:       12px;
    }}
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg); color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 16px; line-height: 1.6; padding: 1rem;
    }}
    /* ── Header ── */
    header {{
      max-width: 720px; margin: 0 auto 1.5rem;
      display: flex; justify-content: space-between;
      align-items: baseline; flex-wrap: wrap; gap: .5rem;
    }}
    header h1 {{ font-size: 1.4rem; color: var(--accent); }}
    .updated {{ font-size: .8rem; color: var(--muted); }}
    /* ── Filter ── */
    .feed-filter {{
      max-width: 720px; margin: 0 auto 1.25rem;
      display: flex; flex-wrap: wrap; gap: .5rem;
    }}
    .filter-btn {{
      background: var(--surface); border: 1px solid var(--border);
      color: var(--muted); padding: .3rem .75rem; border-radius: 999px;
      font-size: .8rem; cursor: pointer; transition: all .15s;
    }}
    .filter-btn.active, .filter-btn:hover {{
      background: var(--accent); color: #fff; border-color: var(--accent);
    }}
    /* ── Cards ── */
    .cards {{
      max-width: 720px; margin: 0 auto;
      display: flex; flex-direction: column; gap: 1rem;
    }}
    .card {{
      background: var(--surface); border: 1px solid var(--border);
      border-radius: var(--r); padding: 1rem 1.25rem;
      cursor: pointer; transition: border-color .15s, transform .1s;
    }}
    .card:hover {{ border-color: var(--accent); transform: translateY(-1px); }}
    .card-header {{
      display: flex; justify-content: space-between;
      align-items: center; margin-bottom: .4rem;
    }}
    .source {{
      font-size: .75rem; font-weight: 600; color: var(--accent);
      text-transform: uppercase; letter-spacing: .05em;
    }}
    .date {{ font-size: .75rem; color: var(--muted); }}
    .title {{ font-size: 1rem; font-weight: 600; margin-bottom: .5rem; }}
    .summary {{ font-size: .875rem; color: var(--muted); margin-bottom: .5rem; }}
    .read-more {{ font-size: .8rem; color: var(--accent); }}

    /* ── Overlay + Reader ── */
    .overlay {{
      display: none; position: fixed; inset: 0;
      background: rgba(0,0,0,.65); z-index: 10;
    }}
    .overlay.open {{ display: block; }}
    .reader {{
      position: fixed; bottom: 0; left: 0; right: 0;
      background: var(--surface); border-radius: var(--r) var(--r) 0 0;
      max-height: 92vh; overflow-y: auto; z-index: 20;
      transform: translateY(100%); transition: transform .3s ease;
      padding: 1.5rem 1.25rem 3rem;
    }}
    .reader.open {{ transform: translateY(0); }}
    .reader-top {{
      display: flex; justify-content: space-between;
      align-items: flex-start; gap: 1rem; margin-bottom: 1.25rem;
    }}
    .r-meta {{
      font-size: .75rem; color: var(--accent);
      text-transform: uppercase; letter-spacing: .05em; margin-bottom: .35rem;
    }}
    .r-title {{ font-size: 1.25rem; font-weight: 700; line-height: 1.35; }}
    .close-btn {{
      background: var(--border); border: none; color: var(--muted);
      width: 34px; height: 34px; border-radius: 50%; font-size: 1.1rem;
      cursor: pointer; flex-shrink: 0; display: flex;
      align-items: center; justify-content: center;
    }}

    /* ── Artikel-inhoud opmaak ── */
    .r-body {{ font-size: .95rem; line-height: 1.85; color: var(--text); }}
    .r-body h1, .r-body h2 {{
      font-size: 1.15rem; font-weight: 700; margin: 1.5rem 0 .6rem;
      color: var(--text); border-bottom: 1px solid var(--border); padding-bottom: .3rem;
    }}
    .r-body h3, .r-body h4 {{
      font-size: 1rem; font-weight: 600; margin: 1.25rem 0 .5rem; color: var(--text);
    }}
    .r-body p {{ margin-bottom: .9rem; }}
    .r-body ul, .r-body ol {{
      margin: .5rem 0 1rem 1.5rem;
    }}
    .r-body li {{ margin-bottom: .3rem; }}
    .r-body blockquote {{
      border-left: 3px solid var(--accent); margin: 1rem 0;
      padding: .5rem 1rem; color: var(--muted);
      background: rgba(91,138,247,.07); border-radius: 0 var(--r) var(--r) 0;
    }}
    .r-body pre {{
      background: #12151e; border: 1px solid var(--border);
      border-radius: 8px; padding: 1rem; overflow-x: auto;
      font-size: .85rem; margin: 1rem 0;
    }}
    .r-body code {{
      background: #12151e; padding: .15em .4em; border-radius: 4px;
      font-size: .875em; font-family: "JetBrains Mono", "Fira Code", monospace;
    }}
    .r-body pre code {{ background: none; padding: 0; font-size: inherit; }}
    .r-body img {{
      max-width: 100%; height: auto; border-radius: 8px;
      margin: 1rem 0; display: block;
    }}
    .r-body figure {{ margin: 1rem 0; }}
    .r-body figcaption {{
      font-size: .8rem; color: var(--muted); text-align: center; margin-top: .35rem;
    }}
    .r-body a {{ color: var(--accent); text-decoration: underline; }}
    .r-body table {{
      width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: .875rem;
    }}
    .r-body th, .r-body td {{
      border: 1px solid var(--border); padding: .5rem .75rem; text-align: left;
    }}
    .r-body th {{ background: var(--border); font-weight: 600; }}

    /* ── Footer ── */
    .r-footer {{
      margin-top: 1.75rem; padding-top: 1rem;
      border-top: 1px solid var(--border);
      display: flex; gap: .75rem; flex-wrap: wrap;
    }}
    .btn {{
      padding: .5rem 1.1rem; border-radius: 8px;
      font-size: .875rem; cursor: pointer; border: none; font-weight: 500;
    }}
    .btn-primary {{ background: var(--accent); color: #fff; text-decoration: none; }}
    .btn-secondary {{ background: var(--border); color: var(--muted); }}

    @media (min-width: 640px) {{
      .reader {{
        max-width: 720px; left: 50%; right: auto;
        transform: translateX(-50%) translateY(100%);
        border-radius: var(--r); bottom: 1rem;
        width: calc(100% - 2rem);
      }}
      .reader.open {{ transform: translateX(-50%) translateY(0); }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>⚡ Tech Digest</h1>
    <span class="updated">Bijgewerkt: {now}</span>
  </header>

  <div class="feed-filter" id="filters"></div>
  <div class="cards" id="cards">{cards_html}</div>

  <div class="overlay" id="overlay" onclick="closeReader()"></div>
  <div class="reader" id="reader">
    <div class="reader-top">
      <div>
        <div class="r-meta" id="r-meta"></div>
        <div class="r-title" id="r-title"></div>
      </div>
      <button class="close-btn" onclick="closeReader()">✕</button>
    </div>
    <div class="r-body" id="r-body"></div>
    <div class="r-footer">
      <a id="r-link" class="btn btn-primary" target="_blank" rel="noopener">Origineel artikel →</a>
      <button class="btn btn-secondary" onclick="closeReader()">Sluiten</button>
    </div>
  </div>

  <script>
    const ARTICLES = {articles_json};

    // Filterknoppen
    const cards = document.querySelectorAll('.card');
    const sources = [...new Set([...cards].map(c => c.dataset.source))];
    const filterContainer = document.getElementById('filters');

    function addBtn(label, value) {{
      const btn = document.createElement('button');
      btn.className = 'filter-btn' + (value === 'all' ? ' active' : '');
      btn.textContent = label;
      btn.onclick = () => {{
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        cards.forEach(c => c.style.display = (value === 'all' || c.dataset.source === value) ? '' : 'none');
      }};
      filterContainer.appendChild(btn);
    }}
    addBtn('Alles', 'all');
    sources.forEach(s => addBtn(s, s));

    // Reader openen
    function openReader(i) {{
      const a = ARTICLES[i];
      document.getElementById('r-meta').textContent  = a.emoji + ' ' + a.source + ' · ' + a.date;
      document.getElementById('r-title').textContent = a.title;
      document.getElementById('r-body').innerHTML    = a.full_html || '<p>Inhoud niet beschikbaar.</p>';
      document.getElementById('r-link').href         = a.link;
      document.getElementById('overlay').classList.add('open');
      document.getElementById('reader').classList.add('open');
      document.getElementById('reader').scrollTop    = 0;
      document.body.style.overflow = 'hidden';
    }}

    function closeReader() {{
      document.getElementById('overlay').classList.remove('open');
      document.getElementById('reader').classList.remove('open');
      document.body.style.overflow = '';
    }}

    document.addEventListener('keydown', e => {{ if (e.key === 'Escape') closeReader(); }});
  </script>
</body>
</html>
"""

if __name__ == "__main__":
    print("📡 Feeds ophalen…\n")
    all_articles = []
    for feed in FEEDS:
        print(f"  {feed['emoji']} {feed['name']}:")
        articles = fetch_feed(feed)
        print(f"  ✅ {len(articles)} artikelen\n")
        all_articles.extend(articles)

    print(f"✅ Totaal: {len(all_articles)} artikelen")
    print("🖊️  HTML genereren…")
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(generate_html(all_articles))
    print("✅ index.html klaar!")
