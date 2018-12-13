import input_helper as ih
import settings_helper as sh
import fs_helper as fh
from redis import StrictRedis


__doc__ = """Create an instance of `redis_helper.Collection` and use it

import redis_helper as rh
model = rh.Collection(...)
"""


logger = fh.get_logger(__name__)
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
