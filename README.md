# ⚡ Tech Digest

Dagelijkse tech nieuwspagina voor cloud engineers — gratis, automatisch, geen email.

## Hoe instellen (5 minuten)

### 1. Maak een GitHub repository aan
Ga naar [github.com/new](https://github.com/new) en maak een **publieke** repository aan, bijv. `tech-digest`.

### 2. Upload de bestanden
Upload beide bestanden naar je repository:
- `fetch_news.py`
- `.github/workflows/update.yml`

### 3. Zet GitHub Pages aan
Ga naar je repository → **Settings** → **Pages** → kies als source **GitHub Actions**.

### 4. Eerste run handmatig starten
Ga naar **Actions** → **Update Tech Digest** → **Run workflow**.
Na ~30 seconden staat je digest live op:
`https://JOUWGEBRUIKERSNAAM.github.io/tech-digest/`

### 5. Voeg toe aan je telefoon
Open de URL in Safari of Chrome op je telefoon en voeg hem toe aan je beginscherm:
- **iPhone**: Deel-knop → "Zet op beginscherm"
- **Android**: Menu → "Toevoegen aan beginscherm"

## Automatisch bijwerken
De pagina wordt elke ochtend om 07:00 automatisch bijgewerkt via GitHub Actions. Gratis!

## Feeds aanpassen
Open `fetch_news.py` en pas de `FEEDS`-lijst bovenin het bestand aan.
Voeg toe wat je wil, verwijder wat je niet interesseert.

---
*Gebouwd met Python + GitHub Actions + GitHub Pages*
