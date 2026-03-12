# Kalshi RFQ Dashboard

Real-time monitor for Kalshi prediction market RFQ (Request for Quote) flow. Focused on NBA props.

## Quick Start (give this to Claude or any AI assistant)

> "Set up the Kalshi RFQ Dashboard for me. Here's my Kalshi API key: `PASTE_KEY_HERE`. I've already dropped my private key .pem file in the repo folder. Follow the steps below."

### Step-by-step setup:

1. **Get your Kalshi API credentials:**
   - Log into [kalshi.com](https://kalshi.com) → Settings → API Keys
   - Create a new API key — you'll get two things:
     - **API key ID** (a UUID string like `466400ae-...`)
     - **Private key file** (a `.pem` file download)
   - Drop the `.pem` file into this repo directory

2. **Install Python dependencies:**
   ```
   pip install -r requirements.txt
   ```

3. **Create `config.json`** by copying `config.example.json`:
   ```
   cp config.example.json config.json
   ```
   Then edit `config.json` with your credentials:
   ```json
   {
       "api_key_id": "YOUR_KALSHI_API_KEY",
       "private_key_path": "your_downloaded_key.pem",
       "base_url": "https://api.elections.kalshi.com/trade-api/v2"
   }
   ```
   - `api_key_id`: The UUID you got from Kalshi
   - `private_key_path`: Just the filename of the `.pem` you dropped in (e.g. `"kalshi_key.pem"`)

4. **Run the dashboard:**
   ```
   python kalshi_dashboard.py
   ```

5. **Open** http://localhost:8050

## Features

- Live RFQ feed with 6-second auto-refresh (~2,500+ NBA RFQs visible)
- Filter by market type (NBA props, game lines), leg count, dollar amount
- Sort by newest, oldest, most legs, highest dollar, highest multiplier
- Click any RFQ card to track it — watches for fill in real-time
- Fill details: YES price, contracts, user bet, MM exposure, multiplier
- Top players and leg distribution sidebar
- Pause/resume with spacebar or click the LIVE badge
- Filled tab auto-pauses so data doesn't shift while you're reading
- Search by player name
- Dedup toggle (1 per user) to reduce noise

## Architecture

- `kalshi_dashboard.py` — HTTP server on port 8050, background trade fetcher, RFQ processing
- `kalshi_trader.py` — Kalshi API client (RSA-PSS auth, REST endpoints, WebSocket)
- `dashboard.html` — Single-file frontend (HTML/CSS/JS, no build step)
- `config.json` — Your API credentials (**not committed to git** — in .gitignore)
- `config.example.json` — Template for config.json

## How it works

The dashboard polls the Kalshi `/communications/rfqs` endpoint for open and closed RFQs. It decodes NBA prop tickers into readable player names and stat lines (e.g. `KXNBAPTS-26MAR11CLEORL-CLEJHARDEN1-15` → "J. Harden 15+ pts"). For filled RFQs, it fetches trade data from `/markets/trades` to show the fill price, contracts, and market maker exposure. The click-to-track feature polls a specific RFQ every 3 seconds to detect when it transitions from open to filled.

## Troubleshooting

- **`FileNotFoundError: config.json not found`** — You need to create `config.json` (step 2 above)
- **`401 Unauthorized`** — Check your API key and private key path in config.json
- **Port 8050 in use** — Kill any existing Python processes or change `PORT` in kalshi_dashboard.py
- **No RFQs showing** — Make sure you're using the live API URL (not demo) and NBA games are scheduled
