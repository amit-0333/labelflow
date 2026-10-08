import os
from dotenv import load_dotenv

load_dotenv()  # reads the .env file


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"