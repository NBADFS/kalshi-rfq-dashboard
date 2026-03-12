# Kalshi RFQ Dashboard

Real-time monitor for Kalshi prediction market RFQ (Request for Quote) flow. Focused on NBA props.

## Quick Start (give this to Claude or any AI assistant)

> "Set up the Kalshi RFQ Dashboard for me. Here's my Kalshi API key: `PASTE_KEY_HERE`. My private key file is at `PASTE_PATH_HERE`. Follow the steps below."

### Step-by-step setup:

1. **Install Python dependencies:**
   ```
   pip install -r requirements.txt
   ```

2. **Create `config.json`** by copying `config.example.json`:
   ```
   cp config.example.json config.json
   ```
   Then edit `config.json` with your credentials:
   ```json
   {
       "api_key_id": "YOUR_KALSHI_API_KEY",
       "private_key_path": "your_private_key.pem",
       "base_url": "https://api.elections.kalshi.com/trade-api/v2"
   }
   ```

3. **Get your Kalshi API key + private key:**
   - Log into [kalshi.com](https://kalshi.com) → Settings → API Keys
   - Create a new API key — this gives you the `api_key_id`
   - Download the RSA private key file (`.pem`) and place it in this directory
   - Set `private_key_path` to the filename (e.g. `"my_key.pem"`) — relative paths work

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
