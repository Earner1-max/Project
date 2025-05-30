#!/usr/bin/env python3
"""
Telegram bot that enforces channel membership requirements before granting access to bot features.
"""

import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from config import BOT_TOKEN, CHANNELS
from handlers import register_handlers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

def main():
    """Main function to start the bot."""
    try:
        # Register all handlers
        register_handlers(dp, bot)
        
        logger.info("Bot started successfully")
        logger.info(f"Monitoring {len(CHANNELS)} required channels:")
        for channel in CHANNELS:
            logger.info(f"  - {channel['name']} (@{channel['username']})")
        
        # Start polling
        executor.start_polling(dp, skip_updates=True)
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == '__main__':
    main()
