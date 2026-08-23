from datetime import datetime
from telegram import Bot
from backend.config import BOT_TOKEN, DB_GROUP_ID
from backend.utils import parse_user_message, format_user_message

bot = Bot(token=BOT_TOKEN)

async def get_user_by_username(username):
    try:
        async for msg in bot.get_chat_history(chat_id=DB_GROUP_ID, limit=300):
            if msg.text and f"Username: {username}" in msg.text:
                data = parse_user_message(msg.text)
                data['message_id'] = msg.message_id
                return data
        return None
    except Exception as e:
        print(f"get_user_by_username error: {e}")
        return None

async def create_user(data):
    try:
        text = format_user_message(data)
        msg = await bot.send_message(chat_id=DB_GROUP_ID, text=text)
        return msg.message_id
    except Exception as e:
        print(f"create_user error: {e}")
        return None

async def update_user(user_id, updates):
    try:
        async for msg in bot.get_chat_history(chat_id=DB_GROUP_ID, limit=300):
            if msg.text and f"ID: {user_id}" in msg.text:
                data = parse_user_message(msg.text)
                data.update(updates)
                new_text = format_user_message(data)
                await bot.edit_message_text(chat_id=DB_GROUP_ID, message_id=msg.message_id, text=new_text)
                return True
        return False
    except Exception as e:
        print(f"update_user error: {e}")
        return False

async def get_user_by_id(user_id):
    try:
        async for msg in bot.get_chat_history(chat_id=DB_GROUP_ID, limit=300):
            if msg.text and f"ID: {user_id}" in msg.text:
                data = parse_user_message(msg.text)
                data['message_id'] = msg.message_id
                return data
        return None
    except Exception as e:
        print(f"get_user_by_id error: {e}")
        return None

async def check_and_reset_streak(user_id):
    try:
        user = await get_user_by_id(user_id)
        if not user:
            return None
        last_active_str = user.get('last_active', '')
        if last_active_str:
            try:
                last_active = datetime.fromisoformat(last_active_str)
                today = datetime.now().date()
                if last_active.date() < today:
                    await update_user(user_id, {
                        'days': 0,
                        'daily_captcha_count': 0,
                        'last_active': datetime.now().isoformat()
                    })
                    user = await get_user_by_id(user_id)
            except:
                pass
        return user
    except Exception as e:
        print(f"check_and_reset_streak error: {e}")
        return None
