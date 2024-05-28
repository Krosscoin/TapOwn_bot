import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import random
import asyncio
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Replace with your actual bot token
TOKEN = '6609411086:AAE7wGvmSqwY1fSLPNo85wgNddD8CDW9wc8'

# In-memory data storage (replace with a persistent database in production)
user_data = {}
global_stats = {
    'total_balance': 0,
    'total_touches': 0,
    'total_players': 0,
    'daily_users': set(),
    'online_users': set()
}

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id not in user_data:
        user_data[user.id] = {'balance': 0, 'referrals': 0, 'last_active': datetime.now()}
        global_stats['total_players'] += 1
    await update.message.reply_text(
        f"Hi {user.first_name}! Welcome to TapOwn! Tap on the coin to earn OWN tokens. Use /tap to start tapping.",
        reply_markup=main_menu_keyboard()
    )

# Tap command handler
async def tap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id not in user_data:
        user_data[user.id] = {'balance': 0, 'referrals': 0, 'last_active': datetime.now()}
        global_stats['total_players'] += 1

    taps = random.randint(1, 10)
    user_data[user.id]['balance'] += taps
    user_data[user.id]['last_active'] = datetime.now()

    global_stats['total_balance'] += taps
    global_stats['total_touches'] += taps
    global_stats['daily_users'].add(user.id)
    global_stats['online_users'].add(user.id)

    await update.message.reply_text(
        f"{user.first_name}, you tapped the coin! Your new balance is {user_data[user.id]['balance']} OWN tokens.",
        reply_markup=main_menu_keyboard()
    )

# Balance command handler
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    balance = user_data.get(user.id, {'balance': 0})['balance']
    await update.message.reply_text(
        f"{user.first_name}, your current balance is {balance} OWN tokens.",
        reply_markup=main_menu_keyboard()
    )

# Leaderboard command handler
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global leaderboard
    leaderboard = sorted(user_data.items(), key=lambda x: x[1]['balance'], reverse=True)[:10]
    leaderboard_text = "\n".join([f"{context.bot.get_chat(uid).first_name}: {data['balance']} OWN" for uid, data in leaderboard])
    await update.message.reply_text(
        f"🏆 Leaderboard 🏆\n\n{leaderboard_text}",
        reply_markup=main_menu_keyboard()
    )

# Events command handler
async def events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Stay tuned for upcoming events! 🎉",
        reply_markup=main_menu_keyboard()
    )

# Referral command handler
async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    referral_code = f"{user.id}"
    await update.message.reply_text(
        f"Invite friends using your referral code: {referral_code}. More friends, more coins!",
        reply_markup=main_menu_keyboard()
    )

# Kross Shield registration command handler
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Register your username with the Kross Shield bot by interacting with it here: [Kross Shield Bot](https://t.me/krosscoinbot).",
        reply_markup=main_menu_keyboard()
    )

# Boost command handler
async def boost(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    boost_amount = boosts.get(user.id, 1) * 2
    boosts[user.id] = boost_amount
    await update.message.reply_text(
        f"Boost activated! Your tapping rewards are now multiplied by {boost_amount}.",
        reply_markup=main_menu_keyboard()
    )

# Stats command handler
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    current_time = datetime.now()
    global_stats['daily_users'] = {uid for uid in global_stats['daily_users'] if user_data[uid]['last_active'] >= current_time - timedelta(days=1)}
    global_stats['online_users'] = {uid for uid in global_stats['online_users'] if user_data[uid]['last_active'] >= current_time - timedelta(minutes=5)}

    total_balance = global_stats['total_balance']
    total_touches = global_stats['total_touches']
    total_players = global_stats['total_players']
    daily_users = len(global_stats['daily_users'])
    online_users = len(global_stats['online_users'])

    await update.message.reply_text(
        f"🌐 Global Stats 🌐\n\nTotal Share Balance: {total_balance} OWN\nTotal Touches: {total_touches}\nTotal Players: {total_players}\nDaily Users: {daily_users}\nOnline Players: {online_users}",
        reply_markup=main_menu_keyboard()
    )

# Main menu keyboard
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("Tap", callback_data='tap')],
        [InlineKeyboardButton("Balance", callback_data='balance')],
        [InlineKeyboardButton("Leaderboard", callback_data='leaderboard')],
        [InlineKeyboardButton("Events", callback_data='events')],
        [InlineKeyboardButton("Refer Friends", callback_data='refer')],
        [InlineKeyboardButton("Register", callback_data='register')],
        [InlineKeyboardButton("Boost", callback_data='boost')],
        [InlineKeyboardButton("Stats", callback_data='stats')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Callback query handler
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == 'tap':
        await tap(update, context)
    elif data == 'balance':
        await balance(update, context)
    elif data == 'leaderboard':
        await leaderboard(update, context)
    elif data == 'events':
        await events(update, context)
    elif data == 'refer':
        await refer(update, context)
    elif data == 'register':
        await register(update, context)
    elif data == 'boost':
        await boost(update, context)
    elif data == 'stats':
        await stats(update, context)

# Main function to start the bot
def main() -> None:
    application = Application.builder().token(TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("tap", tap))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("leaderboard", leaderboard))
    application.add_handler(CommandHandler("events", events))
    application.add_handler(CommandHandler("refer", refer))
    application.add_handler(CommandHandler("register", register))
    application.add_handler(CommandHandler("boost", boost))
    application.add_handler(CommandHandler("stats", stats))

    # Register callback query handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button))

    application.run_polling()

if __name__ == '__main__':
    main()
