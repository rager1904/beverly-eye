import os
url = os.environ.get("DATABASE_URL", "NOT SET")
print(f"DATABASE_URL={repr(url)}")
