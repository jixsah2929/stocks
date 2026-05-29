import requests
from bs4 import BeautifulSoup
import json
import time
import datetime
import os

# Load config.json
with open("config.json", "r") as f:
    config = json.load(f)

CHECK_INTERVAL = config["check_interval_seconds"]
KEYWORDS = [k.lower() for k in config["keywords"]]
PRODUCTS = config["products"]
DISCORD_ENABLED = config["alerts"]["discord"]["enabled"]
DISCORD_WEBHOOK = config["alerts"]["discord"]["webhook_url"]

EXCLUDED_LANG_KEYWORDS = [
    "chinese", "korean", "cn", "kr", "中文版", "韩文版"
]

def is_excluded_language(title):
    title_lower = title.lower()
    return any(excluded in title_lower for excluded in EXCLUDED_LANG_KEYWORDS)

if not os.path.exists("logs"):
    os.makedirs("logs")

def log(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry)
    with open("logs/monitor.log", "a") as f:
        f.write(entry + "\n")

def send_discord_alert(product_name, url, keyword, price=None):
    if not DISCORD_ENABLED or DISCORD_WEBHOOK == "":
        return

    price_text = f"**Price:** ${price:.2f} AUD" if price else "**Price:** Not listed"

    data = {
        "content": (
            f"🔥 **RESTOCK DETECTED!**\n\n"
            f"**Product:** {product_name}\n"
            f"**Status:** `{keyword}`\n"
            f"**Link:** {url}\n"
            f"{price_text}"
        )
    }

    try:
        requests.post(DISCORD_WEBHOOK, json=data)
    except:
        pass

def parse_price(text):
    text = text.replace(",", "")
    for part in text.split():
        if part.startswith("$"):
            try:
                return float(part.replace("$", ""))
            except:
                pass
    return None

# -------------------------
# TOYMATE CHECKER
# -------------------------
def check_toymate():
    url = "https://www.toymate.com.au/search?q=pokemon"
    log("Checking Toymate…")

    try:
        response = requests.get(url, timeout=30)
        soup = BeautifulSoup(response.text, "html.parser")

        products = soup.select(".product-item")

        for item in products:
            title_tag = item.select_one(".product-item-title")
            button_tag = item.select_one("button")

            if not title_tag or not button_tag:
                continue

            title = title_tag.get_text(strip=True)
            button_text = button_tag.get_text(strip=True).lower()

            if is_excluded_language(title):
                continue

            # Extract REAL link
            link = None

            link_tag = item.select_one(".product-item-link")
            if link_tag and link_tag.get("href"):
                link = link_tag["href"]

            if not link:
                alt = item.select_one('a[href*="/products/"]')
                if alt:
                    link = alt["href"]

            if not link:
                data_url = item.get("data-product-url")
                if data_url:
                    link = data_url

            if not link:
                continue

            if link.startswith("/"):
                link = "https://www.toymate.com.au" + link

            # Price
            price = None
            price_tag = item.select_one(".price")
            if price_tag:
                price = parse_price(price_tag.get_text(strip=True))

            if "add to cart" in button_text or "pre order" in button_text:
                log(f"FOUND Toymate: {title} — {button_text} — {price}")
                send_discord_alert(title, link, button_text, price)

    except Exception as e:
        log(f"Toymate error: {e}")

# -------------------------
# TARGET CHECKER
# -------------------------
def check_target():
    url = "https://www.target.com.au/search?text=pokemon+cards"
    log("Checking Target…")

    try:
        response = requests.get(url, timeout=30)
        soup = BeautifulSoup(response.text, "html.parser")

        products = soup.select(".product-tile")

        for item in products:
