from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.models import SignupRequest, LoginRequest, WithdrawRequest
from backend.database import create_user, get_user_by_username, get_user_by_id, update_user, check_and_reset_streak
from backend.utils import generate_user_id
from backend.config import FRONTEND_URL, DB_GROUP_ID
import uvicorn
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import backend.config as config

app = FastAPI()

# CORS – allow your frontend domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://sunshine-work-from-home.site.je",
        "https://www.sunshine-work-from-home.site.je",
        FRONTEND_URL,
        "https://sunshine-v2.onrender.com",
        "http://localhost:5500",
        "http://127.0.0.1:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Manual OPTIONS handler for preflight
@app.options("/{path:path}")
async def options_handler():
    return JSONResponse(
        content={},
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

# Health check
@app.get("/")
async def root():
    return {"status": "alive", "message": "Sunshine backend is running"}

# --- Bot command handlers (moved here for webhook) ---
async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.ADMIN_ID:
        await update.message.reply_text("Unauthorized.")
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /add_balance <USER_ID> <AMOUNT>")
        return
    user_id, amount = args[0], int(args[1])
    from backend.database import get_user_by_id, update_user
    user = await get_user_by_id(user_id)
    if not user:
        await update.message.reply_text("User not found.")
        return
    new_balance = int(user.get('balance', 0)) + amount
    await update_user(user_id, {'balance': new_balance})
    await update.message.reply_text(f"Balance updated. User {user_id} now has ₹{new_balance}.")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.ADMIN_ID: return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /ban <USER_ID>")
        return
    user_id = args[0]
    from backend.database import update_user
    await update_user(user_id, {'status': 'Banned'})
    await update.message.reply_text(f"User {user_id} banned.")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.ADMIN_ID: return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /unban <USER_ID>")
        return
    user_id = args[0]
    from backend.database import update_user
    await update_user(user_id, {'status': 'Active'})
    await update.message.reply_text(f"User {user_id} unbanned.")

async def reset_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.ADMIN_ID: return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /reset_password <USER_ID> <NEW_PASS>")
        return
    user_id, new_pass = args[0], args[1]
    from backend.database import update_user
    await update_user(user_id, {'password': new_pass})
    await update.message.reply_text(f"Password reset for {user_id}.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.ADMIN_ID: return
    msg = ' '.join(context.args)
    if not msg:
        await update.message.reply_text("Usage: /broadcast <MESSAGE>")
        return
    await context.bot.send_message(chat_id=config.USER_GROUP_ID, text=f"Announcement: {msg}")
    await update.message.reply_text("Broadcast sent.")

async def list_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.ADMIN_ID: return
    from backend.database import bot
    users = []
    async for msg in bot.get_chat_history(chat_id=config.DB_GROUP_ID, limit=300):
        if msg.text and "ID: " in msg.text:
            for line in msg.text.split('\n'):
                if line.startswith("ID: "):
                    users.append(line.replace("ID: ", ""))
    if users:
        await update.message.reply_text("Users:\n" + "\n".join(users))
    else:
        await update.message.reply_text("No users found.")

# --- Webhook endpoint ---
@app.post("/webhook")
async def webhook(request: Request):
    """Receive updates from Telegram via webhook."""
    try:
        data = await request.json()
        update = Update.de_json(data, app.state.bot_app.bot)
        await app.state.bot_app.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        print(f"Webhook error: {e}")
        return JSONResponse(status_code=200, content={"status": "error"})

# --- API Routes (unchanged) ---
@app.post("/signup")
async def signup(data: SignupRequest):
    existing = await get_user_by_username(data.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")
    user_id = generate_user_id()
    user_data = {
        'id': user_id,
        'username': data.username,
        'password': data.password,
        'upi': data.upi,
        'usdt': data.usdt,
        'balance': 0,
        'days': 0,
        'daily_captcha_count': 0,
        'last_active': datetime.now().isoformat(),
        'status': 'Active',
        'notes': ''
    }
    await create_user(user_data)
    return {"user_id": user_id}

@app.post("/login")
async def login(data: LoginRequest):
    user = await get_user_by_username(data.username)
    if not user or user.get('password') != data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.get('status') == 'Banned':
        raise HTTPException(status_code=403, detail="Account banned")
    return {"user_id": user['id'], "status": user['status']}

@app.get("/dashboard/{user_id}")
async def dashboard(user_id: str):
    user = await check_and_reset_streak(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user_id": user['id'],
        "username": user['username'],
        "balance": int(user.get('balance', 0)),
        "status": user.get('status', 'Active'),
        "days": int(user.get('days', 0)),
        "daily_captcha_count": int(user.get('daily_captcha_count', 0))
    }

@app.post("/solve_captcha")
async def solve_captcha(request: dict):
    user_id = request.get('user_id')
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user_id")
    user = await check_and_reset_streak(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
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
        bot_app = app.state.bot_app
        if bot_app:
            await bot_app.bot.send_message(chat_id=DB_GROUP_ID, text=f"User {user_id} completed day {days}!")
    else:
        await update_user(user_id, {
            'daily_captcha_count': daily_count,
            'balance': balance,
            'last_active': datetime.now().isoformat()
        })
    return {"success": True, "new_balance": balance, "daily_progress": daily_count, "days": days}

@app.post("/withdraw")
async def withdraw(data: WithdrawRequest):
    user = await get_user_by_id(data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    days = int(user.get('days', 0))
    if days < 21:
        raise HTTPException(status_code=400, detail="Withdrawals only after 21 days")
    notes = user.get('notes', '') + "\nWithdrawal requested."
    await update_user(data.user_id, {'notes': notes})
    bot_app = app.state.bot_app
    if bot_app:
        await bot_app.bot.send_message(chat_id=DB_GROUP_ID, text=f"WITHDRAWAL: User {data.user_id} requested ₹{user.get('balance',0)}")
    return {"status": "submitted"}

# --- Startup: Build bot and set webhook ---
@app.on_event("startup")
async def startup():
    # Build the bot application
    bot_app = Application.builder().token(config.BOT_TOKEN).build()
    
    # Add command handlers
    bot_app.add_handler(CommandHandler("add_balance", add_balance))
    bot_app.add_handler(CommandHandler("ban", ban_user))
    bot_app.add_handler(CommandHandler("unban", unban_user))
    bot_app.add_handler(CommandHandler("reset_password", reset_password))
    bot_app.add_handler(CommandHandler("broadcast", broadcast))
    bot_app.add_handler(CommandHandler("list_all", list_all))
    
    app.state.bot_app = bot_app
    
    # Initialize and start the bot
    await bot_app.initialize()
    await bot_app.start()
    
    # Delete any existing webhook and set the new one
    webhook_url = f"https://sunshine-v2.onrender.com/webhook"
    await bot_app.bot.delete_webhook(drop_pending_updates=True)
    await bot_app.bot.set_webhook(url=webhook_url)
    print(f"Webhook set to: {webhook_url}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
