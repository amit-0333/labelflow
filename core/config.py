import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()


## builds the database address
## hosting sites give one DATABASE_URL, on your laptop we build it from the DB_ parts
def get_database_url():
    url = os.getenv("DATABASE_URL")
    if url:
        ## some hosts give mysql:// but we use the pymysql driver
        if url.startswith("mysql://"):
            url = url.replace("mysql://", "mysql+pymysql://", 1)
        return url

    user = os.getenv("DB_USER")
    password = quote_plus(os.getenv("DB_PASSWORD", ""))
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    name = os.getenv("DB_NAME")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
    IS_PRODUCTION = os.getenv("APP_ENV", "development") == "production"

    SQLALCHEMY_DATABASE_URI = get_database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ## cloud MySQL closes idle connections, these two settings reconnect safely
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}

    ## reject uploads bigger than 5 MB
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024

    ## safer login cookie (secure only works on https, so only in production)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = IS_PRODUCTION