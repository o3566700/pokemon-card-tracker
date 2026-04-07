"""
Pokemon Card Price Scraper
Fetches prices from Snkrdunk API and saves to data/prices.json
"""
import requests
import json
import os
import time
from datetime import datetime


CARDS_FILE = "data/cards.json"
PRICES_FILE = "data/prices.json"

CONDITION_IDS = {
    "condition_a": 18,   # 品相A（裸卡）
    "psa_9": 23,         # PSA 9
    "psa_10": 22,        # PSA 10
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://snkrdunk.com/en/brands/pokemon/trading-cards",
    "Origin": "https://snkrdunk.com",
}


def get_exchange_rate():
    """Get USD to TWD exchange rate from free API"""
    try:
        r = requests.get(
            "https://api.exchangerate-api.com/v4/latest/USD",
            timeout=10
        )
        r.raise_for_status()
        data = r.json()
        rate = data["rates"]["TWD"]
        print(f"Exchange rate: 1 USD = {rate:.2f} TWD")
        return rate
    except Exception as e:
        print(f"Exchange rate fetch failed: {e}, using fallback rate 32.0")
        return 32.0


def parse_price(price_str):
    """Parse 'US $879' or 'US $1,234' -> float"""
    if not price_str:
        return None
    try:
        clean = price_str.replace("US $", "").replace(",", "").strip()
        return float(clean)
    except (ValueError, AttributeError):
        return None


def get_min_price(card_id, condition_id):
    """
    Fetch listings for a card/condition and return the minimum price (USD).
    Prefers active (unsold) listings; falls back to all listings if none found.
    """
    url = f"https://snkrdunk.com/en/v1/trading-cards/{card_id}/used-listings"
    params = {
        "conditionId": condition_id,
        "sortType": "latest",
        "perPage": 16,
        "page": 1,
        "isOnlyOnSale": "false",
    }
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=15)
        if r.status_code == 404:
            print(f"    Card {card_id} not found (404)")
            return None
        r.raise_for_status()

        data = r.json()
        listings = data.get("usedTradingCards", [])
        if not listings:
            return None

        # Prefer unsold (active) listings for current asking price
        active = [l for l in listings if not l.get("isSold", True)]
        pool = active if active else listings

        prices = []
        for listing in pool:
            p = parse_price(listing.get("price", ""))
            if p is not None:
                prices.append(p)

        return min(prices) if prices else None

    except requests.RequestException as e:
        print(f"    Request error: {e}")
        return None
    except (json.JSONDecodeError, KeyError) as e:
        print(f"    Parse error: {e}")
        return None


def load_json(filepath, default):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return default
    return default


def main():
    os.makedirs("data", exist_ok=True)

    cards = load_json(CARDS_FILE, [])
    if not cards:
        print(f"No cards found in {CARDS_FILE}. Please add cards to track.")
        return

    all_prices = load_json(PRICES_FILE, [])

    twd_rate = get_exchange_rate()
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"Date: {today}\n")

    # Track which (date, card_id) combos we already have to avoid duplicates
    existing_keys = {(p["date"], p["card_id"]) for p in all_prices}
    new_entries = []

    for card in cards:
        card_id = card["id"]
        card_name = card["name"]
        print(f"Fetching: {card_name} (ID: {card_id})")

        if (today, card_id) in existing_keys:
            print(f"  Already scraped today, skipping.\n")
            continue

        entry = {
            "date": today,
            "card_id": card_id,
            "card_name": card_name,
        }

        for condition_key, condition_id in CONDITION_IDS.items():
            label = {"condition_a": "品相A", "psa_9": "PSA 9", "psa_10": "PSA 10"}[condition_key]
            print(f"  {label} (conditionId={condition_id})... ", end="", flush=True)

            min_usd = get_min_price(card_id, condition_id)
            time.sleep(0.5)  # polite delay

            if min_usd is not None:
                twd = round(min_usd * twd_rate)
                entry[condition_key] = {"usd": round(min_usd, 2), "twd": twd}
                print(f"US${min_usd:.0f} / TWD${twd:,}")
            else:
                entry[condition_key] = None
                print("No listings")

        new_entries.append(entry)
        print()

    if new_entries:
        all_prices.extend(new_entries)
        with open(PRICES_FILE, "w", encoding="utf-8") as f:
            json.dump(all_prices, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(new_entries)} new record(s). Total: {len(all_prices)} records.")
    else:
        print("No new data to save.")


if __name__ == "__main__":
    main()
