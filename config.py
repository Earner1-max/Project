"""
Configuration file for the Telegram bot.
"""

import os

# Bot token from environment variable
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

# Channel list with usernames (not invite links)
CHANNELS = [
    {"name": "Restrictionlesschat", "username": "Restrictionlesschat"},
    {"name": "botfypay", "username": "botfypay"},
    {"name": "groupofincom", "username": "groupofincom"},
    {"name": "Crpto_Hnter", "username": "Crpto_Hnter"},
]

# Bot messages
MESSAGES = {
    "join_required": "❗ To use this bot, please join all the required channels below:",
    "welcome_back": "✅ Welcome back! You have access to all bot features now.",
    "welcome_new": "🎉 Welcome! You have successfully joined all required channels and now have access to all bot features.",
    "still_missing": "❌ You still need to join some channels. Please make sure you've joined ALL the required channels and try again.",
    "verification_error": "⚠️ There was an error verifying your membership. Please try again in a moment.",
    "checking": "🔍 Checking your membership status...",
}

# Bot settings
VERIFICATION_TIMEOUT = 30  # seconds to wait between verification attempts

# Referral system settings
REFERRAL_REWARD = 0.1  # USDT per referral
WELCOME_BONUS = 0.1  # USDT welcome bonus for new users
MINIMUM_WITHDRAWAL = 1.0  # Minimum USDT to withdraw
