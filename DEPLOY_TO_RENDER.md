# Deploy Telegram Bot to Render (Free 24/7 Hosting)

## Step-by-Step Deployment Guide

### 1. Prepare Your Code
First, create a GitHub repository with all your bot files:

1. Go to GitHub.com and create a new repository
2. Upload all these files from your Replit project:
   - `main.py`
   - `admin_app.py`
   - `handlers.py`
   - `keyboards.py`
   - `config.py`
   - `database.py`
   - `utils.py`
   - `render.yaml`
   - `start_bot.py`
   - `templates/` folder (all HTML files)
   - `static/` folder (if any)

### 2. Create Render Account
1. Go to https://render.com
2. Sign up for a free account
3. Connect your GitHub account

### 3. Deploy the Bot

#### Option A: Using render.yaml (Recommended)
1. In Render dashboard, click "New +"
2. Select "Blueprint"
3. Connect your GitHub repository
4. Select the repository with your bot code
5. Render will automatically detect the `render.yaml` file
6. Set the environment variable:
   - Key: `BOT_TOKEN`
   - Value: Your actual bot token from BotFather

#### Option B: Manual Setup
1. Create Web Service for Admin Panel:
   - Click "New +" → "Web Service"
   - Connect GitHub repository
   - Build Command: `pip install aiogram flask requests`
   - Start Command: `python admin_app.py`
   - Set BOT_TOKEN environment variable

2. Create Background Worker for Bot:
   - Click "New +" → "Background Worker"
   - Connect same GitHub repository
   - Build Command: `pip install aiogram flask requests`
   - Start Command: `python main.py`
   - Set BOT_TOKEN environment variable

### 4. Environment Variables
Set these in Render dashboard:
- `BOT_TOKEN`: Your Telegram bot token

### 5. Database File
Your SQLite database (`bot_users.db`) will be created automatically on first run.
Note: Render's free tier has ephemeral storage, so database may reset on restarts.

### 6. Access Your Bot
- Bot will be running 24/7 on Render
- Admin panel will be accessible via the web service URL
- Both services restart automatically if they crash

## Benefits of Render Free Tier:
- ✅ 750 hours/month (enough for 24/7 operation)
- ✅ Automatic SSL certificates
- ✅ GitHub integration with auto-deploy
- ✅ Environment variable management
- ✅ Logs and monitoring
- ✅ Custom domains support

## Important Notes:
1. Free tier may have cold starts (15-30 second delay when inactive)
2. Database data may be lost on restarts (upgrade to paid for persistent storage)
3. Services sleep after 15 minutes of inactivity but wake up automatically
4. Your bot will continue working even when you're offline

## Alternative Free Options:
- **Railway**: 500 hours/month free
- **Heroku**: Limited free tier
- **Oracle Cloud**: Always free VPS (more complex setup)
- **Google Cloud Run**: Pay-per-use (essentially free for small bots)

Your bot is now ready for 24/7 deployment!