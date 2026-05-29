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
        "content": f"🔥 **RESTOCK DETECTED!**\n\n**Product:** {product_name}\n**Keyword:** `{keyword}`\n**Link:** {url}"
    }

    try:
        requests.post(DISCORD_WEBHOOK, json=data)
        log(f"Discord alert sent for {product_name}.")
    except Exception as e:
        log(f"Failed to send Discord alert: {e}")

def check_product(product):
    name = product["name"]
    url = product["url"]

    log(f"Checking: {name}")

    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text().lower()

        for keyword in KEYWORDS:
            if keyword in text:
                log(f"Keyword '{keyword}' found for {name}!")
                send_discord_alert(name, url, keyword)
                return

        log(f"No restock keywords found for {name}.")

    except Exception as e:
        log(f"Error checking {name}: {e}")

def main():
    log("=== Pokémon Restock Monitor Started ===")

    while True:
        for product in PRODUCTS:
            check_product(product)

        log(f"Sleeping for {CHECK_INTERVAL} seconds...\n")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
