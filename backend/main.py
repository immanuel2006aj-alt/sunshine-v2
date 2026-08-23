from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.models import SignupRequest, LoginRequest, WithdrawRequest
from backend.database import create_user, get_user_by_username, get_user_by_id, update_user, check_and_reset_streak
from backend.utils import generate_user_id
from backend.config import FRONTEND_URL, ADMIN_ID, BOT_TOKEN
import uvicorn
from datetime import datetime
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
import backend.config as config

# Conversation states
BAN_ID, UNBAN_ID, BALANCE_ID, BALANCE_AMOUNT, RESET_ID, RESET_PASS = range(6)

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers={"Access-Control-Allow-Origin": "*"}
    )

@app.get("/")
async def root():
    return {"status": "alive", "message": "Sunshine backend running"}

# --- Helper check for admin ---
def is_admin(update: Update) -> bool:
    return update.effective_user.id == ADMIN_ID

# --- Conversation Handlers ---

# 1. BAN
async def ban_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Unauthorized.")
        return ConversationHandler.END
    await update.message.reply_text("👤 Send me the User ID to ban.")
    return BAN_ID

async def ban_get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.text.strip()
    user = await get_user_by_id(user_id)
    if not user:
        await update.message.reply_text("❌ User not found.")
        return ConversationHandler.END
    await update_user(user_id, {'status': 'Banned'})
    await update.message.reply_text(f"✅ User {user_id} banned successfully.")
    return ConversationHandler.END

# 2. UNBAN
async def unban_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Unauthorized.")
        return ConversationHandler.END
    await update.message.reply_text("👤 Send me the User ID to unban.")
    return UNBAN_ID

async def unban_get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.text.strip()
    user = await get_user_by_id(user_id)
    if not user:
        await update.message.reply_text("❌ User not found.")
        return ConversationHandler.END
    await update_user(user_id, {'status': 'Active'})
    await update.message.reply_text(f"✅ User {user_id} unbanned successfully.")
    return ConversationHandler.END

# 3. ADD BALANCE
async def balance_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Unauthorized.")
        return ConversationHandler.END
    await update.message.reply_text("👤 Send me the User ID to add balance.")
    return BALANCE_ID

async def balance_get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.text.strip()
    user = await get_user_by_id(user_id)
    if not user:
        await update.message.reply_text("❌ User not found.")
        return ConversationHandler.END
    context.user_data['target_id'] = user_id
    await update.message.reply_text("💰 Send me the amount (in ₹) to add.")
    return BALANCE_AMOUNT

async def balance_get_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = int(update.message.text.strip())
        user_id = context.user_data.get('target_id')
        user = await get_user_by_id(user_id)
        if not user:
            await update.message.reply_text("❌ User not found.")
            return ConversationHandler.END
        new_balance = int(user.get('balance', 0)) + amount
        await update_user(user_id, {'balance': new_balance})
        await update.message.reply_text(f"✅ Added ₹{amount} to user {user_id}. New balance: ₹{new_balance}.")
    except ValueError:
        await update.message.reply_text("❌ Please send a valid number.")
        return BALANCE_AMOUNT
    return ConversationHandler.END

# 4. RESET PASSWORD
async def reset_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Unauthorized.")
        return ConversationHandler.END
    await update.message.reply_text("👤 Send me the User ID to reset password.")
    return RESET_ID

async def reset_get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.text.strip()
    user = await get_user_by_id(user_id)
    if not user:
        await update.message.reply_text("❌ User not found.")
        return ConversationHandler.END
    context.user_data['reset_id'] = user_id
    await update.message.reply_text("🔑 Send me the new password.")
    return RESET_PASS

async def reset_get_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_pass = update.message.text.strip()
    user_id = context.user_data.get('reset_id')
    await update_user(user_id, {'password': new_pass})
    await update.message.reply_text(f"✅ Password reset for user {user_id}.")
    return ConversationHandler.END

# 5. CANCEL
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Operation cancelled.")
    return ConversationHandler.END

# 6. START & HELP
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    await update.message.reply_text(
        "🤖 Sunshine Admin Bot\n"
        "Send /help to see all commands."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private" or update.effective_user.id != ADMIN_ID:
        return
    help_text = (
        "📋 *Available Interactive Commands:*\n\n"
        "/ban - Ban a user (bot will ask for ID)\n"
        "/unban - Unban a user (bot will ask for ID)\n"
        "/add_balance - Add money to a user (bot will ask for ID and amount)\n"
        "/reset_password - Reset user password (bot will ask for ID and new pass)\n"
        "/list_all - List all registered users\n"
        "/cancel - Cancel any ongoing operation\n"
        "/help - Show this message"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def list_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private" or update.effective_user.id != ADMIN_ID:
        return
    from backend.database import _load_users
    users = _load_users()
    if users:
        user_list = "\n".join([f"{uid}: {u.get('username')}" for uid, u in users.items()])
        await update.message.reply_text(f"📋 Users:\n{user_list}")
    else:
        await update.message.reply_text("No users found.")

# --- Webhook endpoint ---
@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, app.state.bot_app.bot)
        await app.state.bot_app.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        print(f"Webhook error: {e}")
        return JSONResponse(status_code=200, content={"status": "error"})

# --- API Routes ---
@app.post("/signup")
async def signup(data: SignupRequest):
    try:
        existing = await get_user_by_username(data.username)
        if existing:
            raise HTTPException(status_code=400, detail="Username already taken")
        user_id = generate_user_id()
        user_data = {
            'id': user_id,
            'username': data.username,
            'password': data.password,
            'upi': data.upi,
            'email': data.email,
            'usdt': data.usdt,
            'balance': 0,
            'days': 0,
            'daily_captcha_count': 0,
            'last_active': datetime.now().isoformat(),
            'status': 'Active',
            'notes': ''
        }
        await create_user(user_data)
        try:
            bot = Bot(token=config.BOT_TOKEN)
            await bot.send_message(chat_id=ADMIN_ID, text=f"NEW USER: {user_id} ({data.username})")
        except:
            pass
        return {"user_id": user_id}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Signup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/login")
async def login(data: LoginRequest):
    try:
        user = await get_user_by_username(data.username)
        if not user or user.get('password') != data.password:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if user.get('status') == 'Banned':
            raise HTTPException(status_code=403, detail="Account banned")
        return {"user_id": user['id'], "status": user['status']}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard/{user_id}")
async def dashboard(user_id: str):
    try:
        user = await check_and_reset_streak(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "user_id": user.get('id', user_id),
            "username": user.get('username', 'Unknown'),
            "balance": int(user.get('balance', 0)),
            "status": user.get('status', 'Active'),
            "days": int(user.get('days', 0)),
            "daily_captcha_count": int(user.get('daily_captcha_count', 0))
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Dashboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/solve_captcha")
async def solve_captcha(request: dict):
    try:
        user_id = request.get('user_id')
        if not user_id:
            raise HTTPException(status_code=400, detail="Missing user_id")
        user = await check_and_reset_streak(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.get('status') == 'Banned':
            raise HTTPException(status_code=403, detail="Account banned")
        daily_count = int(user.get('daily_captcha_count', 0))
        days = int(user.get('days', 0))
        balance = int(user.get('balance', 0))
        quota = 262
        daily_count += 1
        balance += 1
        if daily_count >= quota:
            days += 1
            daily_count = 0
            await update_user(user_id, {
                'daily_captcha_count': daily_count,
                'days': days,
                'balance': balance,
                'last_active': datetime.now().isoformat()
            })
            try:
                bot = Bot(token=config.BOT_TOKEN)
                await bot.send_message(chat_id=ADMIN_ID, text=f"User {user_id} completed day {days}!")
            except:
                pass
        else:
            await update_user(user_id, {
                'daily_captcha_count': daily_count,
                'balance': balance,
                'last_active': datetime.now().isoformat()
            })
        return {"success": True, "new_balance": balance, "daily_progress": daily_count, "days": days}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Captcha error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/withdraw")
async def withdraw(data: WithdrawRequest):
    try:
        user = await get_user_by_id(data.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.get('status') == 'Banned':
            raise HTTPException(status_code=403, detail="Account banned")
        days = int(user.get('days', 0))
        if days < 21:
            raise HTTPException(status_code=400, detail="Withdrawals only after 21 days")
        notes = user.get('notes', '') + "\nWithdrawal requested."
        await update_user(data.user_id, {'notes': notes})
        try:
            bot = Bot(token=config.BOT_TOKEN)
            await bot.send_message(chat_id=ADMIN_ID, text=f"WITHDRAWAL: User {data.user_id} requested ₹{user.get('balance',0)}")
        except:
            pass
        return {"status": "submitted"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Withdraw error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Startup: build bot and set webhook ---
@app.on_event("startup")
async def startup():
    bot_app = Application.builder().token(config.BOT_TOKEN).build()

    # Conversation handlers
    conv_ban = ConversationHandler(
        entry_points=[CommandHandler("ban", ban_start)],
        states={BAN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, ban_get_id)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    conv_unban = ConversationHandler(
        entry_points=[CommandHandler("unban", unban_start)],
        states={UNBAN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, unban_get_id)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    conv_balance = ConversationHandler(
        entry_points=[CommandHandler("add_balance", balance_start)],
        states={
            BALANCE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, balance_get_id)],
            BALANCE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, balance_get_amount)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    conv_reset = ConversationHandler(
        entry_points=[CommandHandler("reset_password", reset_start)],
        states={
            RESET_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, reset_get_id)],
            RESET_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, reset_get_pass)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("help", help_command))
    bot_app.add_handler(conv_ban)
    bot_app.add_handler(conv_unban)
    bot_app.add_handler(conv_balance)
    bot_app.add_handler(conv_reset)
    bot_app.add_handler(CommandHandler("list_all", list_all))

    app.state.bot_app = bot_app
    await bot_app.initialize()
    await bot_app.start()
    webhook_url = f"https://sunshine-v2.onrender.com/webhook"
    await bot_app.bot.delete_webhook(drop_pending_updates=True)
    await bot_app.bot.set_webhook(url=webhook_url)
    print(f"Webhook set to: {webhook_url}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
