import sys
try:
    import bot
    print("SUCCESS")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
