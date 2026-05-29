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

# Excluded languages for Toymate
EXCLUDED_LANG_KEYWORDS = [
    "chinese", "korean", "cn", "kr", "中文版", "韩文版"
]

def is_excluded_language(title):
    title_lower = title.lower()
    return any(excluded in title_lower for excluded in EXCLUDED_LANG_KEYWORDS)

# Ensure logs folder exists
if not os.path.exists("logs"):
    os.makedirs("logs")

def log(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry)

    with open("logs/monitor.log", "a") as f:
        f.write(entry + "\n")

def send_discord_alert(product_name, url, keyword):
    if not DISCORD_ENABLED or DISCORD_WEBHOOK == "":
        log("Discord alert skipped (disabled or missing webhook).")
        return

    data = {
        "content": f"🔥 **RESTOCK DETECTED!**\n\n**Product:** {product_name}\n**Status:** `{keyword}`\n**Link:** {url}"
    }

    try:
        requests.post(DISCORD_WEBHOOK, json=data)
        log(f"Discord alert sent for {product_name}.")
    except Exception as e:
        log(f"Failed to send Discord alert: {e}")

# -------------------------
# GENERIC CHECKER
# -------------------------
def check_generic(product):
    name = product["name"]
    url = product["url"]

    log(f"Checking: {name}")

    try:
        response = requests.get(url, timeout=25)
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text().lower()

        for keyword in KEYWORDS:
            if keyword in text:
                log(f"Keyword '{keyword}' found for {name}!")
                send_discord_alert(name, url, keyword)
                return

        log(f"No restock keywords found for {name}.")

    except requests.exceptions.Timeout:
        log(f"Timeout checking {name}. Retrying...")
        try:
            response = requests.get(url, timeout=25)
            soup = BeautifulSoup(response.text, "html.parser")
            text = soup.get_text().lower()

            for keyword in KEYWORDS:
                if keyword in text:
                    log(f"Keyword '{keyword}' found for {name}!")
                    send_discord_alert(name, url, keyword)
                    return

            log(f"No restock keywords found for {name} after retry.")

        except Exception as e:
            log(f"Second failure checking {name}: {e}")

    except Exception as e:
        log(f"Error checking {name}: {e}")

# -------------------------
# TOYMATE CHECKER
# -------------------------
def check_toymate():
    url = "https://www.toymate.com.au/search?q=pokemon"
    log("Checking Toymate…")

    try:
        response = requests.get(url, timeout=25)
        soup = BeautifulSoup(response.text, "html.parser")

        products = soup.select(".product-item")

        for item in products:
            title_tag = item.select_one(".product-item-title")
            link_tag = item.select_one("a")
            button_tag = item.select_one("button")

            if not title_tag or not link_tag or not button_tag:
                continue

            title = title_tag.get_text(strip=True)
            link = "https://www.toymate.com.au" + link_tag["href"]
            button_text = button_tag.get_text(strip=True).lower()

            # Skip Chinese/Korean cards
            if is_excluded_language(title):
                log(f"Skipping non-English product: {title}")
                continue

            # Detect restock
            if "add to cart" in button_text or "pre order" in button_text:
                log(f"FOUND Toymate item: {title} — {button_text}")
                send_discord_alert(title, link, button_text)

    except Exception as e:
        log(f"Error checking Toymate: {e}")

# -------------------------
# TARGET CHECKER
# -------------------------
def check_target():
    url = "https://www.target.com.au/search?text=pokemon+cards"
    log("Checking Target…")

    try:
        response = requests.get(url, timeout=25)
        soup = BeautifulSoup(response.text, "html.parser")

        products = soup.select(".product-tile")

        for item in products:
            title_tag = item.select_one(".product-tile__title")
            link_tag = item.select_one("a")
            button_tag = item.select_one(".product-tile__cta-button")

            if not title_tag or not link_tag or not button_tag:
                continue

            title = title_tag.get_text(strip=True)
            link = "https://www.target.com.au" + link_tag["href"]
            button_text = button_tag.get_text(strip=True).lower()

            # Skip Chinese/Korean cards
            if is_excluded_language(title):
                log(f"Skipping non-English product: {title}")
                continue

            # Detect restock
            if "add to cart" in button_text or "pre order" in button_text:
                log(f"FOUND Target item: {title} — {button_text}")
                send_discord_alert(title, link, button_text)

    except Exception as e:
        log(f"Error checking Target: {e}")

# -------------------------
# MAIN LOOP
# -------------------------
def main():
    log("=== Pokémon Restock Monitor Started ===")

    while True:
        for product in PRODUCTS:
            name = product["name"].lower()

            if name.startswith("toymate"):
                check_toymate()
            elif name.startswith("target"):
                check_target()
            else:
                check_generic(product)

        log(f"Sleeping for {CHECK_INTERVAL} seconds...\n")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
