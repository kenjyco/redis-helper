import os.path
import logging
import input_helper as ih
import settings_helper as sh
from redis import StrictRedis


__doc__ = """Create an instance of `redis_helper.Collection` and use it

import redis_helper as rh
model = rh.Collection(...)
"""


LOGFILE = os.path.abspath('log--redis-helper.log')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(LOGFILE, mode='a')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(funcName)s: %(message)s'
))
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s: %(message)s'))
logger.addHandler(file_handler)
logger.addHandler(console_handler)


get_setting = sh.settings_getter(__name__)


def zshow(key, start=0, end=-1, desc=True, withscores=True):
    """Wrapper to REDIS.zrange"""
    return REDIS.zrange(key, start, end, withscores=withscores, desc=desc)


def identity(x):
    """Return x, unmodified"""
    return x


REDIS_URL = get_setting('redis_url')
REDIS = StrictRedis.from_url(REDIS_URL) if REDIS_URL is not '' else None
from .collection import Collection
