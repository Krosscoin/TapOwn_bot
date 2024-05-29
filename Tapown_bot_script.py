
import logging
import asyncio
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime, timedelta
import json
import random

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Global Variables
users = {}
tasks = {}
leaderboard = []
missions = {}
referrals = {}
stats = {
    'total_share_balance': 0,
    'total_touches': 0,
    'total_players': 0,
    'daily_users': 0,
    'online_players': 0
}

# Read the Telegram token from the environment variable
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Load users data from file
def load_users():
    global users
    if os.path.exists('users.json'):
        with open('users.json', 'r') as file:
            users = json.load(file)

# Save users data to file
def save_users():
    with open('users.json', 'w') as file:
        json.dump(users, file)

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    referral_code = context.args[0] if context.args else None

    if user.id not in users:
        users[user.id] = {
            'username': user.username,
            'balance': 0,
            'touches': 0,
            'last_active': datetime.now().isoformat(),
            'boost_last_played': None,
            'referrals': 0
        }
        stats['total_players'] += 1

        if referral_code and referral_code in users:
            users[referral_code]['referrals'] += 1
            reward_referral(users[referral_code])

        save_users()

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

    await context.bot.send_message(chat_id=chat_id, text="Welcome to TapOwn! Start tapping and earn OWN tokens!", reply_markup=reply_markup)

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

    if query.data == 'tap':
        users[user.id]['touches'] += 1
        users[user.id]['balance'] += 1  # Increase balance by 1 OWN token per tap
        users[user.id]['last_active'] = datetime.now().isoformat()
        stats['total_touches'] += 1
        stats['total_share_balance'] += 1

        save_users()

        await query.edit_message_text(text=f"You tapped! Your balance: {users[user.id]['balance']} OWN tokens.")
    elif query.data == 'leaderboard':
        leaderboard_text = "🏆 Leaderboard 🏆\n\n"
        sorted_users = sorted(users.items(), key=lambda x: x[1]['balance'], reverse=True)
        for i, (user_id, data) in enumerate(sorted_users[:50], start=1):
            leaderboard_text += f"{i}. {data['username']}: {data['balance']} OWN tokens\n"
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
        stats_text = (
            f"📊 Global Stats 📊\n\n"
            f"Total Share Balance: {stats['total_share_balance']} OWN tokens\n"
            f"Total Touches: {stats['total_touches']}\n"
            f"Total Players: {stats['total_players']}\n"
            f"Daily Users: {stats['daily_users']}\n"
            f"Online Players: {stats['online_players']}\n"
        )
        await query.edit_message_text(text=stats_text)
    elif query.data == 'boost':
        if 'boost_last_played' not in users[user.id] or \
           datetime.strptime(users[user.id]['boost_last_played'], '%Y-%m-%d').date() < datetime.today().date():
            users[user.id]['boost_last_played'] = datetime.today().isoformat()
            guess = random.randint(1, 10)
            keyboard = [[InlineKeyboardButton(str(i), callback_data=f'boost_{i}') for i in range(1, 11)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="🔋 Boost Page 🔋\nGuess a number between 1 and 10 to win 300000 OWN tokens.", reply_markup=reply_markup)
        else:
            await query.edit_message_text(text="🔋 Boost Page 🔋\nYou can only play the Boost game once a day.")
    elif query.data.startswith('boost_'):
        number = int(query.data.split('_')[1])
        correct_number = random.randint(1, 10)
        if number == correct_number:
            users[user.id]['balance'] += 300000
            save_users()
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
            [InlineKeyboardButton("Join Kross Blockchain on X", url="https://x.com/krosscoin_team"), InlineKeyboardButton("Check", callback_data='check_kross_x')],
            [InlineKeyboardButton("Join Hashgreed on X", url="https://x.com/hashgreed"), InlineKeyboardButton("Check", callback_data='check_hashgreed_x')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=missions_text, reply_markup=reply_markup)
    elif query.data == 'register':
        await query.edit_message_text(
            text="To register your Kross Wallet, please follow these steps:\n\n1. Go to the Kross Shield bot: [Kross Shield Bot](https://t.me/krosscoinbot)\n2. Interact with the bot using the /myaddress command.\n3. Make sure to register with the same Telegram username."
        )
    elif query.data.startswith('check_'):
        mission = query.data.split('_')[1]
         # You need to implement the logic to check if the user is a member of the specified community.
        # For now, let's assume the check is successful for demonstration purposes.
        is_member = True  # This should be replaced with actual membership checking logic.
        if is_member:
            rewards = {
                'tapown': 10000,
                'kross': 15000,
                'hashgreed': 15000,
                'kross_x': 75000,
                'hashgreed_x': 75000
            }
            users[user.id]['balance'] += rewards[mission]
            save_users()
            await query.edit_message_text(text=f"Mission Accomplished! You have been rewarded {rewards[mission]} OWN tokens.")
        else:
            await query.edit_message_text(text="Mission not done yet, kindly attempt to join.")

async def main():
    load_users()
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))

    # Use this workaround to manage the event loop correctly
    await application.initialize()
    try:
        await application.start()
        await application.updater.start_polling()
        await application.updater.idle()
    finally:
        await application.stop()
        await application.shutdown()

if __name__ == "__main__":
    asyncio.run(main())

