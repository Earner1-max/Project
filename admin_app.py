"""
Admin web application for managing bot users and sending updates.
"""

import asyncio
import logging
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from database import db
from config import BOT_TOKEN
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24)

@app.route('/')
def dashboard():
    """Main dashboard showing user statistics."""
    try:
        # Get user statistics
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Total users
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        # Total balance distributed
        cursor.execute('SELECT SUM(balance) FROM users')
        total_balance = cursor.fetchone()[0] or 0
        
        # Total referrals
        cursor.execute('SELECT COUNT(*) FROM users WHERE referrer_id IS NOT NULL')
        total_referrals = cursor.fetchone()[0]
        
        # Recent users (last 10)
        cursor.execute('''
            SELECT user_id, username, full_name, balance, joined_at 
            FROM users 
            ORDER BY joined_at DESC 
            LIMIT 10
        ''')
        recent_users = cursor.fetchall()
        
        conn.close()
        
        stats = {
            'total_users': total_users,
            'total_balance': round(total_balance, 2),
            'total_referrals': total_referrals,
            'recent_users': recent_users
        }
        
        return render_template('dashboard.html', stats=stats)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        flash(f"Error loading dashboard: {e}", 'error')
        return render_template('dashboard.html', stats={})

@app.route('/users')
def users_list():
    """Display all users with their information."""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, username, full_name, balance, 
                   (SELECT COUNT(*) FROM users u2 WHERE u2.referrer_id = users.user_id) as referral_count,
                   joined_at, wallet_address
            FROM users 
            ORDER BY joined_at DESC
        ''')
        users = cursor.fetchall()
        conn.close()
        
        return render_template('users.html', users=users)
    except Exception as e:
        logger.error(f"Users list error: {e}")
        flash(f"Error loading users: {e}", 'error')
        return render_template('users.html', users=[])

@app.route('/broadcast')
def broadcast_page():
    """Broadcast message page."""
    return render_template('broadcast.html')

@app.route('/send_broadcast', methods=['POST'])
def send_broadcast():
    """Send broadcast message to all users."""
    try:
        message = request.form.get('message', '').strip()
        announcement_type = request.form.get('type', 'text')
        
        if not message:
            flash('Message cannot be empty', 'error')
            return redirect(url_for('broadcast_page'))
        
        # Handle image upload
        image_path = None
        if announcement_type == 'image' and 'image' in request.files:
            image_file = request.files['image']
            if image_file.filename:
                import os
                from werkzeug.utils import secure_filename
                import time
                
                # Create uploads directory if it doesn't exist
                upload_dir = 'static/uploads'
                os.makedirs(upload_dir, exist_ok=True)
                
                # Save the uploaded image
                filename = secure_filename(image_file.filename)
                timestamp = int(time.time())
                unique_filename = f"{timestamp}_{filename}"
                image_path = os.path.join(upload_dir, unique_filename)
                image_file.save(image_path)
        
        # Get all user IDs
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users')
        user_ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if not user_ids:
            flash('No users found to send message to', 'warning')
            return redirect(url_for('broadcast_page'))
        
        # Send messages using Telegram Bot API
        success_count, failed_count = send_broadcast_sync(user_ids, message, image_path, announcement_type)
        
        flash(f'Announcement sent to {len(user_ids)} users successfully!', 'success')
        return redirect(url_for('broadcast_page'))
        
    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        flash(f"Error sending announcement: {e}", 'error')
        return redirect(url_for('broadcast_page'))

def send_broadcast_sync(user_ids, message, image_path=None, announcement_type='text'):
    """Send broadcast message to users using Telegram Bot API."""
    success_count = 0
    failed_count = 0
    
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        logger.error("BOT_TOKEN environment variable not set")
        return success_count, failed_count
    
    for user_id in user_ids:
        try:
            import time
            
            if announcement_type == 'image' and image_path:
                # Send photo with caption
                url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
                
                with open(image_path, 'rb') as photo:
                    files = {'photo': photo}
                    data = {
                        'chat_id': user_id,
                        'caption': f"📢 <b>ANNOUNCEMENT</b> 📢\n\n{message}",
                        'parse_mode': 'HTML'
                    }
                    
                    response = requests.post(url, data=data, files=files, timeout=15)
            else:
                # Send text message
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                data = {
                    'chat_id': user_id,
                    'text': f"📢 <b>ANNOUNCEMENT</b> 📢\n\n{message}",
                    'parse_mode': 'HTML'
                }
                
                response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                success_count += 1
                logger.info(f"Announcement sent to user {user_id}")
            else:
                failed_count += 1
                logger.error(f"Failed to send announcement to user {user_id}: {response.text}")
            
            # Small delay to avoid rate limiting
            time.sleep(0.05)
            
        except Exception as e:
            failed_count += 1
            logger.error(f"Error sending announcement to user {user_id}: {e}")
    
    logger.info(f"Announcement completed: {success_count} successful, {failed_count} failed")
    return success_count, failed_count

@app.route('/user/<int:user_id>')
def user_detail(user_id):
    """Show detailed information about a specific user."""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get user info
        cursor.execute('''
            SELECT user_id, username, full_name, balance, joined_at, wallet_address, referrer_id
            FROM users WHERE user_id = ?
        ''', (user_id,))
        user = cursor.fetchone()
        
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('users_list'))
        
        # Get referrals made by this user
        cursor.execute('''
            SELECT user_id, username, full_name, joined_at
            FROM users WHERE referrer_id = ?
            ORDER BY joined_at DESC
        ''', (user_id,))
        referrals = cursor.fetchall()
        
        conn.close()
        
        return render_template('user_detail.html', user=user, referrals=referrals)
    except Exception as e:
        logger.error(f"User detail error: {e}")
        flash(f"Error loading user details: {e}", 'error')
        return redirect(url_for('users_list'))

@app.route('/database')
def database_page():
    """Database management page."""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get table info
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        # Get users table schema
        cursor.execute("PRAGMA table_info(users)")
        schema = cursor.fetchall()
        
        # Get some database stats
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE balance > 0')
        users_with_balance = cursor.fetchone()[0]
        
        cursor.execute('SELECT AVG(balance) FROM users WHERE balance > 0')
        avg_balance = cursor.fetchone()[0] or 0
        
        conn.close()
        
        db_stats = {
            'tables': tables,
            'schema': schema,
            'total_users': total_users,
            'users_with_balance': users_with_balance,
            'avg_balance': round(avg_balance, 2)
        }
        
        return render_template('database.html', stats=db_stats)
    except Exception as e:
        logger.error(f"Database page error: {e}")
        flash(f"Error loading database: {e}", 'error')
        return render_template('database.html', stats={})

@app.route('/database/query', methods=['POST'])
def execute_query():
    """Execute SQL query."""
    try:
        query = request.form.get('query', '').strip()
        if not query:
            flash('Query cannot be empty', 'error')
            return redirect(url_for('database_page'))
        
        # Security check - only allow SELECT statements
        if not query.upper().startswith('SELECT'):
            flash('Only SELECT queries are allowed for security', 'error')
            return redirect(url_for('database_page'))
        
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        conn.close()
        
        return render_template('query_results.html', 
                             results=results, 
                             columns=columns, 
                             query=query)
        
    except Exception as e:
        logger.error(f"Query execution error: {e}")
        flash(f"Query error: {e}", 'error')
        return redirect(url_for('database_page'))

@app.route('/database')
def database_management():
    """Database management page."""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get table info
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        # Get users table data
        cursor.execute('SELECT * FROM users ORDER BY joined_at DESC LIMIT 50')
        users_data = cursor.fetchall()
        
        # Get column names
        cursor.execute('PRAGMA table_info(users)')
        columns = [row[1] for row in cursor.fetchall()]
        
        conn.close()
        
        return render_template('database.html', 
                             tables=tables, 
                             users_data=users_data, 
                             columns=columns)
    except Exception as e:
        logger.error(f"Database management error: {e}")
        flash(f"Error loading database: {e}", 'error')
        return render_template('database.html', tables=[], users_data=[], columns=[])

@app.route('/database/export')
def export_database():
    """Export database as CSV."""
    try:
        import csv
        import io
        from flask import make_response
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users ORDER BY joined_at DESC')
        users_data = cursor.fetchall()
        
        cursor.execute('PRAGMA table_info(users)')
        columns = [row[1] for row in cursor.fetchall()]
        
        conn.close()
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        writer.writerows(users_data)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = 'attachment; filename=bot_users.csv'
        
        return response
    except Exception as e:
        logger.error(f"Database export error: {e}")
        flash(f"Error exporting database: {e}", 'error')
        return redirect(url_for('database_management'))

@app.route('/api/stats')
def api_stats():
    """API endpoint for statistics."""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(balance) FROM users')
        total_balance = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE referrer_id IS NOT NULL')
        total_referrals = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'total_users': total_users,
            'total_balance': round(total_balance, 2),
            'total_referrals': total_referrals
        })
    except Exception as e:
        logger.error(f"API stats error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/live-users')
def api_live_users():
    """API endpoint for live user activity."""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get all recent users
        cursor.execute('''
            SELECT user_id, username, full_name, balance, joined_at 
            FROM users 
            ORDER BY joined_at DESC
            LIMIT 50
        ''')
        recent_users = cursor.fetchall()
        
        # Get users joined today
        cursor.execute('''
            SELECT COUNT(*) FROM users 
            WHERE date(joined_at) = date('now')
        ''')
        today_users = cursor.fetchone()[0]
        
        # Get total active users (joined in last 24 hours)
        cursor.execute('''
            SELECT COUNT(*) FROM users 
            WHERE datetime(joined_at) >= datetime('now', '-24 hours')
        ''')
        active_users = cursor.fetchone()[0]
        
        conn.close()
        
        users_list = []
        for user in recent_users:
            users_list.append({
                'user_id': user[0],
                'username': user[1] or 'No username',
                'full_name': user[2] or 'No name',
                'balance': float(user[3]),
                'joined_at': user[4],
                'time_ago': get_time_ago(user[4])
            })
        
        return jsonify({
            'recent_users': users_list,
            'today_users': today_users,
            'active_users': active_users,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"API live users error: {e}")
        return jsonify({'error': str(e)}), 500

def get_time_ago(timestamp_str):
    """Calculate time ago from timestamp."""
    try:
        from datetime import datetime
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        now = datetime.now()
        diff = now - timestamp
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}h ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}m ago"
        else:
            return "Just now"
    except:
        return "Unknown"

@app.route('/api/activity-feed')
def api_activity_feed():
    """API endpoint for real-time activity feed."""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get latest activities with user info (show all recent activity)
        cursor.execute('''
            SELECT u.user_id, u.username, u.full_name, u.balance, u.joined_at,
                   CASE 
                       WHEN u.referrer_id IS NOT NULL THEN 'referral'
                       ELSE 'new_user'
                   END as activity_type,
                   u.referrer_id
            FROM users u
            ORDER BY u.joined_at DESC
            LIMIT 30
        ''')
        activities = cursor.fetchall()
        
        conn.close()
        
        activity_list = []
        for activity in activities:
            activity_list.append({
                'user_id': activity[0],
                'username': activity[1] or 'Anonymous',
                'full_name': activity[2] or 'Unknown User',
                'balance': float(activity[3]),
                'joined_at': activity[4],
                'activity_type': activity[5],
                'referrer_id': activity[6],
                'time_ago': get_time_ago(activity[4])
            })
        
        return jsonify({
            'activities': activity_list,
            'count': len(activity_list),
            'last_update': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"API activity feed error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/code-editor')
def code_editor():
    """Code editor page for modifying bot files."""
    try:
        # Get list of Python files in the project
        files = []
        for filename in ['main.py', 'handlers.py', 'keyboards.py', 'config.py', 'database.py', 'utils.py']:
            if os.path.exists(filename):
                files.append(filename)
        
        return render_template('code_editor.html', files=files)
    except Exception as e:
        logger.error(f"Code editor error: {e}")
        flash(f"Error loading code editor: {e}", 'error')
        return redirect(url_for('dashboard'))

@app.route('/api/get-file/<filename>')
def get_file_content(filename):
    """API endpoint to get file content."""
    try:
        # Security check - only allow specific files
        allowed_files = ['main.py', 'handlers.py', 'keyboards.py', 'config.py', 'database.py', 'utils.py', 'admin_app.py']
        if filename not in allowed_files:
            return jsonify({'error': 'File not allowed'}), 403
        
        if not os.path.exists(filename):
            return jsonify({'error': 'File not found'}), 404
        
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            'filename': filename,
            'content': content,
            'success': True
        })
    except Exception as e:
        logger.error(f"Get file error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/save-file/<filename>', methods=['POST'])
def save_file_content(filename):
    """API endpoint to save file content."""
    try:
        # Security check - only allow specific files
        allowed_files = ['main.py', 'handlers.py', 'keyboards.py', 'config.py', 'database.py', 'utils.py']
        if filename not in allowed_files:
            return jsonify({'error': 'File not allowed'}), 403
        
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({'error': 'No content provided'}), 400
        
        # Create backup
        backup_filename = f"{filename}.backup"
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                backup_content = f.read()
            with open(backup_filename, 'w', encoding='utf-8') as f:
                f.write(backup_content)
        
        # Save new content
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(data['content'])
        
        logger.info(f"File {filename} saved successfully")
        return jsonify({
            'success': True,
            'message': f'File {filename} saved successfully',
            'backup_created': backup_filename
        })
    except Exception as e:
        logger.error(f"Save file error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/restart-bot', methods=['POST'])
def restart_bot():
    """API endpoint to restart the bot."""
    try:
        import subprocess
        
        # Kill existing bot process
        subprocess.run(['pkill', '-f', 'python main.py'], check=False)
        
        # Start new bot process
        subprocess.Popen(['python', 'main.py'], cwd='.')
        
        logger.info("Bot restarted successfully")
        return jsonify({
            'success': True,
            'message': 'Bot restarted successfully'
        })
    except Exception as e:
        logger.error(f"Restart bot error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Initialize database
    db.init_database()
    logger.info("Admin web application starting...")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)