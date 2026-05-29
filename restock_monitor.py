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
# TOYMATE CHECKER (FINAL FIXED VERSION)
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

            # 1. Standard link
            link_tag = item.select_one(".product-item-link")
            if link_tag and link_tag.get("href"):
                link = link_tag["href"]

            # 2. Any <a> with /products/
            if not link:
                alt = item.select_one('a[href*="/products/"]')
                if alt:
                    link = alt["href"]

            # 3. data-product-url
            if not link:
                data_url = item.get("data-product-url")
                if data_url:
                    link = data_url

            # If still no link → skip
            if not link:
                continue

            # Ensure correct domain (NO www)
            if link.startswith("/"):
                link = "https://toymate.com.au" + link
            else:
                # Replace www with correct domain
                link = link.replace("https://www.toymate.com.au", "https://toymate.com.au")

            # Ensure trailing slash
            if not link.endswith("/"):
                link += "/"

            # Price
            price = None
            price_tag = item.select_one(".price")
            if price_tag:
                price = parse_price(price_tag.get_text(strip=True))

            # Detect restock
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
            title_tag = item.select_one(".product-tile__title")
            link_tag = item.select_one("a")
            button_tag = item.select_one(".product-tile__cta-button")
            price_tag = item.select_one(".product-tile__price")

            if not title_tag or not link_tag or not button_tag:
                continue

            title = title_tag.get_text(strip=True)
            link = "https://www.target.com.au" + link_tag["href"]
            button_text = button_tag.get_text(strip=True).lower()

            price = None
            if price_tag:
                price = parse_price(price_tag.get_text(strip=True))

            if "add to cart" in button_text or "pre order" in button_text:
                log(f"FOUND Target: {title} — {button_text} — {price}")
                send_discord_alert(title, link, button_text, price)

    except Exception as e:
        log(f"Target error: {e}")

# -------------------------
# GENERIC CHECKER
# -------------------------
def check_generic(product):
    name = product["name"]
    url = product["url"]

    log(f"Checking: {name}")

    try:
        response = requests.get(url, timeout=30)
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text().lower()

        for keyword in KEYWORDS:
            if keyword in text:
                send_discord_alert(name, url, keyword)
                return

    except Exception as e:
        log(f"Error checking {name}: {e}")

# -------------------------
# MAIN LOOP
# -------------------------
def main():
    log("=== Pokémon Restock Monitor Started ===")

    while True:
        for product in PRODUCTS:
            name = product["name"].lower()

            if "toymate" in name:
                check_toymate()
            elif "target" in name:
                check_target()
            else:
                check_generic(product)

        log(f"Sleeping {CHECK_INTERVAL} seconds…\n")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
