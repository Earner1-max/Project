"""
Utility functions for the Telegram bot.
"""

import logging
from typing import List, Dict, Any
from aiogram import Bot
from aiogram.utils.exceptions import ChatNotFound, BotBlocked

from config import CHANNELS

logger = logging.getLogger(__name__)

async def is_user_in_all_channels(bot: Bot, user_id: int) -> tuple[bool, List[str]]:
    """
    Check if a user is a member of all required channels.
    
    Args:
        bot: The bot instance
        user_id: Telegram user ID to check
        
    Returns:
        tuple: (is_member_of_all, list_of_missing_channels)
    """
    missing_channels = []
    
    for channel in CHANNELS:
        try:
            chat_member = await bot.get_chat_member(f"@{channel['username']}", user_id)
            
            # Check if user has appropriate status
            if chat_member.status not in ["member", "administrator", "creator"]:
                missing_channels.append(channel['name'])
                logger.info(f"User {user_id} not a member of {channel['name']} (status: {chat_member.status})")
            else:
                logger.debug(f"User {user_id} verified in {channel['name']} (status: {chat_member.status})")
                
        except (ChatNotFound, BotBlocked) as specific_error:
            if isinstance(specific_error, ChatNotFound):
                logger.error(f"Channel @{channel['username']} not found")
            else:  # BotBlocked
                logger.warning(f"Bot blocked by user {user_id}")
            missing_channels.append(channel['name'])
        except Exception as e:
            error_msg = str(e).lower()
            if "user not found" in error_msg:
                logger.warning(f"User {user_id} not found when checking {channel['username']}")
            else:
                logger.error(f"Error checking membership for user {user_id} in {channel['username']}: {e}")
            missing_channels.append(channel['name'])
    
    is_member_of_all = len(missing_channels) == 0
    return is_member_of_all, missing_channels

async def get_user_info_string(user) -> str:
    """
    Create a formatted string with user information.
    
    Args:
        user: Telegram user object
        
    Returns:
        str: Formatted user information
    """
    user_info = f"👤 {user.full_name}"
    if user.username:
        user_info += f" (@{user.username})"
    user_info += f"\n🆔 ID: {user.id}"
    return user_info

def format_channel_list() -> str:
    """
    Format the required channels list for display.
    
    Returns:
        str: Formatted channel list
    """
    channel_list = "📋 Required Channels:\n"
    for i, channel in enumerate(CHANNELS, 1):
        channel_list += f"{i}. {channel['name']} (@{channel['username']})\n"
    return channel_list
