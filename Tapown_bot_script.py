import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import asyncio
import nest_asyncio
from datetime import datetime, timedelta
import sqlite3
import random

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Read the Telegram token from the environment variable
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Database setup
conn = sqlite3.connect('tapown_bot.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        balance INTEGER,
        touches INTEGER,
        last_active TEXT,
        boost_last_played TEXT,
        referrals INTEGER
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS missions (
        user_id INTEGER,
        mission_name TEXT,
        completed INTEGER,
        last_checked TEXT,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS stats (
        key TEXT PRIMARY KEY,
        value INTEGER
    )
''')
conn.commit()

# Initialize stats if they don't exist
cursor.execute("INSERT OR IGNORE INTO stats (key, value) VALUES ('total_share_balance', 0)")
cursor.execute("INSERT OR IGNORE INTO stats (key, value) VALUES ('total_touches', 0)")
cursor.execute("INSERT OR IGNORE INTO stats (key, value) VALUES ('total_players', 0)")
cursor.execute("INSERT OR IGNORE INTO stats (key, value) VALUES ('daily_users', 0)")
cursor.execute("INSERT OR IGNORE INTO stats (key, value) VALUES ('online_players', 0)")
conn.commit()

# Load users data from database
def load_user(user_id):
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    if user:
        return {
            'user_id': user[0],
            'username': user[1],
            'balance': user[2],
            'touches': user[3],
            'last_active': user[4],
            'boost_last_played': user[5],
            'referrals': user[6]
        }
    return None

# Save user data to database
def save_user(user):
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, balance, touches, last_active, boost_last_played, referrals)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user['user_id'], user['username'], user['balance'], user['touches'], user['last_active'], user['boost_last_played'], user['referrals']))
    conn.commit()

# Update stats in database
def update_stats():
    cursor.execute("SELECT SUM(balance), SUM(touches), COUNT(*), SUM(CASE WHEN DATE(last_active) = DATE('now') THEN 1 ELSE 0 END) FROM users")
    total_share_balance, total_touches, total_players, daily_users = cursor.fetchone()
    online_players = 0  # Implement actual tracking if required

    cursor.execute("UPDATE stats SET value = ? WHERE key = 'total_share_balance'", (total_share_balance,))
    cursor.execute("UPDATE stats SET value = ? WHERE key = 'total_touches'", (total_touches,))
    cursor.execute("UPDATE stats SET value = ? WHERE key = 'total_players'", (total_players,))
    cursor.execute("UPDATE stats SET value = ? WHERE key = 'daily_users'", (daily_users,))
    cursor.execute("UPDATE stats SET value = ? WHERE key = 'online_players'", (online_players,))
    conn.commit()

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    referral_code = context.args[0] if context.args else None

    existing_user = load_user(user.id)
    if not existing_user:
        new_user = {
            'user_id': user.id,
            'username': user.username,
            'balance': 0,
            'touches': 0,
            'last_active': datetime.now().isoformat(),
            'boost_last_played': None,
            'referrals': 0
        }
        save_user(new_user)
        existing_user = new_user

        if referral_code:
            referrer = load_user(referral_code)
            if referrer:
                referrer['referrals'] += 1
                reward_referral(referrer)
                save_user(referrer)

    referral_link = f"https://t.me/tapown_bot?start={user.username}"

    keyboard = [
        [InlineKeyboardButton("Tap", callback_data='tap')],
        [InlineKeyboardButton("Leaderboard", callback_data='leaderboard')],
        [InlineKeyboardButton("Tasks", callback_data='tasks')],
        [InlineKeyboardButton("Stats", callback_data='stats')],
        [InlineKeyboardButton("Boost", callback_data='boost')],
        [InlineKeyboardButton("Missions", callback_data='missions')],
        [InlineKeyboardButton("Referral Link", url=referral_link)],
        [InlineKeyboardButton("Register", callback_data='register')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(chat_id=chat_id, text="Welcome to TapOwn By Kross Blockchain! Start tapping and earning OWN tokens which you'll swap for SEC registered RWA tokens on Hashgreed! OWN your World", reply_markup=reply_markup)

def reward_referral(referrer):
    referral_rewards = {
        1: 5000,
        5: 35000,
        10: 100000,
        50: 500000,
        100: 1500000
    }
    for count, reward in referral_rewards.items():
        if referrer['referrals'] == count:
            referrer['balance'] += reward
            break

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user

    await query.answer()

    existing_user = load_user(user.id)
    if not existing_user:
        await query.edit_message_text(text="User not found. Please restart the bot using /start command.")
        return

    if query.data == 'tap':
        existing_user['touches'] += 1
        existing_user['balance'] += 1  # Increase balance by 1 OWN token per tap
        existing_user['last_active'] = datetime.now().isoformat()
        save_user(existing_user)
        update_stats()

        await query.edit_message_text(text=f"You tapped! Your balance: {existing_user['balance']} OWN tokens.")
    elif query.data == 'leaderboard':
        leaderboard_text = "🏆 Leaderboard 🏆\n\n"
        cursor.execute('SELECT username, balance FROM users ORDER BY balance DESC LIMIT 50')
        top_users = cursor.fetchall()
        for i, user in enumerate(top_users, start=1):
            leaderboard_text += f"{i}. {user[0]}: {user[1]} OWN tokens\n"
        await query.edit_message_text(text=leaderboard_text)
    elif query.data == 'tasks':
        tasks_text = "📋 Tasks 📋\n\nRefer friends using your referral link to earn more OWN tokens.\n"
        tasks_text += "Refer 1 Friend, get 5000 OWN tokens\n"
        tasks_text += "Refer 5 Friends, get 35000 OWN tokens\n"
        tasks_text += "Refer 10 Friends, get 100000 OWN tokens\n"
        tasks_text += "Refer 50 Friends, get 500000 OWN tokens\n"
        tasks_text += "Refer 100 Friends, get 1500000 OWN tokens\n"
        await query.edit_message_text(text=tasks_text)
    elif query.data == 'stats':
        cursor.execute('SELECT value FROM stats WHERE key = "total_share_balance"')
        total_share_balance = cursor.fetchone()[0]
        cursor.execute('SELECT value FROM stats WHERE key = "total_touches"')
        total_touches = cursor.fetchone()[0]
        cursor.execute('SELECT value FROM stats WHERE key = "total_players"')
        total_players = cursor.fetchone()[0]
        cursor.execute('SELECT value FROM stats WHERE key = "daily_users"')
        daily_users = cursor.fetchone()[0]
        cursor.execute('SELECT value FROM stats WHERE key = "online_players"')
        online_players = cursor.fetchone()[0]

        stats_text = (
            f"📊 Global Stats 📊\n\n"
            f"Total Share Balance: {total_share_balance} OWN tokens\n"
            f"Total Touches: {total_touches}\n"
            f"Total Players: {total_players}\n"
            f"Daily Users: {daily_users}\n"
            f"Online Players: {online_players}\n"
        )
        await query.edit_message_text(text=stats_text)
    elif query.data == 'boost':
        if not existing_user['boost_last_played'] or \
           datetime.strptime(existing_user['boost_last_played'], '%Y-%m-%d').date() < datetime.today().date():
            existing_user['boost_last_played'] = datetime.today().isoformat()
            save_user(existing_user)
            keyboard = [[InlineKeyboardButton(str(i), callback_data=f'boost_{i}')] for i in range(1, 11)]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="🔋 Boost Page 🔋\nGuess a number between 1 and 10 to win 300000 OWN tokens.", reply_markup=reply_markup)
        else:
            await query.edit_message_text(text="🔋 Boost Page 🔋\nYou can only play the Boost game once a day.")
    elif query.data.startswith('boost_'):
        number = int(query.data.split('_')[1])
        correct_number = random.randint(1, 10)
        if number == correct_number:
            existing_user['balance'] += 300000
            save_user(existing_user)
            update_stats()
            await query.edit_message_text(text="Congratulations! You guessed the right number and won 300000 OWN tokens.")
        else:
            await query.edit_message_text(text="Sorry, you guessed wrong. Try again tomorrow.")
    elif query.data == 'missions':
        missions_text = "🎉 Missions 🎉\n\nComplete the missions to earn additional rewards:\n"
        missions_text += "1. Join Our TapOwn Community, Reward: 10000 OWN tokens\n"
        missions_text += "2. Join the Kross Blockchain Community, Reward: 15000 OWN tokens\n"
        missions_text += "3. Join the Hashgreed Community, Reward: 15000 OWN tokens\n"
        missions_text += "4. Join Kross Blockchain on X, Reward: 75000 OWN tokens\n"
        missions_text += "5. Join Hashgreed on X, Reward: 75000 OWN tokens\n"
        keyboard = [
            [InlineKeyboardButton("Join TapOwn", url="https://t.me/tapownai"), InlineKeyboardButton("Check", callback_data='check_tapown')],
            [InlineKeyboardButton("Join Kross Blockchain", url="https://t.me/krosscoin_kss"), InlineKeyboardButton("Check", callback_data='check_kross')],
            [InlineKeyboardButton("Join Hashgreed", url="https://t.me/hashgreedroyals"), InlineKeyboardButton("Check", callback_data='check_hashgreed')],
            [InlineKeyboardButton("Join Kross Blockchain on X", url="https://x.com/krosscoin_team"), InlineKeyboardButton("Check", callback_data='check_x_kross')],
            [InlineKeyboardButton("Join Hashgreed on X", url="https://x.com/hashgreed"), InlineKeyboardButton("Check", callback_data='check_x_hashgreed')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=missions_text, reply_markup=reply_markup)
    elif query.data == 'register':
        await query.edit_message_text(
            text="To register your Kross Wallet, please follow these steps:\n\n1. Go to the Kross Shield bot: [Kross Shield Bot](https://t.me/krosscoinbot)\n2. Interact with the bot using the /myaddress command.\n3. Make sure to register with the same Telegram username."
        )
    elif query.data.startswith('check_'):
        mission = query.data.split('_')[1]
        if mission in ['tapown', 'kross', 'hashgreed']:
            is_member = True  # Replace with actual membership checking logic.
            if is_member:
                rewards = {
                    'tapown': 10000,
                    'kross': 15000,
                    'hashgreed': 15000
                }
                existing_user['balance'] += rewards[mission]
                save_user(existing_user)
                update_stats()
                await query.edit_message_text(text=f"Mission Accomplished! You have been rewarded {rewards[mission]} OWN tokens.")
            else:
                await query.edit_message_text(text="Mission not done yet, kindly attempt to join.")
        elif mission in ['x_kross', 'x_hashgreed']:
            # Record the time of the request to check membership after 24 hours
            cursor.execute('''
                INSERT OR REPLACE INTO missions (user_id, mission_name, completed, last_checked)
                VALUES (?, ?, ?, ?)
            ''', (existing_user['user_id'], mission, 0, datetime.now().isoformat()))
            conn.commit()
            await query.edit_message_text(text="TapOwn will verify your X follow within 24 hours and send your OWN tokens if confirmed.")

async def check_missions():
    while True:
        await asyncio.sleep(86400)  # Run the check every 24 hours
        cursor.execute('SELECT * FROM missions WHERE completed = 0')
        pending_missions = cursor.fetchall()
        for mission in pending_missions:
            user_id, mission_name, completed, last_checked = mission
            if datetime.strptime(last_checked, '%Y-%m-%dT%H:%M:%S.%f') + timedelta(hours=24) <= datetime.now():
                # Implement the actual checking logic for Twitter follows here
                is_member = True  # Replace with actual membership checking logic
                if is_member:
                    rewards = {
                        'x_kross': 75000,
                        'x_hashgreed': 75000
                    }
                    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
                    user = cursor.fetchone()
                    if user:
                        user_data = {
                            'user_id': user[0],
                            'username': user[1],
                            'balance': user[2] + rewards[mission_name],
                            'touches': user[3],
                            'last_active': user[4],
                            'boost_last_played': user[5],
                            'referrals': user[6]
                        }
                        save_user(user_data)
                        cursor.execute('UPDATE missions SET completed = 1 WHERE user_id = ? AND mission_name = ?', (user_id, mission_name))
                        conn.commit()

async def run_bot():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))

    await application.initialize()
    await application.start()
    await application.run_polling()

def main():
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(run_bot())
            asyncio.ensure_future(check_missions())
        else:
            asyncio.run(run_bot())
            asyncio.run(check_missions())
    except RuntimeError as e:
        if str(e) == "This event loop is already running":
            logger.error("Event loop is already running")
            loop = asyncio.get_event_loop()
            loop.create_task(run_bot())
            loop.create_task(check_missions())
            loop.run_forever()
        else:
            raise

if __name__ == "__main__":
    main()

