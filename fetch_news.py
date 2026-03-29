import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import html
import re

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

# Maximum artikelen per feed
MAX_PER_FEED = 5

def clean_html(raw: str) -> str:
    """Verwijder HTML-tags en maak tekst leesbaar."""
    if not raw:
        return ""
    soup = BeautifulSoup(raw, "html.parser")
    text = soup.get_text(separator=" ")
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:400] + ("…" if len(text) > 400 else "")

def fetch_feed(feed_info: dict) -> list:
    """Haal artikelen op uit één RSS feed."""
    try:
        parsed = feedparser.parse(feed_info["url"])
        articles = []
        for entry in parsed.entries[:MAX_PER_FEED]:
            title   = html.unescape(entry.get("title", "Geen titel"))
            link    = entry.get("link", "#")
            summary = clean_html(entry.get("summary", entry.get("description", "")))
            # Datum
            pub = entry.get("published_parsed") or entry.get("updated_parsed")
            if pub:
                dt = datetime(*pub[:6], tzinfo=timezone.utc)
                date_str = dt.strftime("%-d %b %Y")
            else:
                date_str = "–"
            articles.append({
                "title":   title,
                "link":    link,
                "summary": summary,
                "date":    date_str,
                "source":  feed_info["name"],
                "emoji":   feed_info["emoji"],
            })
        return articles
    except Exception as e:
        print(f"[WARN] Kon {feed_info['name']} niet laden: {e}")
        return []

def generate_html(all_articles: list) -> str:
    """Genereer een mooie, mobiel-vriendelijke HTML pagina."""
    now = datetime.now().strftime("%-d %B %Y, %H:%M")
    cards_html = ""

    for a in all_articles:
        summary_block = f'<p class="summary">{a["summary"]}</p>' if a["summary"] else ""
        cards_html += f"""
        <article class="card">
            <div class="card-header">
                <span class="source">{a["emoji"]} {a["source"]}</span>
                <span class="date">{a["date"]}</span>
            </div>
            <h2 class="title"><a href="{a["link"]}" target="_blank" rel="noopener">{a["title"]}</a></h2>
            {summary_block}
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
      transition: border-color .15s;
    }}
    .card:hover {{ border-color: var(--accent); }}
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
    .title {{ font-size: 1rem; font-weight: 600; margin-bottom: .5rem; }}
    .title a {{ color: var(--text); text-decoration: none; }}
    .title a:hover {{ color: var(--accent); }}
    .summary {{ font-size: .875rem; color: var(--muted); }}
    @media (max-width: 480px) {{
      .title {{ font-size: .95rem; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>⚡ Tech Digest</h1>
    <span class="updated">Bijgewerkt: {now}</span>
  </header>

  <div class="feed-filter" id="filters"></div>
  <div class="cards" id="cards">
    {cards_html}
  </div>

  <script>
    // Filter-knoppen dynamisch opbouwen
    const cards = document.querySelectorAll('.card');
    const sources = [...new Set([...cards].map(c => c.querySelector('.source').textContent.replace(/^.+? /, '')))];
    const container = document.getElementById('filters');

    function addBtn(label, value) {{
      const btn = document.createElement('button');
      btn.className = 'filter-btn' + (value === 'all' ? ' active' : '');
      btn.textContent = label;
      btn.dataset.filter = value;
      btn.onclick = () => {{
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        cards.forEach(card => {{
          const src = card.querySelector('.source').textContent.replace(/^.+? /, '');
          card.style.display = (value === 'all' || src === value) ? '' : 'none';
        }});
      }};
      container.appendChild(btn);
    }}

    addBtn('Alles', 'all');
    sources.forEach(s => addBtn(s, s));
  </script>
</body>
</html>
"""

if __name__ == "__main__":
    print("📡 Feeds ophalen…")
    all_articles = []
    for feed in FEEDS:
        articles = fetch_feed(feed)
        print(f"  {feed['emoji']} {feed['name']}: {len(articles)} artikelen")
        all_articles.extend(articles)

    print(f"\n✅ Totaal: {len(all_articles)} artikelen")
    print("🖊️  HTML genereren…")

    html_output = generate_html(all_articles)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_output)

    print("✅ index.html aangemaakt!")
