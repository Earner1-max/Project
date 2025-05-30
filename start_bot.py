#!/usr/bin/env python3
"""
Startup script for Render deployment
"""
import os
import subprocess
import sys
import time
import threading

def run_admin_app():
    """Run the admin web application"""
    print("Starting admin web application...")
    subprocess.run([sys.executable, "admin_app.py"])

def run_bot():
    """Run the Telegram bot"""
    print("Starting Telegram bot...")
    subprocess.run([sys.executable, "main.py"])

if __name__ == "__main__":
    # Check if BOT_TOKEN is set
    if not os.getenv("BOT_TOKEN"):
        print("ERROR: BOT_TOKEN environment variable is not set!")
        sys.exit(1)
    
    print("Starting Telegram Bot System...")
    
    # Start admin app in a separate thread
    admin_thread = threading.Thread(target=run_admin_app, daemon=True)
    admin_thread.start()
    
    # Give admin app time to start
    time.sleep(3)
    
    # Start the bot (main process)
    run_bot()