import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    BOT_NAME = "Xentera"

    ACRCLOUD_HOST = os.getenv('ACRCLOUD_HOST')
    ACRCLOUD_ACCESS_KEY = os.getenv('ACRCLOUD_ACCESS_KEY')
    ACRCLOUD_ACCESS_SECRET = os.getenv('ACRCLOUD_ACCESS_SECRET')
    
    @classmethod
    def validate(cls):
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set")
