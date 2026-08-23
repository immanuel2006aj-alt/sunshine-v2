import random

def generate_user_id():
    return str(random.randint(100000, 999999))

def parse_user_message(text):
    # Not needed for JSON DB, but kept for compatibility
    return {}

def format_user_message(data):
    # Not needed for JSON DB, but kept for compatibility
    return ""
