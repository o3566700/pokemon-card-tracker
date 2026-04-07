"""
Pokemon Card Price Tracker - Flask Web App
"""
import json
import os
from flask import Flask, render_template, abort

app = Flask(__name__)


def load_json(filepath, default=None):
    if default is None:
        default = []
    if not os.path.exists(filepath):
        return default
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return default


def get_latest_prices(all_prices):
    """Return dict of card_id -> latest price entry"""
    latest = {}
    for p in all_prices:
        cid = p["card_id"]
        if cid not in latest or p["date"] > latest[cid]["date"]:
            latest[cid] = p
    return latest


def fmt_twd(val):
    """Format TWD price: None -> 'N/A', int -> 'NT$12,345'"""
    if val is None:
        return "N/A"
    return f"NT${val:,}"


@app.route("/")
def index():
    cards = load_json("data/cards.json")
    all_prices = load_json("data/prices.json")
    latest_map = get_latest_prices(all_prices)

    card_data = []
    for card in cards:
        cid = card["id"]
        latest = latest_map.get(cid)
        card_data.append({
            "id": cid,
            "name": card["name"],
            "latest": latest,
            "condition_a_twd": latest["condition_a"]["twd"] if latest and latest.get("condition_a") else None,
            "psa_9_twd": latest["psa_9"]["twd"] if latest and latest.get("psa_9") else None,
            "psa_10_twd": latest["psa_10"]["twd"] if latest and latest.get("psa_10") else None,
            "date": latest["date"] if latest else None,
        })

    return render_template("index.html", cards=card_data, fmt_twd=fmt_twd)


@app.route("/card/<int:card_id>")
def card_detail(card_id):
    cards = load_json("data/cards.json")
    card = next((c for c in cards if c["id"] == card_id), None)
    if not card:
        abort(404)

    all_prices = load_json("data/prices.json")
    card_prices = sorted(
        [p for p in all_prices if p["card_id"] == card_id],
        key=lambda x: x["date"]
    )

    dates = [p["date"] for p in card_prices]
    condition_a = [p["condition_a"]["twd"] if p.get("condition_a") else None for p in card_prices]
    psa_9 = [p["psa_9"]["twd"] if p.get("psa_9") else None for p in card_prices]
    psa_10 = [p["psa_10"]["twd"] if p.get("psa_10") else None for p in card_prices]

    latest = card_prices[-1] if card_prices else None

    return render_template(
        "card.html",
        card=card,
        dates=json.dumps(dates),
        condition_a=json.dumps(condition_a),
        psa_9=json.dumps(psa_9),
        psa_10=json.dumps(psa_10),
        latest=latest,
        fmt_twd=fmt_twd,
        has_data=bool(card_prices),
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
