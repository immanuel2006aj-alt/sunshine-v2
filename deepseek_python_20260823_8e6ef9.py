from datetime import datetime
from telegram import Bot
from backend.config import BOT_TOKEN, DB_GROUP_ID
from backend.utils import parse_user_message, format_user_message

# Initialize Telegram Bot
bot = Bot(token=BOT_TOKEN)

async def get_user_by_username(username):
    """
    Find a user by username in the DB group.
    Returns user data dict or None if not found / error.
    """
    try:
        async for msg in bot.get_chat_history(chat_id=DB_GROUP_ID, limit=300):
            if msg.text and f"Username: {username}" in msg.text:
                data = parse_user_message(msg.text)
                if data:
                    data['message_id'] = msg.message_id
                    return data
        return None
    except Exception as e:
        print(f"[DB] get_user_by_username error: {e}")
        return None

async def create_user(data):
    """
    Create a new user message in the DB group.
    Returns message_id on success, None on failure.
    """
    try:
        text = format_user_message(data)
        msg = await bot.send_message(chat_id=DB_GROUP_ID, text=text)
        return msg.message_id
    except Exception as e:
        print(f"[DB] create_user error: {e}")
        return None

async def update_user(user_id, updates):
    """
    Update an existing user's data in the DB group.
    Returns True on success, False on failure.
    """
    try:
        async for msg in bot.get_chat_history(chat_id=DB_GROUP_ID, limit=300):
            if msg.text and f"ID: {user_id}" in msg.text:
                data = parse_user_message(msg.text)
                if data is None:
                    data = {}
                data.update(updates)
                new_text = format_user_message(data)
                await bot.edit_message_text(
                    chat_id=DB_GROUP_ID,
                    message_id=msg.message_id,
                    text=new_text
                )
                return True
        return False
    except Exception as e:
        print(f"[DB] update_user error for {user_id}: {e}")
        return False

async def get_user_by_id(user_id):
    """
    Fetch a user by their unique ID.
    Returns user data dict or None if not found / error.
    """
    try:
        async for msg in bot.get_chat_history(chat_id=DB_GROUP_ID, limit=300):
            if msg.text and f"ID: {user_id}" in msg.text:
                data = parse_user_message(msg.text)
                if data:
                    data['message_id'] = msg.message_id
                    return data
        return None
    except Exception as e:
        print(f"[DB] get_user_by_id error for {user_id}: {e}")
        return None

async def check_and_reset_streak(user_id):
    """
    Check if the user missed a day – if so, reset streak.
    Returns the updated user data dict, or None if user not found.
    """
    try:
        user = await get_user_by_id(user_id)
        if not user:
            return None

        last_active_str = user.get('last_active', '')
        if last_active_str:
            try:
                last_active = datetime.fromisoformat(last_active_str)
                today = datetime.now().date()
                # If last active is before today, they missed a day
                if last_active.date() < today:
                    await update_user(user_id, {
                        'days': 0,
                        'daily_captcha_count': 0,
                        'last_active': datetime.now().isoformat()
                    })
                    # Refresh user data after reset
                    user = await get_user_by_id(user_id)
            except Exception as e:
                print(f"[DB] streak reset parsing error: {e}")
                # If date parsing fails, we don't reset
                pass
        return user
    except Exception as e:
        print(f"[DB] check_and_reset_streak error for {user_id}: {e}")
        return None