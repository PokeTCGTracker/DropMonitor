import json
import os
import re
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus
import requests
import feedparser
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent
STATE_FILE = ROOT / "state.json"
PRODUCTS_FILE = ROOT / "products.json"
WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
USER_AGENT = "PokemonTCGDropMonitor/0.1 (personal hobby tracker; contact: configure locally)"
MAX_ALERTS_PER_RUN = 15

# Google News RSS searches provide a useful free starting point for announcements,
# restocks, deals, and singles chatter. These are discovery feeds, not guaranteed
# real-time inventory feeds.
SEARCHES = [
    ("Official Pokémon TCG news", 'site:pokemon.com/us/news "Pokémon TCG"'),
    ("Pokémon Center releases/restocks", '"Pokemon Center" TCG (restock OR available OR release)'),
    ("Retailer restocks", '"Pokemon TCG" (restock OR "back in stock" OR drop)'),
    ("Pokémon TCG deals", '"Pokemon TCG" (deal OR sale OR discount)'),
    ("Pokémon TCG singles/market", '"Pokemon TCG" (singles OR card prices OR market)'),
    ("Pokémon TCG release news", '"Pokemon TCG" upcoming release OR expansion OR product'),
]

def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def google_news_rss(query):
    return "https://news.google.com/rss/search?q=" + quote_plus(query) + "&hl=en-US&gl=US&ceid=US:en"

def stable_id(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]

def send_discord(message):
    if not WEBHOOK:
        print("DISCORD_WEBHOOK_URL is not set; printing alert instead:\n" + message)
        return False
    response = requests.post(WEBHOOK, json={"content": message[:1900]}, timeout=15)
    response.raise_for_status()
    return True

def alert_message(kind, title, url, detail=""):
    prefix = "📰" if kind == "news" else "🛒"
    lines = [f"{prefix} **Pokémon TCG {kind.upper()} ALERT**", f"**{title[:220]}**"]
    if detail:
        lines.append(detail[:350])
    lines.append(url)
    return "\n".join(lines)

def collect_news(seen):
    alerts = []
    for label, query in SEARCHES:
        feed_url = google_news_rss(query)
        try:
            feed = feedparser.parse(feed_url)
        except Exception as exc:
            print(f"Feed failed ({label}): {exc}")
            continue
        for entry in feed.entries[:20]:
            title = (getattr(entry, "title", "") or "").strip()
            link = (getattr(entry, "link", "") or "").strip()
            published = (getattr(entry, "published", "") or "").strip()
            if not title or not link:
                continue
            key = stable_id(link)
            if key in seen:
                continue
            seen.add(key)
            alerts.append((key, alert_message("news", title, link, f"Source category: {label}" + (f" · {published}" if published else ""))))
    return alerts

def check_products(seen, products):
    alerts = []
    for product in products:
        url = product.get("url", "").strip()
        name = product.get("name", url)
        if not url:
            continue
        try:
            response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            title_tag = soup.find("title")
            page_title = title_tag.get_text(" ", strip=True) if title_tag else name
            description_tag = soup.find("meta", attrs={"name": "description"})
            description = description_tag.get("content", "") if description_tag else ""
            page_text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).lower()
            content = (page_title + " " + description + " " + page_text).lower()

            in_stock_terms = [s.lower() for s in product.get("in_stock_terms", ["add to cart", "in stock", "available now"])]
            out_stock_terms = [s.lower() for s in product.get("out_of_stock_terms", ["sold out", "out of stock", "currently unavailable"])]
            in_stock = any(term in content for term in in_stock_terms)
            out_stock = any(term in content for term in out_stock_terms)

            # Alert only on an observed transition to an apparently available state.
            # Page text can be misleading; users should verify on the retailer page.
            status = "in_stock" if in_stock and not out_stock else "unknown_or_unavailable"
            state_key = "product:" + stable_id(url)
            old_status = seen.get("__product_status__", {}).get(state_key)
            seen.setdefault("__product_status__", {})[state_key] = status
            if status == "in_stock" and old_status != "in_stock":
                alerts.append((stable_id(url + status), alert_message("RESTOCK", name or page_title, url, "Page text suggests availability. Verify stock and price at the retailer.")))
            print(f"Product checked: {name} -> {status}")
            time.sleep(1.0)
        except Exception as exc:
            print(f"Product check failed ({name}): {exc}")
    return alerts

def main():
    if not WEBHOOK:
        print("WARNING: Discord webhook is not configured. Alerts will be printed to the workflow log.")
    state = load_json(STATE_FILE, {"seen": []})
    # Preserve product status transitions separately from news IDs.
    seen_list = state.get("seen", [])
    seen = set(seen_list)
    # Product transition map is stored outside the set.
    product_status = state.get("product_status", {})
    seen_dict = {"__product_status__": product_status}

    news_alerts = collect_news(seen)
    products = load_json(PRODUCTS_FILE, [])
    product_alerts = check_products(seen_dict, products)
    all_alerts = news_alerts + product_alerts

    sent = 0
    for _, message in all_alerts[:MAX_ALERTS_PER_RUN]:
        try:
            send_discord(message)
            sent += 1
            time.sleep(1.0)
        except Exception as exc:
            print(f"Discord send failed: {exc}")

    # Keep a bounded history so the state file stays small.
    save_json(STATE_FILE, {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "seen": list(seen)[-5000:],
        "product_status": seen_dict.get("__product_status__", {}),
    })
    print(f"Run complete. New feed items: {len(news_alerts)}; product alerts: {len(product_alerts)}; attempted alerts: {sent}")

if __name__ == "__main__":
    main()
