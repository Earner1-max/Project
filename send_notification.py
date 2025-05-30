#!/usr/bin/env python3
"""
Send notification to all bot users
Usage: python send_notification.py "Your message here"
"""

import os
import sys
import sqlite3
import requests
import time
from datetime import datetime

def get_bot_users():
    """Get all user IDs from database."""
    try:
        conn = sqlite3.connect('bot_users.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_id FROM users')
        users = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return users
    except Exception as e:
        print(f"Database error: {e}")
        return []

def send_notification(user_ids, message):
    """Send notification to users using Telegram Bot API."""
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        print("Error: BOT_TOKEN environment variable not set")
        return
    
    success_count = 0
    failed_count = 0
    
    print(f"Sending notification to {len(user_ids)} users...")
    print(f"Message: {message}")
    print("-" * 50)
    
    for i, user_id in enumerate(user_ids, 1):
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                'chat_id': user_id,
                'text': f"📢 NOTIFICATION 📢\n\n{message}",
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                success_count += 1
                print(f"✅ [{i}/{len(user_ids)}] Sent to user {user_id}")
            else:
                failed_count += 1
                print(f"❌ [{i}/{len(user_ids)}] Failed to send to user {user_id}: {response.text}")
            
            # Rate limiting - wait between requests
            time.sleep(0.1)
            
        except Exception as e:
            failed_count += 1
            print(f"❌ [{i}/{len(user_ids)}] Error sending to user {user_id}: {e}")
    
    print("-" * 50)
    print(f"✅ Success: {success_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"📊 Total: {len(user_ids)}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python send_notification.py \"Your message here\"")
        print("Example: python send_notification.py \"Welcome to our new feature!\"")
        return
    
    message = sys.argv[1]
    
    # Get all users
    users = get_bot_users()
    if not users:
        print("No users found in database")
        return
    
    # Confirm before sending
    print(f"About to send notification to {len(users)} users:")
    print(f"Message: {message}")
    confirm = input("Continue? (y/N): ").lower().strip()
    
    if confirm == 'y':
        send_notification(users, message)
    else:
        print("Cancelled")

if __name__ == "__main__":
    main()