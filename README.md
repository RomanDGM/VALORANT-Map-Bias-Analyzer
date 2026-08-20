# VALORANT Map Bias Analyzer

A data pipeline that scrapes competitive match data from the **HenrikDev VALORANT API**, stores it in SQLite, and applies **logistic regression**, **chi-square tests**, and **odds ratio analysis** to determine whether each map statistically favors the attacking or defending side.

Built using data from **LATAM Radiant-tier players** during **V26 Act I (e11a4)**.

---

## Key Findings (V26 Act I — LATAM Radiant, ~2,600 matches)

| Map     | Attacker WR | Defender WR | Difference | Classification     | Odds Ratio | p-value |
|---------|-------------|-------------|------------|--------------------|------------|---------|
| Ascent  | 55.7%       | 43.2%       | +12.5pp    | **ATTACKER-sided** | 1.653      | 0.019 ✓ |
| Breeze  | 53.6%       | 44.3%       | +9.3pp     | **ATTACKER-sided** | 1.451      | 0.068   |
| Haven   | 52.1%       | 46.4%       | +5.7pp     | **ATTACKER-sided** | 1.258      | 0.262   |
| Lotus   | 51.6%       | 47.4%       | +4.2pp     | Balanced           | 1.184      | 0.412   |
| Sunset  | 51.0%       | 46.9%       | +4.1pp     | Balanced           | 1.180      | 0.417   |
| Summit  | 49.8%       | 49.2%       | +0.5pp     | Balanced           | 1.021      | 0.920   |
| Split   | 49.5%       | 50.0%       | -0.5pp     | Balanced           | 0.979      | 0.917   |

> **Ascent** is the only map with a statistically significant side bias (p < 0.05). Attackers are **1.65× more likely to win** on Ascent at Radiant LATAM level — notably diverging from the global average (45.9% attacker WR), suggesting a rank and region-specific meta effect.

---

## Project Structure

```
valorant-map-bias/
├── main.py          # CLI entry point
├── config.py        # API key, region, season settings
├── scraper.py       # HenrikDev API scraper (v4)
├── database.py      # SQLite schema and CRUD operations
├── analysis.py      # Win rates, logistic regression, chi-square, odds ratio
├── dashboard.py     # Matplotlib visualizations
├── requirements.txt
├── .env.example     # API key template
└── data/
    ├── valorant.db          # SQLite database (git-ignored)
    ├── win_rates.png        # Generated chart
    ├── classification.png   # Generated chart
    └── confusion_matrix.png # Generated chart
```

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/your-username/valorant-map-bias.git
cd valorant-map-bias
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Set your API key**

Get a free key at [https://api.henrikdev.xyz/dashboard/api-keys](https://api.henrikdev.xyz/dashboard/api-keys), then either:

```bash
# Option A — environment variable (recommended)
export HENRIKDEV_API_KEY=HDEV-your-key-here   # Linux/Mac
set HENRIKDEV_API_KEY=HDEV-your-key-here      # Windows

# Option B — edit config.py directly (never commit this)
API_KEY = "HDEV-your-key-here"
```

**4. Configure region and season in `config.py`**
```python
REGION       = "latam"   # eu, na, latam, br, ap, kr
SEASON_SHORT = "e11a4"   # e11a4 = V26 Act I
```

---

## Usage

```bash
# Scrape top 100 leaderboard players (20 matches each)
python main.py --leaderboard --top 100 --matches 20

# Scrape a specific player
python main.py --scrape PlayerName TAG

# Run analysis + generate charts
python main.py --analyze --dashboard

# Do everything in one command
python main.py --all
```

### All flags

| Flag | Description |
|------|-------------|
| `--leaderboard` | Fetch top N players from the ranked leaderboard and scrape their matches |
| `--top N` | Number of leaderboard players to process (default: 100) |
| `--matches N` | Matches per player (default: 20) |
| `--scrape NAME TAG` | Scrape a specific player |
| `--analyze` | Run the full statistical analysis |
| `--dashboard` | Generate charts in `data/` |
| `--all` | Leaderboard + analyze + dashboard |

---

## How It Works

### 1. Data collection
The scraper hits three HenrikDev endpoints:
- `GET /valorant/v3/leaderboard/{region}/{platform}` — top ranked players
- `GET /valorant/v4/matches/{region}/{platform}/{name}/{tag}` — match history
- `GET /valorant/v4/match/{region}/{matchid}` — full match detail

Each match is stored with its map, team starting sides, and outcome. Duplicate matches are automatically skipped.

### 2. Win rate analysis
For each map, attacker and defender win rates are computed and compared against a ±5pp threshold to classify the map.

### 3. Statistical testing

**Chi-square test** — tests whether starting side and match outcome are independent. A p-value < 0.05 indicates the side assignment is not random with respect to winning.

**Odds Ratio (logistic regression via statsmodels)** — quantifies *how much* attacking affects win probability, with a 95% confidence interval. An OR > 1 with CI not crossing 1 confirms a real effect.

**Logistic regression (sklearn)** — trained on `[map, side]` to predict outcomes. Accuracy near 50% is expected given VALORANT's design for balance; the value lies in the coefficients and per-map tests above.

### 4. Why accuracy ≈ 52% is not a failure
VALORANT is balanced by design — the model's feature set (map + side) explains only a fraction of match variance. The meaningful outputs are the **odds ratios and p-values**, not classification accuracy. This is consistent with how side-bias is analyzed in competitive game research.

---

## Notes

- **Rate limit**: The free HenrikDev tier allows 30 req/min. The scraper enforces a 2s delay between calls and retries automatically on 429 responses.
- **Data accumulation**: Re-running the scraper adds new data without duplicating existing matches. Delete `data/valorant.db` to start fresh.
- **Season filter**: Only matches from `SEASON_SHORT` are stored. Update this value in `config.py` when a new act begins.

---

## Tech Stack

`Python` · `SQLite` · `pandas` · `scikit-learn` · `statsmodels` · `scipy` · `matplotlib` · `HenrikDev API`
