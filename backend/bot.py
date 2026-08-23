from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from backend.config import ADMIN_ID, GROUP_ID
from backend.database import get_user_by_id, update_user

async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Unauthorized.")
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /add_balance <USER_ID> <AMOUNT>")
        return
    user_id, amount = args[0], int(args[1])
    user = await get_user_by_id(user_id)
    if not user:
        await update.message.reply_text("User not found.")
        return
    new_balance = int(user.get('balance', 0)) + amount
    await update_user(user_id, {'balance': new_balance})
    await update.message.reply_text(f"Balance updated. User {user_id} now has ₹{new_balance}.")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /ban <USER_ID>")
        return
    user_id = args[0]
    await update_user(user_id, {'status': 'Banned'})
    await update.message.reply_text(f"User {user_id} banned.")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /unban <USER_ID>")
        return
    user_id = args[0]
    await update_user(user_id, {'status': 'Active'})
    await update.message.reply_text(f"User {user_id} unbanned.")

async def reset_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /reset_password <USER_ID> <NEW_PASS>")
        return
    user_id, new_pass = args[0], args[1]
    await update_user(user_id, {'password': new_pass})
    await update.message.reply_text(f"Password reset for {user_id}.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    msg = ' '.join(context.args)
    if not msg:
        await update.message.reply_text("Usage: /broadcast <MESSAGE>")
        return
    await context.bot.send_message(chat_id=GROUP_ID, text=f"📢 {msg}")
    await update.message.reply_text("Broadcast sent to the group.")

async def list_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    from backend.database import _load_users
    users = _load_users()
    if users:
        user_list = "\n".join([f"{uid}: {u.get('username')}" for uid, u in users.items()])
        await update.message.reply_text(f"Users:\n{user_list}")
    else:
        await update.message.reply_text("No users found.")

def setup_handlers(app):
    app.add_handler(CommandHandler("add_balance", add_balance))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("unban", unban_user))
    app.add_handler(CommandHandler("reset_password", reset_password))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("list_all", list_all))
