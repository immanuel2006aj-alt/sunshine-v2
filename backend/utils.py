import random

def generate_user_id():
    return str(random.randint(100000, 999999))

def parse_user_message(text):
    lines = text.strip().split('\n')
    data = {}
    for line in lines:
        if ': ' in line:
            key, val = line.split(': ', 1)
            data[key.lower().replace(' ', '_')] = val
    return data

def format_user_message(data):
    lines = [
        f"ID: {data.get('id', '')}",
        f"Username: {data.get('username', '')}",
        f"Password: {data.get('password', '')}",
        f"UPI: {data.get('upi', '')}",
        f"USDT: {data.get('usdt', '')}",
        f"Balance: ₹{data.get('balance', 0)}",
        f"Days Active: {data.get('days', 0)}",
        f"Daily Captcha: {data.get('daily_captcha_count', 0)}",
        f"Last Active: {data.get('last_active', '')}",
        f"Status: {data.get('status', 'Active')}",
        f"Notes: {data.get('notes', '')}",
    ]
    return '\n'.join(lines)
