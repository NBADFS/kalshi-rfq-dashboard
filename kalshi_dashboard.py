"""
Kalshi RFQ Dashboard — real-time monitoring of RFQ flow
Run:   python kalshi_dashboard.py
Open:  http://localhost:8050
"""
import http.server
import json
import re
import time
import os
import sys
import threading
from http.server import ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kalshi_trader as kt

PORT = 8050
kt.private_key = kt.load_private_key(kt.PRIVATE_KEY_PATH)

# ── PLAYER NAME DECODER ─────────────────────────────────────────────────────
PLAYERS = {
    "JHARDEN1": "J. Harden", "DMITCHELL45": "D. Mitchell", "EMOBLEY4": "E. Mobley",
    "DSCHRODER8": "D. Schroder", "PBANCHERO5": "P. Banchero", "DBANE3": "D. Bane",
    "JSUGGS4": "J. Suggs", "WCARTER34": "W. Carter Jr", "FWAGNER22": "F. Wagner",
    "KDURANT7": "K. Durant", "NJOKIC15": "N. Jokic", "JMURRAY27": "J. Murray",
    "RSHEPPARD15": "R. Sheppard", "ASENGUN28": "A. Sengun", "ATHOMPSON1": "A. Thompson",
    "TEASON17": "T. Eason", "JGREEN4": "J. Green", "DBROOKS7": "D. Brooks",
    "JBRUNSON11": "J. Brunson", "KTOWNS32": "K. Towns", "MBRIDGES25": "M. Bridges",
    "MROBINSON23": "M. Robinson", "OANUNOBY8": "OG Anunoby", "KGEORGE3": "K. George",
    "ABAILEY19": "A. Bailey", "DDIVINC0": "D. DiVincenzo", "JHARTJR3": "J. Hart",
    "AEDWARDS5": "A. Edwards", "KLEONARD2": "K. Leonard", "JRANDLE30": "J. Randle",
    "DGARLAND10": "D. Garland", "RGOBERT27": "R. Gobert", "BMATHURIN9": "B. Mathurin",
    "DJONES5": "D. Jones Jr", "LBALL1": "L. Ball", "BMILLER24": "B. Miller",
    "KKNUEPPEL7": "K. Knueppel", "MDIABATE14": "M. Diabate", "RWESTBROOK18": "R. Westbrook",
    "DDEROZAN10": "D. DeRozan", "TMURPHY25": "T. Murphy", "IQUICKLEY5": "I. Quickley",
    "SBARNES4": "S. Barnes", "RBARRETT9": "R. Barrett", "SBEY41": "S. Bey",
    "DQUEEN22": "D. Queen", "ZWILLIAMSON1": "Z. Williamson", "CJOHNSON23": "C. Johnson",
    "AGORDON32": "A. Gordon", "LMARKKANE23": "L. Markkanen", "JCLARKSO00": "J. Clarkson",
    "TCRAIG3": "T. Craig", "KPORTER4": "K. Porter Jr", "CHAMBRIDGES0": "Mi. Bridges",
    "BPODZIEMSKI2": "B. Podziemski", "SCURRY10": "S. Curry", "DGREEN23": "D. Green",
    "AWIGG22": "A. Wiggins", "KLOONEY5": "K. Looney", "JKUMINGA00": "J. Kuminga",
    "THALIBURT0": "T. Haliburton", "PSIAKAM43": "P. Siakam", "NSMITH14": "N. Smith Jr",
    "MTURNER33": "M. Turner", "TMANN1": "T. Mann", "BHIELD24": "B. Hield",
    "JMORANT12": "J. Morant", "DJACKSO13": "D. Jackson Jr", "BBOGDANO8": "B. Bogdanovic",
    "SGILGEO24": "S. Gilgeous-Alexander", "JWILLIAM8": "J. Williams",
    "CHOLMGRE7": "C. Holmgren", "LDORT5": "L. Dort", "IHART20": "I. Hartenstein",
    "JTATUMA0": "J. Tatum", "JBROWN7": "J. Brown", "DWHITE0": "D. White",
    "KPORZIN8": "K. Porzingis", "RWESTBR0": "R. Westbrook", "ADAVIS3": "A. Davis",
    "LJAMES23": "L. James", "DRUSSELLL1": "D. Russell", "AREAVES15": "A. Reaves",
    "MCONNELL7": "M. Conley", "JMCDANIEL0": "J. McDaniels", "NREID33": "N. Reid",
    "GANETOKUNMPO34": "G. Antetokounmpo", "DLILLARD0": "D. Lillard",
    "BPORTIS9": "B. Portis", "KMIDD22": "K. Middleton",
    "DBOOK1": "D. Booker", "KBEAL3": "K. Beal", "JNURK20": "J. Nurkic",
    "BRODONE10": "B. Rodonee", "TBEY8": "T. Bey",
    "DYOUNG11": "T. Young", "DJMURRAY5": "D. Murray", "CCOLLINS20": "C. Collins",
    "JCOLLINS20": "J. Collins", "KMAXEY0": "T. Maxey", "TYRESE0": "T. Maxey",
    "JEMBIID21": "J. Embiid", "PMILLS8": "P. Mills",
    "LDON45": "L. Doncic", "LDONCIC77": "L. Doncic", "KIRVING11": "K. Irving",
    "PJWASHINGT25": "P.J. Washington", "DGAFFOR21": "D. Gafford",
    "DFOX5": "D. Fox", "DMONK1": "D. Monk", "KSABONI10": "D. Sabonis",
    "DSABONIS10": "D. Sabonis", "KHUERTER3": "K. Huerter",
    "BLOPEZ11": "B. Lopez", "CBRAUN0": "C. Braun", "DDIVINCENZO0": "D. DiVincenzo",
    "HJONES2": "H. Jones", "JSMITH10": "J. Smith", "PACHIUWA9": "P. Achiuwa",
    "MBRIDGES0": "Mi. Bridges",
}

CAT_MAP = {
    "KXNBAPTS": "pts", "KXNBAREB": "reb", "KXNBAAST": "ast",
    "KXNBA3PT": "3pt", "KXNBA2D": "dd", "KXNBASTL": "stl",
    "KXNBABLK": "blk", "KXNBAGAME": "game", "KXNBASPREAD": "spread",
    "KXNBATOTAL": "total",
}

CAT_LABELS = {
    "pts": "pts", "reb": "reb", "ast": "ast", "3pt": "3pt",
    "dd": "dbl-dbl", "stl": "stl", "blk": "blk",
    "game": "ML", "spread": "spread", "total": "total",
}

PROP_CATS = {"pts", "reb", "ast", "3pt", "dd", "stl", "blk"}


def decode_leg(ticker, side):
    parts = ticker.split("-")
    prefix = parts[0]
    cat = CAT_MAP.get(prefix, "other")
    label = CAT_LABELS.get(cat, cat)
    s = side.upper()

    if prefix == "KXNBAGAME":
        team = parts[-1] if len(parts) > 1 else "?"
        return {"desc": "%s %s" % (team, label), "cat": cat, "side": side, "ticker": ticker}
    elif prefix == "KXNBASPREAD":
        raw = parts[-1] if len(parts) > 1 else "?"
        m = re.match(r"([A-Z]+)(\d+\.?\d*)", raw)
        if m:
            team, num = m.group(1), m.group(2)
            sign = "-" if side == "yes" else "+"
            return {"desc": "%s %s%s" % (team, sign, num), "cat": cat, "side": side, "ticker": ticker}
        return {"desc": "%s %s %s" % (s, raw, label), "cat": cat, "side": side, "ticker": ticker}
    elif prefix == "KXNBATOTAL":
        raw = parts[-1] if len(parts) > 1 else "?"
        pfx = "o" if side == "yes" else "u"
        return {"desc": "%s%s" % (pfx, raw), "cat": cat, "side": side, "ticker": ticker}
    elif len(parts) >= 4:
        player_seg = parts[2]
        player_code = player_seg[3:]
        name = PLAYERS.get(player_code, player_code)
        line = parts[3]
        return {"desc": "%s %s+ %s" % (name, line, label), "cat": cat, "side": side, "ticker": ticker}

    # Non-NBA tickers: extract a short readable label
    # Match patterns like KXNCAAMBGAME-...-TEAM or KXNHLGAME-...-TEAM
    sport_match = re.match(r"KX(NCAAMB|NHL|UFC|MLB|NFL|MLS|ATP|UCL|WNBA|SOC)(\w*)", prefix)
    if sport_match:
        sport = sport_match.group(1)
        kind = sport_match.group(2) or ""
        team = parts[-1] if len(parts) > 1 else "?"
        if "SPREAD" in kind:
            sign = "-" if side == "yes" else "+"
            m2 = re.match(r"([A-Z]+)(\d+\.?\d*)", team)
            if m2:
                return {"desc": "%s: %s %s%s" % (sport, m2.group(1), sign, m2.group(2)), "cat": "other", "side": side, "ticker": ticker}
        elif "TOTAL" in kind:
            pfx = "o" if side == "yes" else "u"
            return {"desc": "%s: %s%s" % (sport, pfx, team), "cat": "other", "side": side, "ticker": ticker}
        else:
            return {"desc": "%s: %s" % (sport, team), "cat": "other", "side": side, "ticker": ticker}
    return {"desc": ticker, "cat": "other", "side": side, "ticker": ticker}


# ── CACHE ────────────────────────────────────────────────────────────────────
_cache_lock = threading.Lock()
_cache = {
    "open": {"data": [], "ts": 0},
    "closed": {"data": [], "ts": 0},
    "trades": {},
}
OPEN_TTL = 6
CLOSED_TTL = 15


def _fetch_rfqs(status, max_pages=5):
    all_rfqs = []
    cursor = ""
    for _ in range(max_pages):
        resp = kt.api_request("GET", "/communications/rfqs?status=%s&limit=1000&cursor=%s" % (status, cursor))
        if resp.status_code != 200:
            break
        data = resp.json()
        batch = data.get("rfqs", [])
        all_rfqs.extend(batch)
        cursor = data.get("cursor", "")
        if not cursor or not batch:
            break
    return all_rfqs


def get_rfqs(status):
    now = time.time()
    ttl = OPEN_TTL if status == "open" else CLOSED_TTL
    with _cache_lock:
        if now - _cache[status]["ts"] < ttl:
            return _cache[status]["data"]
    rfqs = _fetch_rfqs(status)
    with _cache_lock:
        _cache[status]["data"] = rfqs
        _cache[status]["ts"] = now
    return rfqs


def get_trade(mve_ticker):
    with _cache_lock:
        if mve_ticker in _cache["trades"]:
            return _cache["trades"][mve_ticker]
    resp = kt.api_request("GET", "/markets/trades?ticker=%s&limit=1" % mve_ticker)
    trade = None
    if resp.status_code == 200:
        trades = resp.json().get("trades", [])
        if trades:
            trade = trades[0]
    with _cache_lock:
        _cache["trades"][mve_ticker] = trade
    return trade


# ── BACKGROUND TRADE FETCHER ────────────────────────────────────────────────
def _bg_trade_fetcher():
    """Continuously pre-fetches trade data for closed RFQs."""
    while True:
        try:
            closed = get_rfqs("closed")
            checked = 0
            for r in closed:
                mve = r.get("market_ticker", "")
                if not mve:
                    continue
                with _cache_lock:
                    if mve in _cache["trades"]:
                        continue
                get_trade(mve)
                checked += 1
                if checked >= 30:
                    break
                time.sleep(0.15)
        except Exception:
            pass
        time.sleep(10)


# ── FEED BUILDER ─────────────────────────────────────────────────────────────
def process_rfq(r, status):
    legs = r.get("mve_selected_legs", [])
    if not legs:
        return None

    decoded = [decode_leg(l.get("market_ticker", ""), l.get("side", "yes")) for l in legs]
    target = float(r.get("target_cost_dollars", "0") or "0")

    entry = {
        "id": r.get("id", ""),
        "status": status,
        "created_ts": r.get("created_ts", ""),
        "target": target,
        "num_legs": len(legs),
        "legs": decoded,
        "mve_ticker": r.get("market_ticker", ""),
        "creator_id": r.get("creator_id", "")[:10],
    }

    if status == "closed":
        mve = r.get("market_ticker", "")
        with _cache_lock:
            trade = _cache["trades"].get(mve)
        if trade:
            yp = float(trade.get("yes_price_dollars", "0") or "0")
            np_ = float(trade.get("no_price_dollars", "0") or "0")
            trade_count = int(trade.get("count", 0) or 0)
            entry["status"] = "filled"
            # Use RFQ target when available (trade count may be from a different RFQ on same MVE)
            if yp > 0 and target > 0:
                contracts = int(round(target / yp))
                retail_cost = round(target, 2)
            elif trade_count > 0:
                contracts = trade_count
                retail_cost = round(trade_count * yp, 2)
            else:
                contracts = 0
                retail_cost = 0.0
            mm_exp = round(contracts * np_, 2)
            entry["fill"] = {
                "yes_price": yp,
                "no_price": np_,
                "contracts": contracts,
                "retail_cost": retail_cost,
                "mm_exposure": mm_exp,
                "multiplier": round(1 / yp, 1) if yp > 0 else 0,
            }
        else:
            entry["status"] = "closed"

    return entry


def build_feed(params):
    status_f = params.get("status", ["all"])[0]
    market_f = params.get("market", ["all"])[0]
    min_legs = int(params.get("min_legs", ["1"])[0])
    max_legs = int(params.get("max_legs", ["50"])[0])
    search = params.get("search", [""])[0].lower()
    limit = int(params.get("limit", ["80"])[0])
    dedup = params.get("dedup", ["0"])[0] == "1"

    results = []

    if status_f in ("all", "open"):
        for r in get_rfqs("open"):
            e = process_rfq(r, "open")
            if e:
                results.append(e)

    if status_f in ("all", "filled"):
        for r in get_rfqs("closed"):
            e = process_rfq(r, "closed")
            if e:
                results.append(e)

    # ── filters ──
    filtered = []
    for e in results:
        if e["num_legs"] < min_legs or e["num_legs"] > max_legs:
            continue
        if market_f != "all":
            cats = {l["cat"] for l in e["legs"]}
            has_other = "other" in cats
            # Strict NBA-only: skip any RFQ that has non-NBA legs
            if market_f in ("nba_props", "nba_game", "nba_all") and has_other:
                continue
            if market_f == "nba_props" and not cats & PROP_CATS:
                continue
            if market_f == "nba_game" and "game" not in cats:
                continue
            if market_f == "nba_all" and not any(c in CAT_MAP.values() for c in cats):
                continue
        if search:
            text = " ".join(l["desc"] for l in e["legs"]).lower()
            if search not in text:
                continue
        if status_f == "filled" and e["status"] != "filled":
            continue
        filtered.append(e)

    # ── dedup by creator ──
    if dedup:
        latest = {}
        for e in filtered:
            cid = e["creator_id"]
            if cid not in latest or e["created_ts"] > latest[cid]["created_ts"]:
                latest[cid] = e
        filtered = list(latest.values())

    filtered.sort(key=lambda x: x.get("created_ts", ""), reverse=True)
    return filtered[:limit]


def get_single_rfq(rfq_id):
    """Look up a specific RFQ by ID, detect open→closed transitions."""
    # Check open cache first
    for r in get_rfqs("open"):
        if r.get("id") == rfq_id:
            return process_rfq(r, "open")
    # Not in open — force-refresh closed cache to catch transition
    with _cache_lock:
        _cache["closed"]["ts"] = 0
    for r in get_rfqs("closed"):
        if r.get("id") == rfq_id:
            mve = r.get("market_ticker", "")
            if mve:
                # Clear cached None so we always retry for the tracker
                with _cache_lock:
                    if not _cache["trades"].get(mve):
                        _cache["trades"].pop(mve, None)
                get_trade(mve)
            return process_rfq(r, "closed")
    return None


def build_stats():
    open_rfqs = get_rfqs("open")
    nba_count = 0
    total_vol = 0.0
    total_legs = 0
    player_counts = defaultdict(int)
    leg_dist = defaultdict(int)

    for r in open_rfqs:
        legs = r.get("mve_selected_legs", [])
        if not legs:
            continue
        # Only count pure-NBA RFQs (all legs must be KXNBA*)
        all_nba = all(l.get("market_ticker", "").startswith("KXNBA") for l in legs)
        if not all_nba:
            continue
        nba_count += 1
        total_vol += float(r.get("target_cost_dollars", "0") or "0")
        total_legs += len(legs)
        leg_dist[len(legs)] += 1
        for l in legs:
            d = decode_leg(l.get("market_ticker", ""), l.get("side", "yes"))
            if d["cat"] in PROP_CATS:
                parts = d["desc"].split(" ")
                if len(parts) >= 2:
                    player_counts[parts[0] + " " + parts[1]] += 1

    top_players = sorted(player_counts.items(), key=lambda x: -x[1])[:12]
    top_legs = sorted(leg_dist.items(), key=lambda x: x[0])

    return {
        "total_open": len(open_rfqs),
        "nba_open": nba_count,
        "total_volume": round(total_vol, 2),
        "avg_legs": round(total_legs / max(nba_count, 1), 1),
        "top_players": [{"name": p, "count": c} for p, c in top_players],
        "leg_distribution": [{"legs": l, "count": c} for l, c in top_legs],
    }


# ── HTTP HANDLER ─────────────────────────────────────────────────────────────
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._serve_html()
        elif parsed.path == "/api/feed":
            self._json(build_feed(parse_qs(parsed.query)))
        elif parsed.path == "/api/rfq":
            params = parse_qs(parsed.query)
            rfq_id = params.get("id", [""])[0]
            result = get_single_rfq(rfq_id) if rfq_id else None
            self._json(result or {"error": "not_found"})
        elif parsed.path == "/api/stats":
            self._json(build_stats())
        else:
            self.send_error(404)

    def _serve_html(self):
        fp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.html")
        with open(fp, "r", encoding="utf-8") as f:
            html = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


# ── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    t = threading.Thread(target=_bg_trade_fetcher, daemon=True)
    t.start()

    server = ThreadingHTTPServer(("", PORT), Handler)
    print("Kalshi RFQ Dashboard  ->  http://localhost:%d" % PORT)
    print("Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()
