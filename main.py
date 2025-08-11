# main.py
import os
import logging
from datetime import datetime
from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
import time

load_dotenv()

from utils import (
    get_opening_clues,
    get_fii_dii,
    get_top_gainers_losers,
    get_sector_performance,
    get_closing_summary,
)

from telegram import Bot

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config from env
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TARGET_CHAT = os.getenv("TELEGRAM_TARGET_CHAT_ID")
SCHEDULE_OPENING = os.getenv("SCHEDULE_OPENING", "08:30")
SCHEDULE_CLOSE = os.getenv("SCHEDULE_CLOSE", "21:20")

if not BOT_TOKEN or not TARGET_CHAT:
    logger.error("Please set TELEGRAM_BOT_TOKEN and TELEGRAM_TARGET_CHAT_ID in .env")
    raise SystemExit("Missing required env vars")

bot = Bot(token=BOT_TOKEN)
app = Flask(__name__)

scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

# Message formatter helpers

def emoji_wrap(title, emoji):
    return f"{emoji} {title}"


def post_message(text, parse_mode="Markdown"):
    try:
        bot.send_message(chat_id=TARGET_CHAT, text=text, parse_mode=parse_mode)
        logger.info("Posted message to %s", TARGET_CHAT)
    except Exception as e:
        logger.exception("Failed to send message: %s", e)


# Jobs

def job_opening_clues():
    logger.info("Running opening clues job: %s", datetime.now())
    payload = get_opening_clues()
    # payload is already emoji-friendly
    post_message(payload)


def job_closing_and_fii():
    logger.info("Running closing summary + FII/DII job: %s", datetime.now())
    fii = get_fii_dii()
    closing = get_closing_summary()
    gainers, losers = get_top_gainers_losers(limit=5)
    sector = get_sector_performance(limit=6)

    parts = [fii, closing, "\n*Top Gainers*\n" + gainers, "\n*Top Losers*\n" + losers, "\n*Sector Snapshot*\n" + sector]
    message = "\n\n".join([p for p in parts if p])
    post_message(message)


# Health check
@app.route("/", methods=["GET"])
def index():
    return "Telegram Market Bot is running. Scheduler jobs: opening @%s, close @%s" % (SCHEDULE_OPENING, SCHEDULE_CLOSE)


@app.route("/run-open", methods=["POST"])
def run_open():
    # Manual trigger (protected by secret if you want)
    job_opening_clues()
    return "Opening posted"


@app.route("/run-close", methods=["POST"])
def run_close():
    job_closing_and_fii()
    return "Close posted"


def schedule_jobs():
    # parse HH:MM
    h_o, m_o = map(int, SCHEDULE_OPENING.split(":"))
    h_c, m_c = map(int, SCHEDULE_CLOSE.split(":"))

    scheduler.add_job(job_opening_clues, 'cron', hour=h_o, minute=m_o)
    scheduler.add_job(job_closing_and_fii, 'cron', hour=h_c, minute=m_c)
    scheduler.start()
    logger.info("Scheduler started with opening=%s closing=%s", SCHEDULE_OPENING, SCHEDULE_CLOSE)


if __name__ == "_main_":
    schedule_jobs()
    # For dev run
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))