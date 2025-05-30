"""
Database management for user referrals and earnings.
"""

import sqlite3
import logging
from typing import Optional, Tuple
from config import REFERRAL_REWARD, WELCOME_BONUS

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "bot_users.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Initialize the database with required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                referrer_id INTEGER,
                referral_count INTEGER DEFAULT 0,
                balance REAL DEFAULT 0.0,
                wallet_address TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (referrer_id) REFERENCES users (user_id)
            )
        ''')
        
        # Create referrals table for tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER,
                reward_amount REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (referrer_id) REFERENCES users (user_id),
                FOREIGN KEY (referred_id) REFERENCES users (user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def add_user(self, user_id: int, username: str, full_name: str, referrer_id: Optional[int] = None) -> bool:
        """Add a new user to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if user already exists
            cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
            if cursor.fetchone():
                return False  # User already exists
            
            # Add new user with welcome bonus
            cursor.execute('''
                INSERT INTO users (user_id, username, full_name, referrer_id, balance, start_count, last_start)
                VALUES (?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            ''', (user_id, username, full_name, referrer_id, WELCOME_BONUS))
            
            # If this user was referred, add referral reward
            if referrer_id:
                self._add_referral_reward(cursor, referrer_id, user_id)
            
            conn.commit()
            logger.info(f"Added new user {user_id} with referrer {referrer_id}")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error adding user {user_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def _add_referral_reward(self, cursor, referrer_id: int, referred_id: int):
        """Add referral reward to referrer (internal method)."""
        # Update referrer's balance and count
        cursor.execute('''
            UPDATE users 
            SET balance = balance + ?, referral_count = referral_count + 1
            WHERE user_id = ?
        ''', (REFERRAL_REWARD, referrer_id))
        
        # Record the referral
        cursor.execute('''
            INSERT INTO referrals (referrer_id, referred_id, reward_amount)
            VALUES (?, ?, ?)
        ''', (referrer_id, referred_id, REFERRAL_REWARD))
        
        # Send notification to referrer about the reward
        self._send_referral_notification(referrer_id, referred_id)
    
    def _send_referral_notification(self, referrer_id: int, referred_id: int):
        """Send notification to referrer about new referral reward."""
        try:
            import requests
            import os
            import threading
            
            def send_notification():
                try:
                    bot_token = os.getenv('BOT_TOKEN')
                    if not bot_token:
                        logger.error("BOT_TOKEN not found for notification")
                        return
                    
                    # Get referrer's current balance and referral count
                    conn = self.get_connection()
                    cursor = conn.cursor()
                    cursor.execute('SELECT balance, referral_count FROM users WHERE user_id = ?', (referrer_id,))
                    result = cursor.fetchone()
                    conn.close()
                    
                    if result:
                        balance, referral_count = result
                        
                        message = f"""🎉 <b>New Referral Reward!</b> 🎉

💰 You earned <b>+{REFERRAL_REWARD} USDT</b> for a successful referral!
👤 New user ID: <code>{referred_id}</code>

📊 <b>Your Stats:</b>
💵 Current Balance: <b>{balance:.2f} USDT</b>
👥 Total Referrals: <b>{referral_count}</b>

Keep sharing your referral link to earn more! 🚀"""

                        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                        data = {
                            'chat_id': referrer_id,
                            'text': message,
                            'parse_mode': 'HTML'
                        }
                        
                        response = requests.post(url, data=data, timeout=10)
                        if response.status_code == 200:
                            logger.info(f"Referral notification sent to user {referrer_id}")
                        else:
                            logger.error(f"Failed to send referral notification to user {referrer_id}: {response.text}")
                            
                except Exception as e:
                    logger.error(f"Error in notification thread: {e}")
            
            # Send notification in background thread to avoid blocking
            thread = threading.Thread(target=send_notification)
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            logger.error(f"Error setting up referral notification: {e}")
    
    def get_user_stats(self, user_id: int) -> Tuple[float, int]:
        """Get user's balance and referral count."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT balance, referral_count FROM users WHERE user_id = ?
            ''', (user_id,))
            result = cursor.fetchone()
            if result:
                return (float(result[0]), int(result[1]))
            else:
                return (0.0, 0)
        except sqlite3.Error as e:
            logger.error(f"Error getting user stats for {user_id}: {e}")
            return (0.0, 0)
        finally:
            conn.close()
    
    def update_start_count(self, user_id: int) -> int:
        """Update and return the start command count for a user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if user exists and get current start_count
            cursor.execute('SELECT start_count FROM users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            
            if result:
                # User exists, increment start count
                current_count = result[0] if result[0] is not None else 0
                new_count = current_count + 1
                cursor.execute('''
                    UPDATE users 
                    SET start_count = ?, last_start = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                ''', (new_count, user_id))
                conn.commit()
                return new_count
            else:
                return 1  # New user will have count 1
                
        except sqlite3.Error as e:
            logger.error(f"Error updating start count for {user_id}: {e}")
            return 1
        finally:
            conn.close()
    
    def get_total_start_requests(self) -> int:
        """Get total number of start requests across all users."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT SUM(COALESCE(start_count, 1)) FROM users')
            result = cursor.fetchone()
            return result[0] if result[0] else 0
        except sqlite3.Error as e:
            logger.error(f"Error getting total start requests: {e}")
            return 0
        finally:
            conn.close()
    
    def update_wallet(self, user_id: int, wallet_address: str) -> bool:
        """Update user's wallet address."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE users SET wallet_address = ? WHERE user_id = ?
            ''', (wallet_address, user_id))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Error updating wallet for {user_id}: {e}")
            return False
        finally:
            conn.close()
    
    def deduct_balance(self, user_id: int, amount: float) -> bool:
        """Deduct amount from user's balance for withdrawal."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE users SET balance = balance - ? 
                WHERE user_id = ? AND balance >= ?
            ''', (amount, user_id, amount))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Error deducting balance for {user_id}: {e}")
            return False
        finally:
            conn.close()

# Global database instance
db = Database()