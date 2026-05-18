import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
OWNER_ID: int = int(os.getenv("OWNER_ID", "0"))
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "learning.db")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
