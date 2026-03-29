import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import html
import re
import json
import time
 
# ── Feeds om te volgen ────────────────────────────────────────────────────────
FEEDS = [
    {"name": "Hacker News",    "url": "https://news.ycombinator.com/rss",               "emoji": "🔶"},
    {"name": "AWS Blog",       "url": "https://aws.amazon.com/blogs/aws/feed/",          "emoji": "☁️"},
    {"name": "Kubernetes",     "url": "https://kubernetes.io/feed.xml",                  "emoji": "⚙️"},
    {"name": "CNCF",           "url": "https://www.cncf.io/feed/",                       "emoji": "🌐"},
    {"name": "HashiCorp",      "url": "https://www.hashicorp.com/blog/feed.xml",         "emoji": "🔷"},
    {"name": "The Register",   "url": "https://www.theregister.com/headlines.atom",      "emoji": "📰"},
    {"name": "Docker",         "url": "https://www.docker.com/feed/",                    "emoji": "🐳"},
    {"name": "Google Cloud",   "url": "https://cloudblog.withgoogle.com/rss/",           "emoji": "🔵"},
]
 
MAX_PER_FEED = 5
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; TechDigestBot/1.0)"}
 
def clean_html(raw: str) -> str:
    """Verwijder HTML-tags en maak tekst leesbaar."""
    if not raw:
        return ""
    soup = BeautifulSoup(raw, "html.parser")
    text = soup.get_text(separator=" ")
    text = re.sub(r'\s+', ' ', text).strip()
    return text
 
def fetch_full_article(url: str) -> str:
    """Haal de volledige artikeltekst op van de originele URL."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
 
        # Verwijder navigatie, header, footer, sidebar, scripts
        for tag in soup(["nav", "header", "footer", "aside", "script",
                          "style", "form", "iframe", "figure"]):
            tag.decompose()
 
        # Zoek de hoofd-inhoud in deze volgorde
        content = (
            soup.find("article") or
            soup.find(attrs={"role": "main"}) or
            soup.find("main") or
            soup.find(class_=re.compile(r"(post|article|entry|content|body)[-_]?(content|body|text|main)?", re.I)) or
            soup.find("body")
        )
 
        if not content:
            return ""
 
        paragraphs = content.find_all("p")
        text = " ".join(p.get_text(separator=" ") for p in paragraphs)
        text = re.sub(r'\s+', ' ', text).strip()
 
        # Maximaal ~3000 tekens (genoeg voor 10 minuten lezen)
        if len(text) > 3000:
            text = text[:3000] + "…"
 
        return text
    except Exception:
        return ""
 
def fetch_feed(feed_info: dict) -> list:
    """Haal artikelen op uit één RSS feed, inclusief volledige tekst."""
    try:
        parsed = feedparser.parse(feed_info["url"])
        articles = []
        for entry in parsed.entries[:MAX_PER_FEED]:
            title   = html.unescape(entry.get("title", "Geen titel"))
            link    = entry.get("link", "#")
            summary = clean_html(entry.get("summary", entry.get("description", "")))
            # Beperk samenvatting tot ~300 tekens voor de kaart
            short_summary = summary[:300] + ("…" if len(summary) > 300 else "")
 
            # Datum
            pub = entry.get("published_parsed") or entry.get("updated_parsed")
            if pub:
                dt = datetime(*pub[:6], tzinfo=timezone.utc)
                date_str = dt.strftime("%-d %b %Y")
            else:
                date_str = "–"
 
            print(f"    📄 Ophalen: {title[:60]}…")
            full_text = fetch_full_article(link)
            # Als ophalen mislukt, gebruik RSS-beschrijving als fallback
            if not full_text:
                full_text = summary
            time.sleep(0.5)  # Vriendelijk voor servers
 
            articles.append({
                "title":      title,
                "link":       link,
                "summary":    short_summary,
                "full_text":  full_text,
                "date":       date_str,
                "source":     feed_info["name"],
                "emoji":      feed_info["emoji"],
            })
        return articles
    except Exception as e:
        print(f"[WARN] Kon {feed_info['name']} niet laden: {e}")
        return []
 
def generate_html(all_articles: list) -> str:
    """Genereer een mooie, mobiel-vriendelijke HTML pagina met ingebouwde reader."""
    now = datetime.now().strftime("%-d %B %Y, %H:%M")
 
    # Sla artikeldata op als JSON voor JavaScript
    articles_json = json.dumps([{
        "title":     a["title"],
        "link":      a["link"],
        "full_text": a["full_text"],
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
        </article>
        """
 
    return f"""<!DOCTYPE html>
<html lang="nl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Tech Digest</title>
  <style>
    :root {{
      --bg:       #0f1117;
      --surface:  #1a1d27;
      --border:   #2a2d3a;
      --accent:   #5b8af7;
      --text:     #e2e8f0;
      --muted:    #8892a4;
      --radius:   12px;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 16px;
      line-height: 1.6;
      padding: 1rem;
    }}
    header {{
      max-width: 720px;
      margin: 0 auto 1.5rem;
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      flex-wrap: wrap;
      gap: .5rem;
    }}
    header h1 {{ font-size: 1.4rem; color: var(--accent); }}
    header .updated {{ font-size: .8rem; color: var(--muted); }}
    .feed-filter {{
      max-width: 720px;
      margin: 0 auto 1.25rem;
      display: flex;
      flex-wrap: wrap;
      gap: .5rem;
    }}
    .filter-btn {{
      background: var(--surface);
      border: 1px solid var(--border);
      color: var(--muted);
      padding: .3rem .75rem;
      border-radius: 999px;
      font-size: .8rem;
      cursor: pointer;
      transition: all .15s;
    }}
    .filter-btn.active, .filter-btn:hover {{
      background: var(--accent);
      color: #fff;
      border-color: var(--accent);
    }}
    .cards {{
      max-width: 720px;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }}
    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1rem 1.25rem;
      cursor: pointer;
      transition: border-color .15s, transform .1s;
    }}
    .card:hover {{ border-color: var(--accent); transform: translateY(-1px); }}
    .card-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: .4rem;
    }}
    .source {{
      font-size: .75rem;
      font-weight: 600;
      color: var(--accent);
      text-transform: uppercase;
      letter-spacing: .05em;
    }}
    .date {{ font-size: .75rem; color: var(--muted); }}
    .title {{ font-size: 1rem; font-weight: 600; margin-bottom: .5rem; color: var(--text); }}
    .summary {{ font-size: .875rem; color: var(--muted); margin-bottom: .5rem; }}
    .read-more {{ font-size: .8rem; color: var(--accent); }}
 
    /* ── Reader overlay ─────────────────────────────── */
    .overlay {{
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,.6);
      z-index: 10;
    }}
    .overlay.open {{ display: block; }}
    .reader {{
      position: fixed;
      bottom: 0; left: 0; right: 0;
      background: var(--surface);
      border-radius: var(--radius) var(--radius) 0 0;
      max-height: 90vh;
      overflow-y: auto;
      z-index: 20;
      transform: translateY(100%);
      transition: transform .3s ease;
      padding: 1.5rem 1.25rem 2rem;
    }}
    .reader.open {{ transform: translateY(0); }}
    .reader-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 1rem;
      gap: 1rem;
    }}
    .reader-meta {{
      font-size: .75rem;
      color: var(--accent);
      text-transform: uppercase;
      letter-spacing: .05em;
      margin-bottom: .4rem;
    }}
    .reader-title {{
      font-size: 1.2rem;
      font-weight: 700;
      line-height: 1.4;
      color: var(--text);
    }}
    .close-btn {{
      background: var(--border);
      border: none;
      color: var(--muted);
      width: 32px; height: 32px;
      border-radius: 50%;
      font-size: 1.2rem;
      cursor: pointer;
      flex-shrink: 0;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .reader-body {{
      font-size: .95rem;
      color: var(--text);
      line-height: 1.8;
      margin-top: 1rem;
    }}
    .reader-footer {{
      margin-top: 1.5rem;
      padding-top: 1rem;
      border-top: 1px solid var(--border);
      display: flex;
      gap: 1rem;
    }}
    .btn {{
      padding: .5rem 1rem;
      border-radius: 8px;
      font-size: .875rem;
      cursor: pointer;
      border: none;
    }}
    .btn-primary {{
      background: var(--accent);
      color: #fff;
      text-decoration: none;
    }}
    .btn-secondary {{
      background: var(--border);
      color: var(--muted);
    }}
    @media (min-width: 640px) {{
      .reader {{
        max-width: 720px;
        left: 50%; right: auto;
        transform: translateX(-50%) translateY(100%);
        border-radius: var(--radius);
        bottom: 1rem;
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
 
  <!-- Reader overlay -->
  <div class="overlay" id="overlay" onclick="closeReader()"></div>
  <div class="reader" id="reader">
    <div class="reader-header">
      <div>
        <div class="reader-meta" id="r-meta"></div>
        <div class="reader-title" id="r-title"></div>
      </div>
      <button class="close-btn" onclick="closeReader()">✕</button>
    </div>
    <div class="reader-body" id="r-body"></div>
    <div class="reader-footer">
      <a id="r-link" class="btn btn-primary" target="_blank" rel="noopener">Origineel artikel →</a>
      <button class="btn btn-secondary" onclick="closeReader()">Sluiten</button>
    </div>
  </div>
 
  <script>
    const ARTICLES = {articles_json};
 
    // Filter-knoppen
    const cards = document.querySelectorAll('.card');
    const sources = [...new Set([...cards].map(c => c.dataset.source))];
    const container = document.getElementById('filters');
 
    function addBtn(label, value) {{
      const btn = document.createElement('button');
      btn.className = 'filter-btn' + (value === 'all' ? ' active' : '');
      btn.textContent = label;
      btn.onclick = () => {{
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        cards.forEach(card => {{
          card.style.display = (value === 'all' || card.dataset.source === value) ? '' : 'none';
        }});
      }};
      container.appendChild(btn);
    }}
    addBtn('Alles', 'all');
    sources.forEach(s => addBtn(s, s));
 
    // Reader
    function openReader(index) {{
      const a = ARTICLES[index];
      document.getElementById('r-meta').textContent = a.emoji + ' ' + a.source + ' · ' + a.date;
      document.getElementById('r-title').textContent = a.title;
      document.getElementById('r-body').textContent  = a.full_text || 'Inhoud niet beschikbaar.';
      document.getElementById('r-link').href         = a.link;
      document.getElementById('overlay').classList.add('open');
      document.getElementById('reader').classList.add('open');
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
    print("📡 Feeds ophalen…")
    all_articles = []
    for feed in FEEDS:
        print(f"\n  {feed['emoji']} {feed['name']}:")
        articles = fetch_feed(feed)
        print(f"  ✅ {len(articles)} artikelen opgehaald")
        all_articles.extend(articles)
 
    print(f"\n✅ Totaal: {len(all_articles)} artikelen")
    print("🖊️  HTML genereren…")
 
    html_output = generate_html(all_articles)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_output)
 
    print("✅ index.html aangemaakt!")