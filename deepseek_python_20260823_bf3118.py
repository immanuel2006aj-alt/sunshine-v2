from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.models import SignupRequest, LoginRequest, WithdrawRequest
from backend.database import create_user, get_user_by_username, get_user_by_id, update_user, check_and_reset_streak
from backend.utils import generate_user_id
from backend.config import FRONTEND_URL, DB_GROUP_ID
import uvicorn
import threading
from datetime import datetime
from telegram.ext import Application
from backend.bot import setup_handlers
import backend.config as config

app = FastAPI()

# CORS – allow your frontend domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL,
        "https://sunshine-work-from-home.site.je",
        "https://sunshine-v2.onrender.com",
        "http://localhost:5500",
        "http://127.0.0.1:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.on_event("startup")
async def startup():
    # Build the bot application
    bot_app = Application.builder().token(config.BOT_TOKEN).build()
    setup_handlers(bot_app)
    app.state.bot_app = bot_app

    # Run the bot in a separate thread (blocking call)
    def run_bot():
        bot_app.run_polling()
    
    thread = threading.Thread(target=run_bot, daemon=True)
    thread.start()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)