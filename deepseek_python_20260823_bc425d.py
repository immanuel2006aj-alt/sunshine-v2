import json
import os
from datetime import datetime
from typing import Optional, Dict, Any

# Path to the JSON file (stored in the backend folder)
DB_FILE = os.path.join(os.path.dirname(__file__), "users.json")

def _load_users() -> Dict[str, Dict[str, Any]]:
    """Load all users from the JSON file."""
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def _save_users(users: Dict[str, Dict[str, Any]]) -> None:
    """Save users to the JSON file."""
    try:
        with open(DB_FILE, "w") as f:
            json.dump(users, f, indent=2)
    except Exception as e:
        print(f"[DB] Save error: {e}")

async def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Find a user by username."""
    users = _load_users()
    for uid, data in users.items():
        if data.get("username") == username:
            return data
    return None

async def create_user(data: Dict[str, Any]) -> Optional[str]:
    """Create a new user and return the user_id."""
    users = _load_users()
    user_id = data.get("id")
    if not user_id:
        return None
    if user_id in users:
        return None  # already exists
    users[user_id] = data
    _save_users(users)
    return user_id

async def update_user(user_id: str, updates: Dict[str, Any]) -> bool:
    """Update an existing user."""
    users = _load_users()
    if user_id not in users:
        return False
    users[user_id].update(updates)
    _save_users(users)
    return True

async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get a user by ID."""
    users = _load_users()
    return users.get(user_id)

async def check_and_reset_streak(user_id: str) -> Optional[Dict[str, Any]]:
    """Check if the user missed a day – reset streak if needed."""
    user = await get_user_by_id(user_id)
    if not user:
        return None
    last_active_str = user.get("last_active")
    if last_active_str:
        try:
            last_active = datetime.fromisoformat(last_active_str)
            today = datetime.now().date()
            if last_active.date() < today:
                # missed a day – reset streak
                user["days"] = 0
                user["daily_captcha_count"] = 0
                user["last_active"] = datetime.now().isoformat()
                await update_user(user_id, user)
                user = await get_user_by_id(user_id)
        except:
            pass
    return user