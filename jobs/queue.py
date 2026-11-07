import redis
from rq import Queue
from core.config import Config

## one connection and one queue, shared by the whole app
redis_conn = redis.from_url(Config.REDIS_URL)
queue = Queue("default", connection=redis_conn)