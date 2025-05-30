"""
Keyboard layouts for the Telegram bot.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import CHANNELS

def get_join_keyboard():
    """
    Create an inline keyboard with join buttons for each required channel
    and a verification button.
    
    Returns:
        InlineKeyboardMarkup: Keyboard with channel join buttons
    """
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    # Add join buttons for each channel
    for channel in CHANNELS:
        url = f"https://t.me/{channel['username']}"
        button_text = f"📢 Join {channel['name']}"
        keyboard.add(InlineKeyboardButton(button_text, url=url))
    
    # Add verification button
    keyboard.add(InlineKeyboardButton("✅ I Joined All Channels", callback_data="check_channels"))
    
    return keyboard

def get_retry_keyboard():
    """
    Create a simple retry keyboard for when verification fails.
    
    Returns:
        InlineKeyboardMarkup: Keyboard with retry button
    """
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔄 Check Again", callback_data="check_channels"))
    return keyboard

def get_main_menu_keyboard():
    """
    Create the main menu keyboard for users who have access.
    
    Returns:
        InlineKeyboardMarkup: Main menu keyboard
    """
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    # Add main menu items
    keyboard.add(
        InlineKeyboardButton("👥 Refer & Earn", callback_data="refer"),
        InlineKeyboardButton("💰 My Balance", callback_data="balance")
    )
    keyboard.add(
        InlineKeyboardButton("💸 Withdraw", callback_data="withdraw"),
        InlineKeyboardButton("📊 Status", callback_data="status")
    )
    keyboard.add(InlineKeyboardButton("ℹ️ Help", callback_data="help"))
    
    return keyboard

def get_back_keyboard():
    """
    Create a simple back button keyboard.
    
    Returns:
        InlineKeyboardMarkup: Back button keyboard
    """
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu"))
    return keyboard

def get_withdraw_keyboard():
    """
    Create withdraw confirmation keyboard.
    
    Returns:
        InlineKeyboardMarkup: Withdraw keyboard
    """
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("💳 Enter Wallet Address", callback_data="enter_wallet"))
    keyboard.add(InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu"))
    return keyboard
