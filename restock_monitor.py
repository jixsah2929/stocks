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

def check_generic(product):
    """Generic keyword-based checker for stores like Kmart, JB Hi-Fi, EB Games."""
    name = product["name"]
    url = product["url"]

    log(f"Checking: {name}")

    try:
        response = requests.get(url, timeout=25)
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text().lower()

        for keyword
