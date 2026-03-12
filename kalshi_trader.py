"""
Kalshi API Trader — Buy No / Sell Yes on any market
Usage:
    python kalshi_trader.py                     # interactive mode
    python kalshi_trader.py --ticker KXNBA-...  # look up a specific market
"""

import requests
import datetime
import base64
import uuid
import json
import os
import sys
import threading
from urllib.parse import urlparse
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding

try:
    import websocket
    HAS_WEBSOCKET = True
except ImportError:
    HAS_WEBSOCKET = False

# ── CONFIG ──────────────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_config_path = os.path.join(_SCRIPT_DIR, "config.json")

if os.path.exists(_config_path):
    with open(_config_path, "r") as _f:
        _config = json.load(_f)
    API_KEY_ID = _config["api_key_id"]
    _key_path = _config["private_key_path"]
    if not os.path.isabs(_key_path):
        _key_path = os.path.join(_SCRIPT_DIR, _key_path)
    PRIVATE_KEY_PATH = _key_path
    BASE_URL = _config.get("base_url", "https://api.elections.kalshi.com/trade-api/v2")
else:
    raise FileNotFoundError(
        "config.json not found. Copy config.example.json to config.json "
        "and fill in your API key and private key path."
    )
# ────────────────────────────────────────────────────────────────────────────


def load_private_key(key_path):
    with open(key_path, "rb") as f:
        return serialization.load_pem_private_key(
            f.read(), password=None, backend=default_backend()
        )


def create_signature(private_key, timestamp, method, path):
    path_without_query = path.split("?")[0]
    message = f"{timestamp}{method}{path_without_query}".encode("utf-8")
    signature = private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH,
        ),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("utf-8")


def api_request(method, path, data=None):
    timestamp = str(int(datetime.datetime.now().timestamp() * 1000))
    full_path = urlparse(BASE_URL + path).path
    signature = create_signature(private_key, timestamp, method, full_path)

    headers = {
        "KALSHI-ACCESS-KEY": API_KEY_ID,
        "KALSHI-ACCESS-SIGNATURE": signature,
        "KALSHI-ACCESS-TIMESTAMP": timestamp,
        "Content-Type": "application/json",
    }

    url = BASE_URL + path
    if method == "GET":
        return requests.get(url, headers=headers)
    elif method == "POST":
        return requests.post(url, headers=headers, json=data)


def get_balance():
    resp = api_request("GET", "/portfolio/balance")
    data = resp.json()
    print(f"  Balance: ${data.get('balance', 0) / 100:.2f}")
    return data


def search_markets(query, limit=10):
    """Search for markets by keyword."""
    resp = api_request("GET", f"/markets?status=open&limit={limit}&cursor=&series_ticker=&event_ticker=")
    if resp.status_code != 200:
        print(f"  Error: {resp.status_code} — {resp.text}")
        return []
    return resp.json().get("markets", [])


def get_market(ticker):
    """Get details for a specific market ticker."""
    resp = api_request("GET", f"/markets/{ticker}")
    if resp.status_code != 200:
        print(f"  Error: {resp.status_code} — {resp.text}")
        return None
    return resp.json().get("market", resp.json())


def get_orderbook(ticker):
    """Get the order book for a market."""
    resp = api_request("GET", f"/markets/{ticker}/orderbook")
    if resp.status_code != 200:
        print(f"  Error: {resp.status_code} — {resp.text}")
        return None
    return resp.json().get("orderbook", resp.json())


def place_order(ticker, side, action, count, price_cents, order_type="limit"):
    """
    Place an order.
      ticker:      market ticker (e.g., "KXNBA-26MAR11-KAT-DD-Y")
      side:        "yes" or "no"
      action:      "buy" or "sell"
      count:       number of contracts
      price_cents: price in cents (1-99)
      order_type:  "limit" or "market"
    """
    order_data = {
        "ticker": ticker,
        "action": action,
        "side": side,
        "count": count,
        "type": order_type,
        "client_order_id": str(uuid.uuid4()),
    }

    # Set price based on side
    if order_type == "limit":
        if side == "yes":
            order_data["yes_price"] = price_cents
        else:
            order_data["no_price"] = price_cents

    print(f"\n  Placing order:")
    print(f"    Ticker: {ticker}")
    print(f"    Side:   {side}")
    print(f"    Action: {action}")
    print(f"    Count:  {count}")
    print(f"    Price:  {price_cents}c")
    print(f"    Type:   {order_type}")

    resp = api_request("POST", "/portfolio/orders", order_data)

    if resp.status_code == 200 or resp.status_code == 201:
        print(f"  OK: Order placed successfully!")
        print(f"    {json.dumps(resp.json(), indent=2)}")
    else:
        print(f"  FAIL: Order failed: {resp.status_code}")
        print(f"    {resp.text}")

    return resp


def get_rfqs(market_ticker=None, event_ticker=None, status="open"):
    """Get RFQ activity. Filter by market or event ticker."""
    params = f"?status={status}&limit=100"
    if market_ticker:
        params += f"&market_ticker={market_ticker}"
    if event_ticker:
        params += f"&event_ticker={event_ticker}"
    resp = api_request("GET", f"/communications/rfqs{params}")
    if resp.status_code != 200:
        print(f"  Error: {resp.status_code} — {resp.text}")
        return []
    return resp.json().get("rfqs", [])


def display_rfqs(rfqs):
    """Pretty-print RFQ list."""
    if not rfqs:
        print("  No RFQs found.")
        return
    print(f"\n  {'ID':12s}  {'Ticker':45s}  {'Contracts':>10s}  {'Target $':>10s}  {'Status':8s}  Created")
    print("  " + "-" * 110)
    for r in rfqs:
        legs = r.get("mve_selected_legs", [])
        leg_str = ""
        if legs:
            leg_parts = []
            for leg in legs:
                side = leg.get("side", "?")
                mt = leg.get("market_ticker", "?")
                leg_parts.append(f"{side.upper()}:{mt}")
            leg_str = " | Legs: " + ", ".join(leg_parts)
        print(f"  {r.get('id','?'):12s}  "
              f"{r.get('market_ticker','N/A'):45s}  "
              f"{r.get('contracts_fp','?'):>10s}  "
              f"${r.get('target_cost_dollars','?'):>9s}  "
              f"{r.get('status','?'):8s}  "
              f"{r.get('created_ts','')[:19]}"
              f"{leg_str}")


def stream_rfqs():
    """Stream real-time RFQ activity via WebSocket."""
    if not HAS_WEBSOCKET:
        print("  websocket-client not installed. Run: pip install websocket-client")
        return

    ws_url = "wss://api.elections.kalshi.com/communications"
    timestamp = str(int(datetime.datetime.now().timestamp() * 1000))
    path = "/communications"
    signature = create_signature(private_key, timestamp, "GET", f"/trade-api/v2{path}")

    def on_open(ws):
        print("  Connected to RFQ WebSocket. Listening for activity...")
        sub = {
            "id": 1,
            "cmd": "subscribe",
            "params": {"channels": ["communications"]}
        }
        ws.send(json.dumps(sub))

    def on_message(ws, message):
        data = json.loads(message)
        msg_type = data.get("type", "")
        msg = data.get("msg", {})
        ts = datetime.datetime.now().strftime("%H:%M:%S")

        if msg_type == "rfq_created":
            ticker = msg.get("market_ticker", "N/A")
            contracts = msg.get("contracts_fp", "?")
            cost = msg.get("target_cost_dollars", "?")
            legs = msg.get("mve_selected_legs", [])
            leg_str = ""
            if legs:
                parts = [f"{l.get('side','?').upper()}:{l.get('market_ticker','?')}" for l in legs]
                leg_str = f" | Legs: {', '.join(parts)}"
            print(f"  [{ts}] RFQ CREATED  {ticker}  {contracts} contracts  target ${cost}{leg_str}")
        elif msg_type == "rfq_deleted":
            print(f"  [{ts}] RFQ DELETED  {msg.get('market_ticker', 'N/A')}")
        elif msg_type == "quote_created":
            bid = msg.get("yes_bid_price", "?")
            ask = msg.get("no_bid_price", "?")
            print(f"  [{ts}] QUOTE        {msg.get('market_ticker', 'N/A')}  yes_bid={bid} no_bid={ask}")
        elif msg_type == "quote_accepted":
            side = msg.get("accepted_side", "?")
            qty = msg.get("accepted_contracts", "?")
            print(f"  [{ts}] ACCEPTED     {msg.get('market_ticker', 'N/A')}  side={side} qty={qty}")
        elif msg_type == "quote_executed":
            print(f"  [{ts}] EXECUTED     order_id={msg.get('order_id', '?')}")
        else:
            print(f"  [{ts}] {msg_type}: {json.dumps(msg)[:200]}")

    def on_error(ws, error):
        print(f"  WebSocket error: {error}")

    def on_close(ws, close_status, close_msg):
        print("  WebSocket closed.")

    headers = {
        "KALSHI-ACCESS-KEY": API_KEY_ID,
        "KALSHI-ACCESS-SIGNATURE": signature,
        "KALSHI-ACCESS-TIMESTAMP": timestamp,
    }

    ws = websocket.WebSocketApp(
        ws_url,
        header=headers,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )
    print("  Connecting to RFQ stream (Ctrl+C to stop)...")
    ws.run_forever()


def display_market(market):
    """Pretty-print market info."""
    print(f"\n  Market: {market.get('title', 'N/A')}")
    print(f"  Ticker: {market.get('ticker', 'N/A')}")
    print(f"  Status: {market.get('status', 'N/A')}")
    yes_bid = market.get('yes_bid', 0)
    yes_ask = market.get('yes_ask', 0)
    no_bid = market.get('no_bid', 0) if market.get('no_bid') else (100 - yes_ask if yes_ask else 0)
    no_ask = market.get('no_ask', 0) if market.get('no_ask') else (100 - yes_bid if yes_bid else 0)
    print(f"  Yes:    {yes_bid}c bid / {yes_ask}c ask")
    print(f"  No:     {no_bid}c bid / {no_ask}c ask")
    print(f"  Volume: {market.get('volume', 'N/A')}")


def interactive_mode():
    print("\n" + "=" * 60)
    print("  KALSHI API TRADER")
    print("=" * 60)
    print(f"  Server: {BASE_URL}")

    print("\n  Checking connection...")
    get_balance()

    while True:
        print("\n  Commands:")
        print("    1) Look up market by ticker")
        print("    2) View orderbook")
        print("    3) Buy NO on a market")
        print("    4) Buy YES on a market")
        print("    5) View positions")
        print("    6) View balance")
        print("    7) View RFQs (snapshot)")
        print("    8) Stream RFQs (live feed)")
        print("    q) Quit")

        choice = input("\n  > ").strip()

        if choice == "q":
            break

        elif choice == "1":
            ticker = input("  Ticker: ").strip()
            market = get_market(ticker)
            if market:
                display_market(market)

        elif choice == "2":
            ticker = input("  Ticker: ").strip()
            book = get_orderbook(ticker)
            if book:
                print(f"\n  Order Book for {ticker}:")
                print(f"    Yes bids: {book.get('yes', [])}")
                print(f"    No bids:  {book.get('no', [])}")

        elif choice in ("3", "4"):
            side = "no" if choice == "3" else "yes"
            ticker = input("  Ticker: ").strip()

            # Show current market first
            market = get_market(ticker)
            if market:
                display_market(market)

            count = int(input("  # of contracts: ").strip())
            price = int(input(f"  Price in cents (1-99): ").strip())

            confirm = input(f"\n  Confirm: BUY {count}x {side.upper()} @ {price}c on {ticker}? (y/n) ")
            if confirm.lower() == "y":
                place_order(ticker, side, "buy", count, price)
            else:
                print("  Cancelled.")

        elif choice == "5":
            resp = api_request("GET", "/portfolio/positions")
            if resp.status_code == 200:
                positions = resp.json().get("market_positions", [])
                if not positions:
                    print("  No open positions.")
                for pos in positions:
                    print(f"  {pos.get('ticker')}: "
                          f"yes={pos.get('position', 0)}, "
                          f"cost=${pos.get('total_traded', 0) / 100:.2f}")
            else:
                print(f"  Error: {resp.text}")

        elif choice == "6":
            get_balance()

        elif choice == "7":
            ticker = input("  Filter by market ticker (or Enter for all): ").strip()
            rfqs = get_rfqs(market_ticker=ticker if ticker else None)
            display_rfqs(rfqs)

        elif choice == "8":
            stream_rfqs()


if __name__ == "__main__":
    private_key = load_private_key(PRIVATE_KEY_PATH)

    if len(sys.argv) > 2 and sys.argv[1] == "--ticker":
        market = get_market(sys.argv[2])
        if market:
            display_market(market)
    else:
        interactive_mode()
