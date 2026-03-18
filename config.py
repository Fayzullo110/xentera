import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv('640746951:AAHQO0stCvKdRP2wr4WalT4N4SegRmwTO_0')
    BOT_NAME = "Xentera"

    ACRCLOUD_HOST = os.getenv('identify-xxx.acrcloud.com')
    ACRCLOUD_ACCESS_KEY = os.getenv('a18019d047c6910b77d458059fc67d59')
    ACRCLOUD_ACCESS_SECRET = os.getenv('MsVEtvMLBEx1nzDm4UqS4kb4lThgAj22NKfJYsMk')
    
    @classmethod
    def validate(cls):
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set")
