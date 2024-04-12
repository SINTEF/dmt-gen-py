

def to_safe_string(value: str|None)-> str:
    """Converts a string to a safe string"""
    return value if value else ""
