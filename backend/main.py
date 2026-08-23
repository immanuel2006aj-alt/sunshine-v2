from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.models import SignupRequest, LoginRequest, WithdrawRequest
from backend.database import create_user, get_user_by_username, get_user_by_id, update_user, check_and_reset_streak
from backend.utils import generate_user_id
from backend.config import FRONTEND_URL, GROUP_ID, BOT_TOKEN
import uvicorn
import threading
import asyncio
from datetime import datetime
from telegram import Bot
from telegram.ext import Application
from backend.bot import setup_handlers
import backend.config as config

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
            await bot.send_message(chat_id=config.GROUP_ID, text=f"NEW USER: {user_id} ({data.username})")
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
                await bot.send_message(chat_id=config.GROUP_ID, text=f"User {user_id} completed day {days}!")
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
        days = int(user.get('days', 0))
        if days < 21:
            raise HTTPException(status_code=400, detail="Withdrawals only after 21 days")
        notes = user.get('notes', '') + "\nWithdrawal requested."
        await update_user(data.user_id, {'notes': notes})
        try:
            bot = Bot(token=config.BOT_TOKEN)
            await bot.send_message(chat_id=config.GROUP_ID, text=f"WITHDRAWAL: User {data.user_id} requested ₹{user.get('balance',0)}")
        except:
            pass
        return {"status": "submitted"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Withdraw error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Bot polling in background ---
def start_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        bot_app = Application.builder().token(config.BOT_TOKEN).build()
        setup_handlers(bot_app)
        # Delete any existing webhook to ensure polling works
        loop.run_until_complete(bot_app.bot.delete_webhook(drop_pending_updates=True))
        print("Webhook cleared. Starting polling...")
        bot_app.run_polling(drop_pending_updates=True)
    except Exception as e:
        print(f"Bot thread error: {e}")
        while True:
            import time
            time.sleep(60)

@app.on_event("startup")
async def startup():
    thread = threading.Thread(target=start_bot, daemon=True)
    thread.start()
    print("Bot polling started in background.")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
