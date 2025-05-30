"""
Message and callback handlers for the Telegram bot.
"""

import logging
from aiogram import types, Bot, Dispatcher
from aiogram.utils.exceptions import MessageNotModified

from config import MESSAGES, CHANNELS, REFERRAL_REWARD, MINIMUM_WITHDRAWAL, WELCOME_BONUS
from keyboards import get_join_keyboard, get_retry_keyboard, get_main_menu_keyboard, get_back_keyboard, get_withdraw_keyboard
from utils import is_user_in_all_channels, get_user_info_string, format_channel_list
from database import db

logger = logging.getLogger(__name__)

async def start_handler(message: types.Message, bot: Bot):
    """
    Handle the /start command.
    
    Args:
        message: Incoming message
        bot: Bot instance
    """
    user = message.from_user
    user_id = user.id
    
    logger.info(f"Start command from user {user_id} ({user.full_name})")
    
    # Update start count for tracking
    start_count = db.update_start_count(user_id)
    total_starts = db.get_total_start_requests()
    logger.info(f"User {user_id} start count: {start_count}, Total starts: {total_starts}")
    
    # Check for referral parameter
    referrer_id = None
    if message.get_args():
        try:
            referrer_id = int(message.get_args())
            logger.info(f"User {user_id} referred by {referrer_id}")
        except ValueError:
            logger.warning(f"Invalid referral ID: {message.get_args()}")
    
    # Check if user is in all required channels
    is_member, missing_channels = await is_user_in_all_channels(bot, user_id)
    
    if not is_member:
        logger.info(f"User {user_id} missing channels: {missing_channels}")
        
        # Create message with channel links
        message_text = MESSAGES["join_required"] + "\n\n"
        for channel in CHANNELS:
            message_text += f"🔗 https://t.me/{channel['username']} - {channel['name']}\n"
        message_text += "\nClick the buttons below to join each channel:"
        
        await message.answer(
            message_text,
            reply_markup=get_join_keyboard()
        )
    else:
        logger.info(f"User {user_id} has access to all channels")
        
        # Add user to database and handle referral
        username = user.username or ""
        full_name = user.full_name or f"User {user_id}"
        
        user_added = db.add_user(user_id, username, full_name, referrer_id)
        if user_added:
            # Show welcome message with bonus
            welcome_msg = f"🎉 Welcome! You've joined successfully!\n💰 Welcome bonus: +{WELCOME_BONUS} USDT added to your account!"
            if referrer_id:
                # Notify referrer about new referral
                try:
                    await bot.send_message(
                        referrer_id,
                        f"🎉 Great news! You got a new referral!\n"
                        f"👤 {full_name} just joined using your link\n"
                        f"💰 You earned +{REFERRAL_REWARD} USDT!\n\n"
                        f"Keep sharing to earn more!"
                    )
                    logger.info(f"Referral notification sent to {referrer_id}")
                except Exception as e:
                    logger.error(f"Failed to notify referrer {referrer_id}: {e}")
            
            await message.answer(welcome_msg)
        
        await message.answer(
            MESSAGES["welcome_back"],
            reply_markup=get_main_menu_keyboard()
        )

async def help_handler(message: types.Message):
    """
    Handle the /help command.
    
    Args:
        message: Incoming message
    """
    user = message.from_user
    user_id = user.id
    
    # Check if user has access to determine help content
    from database import Database
    db = Database()
    
    # Check if user exists in database (meaning they've verified)
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
    is_verified = cursor.fetchone() is not None
    conn.close()
    
    if is_verified:
        # Clean help for verified users
        help_text = (
            "🤖 **USDT Airdrop Bot**\n\n"
            "Welcome! You have full access to all bot features.\n\n"
            "**Available Commands:**\n"
            "/start - Access main menu\n"
            "/help - Show this help message\n"
            "/status - Check your account status\n\n"
            "**Features:**\n"
            "💰 Refer friends and earn 0.1 USDT per referral\n"
            "💸 Withdraw your earnings (minimum 1.0 USDT)\n"
            "📊 Track your balance and referrals"
        )
    else:
        # Show channel requirements for unverified users
        help_text = (
            "🤖 **Channel Membership Bot**\n\n"
            "This bot requires you to join specific channels before accessing its features.\n\n"
            "**Commands:**\n"
            "/start - Start the bot and check membership\n"
            "/help - Show this help message\n"
            "/status - Check your current membership status\n\n"
            f"{format_channel_list()}\n"
            "After joining all channels, use the verification button to gain access."
        )
    
    await message.answer(help_text, parse_mode="Markdown")

async def status_handler(message: types.Message, bot: Bot):
    """
    Handle the /status command.
    
    Args:
        message: Incoming message
        bot: Bot instance
    """
    user = message.from_user
    user_id = user.id
    
    logger.info(f"Status command from user {user_id}")
    
    # Check if user is in database (verified)
    from database import Database
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT balance, referral_count FROM users WHERE user_id = ?', (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    
    if user_data:
        # Clean status for verified users - no channel information
        balance, referral_count = user_data
        status_text = f"{await get_user_info_string(user)}\n\n"
        status_text += "✅ **Status: Verified Member**\n\n"
        status_text += f"💰 Balance: **{balance:.2f} USDT**\n"
        status_text += f"👥 Referrals: **{referral_count}**\n"
        status_text += f"💸 Available for withdrawal: **{max(0, balance - 1.0):.2f} USDT**"
        
        keyboard = get_main_menu_keyboard()
    else:
        # Show channel requirements for unverified users
        is_member, missing_channels = await is_user_in_all_channels(bot, user_id)
        status_text = f"{await get_user_info_string(user)}\n\n"
        
        if is_member:
            status_text += "✅ **Status: Ready for Verification**\n"
            status_text += "You are a member of all required channels. Click verify to continue."
        else:
            status_text += "❌ **Status: Access Restricted**\n"
            status_text += f"Missing channels: {', '.join(missing_channels)}"
        
        keyboard = get_main_menu_keyboard() if is_member else get_join_keyboard()
    
    await message.answer(status_text, parse_mode="Markdown", reply_markup=keyboard)

async def check_channels_callback(callback_query: types.CallbackQuery, bot: Bot):
    """
    Handle the channel verification callback.
    
    Args:
        callback_query: Incoming callback query
        bot: Bot instance
    """
    user = callback_query.from_user
    user_id = user.id
    
    logger.info(f"Channel check callback from user {user_id}")
    
    # Answer the callback query immediately
    await callback_query.answer(MESSAGES["checking"])
    
    try:
        # Check if user is now in all channels
        is_member, missing_channels = await is_user_in_all_channels(bot, user_id)
        
        if is_member:
            logger.info(f"User {user_id} successfully joined all channels")
            
            # Clean welcome message without channel links
            clean_welcome = """✅ **Verification Successful!**

🎉 Welcome to our community! You now have full access to all bot features.

💰 **Your Benefits:**
• 0.1 USDT welcome bonus added to your account
• Earn 0.1 USDT for each successful referral
• Minimum withdrawal: 1.0 USDT

Choose an option below to get started:"""
            
            await callback_query.message.edit_text(
                clean_welcome,
                parse_mode="Markdown",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            logger.info(f"User {user_id} still missing channels: {missing_channels}")
            
            # Show which channels are still missing with links
            missing_text = f"{MESSAGES['still_missing']}\n\n"
            missing_text += "You still need to join these channels:\n"
            for channel in CHANNELS:
                if channel['name'] in missing_channels:
                    missing_text += f"🔗 https://t.me/{channel['username']} - {channel['name']}\n"
            
            await callback_query.message.edit_text(
                missing_text,
                reply_markup=get_retry_keyboard()
            )
            
    except MessageNotModified:
        # Message content is the same, ignore
        pass
    except Exception as e:
        logger.error(f"Error in channel check callback: {e}")
        await callback_query.message.edit_text(
            MESSAGES["verification_error"],
            reply_markup=get_retry_keyboard()
        )

async def help_callback(callback_query: types.CallbackQuery):
    """
    Handle the help callback.
    
    Args:
        callback_query: Incoming callback query
    """
    await callback_query.answer()
    
    help_text = (
        "🤖 **Bot Help**\n\n"
        f"{format_channel_list()}\n"
        "Use the buttons below to navigate or check your membership status."
    )
    
    await callback_query.message.edit_text(
        help_text,
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard()
    )

async def status_callback(callback_query: types.CallbackQuery, bot: Bot):
    """
    Handle the status callback.
    
    Args:
        callback_query: Incoming callback query
        bot: Bot instance
    """
    await callback_query.answer()
    
    user = callback_query.from_user
    user_id = user.id
    
    # Check current membership status
    is_member, missing_channels = await is_user_in_all_channels(bot, user_id)
    
    status_text = f"{await get_user_info_string(user)}\n\n"
    
    if is_member:
        status_text += "✅ Status: Full Access\n"
        status_text += "You are a member of all required channels."
    else:
        status_text += "❌ Status: Access Restricted\n"
        status_text += f"Missing channels: {', '.join(missing_channels)}"
    
    keyboard = get_main_menu_keyboard() if is_member else get_join_keyboard()
    
    await callback_query.message.edit_text(
        status_text,
        reply_markup=keyboard
    )

async def refer_callback(callback_query: types.CallbackQuery, bot: Bot):
    """Handle the refer & earn callback."""
    await callback_query.answer()
    user = callback_query.from_user
    user_id = user.id
    
    balance, referral_count = db.get_user_stats(user_id)
    bot_info = await bot.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start={user_id}"
    
    refer_text = (
        f"👥 **Refer & Earn Program**\n\n"
        f"💰 **Your Stats:**\n"
        f"• Balance: {balance:.2f} USDT\n"
        f"• Referrals: {referral_count}\n"
        f"• Earnings: {referral_count * REFERRAL_REWARD:.2f} USDT\n\n"
        f"🎯 **How it works:**\n"
        f"• Share your referral link\n"
        f"• Earn {REFERRAL_REWARD} USDT per referral\n"
        f"• Minimum withdrawal: {MINIMUM_WITHDRAWAL} USDT\n\n"
        f"🔗 **Your Referral Link:**\n"
        f"`{referral_link}`\n\n"
        f"💡 Share this link with friends to start earning!"
    )
    
    await callback_query.message.edit_text(
        refer_text,
        parse_mode="Markdown",
        reply_markup=get_back_keyboard()
    )

async def balance_callback(callback_query: types.CallbackQuery):
    """Handle the balance callback."""
    await callback_query.answer()
    user_id = callback_query.from_user.id
    
    balance, referral_count = db.get_user_stats(user_id)
    
    balance_text = (
        f"💰 **Your Balance**\n\n"
        f"💵 **Current Balance:** {balance:.2f} USDT\n"
        f"👥 **Total Referrals:** {referral_count}\n"
        f"📈 **Total Earned:** {referral_count * REFERRAL_REWARD:.2f} USDT\n\n"
        f"💸 **Withdrawal Status:**\n"
    )
    
    if balance >= MINIMUM_WITHDRAWAL:
        balance_text += f"✅ You can withdraw {balance:.2f} USDT\n"
    else:
        needed = MINIMUM_WITHDRAWAL - balance
        balance_text += f"❌ Need {needed:.2f} more USDT to withdraw\n"
        balance_text += f"🎯 Refer {int(needed / REFERRAL_REWARD)} more friends!"
    
    await callback_query.message.edit_text(
        balance_text,
        parse_mode="Markdown",
        reply_markup=get_back_keyboard()
    )

async def withdraw_callback(callback_query: types.CallbackQuery):
    """Handle the withdraw callback."""
    await callback_query.answer()
    user_id = callback_query.from_user.id
    
    balance, _ = db.get_user_stats(user_id)
    
    if balance >= MINIMUM_WITHDRAWAL:
        withdraw_text = (
            f"💸 **Withdrawal Request**\n\n"
            f"💰 **Available Balance:** {balance:.2f} USDT\n"
            f"💳 **Withdrawal Amount:** {balance:.2f} USDT\n\n"
            f"📝 **Next Step:**\n"
            f"Please provide your USDT wallet address to proceed with the withdrawal.\n\n"
            f"⚠️ **Important:**\n"
            f"• Make sure your wallet supports USDT\n"
            f"• Double-check your wallet address\n"
            f"• Processing takes 24-48 hours"
        )
        keyboard = get_withdraw_keyboard()
    else:
        needed = MINIMUM_WITHDRAWAL - balance
        withdraw_text = (
            f"❌ **Insufficient Balance**\n\n"
            f"💰 **Current Balance:** {balance:.2f} USDT\n"
            f"💸 **Minimum Withdrawal:** {MINIMUM_WITHDRAWAL} USDT\n"
            f"📊 **Need:** {needed:.2f} more USDT\n\n"
            f"🎯 **To reach minimum:**\n"
            f"Refer {int(needed / REFERRAL_REWARD)} more friends to earn {needed:.2f} USDT"
        )
        keyboard = get_back_keyboard()
    
    await callback_query.message.edit_text(
        withdraw_text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )

async def back_to_menu_callback(callback_query: types.CallbackQuery):
    """Handle back to menu callback."""
    await callback_query.answer()
    
    await callback_query.message.edit_text(
        "🏠 **Main Menu**\n\nChoose an option below:",
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard()
    )

async def enter_wallet_callback(callback_query: types.CallbackQuery):
    """Handle enter wallet address callback."""
    await callback_query.answer()
    
    await callback_query.message.edit_text(
        "💳 **Enter Wallet Address**\n\n"
        "Please send your USDT wallet address in the next message.\n\n"
        "⚠️ **Important:**\n"
        "• Make sure your wallet supports USDT\n"
        "• Double-check your wallet address\n"
        "• Only TRC20 USDT addresses are supported\n\n"
        "📝 Type your wallet address and send it:",
        parse_mode="Markdown"
    )
    
    # Set user state to waiting for wallet
    # We'll use a simple global dict for this demo
    if not hasattr(enter_wallet_callback, 'waiting_for_wallet'):
        enter_wallet_callback.waiting_for_wallet = set()
    enter_wallet_callback.waiting_for_wallet.add(callback_query.from_user.id)

async def handle_wallet_message(message: types.Message):
    """Handle wallet address messages."""
    user_id = message.from_user.id
    
    # Check if user is in wallet waiting state
    if (hasattr(enter_wallet_callback, 'waiting_for_wallet') and 
        user_id in enter_wallet_callback.waiting_for_wallet):
        
        wallet_address = message.text.strip()
        balance, _ = db.get_user_stats(user_id)
        
        if balance >= MINIMUM_WITHDRAWAL:
            # Process withdrawal
            if db.update_wallet(user_id, wallet_address) and db.deduct_balance(user_id, balance):
                await message.answer(
                    f"✅ **Withdrawal Request Submitted**\n\n"
                    f"💰 **Amount:** {balance:.2f} USDT\n"
                    f"💳 **Wallet:** {wallet_address}\n\n"
                    f"⏳ **Please wait 24 hours to receive your payment.**\n\n"
                    f"Your request has been processed and will be sent to your wallet within 24 hours.",
                    parse_mode="Markdown",
                    reply_markup=get_main_menu_keyboard()
                )
            else:
                await message.answer(
                    "❌ Error processing withdrawal. Please try again.",
                    reply_markup=get_main_menu_keyboard()
                )
        else:
            await message.answer(
                f"❌ Insufficient balance. You need {MINIMUM_WITHDRAWAL:.2f} USDT to withdraw.",
                reply_markup=get_main_menu_keyboard()
            )
        
        # Remove from waiting state
        enter_wallet_callback.waiting_for_wallet.discard(user_id)
    else:
        # Handle other messages with auto-reply
        await auto_reply_handler(message)

async def auto_reply_handler(message: types.Message):
    """Handle unrecognized messages with intelligent auto-replies."""
    user = message.from_user
    user_id = user.id
    message_text = message.text.lower() if message.text else ""
    
    # Check if user is verified
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT balance, referral_count FROM users WHERE user_id = ?', (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    
    is_verified = user_data is not None
    
    # Auto-reply responses based on message content
    if any(word in message_text for word in ['help', 'support', 'assist', 'how']):
        total_starts = db.get_total_start_requests()
        await message.answer(
            "🤖 **Auto-Reply: Help**\n\n"
            "I'm here to help! Here are the available commands:\n\n"
            "• /start - Access main menu (anytime)\n"
            "• /help - Show help information\n"
            "• /status - Check your account status\n\n"
            f"📊 Total /start requests received: {total_starts}\n\n"
            "Use the buttons below for quick actions.",
            reply_markup=get_main_menu_keyboard() if is_verified else get_join_keyboard()
        )
    elif any(word in message_text for word in ['balance', 'money', 'usdt', 'earning', 'earn']):
        if is_verified:
            balance, referrals = user_data
            await message.answer(
                f"💰 **Auto-Reply: Your Balance**\n\n"
                f"Current Balance: **{balance:.2f} USDT**\n"
                f"Total Referrals: **{referrals}**\n"
                f"Available for withdrawal: **{max(0, balance - 1.0):.2f} USDT**\n\n"
                f"Minimum withdrawal: 1.0 USDT",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await message.answer(
                "💰 **Auto-Reply: Join Required**\n\n"
                "To access balance and earning features, please join our required channels first.",
                reply_markup=get_join_keyboard()
            )
    elif any(word in message_text for word in ['withdraw', 'payout', 'cash', 'payment']):
        if is_verified:
            balance, _ = user_data
            if balance >= MINIMUM_WITHDRAWAL:
                await message.answer(
                    f"💸 **Auto-Reply: Withdrawal Available**\n\n"
                    f"Your balance: {balance:.2f} USDT\n"
                    f"Ready for withdrawal!\n\n"
                    f"Processing time: 24-48 hours\n"
                    f"Use the 'Withdraw' button to proceed.",
                    reply_markup=get_main_menu_keyboard()
                )
            else:
                needed = MINIMUM_WITHDRAWAL - balance
                await message.answer(
                    f"💸 **Auto-Reply: Minimum Not Met**\n\n"
                    f"Current balance: {balance:.2f} USDT\n"
                    f"Minimum required: {MINIMUM_WITHDRAWAL} USDT\n"
                    f"Need {needed:.2f} more USDT\n\n"
                    f"Refer more friends to reach the minimum!",
                    reply_markup=get_main_menu_keyboard()
                )
        else:
            await message.answer(
                "💸 **Auto-Reply: Join Required**\n\n"
                "Please join our required channels to access withdrawal features.",
                reply_markup=get_join_keyboard()
            )
    elif any(word in message_text for word in ['refer', 'invite', 'friend', 'link']):
        if is_verified:
            referral_link = f"https://t.me/{MESSAGES['bot_username']}?start={user_id}"
            await message.answer(
                f"👥 **Auto-Reply: Your Referral Link**\n\n"
                f"Earn 0.1 USDT for each successful referral!\n\n"
                f"Your link:\n`{referral_link}`\n\n"
                f"Share this link with friends to earn rewards.",
                parse_mode="Markdown",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await message.answer(
                "👥 **Auto-Reply: Join First**\n\n"
                "Join our channels to access the referral system and start earning!",
                reply_markup=get_join_keyboard()
            )
    elif any(word in message_text for word in ['thank', 'thanks', 'good', 'great', 'awesome']):
        await message.answer(
            "😊 **Auto-Reply**\n\n"
            "You're welcome! I'm glad I could help.\n\n"
            "Feel free to use the menu buttons for any other actions you need.",
            reply_markup=get_main_menu_keyboard() if is_verified else get_join_keyboard()
        )
    elif any(word in message_text for word in ['hi', 'hello', 'hey', 'good morning', 'good evening']):
        await message.answer(
            f"👋 **Auto-Reply: Hello!**\n\n"
            f"Hello {user.first_name}! Welcome to our USDT airdrop bot.\n\n"
            f"{'Use the menu below to access your account.' if is_verified else 'Please join our required channels to get started.'}\n\n"
            f"How can I help you today?",
            reply_markup=get_main_menu_keyboard() if is_verified else get_join_keyboard()
        )
    else:
        # Generic auto-reply for other messages
        await message.answer(
            "🤖 **Auto-Reply**\n\n"
            "Thank you for your message! I'm currently handling requests automatically.\n\n"
            "For immediate assistance:\n"
            "• Use the menu buttons below\n"
            "• Type /help for available commands\n"
            "• Type /status to check your account\n\n"
            "Your message has been received and logged.",
            reply_markup=get_main_menu_keyboard() if is_verified else get_join_keyboard()
        )

def register_handlers(dp: Dispatcher, bot: Bot):
    """
    Register all handlers with the dispatcher.
    
    Args:
        dp: Dispatcher instance
        bot: Bot instance
    """
    # Message handlers
    dp.register_message_handler(
        lambda message: start_handler(message, bot),
        commands=['start']
    )
    dp.register_message_handler(help_handler, commands=['help'])
    dp.register_message_handler(
        lambda message: status_handler(message, bot),
        commands=['status']
    )
    
    # Callback query handlers
    dp.register_callback_query_handler(
        lambda callback_query: check_channels_callback(callback_query, bot),
        lambda callback_query: callback_query.data == "check_channels"
    )
    dp.register_callback_query_handler(
        help_callback,
        lambda callback_query: callback_query.data == "help"
    )
    dp.register_callback_query_handler(
        lambda callback_query: status_callback(callback_query, bot),
        lambda callback_query: callback_query.data == "status"
    )
    
    # Referral system callbacks
    dp.register_callback_query_handler(
        lambda callback_query: refer_callback(callback_query, bot),
        lambda callback_query: callback_query.data == "refer"
    )
    dp.register_callback_query_handler(
        balance_callback,
        lambda callback_query: callback_query.data == "balance"
    )
    dp.register_callback_query_handler(
        withdraw_callback,
        lambda callback_query: callback_query.data == "withdraw"
    )
    dp.register_callback_query_handler(
        back_to_menu_callback,
        lambda callback_query: callback_query.data == "back_to_menu"
    )
    dp.register_callback_query_handler(
        enter_wallet_callback,
        lambda callback_query: callback_query.data == "enter_wallet"
    )
    
    # Text message handler for wallet addresses
    dp.register_message_handler(
        handle_wallet_message,
        content_types=['text']
    )
    
    logger.info("All handlers registered successfully")
